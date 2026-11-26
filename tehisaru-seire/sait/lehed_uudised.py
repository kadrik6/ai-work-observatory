"""Uudised, Hanked ja Töö publikatsioonid (Kadri 5.11.2026 23:17: need olid uuelt saidilt puudu).

Andmed tulevad Kadri loal projekti kaustast toodud avalikust hetkeseisust (sait/vota_kaasa.py):
sisu/uudised.jsonl, sisu/uudiste-vaited.json, sisu/uudiste-olek.json, sisu/hanked-leht.json, sisu/publikatsioonid.json.
Iga pealkirja number tuleb andmetest; pealkirjad, mida mall ei kata, kontrollitakse abi.kontrolli() abil.
"""
import collections
import datetime
import re

from abi import ARVSONAD, SEESTYTLEV, a, kontrolli, link, jaga, pea, seotud, sonaga
from andmekiht import AndmeViga
from komponendid import e, faktid, kp, pr, tbl_div
import json as _json
from pathlib import Path as _Path

import lae_logod

HANKED_URL = "https://riigihanked.riik.ee/"
OPENALEX_URL = "https://openalex.org/"
OECD_URL = "https://doi.org/10.1787/c2c09a06-en"

LIIK = {"uudis": ("uudis", "vaikne"), "aruanne": ("aruanne", ""), "uuring": ("uuring", ""),
        "arvamus": ("arvamus", "arv"), "eksitav": ("eksitav", "risk")}
# Teemafilter (Kadri 11.11.2026): „strateegia“ kuulub riigi alla, „tehisaru“ (ai_uldine) ja „andmed“ on teemana „muu“,
# sest tehisaru ja andmed on nüüd eraldi valdkonnafilter. Tundmatu teema läheb „muu“ alla, et uus liik ei jääks filtrita.
# Koondamine on teema „töö“ all (Kadri 11.11.2026: „võta koondamine siit ära, see info peaks koonduma töö alla“).
# Koondamisuudisel jääb alles tehisaru rolli märk, nii et töö all on koondamine endiselt äratuntav.
TEEMA = {"too": "töö", "riik": "riik", "uuring": "uuring", "muu": "muu", "eksitav": "eksitav"}
TEEMA_FILTER = {"ai_too": "too", "koondamine": "too", "riik": "riik", "strateegia": "riik", "uuring": "uuring",
                "ai_uldine": "muu", "andmed": "muu", "eksitav": "eksitav"}
# Valdkonna filtrit pole (Kadri 12.11.2026: „võta valdkondade filter maha, nagunii kõik tehisaruga seonduv“).
# Täpsemad teemad (Kadri 12.11.2026: „teemadesse äkki annab midagi täpsemat juurde lisada“) on läbivad: üks uudis võib olla
# korraga nt „töö“ ja „noored“. Need tulevad märksõnadest (masinmärgistus), nupu title ütleb seda.
ALAMTEEMA = {
    "noored": ("noored", re.compile(r"\bnoor|young|youth|first job|esimes\w* töö|job seekers|graduate|lõpetaja|entry-level", re.I), True),
    "oskused": ("oskused ja koolitus", re.compile(r"oskus|koolitus|õpitegevus|\bskill|training|reskill|upskill|haridus|education|coding school", re.I), False),
    "agendid": ("AI-agendid", re.compile(r"\bagent|agendi|kratt|krati|\bMCP\b|AI-isikukood", re.I), True),
}

TITLE_ALAM = ' title="Täpsem teema märksõnade järgi; uudis võib olla mitme teema all"'


def alamteemad(r):
    """Läbivad täpsemad teemad: pealkirjast; noored ja agendid ka kokkuvõttest (oskused ainult pealkirjast, muidu liiga lai)."""
    pk, kogu = r.get("pealkiri", ""), f'{r.get("pealkiri", "")} {r.get("pohjus", "")} {r.get("arv_tekst", "")}'
    return [k for k, (_, m, laiem) in ALAMTEEMA.items() if m.search(kogu if laiem else pk)]


# Teema „riik“ (TOOELU kogumine alates 9.11.2026): riigi otsused, eelnõud, hanked, tähtajad, üritused ja aruanded
RIIGI_LIIK = {"otsus": "otsus", "eelnõu": "eelnõu", "hange": "hange", "tähtaeg": "tähtaeg", "üritus": "üritus", "aruanne": "aruanne"}
ROLL = {"otsene": "tehisaru otsene põhjus", "osaline": "tehisaru üks põhjus", "kaudne": "tehisaru kaudselt",
        "tulevikus": "tehisaru võib tulevikus",
        "ei_pohjus": "tehisaru pole põhjus", "ei_mainita": "tehisaru ei mainita", "statistika": "statistika"}
HINNANG = {"tosi": ("peab paika", "ok"), "osaliselt": ("osaliselt", "warn"), "vale": ("vale", "risk"),
           "eksitav": ("eksitav", "risk"), "kontrollimata": ("kontrollimata", "warn")}


def _vaja(A, voti, fail):
    if A.get(voti) is None:
        raise AndmeViga(f"Vaade vajab faili sait/sisu/{fail} (tuuakse Kadri loal: python3 sait/vota_kaasa.py)")
    return A[voti]


def _arv(n):
    return f"{n:,}".replace(",", " ")


def _eur(v):
    if v is None:
        return "—"
    if v >= 1e6:
        return f"{pr(v / 1e6)} mln €"
    return f"{_arv(int(round(v / 1000)))} tuh €"


# ---------------------------------------------------------------- Uudised

# Allika logo (Kadri 11.11.2026): logo uudise kõrval, nimi hõljudes. Logod laeb sait/lae_logod.py (GitHub Actions).
_LOGO_NIMEKIRI = _Path(__file__).resolve().parent / "pilt" / "logod" / "logod.json"
LOGOD = _json.loads(_LOGO_NIMEKIRI.read_text(encoding="utf-8")) if _LOGO_NIMEKIRI.exists() else {}


def _allikas(r):
    fail = lae_logod.logo_fail(LOGOD, r["url"])
    if not fail:
        return f'<span class="u-a">{e(r["allikas"])}</span>'
    return (f'<span class="u-a u-logo" title="{e(r["allikas"])}">'
            f'<img src="pilt/logod/{e(fail)}" alt="{e(r["allikas"])}" width="18" height="18" loading="lazy"></span>')


def _uudis(r, peida="", kuup=None):
    """kuup: mis kuupäev rea ees on (vaikimisi avaldamise päev; tulevaste ürituste loendis tähtaeg)."""
    liik, kl = LIIK.get(r.get("liik"), (r.get("liik", ""), ""))
    if r.get("liik") not in LIIK:
        raise AndmeViga(f"uudised.jsonl: tundmatu liik {r.get('liik')!r} ({r.get('pealkiri', '')[:40]})")
    if not r.get("url"):
        raise AndmeViga(f"uudised.jsonl: uudisel puudub link ({r.get('pealkiri', '')[:40]})")
    sildid = [f'<span class="u-l {kl}">{e(liik)}</span>']
    # Teema silti pole: teema on paneeli filtris (Kadri 7.11.2026: vähem märke ühel real)
    if r.get("teema") == "koondamine" and r.get("ai_roll") in ROLL:
        sildid.append(f'<span class="u-t{" s" if r["ai_roll"] in ("otsene", "osaline") else ""}">{e(ROLL[r["ai_roll"]])}</span>')
    # „Jätkulugu:“ on märgina, mitte kaks korda tekstis (Kadri 7.11.2026: teksti on liiga palju)
    import re as _re
    eesliide = _re.compile(r"^\s*jätkulugu:\s*", _re.I)
    arv_t, pohjus = r.get("arv_tekst") or "", r.get("pohjus", "")
    jatk = bool(r.get("_jatk") or eesliide.match(arv_t) or eesliide.match(pohjus))
    arv_t, pohjus = eesliide.sub("", arv_t), eesliide.sub("", pohjus)
    arv_t, pohjus = arv_t[:1].upper() + arv_t[1:], pohjus[:1].upper() + pohjus[1:]
    if r.get("teema") == "riik":
        if r.get("riigi_liik") and r["riigi_liik"] not in RIIGI_LIIK:
            raise AndmeViga(f"uudised.jsonl: tundmatu riigi_liik {r.get('riigi_liik')!r} ({r.get('pealkiri', '')[:40]})")
        if r.get("riigi_liik"):
            sildid.append(f'<span class="u-t">{e(RIIGI_LIIK[r["riigi_liik"]])}</span>')
        if r.get("tahtaeg"):
            sildid.append(f'<span class="u-t s">tähtaeg {e(kp(r["tahtaeg"]))}</span>')
    if jatk:
        sildid.append('<span class="u-t">jätkulugu</span>')
    if r.get("suur"):
        sildid.append('<span class="u-l suur">suur uudis</span>')
    lv = r.get("levik")
    if lv and isinstance(lv.get("arv"), int) and lv["arv"] > 1:
        # Populaarsus = mitu väljaannet sama lugu kajastas (klikke väljaanded ei avalda; Kadri 6.11.2026)
        kellelt = ", ".join(lv.get("allikad") or [])
        sildid.append(f'<span class="u-t lv" title="Kajastasid: {e(kellelt)} (kontrollitud {e(kp(lv.get("kontrollitud", "")) if lv.get("kontrollitud") else "")})">{lv["arv"]} väljaannet</span>')
    if not r.get("kontrollitud"):
        sildid.append('<span class="u-t">loetud ainult pealkiri</span>')
    arv = f'<b>{e(arv_t)}.</b> ' if arv_t else ""
    alam = " ".join(alamteemad(r))
    alam = ' data-alam="' + alam + '"' if alam else ""
    return (f'<li data-teema="{e(TEEMA_FILTER.get(r.get("teema"), "muu"))}"{alam} data-liik="{e(r["liik"])}"{peida}>'
            f'<span class="d">{kuup or kp(r["kuupaev"])}</span>'
            f'<div><a href="{e(r["url"])}">{e(r["pealkiri"])}</a>'
            f'<p class="u-k">{arv}{e(pohjus)}</p>'
            f'<p class="u-m">{"".join(sildid)}{_allikas(r)}</p></div></li>')


# „Uus“-märki uudistel pole (Kadri 11.11.2026: „nobody does that“). Värskust näitab ajajoon: uusim päev on üleval ja
# sinine, „täna“ ja „eile“ arvutab brauser lugeja kuupäeva järgi (sait.js), nii et silt ei vanane staatilisel lehel.
PAEVI = 14  # nii mitu päeva näidatakse ajajoonel eraldi; vanemad uudised on kuu kaupa


def _seis(read, kontroll):
    """Kas viimasel kontrollil lisandus selle piirkonna uudiseid (Kadri 6.11: tühi päev ei tohi paista nagu katkine leht)."""
    if not kontroll:
        return ""
    paev = kontroll[:10]
    uued = sum(1 for r in read if r.get("lisatud") == paev)
    if uued:
        return f'<p class="ps u-seis">Viimane kontroll {kp(paev)} kell {kontroll[11:16]}. Sel päeval lisandus <b>{uued}</b> {"uudis" if uued == 1 else "uudist"}.</p>'
    return f'<p class="ps u-seis">Viimane kontroll {kp(paev)} kell {kontroll[11:16]}. Sel päeval uusi uudiseid ei lisandunud.</p>'


# Filtrinuppude kindel järjekord (Kadri 11.11.2026: koondamised olid liiga suure fookuse all, kuigi neid uudiseid on harva).
# Koondamisel pole enam oma nuppu, see on töö all.
TEEMA_JARJEKORD = ("too", "riik", "uuring", "muu", "eksitav")
assert set(TEEMA_JARJEKORD) == set(TEEMA) == set(TEEMA_FILTER.values())
# Nuppude järjekord: põhiteema ja selle täpsem teema kõrvuti
NUPPUDE_JARJEKORD = ("too", "noored", "oskused", "riik", "agendid", "uuring", "muu", "eksitav")


KUUL = ("jaan", "veebr", "märts", "apr", "mai", "juuni", "juuli", "aug", "sept", "okt", "nov", "dets")
NADALAPAEV = ("esmaspäev", "teisipäev", "kolmapäev", "neljapäev", "reede", "laupäev", "pühapäev")


def _paevad(read, nahtav, kontroll):
    """Ajajoon (Kadri 11.11.2026 valis katsetest D1, kompaktsena): viimased PAEVI päeva päevade kaupa, vanemad kuu kaupa.

    nahtav: kas rida on vaikimisi näha (valdkonna filter). Päev, kus vaikimisi ühtki rida pole, on alguses peidus;
    sait.js peidab ja näitab päevi filtri järgi ning märgib uusima nähtava päeva."""
    if not read:
        return ""
    alg = datetime.date.fromisoformat((kontroll or read[0]["kuupaev"])[:10])
    ruhmad = {}
    for r, n in zip(read, nahtav):
        d = datetime.date.fromisoformat(r["kuupaev"][:10])
        k = r["kuupaev"][:10] if (alg - d).days < PAEVI else r["kuupaev"][:7]
        ruhmad.setdefault(k, []).append((r, n))
    osad, esimene = [], True
    for k, rr in ruhmad.items():
        nahtaval = any(n for _, n in rr)
        if len(k) == 10:
            d = datetime.date.fromisoformat(k)
            pais = (f'<div class="u-pk"><b>{d.day}.</b><span class="u-pn">{NADALAPAEV[d.weekday()]}</span>'
                    f'<span>{KUUL[d.month - 1]}{"" if d.year == alg.year else " " + str(d.year)}</span></div>')
            kl, data = "u-paev", f' data-paev="{k}"'
        else:
            pais = (f'<div class="u-pk"><b>{KUUL[int(k[5:]) - 1]}</b><span>varem{"" if k[:4] == str(alg.year) else " " + k[:4]}</span></div>')
            kl, data = "u-paev u-kuu", ""
        if nahtaval and esimene:
            kl, esimene = kl + " uusim", False
        # Kuu rühmas on kuu ja aasta päises, real ainult päev ja kuu: täiskuupäev ei mahu veergu (Kadri 12.11.2026)
        loend = "".join(_uudis(r, "" if n else " hidden", None if len(k) == 10 else kp(r["kuupaev"]).rsplit(".", 1)[0] + ".") for r, n in rr)
        osad.append(f'<div class="{kl}"{data}{"" if nahtaval else " hidden"}>{pais}<ul class="u-voog">{loend}</ul></div>')
    return f'<div class="u-paevad">{"".join(osad)}</div>'


def _uudiste_paneel(rid, read, kontroll=None, peidus=False):
    """Üks piirkond (Eesti või maailm) saki paneelina: valdkonna ja teema filter ning ajajoon."""
    fk = [TEEMA_FILTER.get(r.get("teema"), "muu") for r in read]
    ak = [alamteemad(r) for r in read]
    nupp = lambda v, silt, n, valitud, title="": (  # noqa: E731
        f'<button type="button" data-f="{e(v)}" aria-pressed="{"true" if valitud else "false"}"{TITLE_ALAM if title else ""}>'
        f'{e(silt)} <span class="arv">{n}</span></button>')
    rida = nupp("", "kõik", len(read), True)
    for t in NUPPUDE_JARJEKORD:
        if t in TEEMA and t in fk:
            rida += nupp(t, TEEMA[t], fk.count(t), False)
        elif t in ALAMTEEMA and any(t in a for a in ak):
            rida += nupp(t, ALAMTEEMA[t][0], sum(t in a for a in ak), False, True)
    return f"""
  <section role="tabpanel" class="u-paneel" id="{rid}" aria-labelledby="tab-{rid}"{" hidden" if peidus else ""}>
  {_seis(read, kontroll)}
  <div class="u-f ek-f" role="group" aria-label="Vali teema"><span class="ek-f-silt">Teema</span>{rida}</div>
  <p class="ps u-tyhi" hidden>Selle valikuga uudiseid pole.</p>
  {_paevad(read, [True] * len(read), kontroll)}
  </section>"""


def uudised(A, vaade, vaated=None):
    U = _vaja(A, "uudised", "uudised.jsonl")
    V = _vaja(A, "uudiste_vaited", "uudiste-vaited.json")
    O = _vaja(A, "uudiste_olek", "uudiste-olek.json")
    kontrolli(vaade, "Eestist ja maailmast", "arvamus")
    U = sorted((dict(r) for r in U), key=lambda r: r["kuupaev"], reverse=True)
    esimene = {}
    for r in U:  # jätkulugu: kogumine märkis nii või sama ettevõtte lugu on varasema kuupäevaga olemas
        if r.get("ettevote"):
            esimene[r["ettevote"]] = min(esimene.get(r["ettevote"], r["kuupaev"]), r["kuupaev"])
    for r in U:
        if r.get("ettevote"):
            r["_jatk"] = (r.get("arv_tekst") or "").lower().startswith("jätkulugu") or r["kuupaev"] > esimene[r["ettevote"]]
    ee = [r for r in U if r["piirkond"] == "EE"]
    m = [r for r in U if r["piirkond"] != "EE"]
    suured = [r for r in U if r.get("suur")]
    arvamusi = sum(r["liik"] == "arvamus" for r in U)
    viimane = O["viimane_kontroll"]
    vk = datetime.datetime.fromisoformat(viimane)
    korras = sum(1 for s in O["allikad"] if s["ok"])

    def _suurim(read):
        s = [r for r in read if r.get("suur")]
        return s[0] if s else (read[0] if read else None)

    ee_s, m_s = _suurim(ee), _suurim(m)
    from lehed_ulevaade import kpi_pais, kpi_plaat
    nadal = (vk.date() - datetime.timedelta(days=6)).isoformat()
    uusi = lambda read: sum(r["kuupaev"] >= nadal for r in read)  # noqa: E731
    # Kadri 11.11.2026: allikarida „Seire uudistekogumine“ ei andnud infot ja võttis ruumi; plaadid on madalamad,
    # et uudised paistaks kiiremini. Kust uudised tulevad, on jaotises „Allikad“.
    aside = kpi_pais(
        kpi_plaat("ud-ee", "Eesti uudised", str(len(ee)), "",
                  {"muutus": (f"+{uusi(ee)} nädalaga", f'uusim {kp(ee[0]["kuupaev"])}' if ee else "")}, "", fookus=True),
        kpi_plaat("ud-maailm", "Maailma uudised ja uuringud", str(len(m)), "",
                  {"muutus": (f"+{uusi(m)} nädalaga", f'uusim {kp(m[0]["kuupaev"])}' if m else "")}, ""),
        kpi_plaat("ud-suured", "Suured uudised", str(len(suured)), "",
                  {"tekst": f"riigi otsus, statistika, üle 50 koondatu · <b>{arvamusi} arvamuslugu</b>"}, ""),
        kpi_plaat("ud-kontroll", "Viimane kontroll", f"{vk.day}.{vk.month:02d}", f"{vk:%H:%M}",
                  {"tekst": f'<b>{korras}/{len(O["allikad"])}</b> allikat vastas · 7.23 ja 17.53'}, ""),
        tihe=True,
    )
    lead = "Arvamus ei ole tõend."

    allikad = "".join(f'<li><span class="{"ok" if s["ok"] else "risk"}">{"vastas" if s["ok"] else "ei vastanud"}</span> {e(s["nimi"])}</li>' for s in O["allikad"])
    sec_k = f"""
<div class="g12">
<section class="pn sp12" id="uudiste-allikad" aria-labelledby="h-uudiste-allikad">
  <div class="pn-h"><h2 id="h-uudiste-allikad">Kust uudised tulevad</h2></div>
  <div class="g2 u-kuidas">
    <ul class="u-allikad">{allikad}</ul>
    <p class="ps">ERR (eesti ja inglise keeles), uudisteotsing Eestis ja maailmas ning Challengeri kuuaruanne. Tasulise artikli puhul on ainult pealkiri.</p>
    <p class="ps">„N väljaannet“ on see, mitu väljaannet sama lugu kajastas. „Loetud ainult pealkiri“ tähendab, et artiklit ei avatud. Koondamise juures on ettevõtte enda sõnad tehisaru kohta, mitte meie hinnang.</p>
  </div>
</section>
</div>"""
    # Kadri 11.11.2026: Eesti ja maailm eraldi sakkides (vaikimisi Eesti), sama nupustiil nagu teistel lehtedel.
    # Ettekanded, podcastid ja tulevased üritused on oma lehel, mitte uudiste voos.
    sakk = lambda rid, nimi, n, valitud: (  # noqa: E731
        f'<button type="button" role="tab" id="tab-{rid}" aria-controls="{rid}" aria-selected="{"true" if valitud else "false"}">'
        f'{nimi} <span class="arv">{n}</span></button>')
    sec_u = f"""
<div class="g12">
<section class="pn sp12 u-ajajoon" id="uudised-paevad" aria-labelledby="h-uudised-paevad">
  <div class="pn-h"><h2 id="h-uudised-paevad">Uudised päevade kaupa, uusim üleval</h2></div>
  <div class="p-tabs u-sakid" role="tablist" aria-label="Piirkond">{sakk("eesti-uudised", "Eesti", len(ee), True)}{sakk("maailma-uudised", "Maailm", len(m), False)}</div>
  {_uudiste_paneel("eesti-uudised", ee, viimane)}
  {_uudiste_paneel("maailma-uudised", m, viimane, peidus=True)}
</section>
</div>"""
    # Kadri 12.11.2026: „löö ettekanded, üritused ja podcastid uudiste kõrvale lahku“ – igaüks oma alamleht
    osad = ettekannete_osad(A, vaade)
    return jaga(A, vaade, lead, [], [
        ("uudised", [("uudised-paevad", "Uudised")], sec_u),
        ("allikad", [("uudiste-allikad", "Allikad")], sec_k),
        ("ettekanded", [("ettekanded", "Ettekanded"), ("ettekannete-allikad", "Allikad")], osad["ettekanded"]),
        ("uritused", [("tulekul", "Tulekul")], osad["uritused"]),
        ("podcastid", [("podcastid", "Podcastid"), ("podcastide-allikad", "Allikad")], osad["podcastid"]),
    ], aside=aside)


# ---------------------------------------------------------------- Ettekanded (Kadri 8.11.2026)

ETTEKANDE_TEEMA = {"too": "Töö", "ettevotted": "Ettevõtted", "inimesed": "Inimesed", "avalik-sektor": "Avalik sektor"}

# Kadri 11.11.2026: ühes nimekirjas olid hariduse, vähidiagnostika, akude ja kõnetuvastuse ettekanded segamini.
# Rühm = valdkond, millest ettekanne räägib (lugeja küsimus „mida see minu valdkonnas tähendab“), mitte ürituse nimi.
# Järjekord on lehe järjekord; tühja rühma ei näidata. Uus kirje saab ettekanded.json-is välja „ruhm“.
ETTEKANDE_RUHM = {
    "too": ("Töö ja organisatsioon", "Kuidas tehisaru muudab tööd, ameteid ja ettevõtete tööviisi."),
    "riik": ("Riik ja haridus", "Riigiasutuste tehisarukatsed ning tehisaru koht koolis."),
    "tulevik": ("Tehisaru areng ja tulevik", "Pikemad vestlused sellest, kuhu tehisaru liigub ja mida see tähendab."),
    # Kadri 11.11.2026 kinnitas alapealkirja (podcastide lõim): teadlaste vestlused, mis aitavad tehisarust mõelda
    "taust": ("Taust: mõistus ja informatsioon", "Teadlaste vestlused mõistusest, arutlemisest ja informatsioonist, mis aitavad tehisaru üle mõelda."),
    "tervis": ("Tervishoid", "Tehisaru arsti abilisena: diagnostika ja selle kontroll."),
    "energia": ("Energia", "Elektriturg, akud ja võrk: kus masinõpe teeb otsuseid iga 15 minuti järel."),
    "kone-pilt": ("Kõne ja pilt", "Kõnetuvastus ja masinnägemine päris tingimustes."),
    "muu": ("Muu", "Ettekanded, millele pole veel rühma määratud."),
}


# Ettekande liik (Kadri 11.11.2026: „ettekande meetod: podcastid, seminarid jms“). Liik tuleb allikast, sest sama sari
# on alati sama vormiga. Järjekord on filtri järjekord, kui arvud on võrdsed.
EK_LIIK = {"podcast": "podcast", "seminar": "seminar", "konverents": "konverents", "veebiseminar": "veebiseminar"}


def _kp_osa(iso):
    """Kuupäev või ainult aasta (kui seminari täpne päev pole avalik)."""
    return kp(iso) if len(iso) == 10 else iso


def _ettekanne(r, allikad):
    for k in ("id", "esineja", "pealkiri", "kuupaev", "video", "kokkuvote", "allikas"):
        if not r.get(k):
            raise AndmeViga(f"ettekanded.json: kirjel {r.get('id', '?')} puudub {k}")
    if r["allikas"] not in allikad:
        raise AndmeViga(f"ettekanded.json: {r['id']} allikas {r['allikas']} pole usaldatud allikate loendis")
    if not r["video"].startswith("https://"):
        raise AndmeViga(f"ettekanded.json: {r['id']} video link pole https")
    teemad = "".join(f'<span class="u-t">{e(ETTEKANDE_TEEMA[t])}</span>' for t in r.get("teemad", []) if t in ETTEKANDE_TEEMA)
    uritus = (f'<a class="u-ur" href="{e(r["uritus_url"])}">{e(r["uritus"])}</a>' if r.get("uritus_url") else e(r.get("uritus", "")))
    mottes = "".join(f"<li>{e(m)}</li>" for m in r.get("mottes", []))
    # Liik tuleb allikast (EK_LIIK); kui link viib saate lehele, ütleb „algus“, kust lõik algab
    liik = allikad[r["allikas"]].get("liik")
    if liik not in EK_LIIK:
        raise AndmeViga(f"ettekanded.json: allika {r['allikas']} liik {liik!r} pole lubatud ({', '.join(EK_LIIK)})")
    algus = f' <span class="ek-algus">lõik algab {e(r["algus"])}</span>' if r.get("algus") else ""
    tegija = f' · {e(r["tegija"])}' if r.get("tegija") and r["tegija"] != r.get("uritus") else ""
    a = allikad[r["allikas"]]
    kes = f' data-kes="{_tunnus(_korraldaja(a))}"' + (f' data-uksus="{_tunnus(r["tegija"])}"' if r.get("tegija") else "")
    return (f'<li data-liik="{liik}" data-allikas="{e(r["allikas"])}"{kes}>'
            f'<span class="d">{_kp_osa(r["kuupaev"])}</span>'
            f'<div><a href="{e(r["video"])}">{e(r["pealkiri"])}</a>{algus}'
            f'<p class="ek-kes"><b>{e(r["esineja"])}</b>{", " + e(r["amet"]) if r.get("amet") else ""} · {uritus}{tegija}</p>'
            f'<p class="u-k">{e(r["kokkuvote"])}</p>'
            f'{f"<ul class=ek-m>{mottes}</ul>" if mottes else ""}'
            f'<p class="u-m"><span class="u-l arv">{EK_LIIK[liik]}</span>{teemad}'
            f'{_ek_allikas(allikad[r["allikas"]], r.get("kontroll", ""))}</p></div></li>')


def _korraldaja(a):
    """Kes sisu teeb (Kadri 12.11.2026): sarja korraldaja, nt Tartu Ülikool nii UTTV kui andmeteaduse seminari puhul."""
    return a.get("korraldaja") or a["nimi"]


def _tunnus(t):
    return re.sub(r"[^a-z0-9]+", "-", t.lower().translate(str.maketrans("äöüõšž", "aouosz"))).strip("-")


def _ek_allikas(a, kontroll):
    """Ettekande sari logona, kui logo on olemas (Kadri 12.11.2026: „lisa podcastidele ka logod“); nimi on title-is."""
    fail = lae_logod.logo_fail(LOGOD, a["url"])
    title = a["nimi"] + (" · " + kontroll if kontroll else "")
    if not fail:
        return f'<span class="u-a" title="{e(kontroll)}">{e(a["nimi"])}</span>'
    return (f'<span class="u-a u-logo" title="{e(title)}">'
            f'<img src="pilt/logod/{e(fail)}" alt="{e(a["nimi"])}" width="18" height="18" loading="lazy"></span>')


def tulekul(A, tana):
    """Tulevased Eesti riigi üritused ja tähtajad (Kadri 11.11.2026: ettekanded ja podcastid eraldi lehel koos tulevaste
    üritustega). Tulevad igapäevasest uudistekogumisest (teema „riik“, väli tahtaeg), lähim eespool. Kõik riigi
    otsused jäävad lehele Eesti otsused; siin on ainult see, mis on veel ees."""
    ees = sorted((r for r in (A.get("uudised") or []) if r.get("teema") == "riik" and (r.get("tahtaeg") or "") >= tana),
                 key=lambda r: r["tahtaeg"])
    loend = (f'<ul class="u-voog ek-tulekul">{"".join(_uudis(r, kuup=kp(r["tahtaeg"])) for r in ees)}</ul>' if ees
             else '<p class="ps">Tulevasi üritusi ega tähtaegu praegu pole.</p>')
    return ees, f"""
<section class="pn sp12" id="tulekul" aria-labelledby="h-tulekul">
  <div class="pn-h"><h2 id="h-tulekul">{f"<b>{len(ees)} üritust või tähtaega</b>, lähim eespool" if ees else "Üritusi ega tähtaegu praegu pole"}</h2></div>
  {loend}
  <p class="ps">Tulevaste seminaride ja veebiseminaride kava veel ei koguta. Kõik riigi otsused ja eelnõud on lehel <a href="tehisaru-maarus.html#eesti-otsused">Eesti otsused</a>.</p>
</section>"""


def ettekanded(A, vaade, tana=None):
    """Kõik kolm alamlehe osa ühes tekstis (testidele ja vanadele kutsujatele)."""
    return "".join(ettekannete_osad(A, vaade, tana).values())


def _ek_loend(sid, read, allikad, pealkiri, tuhi):
    """Ettekannete või podcastide loend valdkonna rühmades koos liigi- ja allikafiltriga (Kadri 11.11.2026)."""
    from collections import Counter
    ruhmad = {k: [r for r in read if (r.get("ruhm") if r.get("ruhm") in ETTEKANDE_RUHM else "muu") == k] for k in ETTEKANDE_RUHM}
    ruhmad = {k: v for k, v in ruhmad.items() if v}
    valik = "".join(f'<a href="#ek-{k}" data-ruhm="{k}">{e(ETTEKANDE_RUHM[k][0])} <span class="arv">{len(v)}</span></a>' for k, v in ruhmad.items())
    plokid = "".join(
        f'<div class="ek-r" id="ek-{k}"><h3>{e(ETTEKANDE_RUHM[k][0])} <span class="arv">{len(v)}</span></h3>'
        f'<p class="ps">{e(ETTEKANDE_RUHM[k][1])}</p>'
        f'<ul class="u-voog ek">{"".join(_ettekanne(r, allikad) for r in v)}</ul></div>' for k, v in ruhmad.items())
    liigid = Counter(allikad[r["allikas"]].get("liik") for r in read)
    kes = Counter(_korraldaja(allikad[r["allikas"]]) for r in read)
    uksused = Counter(r["tegija"] for r in read if r.get("tegija"))

    def _rida(k, silt, loend):
        nupud = "".join(f'<button type="button" data-v="{e(v)}" aria-pressed="false">{e(nimi)} <span class="arv">{n}</span></button>'
                        for v, nimi, n in loend)
        return (f'<div class="u-f ek-f" data-k="{k}" role="group" aria-label="Vali {silt.lower()}"><span class="ek-f-silt">{silt}</span>'
                f'<button type="button" data-v="" aria-pressed="true">kõik <span class="arv">{len(read)}</span></button>{nupud}</div>')
    jrk = list(EK_LIIK)
    # Rida, kus oleks ainult üks valik (nt podcastide lehel liik), jääb ära
    filter_ = ((_rida("liik", "Liik", [(v, EK_LIIK[v], n) for v, n in sorted(liigid.items(), key=lambda x: (-x[1], jrk.index(x[0])))])
                if len(liigid) > 1 else "")
               + (_rida("kes", "Kes teeb", [(_tunnus(v), v, n) for v, n in sorted(kes.items(), key=lambda x: (-x[1], x[0]))])
                  if len(kes) > 1 else "")
               # Üksus (instituut, teaduskond) on kirjas UTTV ja TÜ seminaride juures; rida tuleb, kui üksusi on vähemalt kaks
               + (_rida("uksus", "Üksus", [(_tunnus(v), v, n) for v, n in sorted(uksused.items(), key=lambda x: (-x[1], x[0]))])
                  if len(uksused) > 1 else ""))
    sisu = (f'{filter_}<nav class="ek-valik" aria-label="Valdkonnad">{valik}</nav>{plokid}'
            f'<p class="ps ek-tyhi" hidden>Selle valikuga ettekandeid pole.</p>' if read else f'<p class="ps">{tuhi}</p>')
    return f"""
<section class="pn sp12" id="{sid}" aria-labelledby="h-{sid}">
  <div class="pn-h"><h2 id="h-{sid}">{pealkiri}</h2></div>
  {sisu}
</section>"""


def _ek_allikad(sid, allikad, pealkiri, markus):
    al = "".join(f'<li><a href="{e(a["url"])}">{e(a["nimi"])}</a>{" · " + e(a["miks"]) if a.get("miks") else ""}</li>' for a in allikad)
    return f"""
<section class="pn sp12" id="{sid}" aria-labelledby="h-{sid}">
  <div class="pn-h"><h2 id="h-{sid}">{pealkiri}</h2></div>
  <ul class="u-allikad">{al}</ul>
  <p class="ps">{markus}</p>
</section>"""


def ettekannete_osad(A, vaade, tana=None):
    """Kolm alamlehte (Kadri 12.11.2026: „löö ettekanded, üritused ja podcastid uudiste kõrvale lahku“):
    ettekanded (seminarid, konverentsid, veebiseminarid), tulevased üritused ja podcastid. Liik tuleb allikast."""
    tana = tana or datetime.date.today().isoformat()
    ees, sec_tul = tulekul(A, tana)
    E = A.get("ettekanded") or {"allikad": [], "ettekanded": []}
    allikad = {a["id"]: a for a in E.get("allikad", [])}
    read = sorted(E.get("ettekanded", []), key=lambda r: r["kuupaev"], reverse=True)
    on_pod = lambda r: allikad.get(r.get("allikas"), {}).get("liik") == "podcast"  # noqa: E731
    tk, pod = [r for r in read if not on_pod(r)], [r for r in read if on_pod(r)]
    ootel = (A.get("ootel") or {}).get("ettekanded", 0)
    from abi import alam_h1
    n, m = len(tk), len(pod)
    alam_h1(vaade, "ettekanded.html",
            f"Ettekanded: **{n} {'kokkuvõte' if n == 1 else 'kokkuvõtet'}** seminaride ja konverentside salvestistest"
            " ¦ kokkuvõte on meie sõnadega, esineja kogemus ei ole mõõtmistulemus" if n
            else "Ettekanded: **kokkuvõtted ootavad kinnitust**")
    alam_h1(vaade, "uritused.html",
            f"Tulekul: järgmine üritus või tähtaeg on **{kp(ees[0]['tahtaeg'])}**" if ees
            else "Tulekul: **tulevasi üritusi praegu pole**")
    alam_h1(vaade, "podcastid.html",
            f"Podcastid: **{m} {'vestlus' if m == 1 else 'vestlust'}** tehisaru arengust, tööst ja mõistusest"
            " ¦ külalise arvamus on arvamus, mitte mõõtmine" if m else "Podcastid: **kokkuvõtted ootavad kinnitust**")
    oot = f", <b>{ootel} ootab kinnitust</b>" if ootel and read else ""
    pod_al = [a for a in allikad.values() if a.get("liik") == "podcast"]
    tk_al = [a for a in allikad.values() if a.get("liik") != "podcast"]
    return {
        "ettekanded": '<div class="g12">' + _ek_loend(
            "ettekanded", tk, allikad, f"Kuula ja vaata: ettekanded valdkonna järgi, igas uuemad eespool{oot}",
            f"Ettekandeid pole veel kinnitatud{f' ({ootel} ootab)' if ootel else ''}.") + _ek_allikad(
            "ettekannete-allikad", tk_al, "Usaldatud seminarid ja konverentsid",
            "Kokkuvõte tehakse salvestise subtiitritest ja seda kontrollitakse paari väite kaupa; subtiitrite teksti saidil ei hoita. "
            "Uus ettekanne läheb saidile pärast kinnitamist.") + "</div>",
        "uritused": '<div class="g12">' + sec_tul + "</div>",
        "podcastid": '<div class="g12">' + _ek_loend(
            "podcastid", pod, allikad, "Kuula: podcastid valdkonna järgi, igas uuemad eespool",
            "Podcaste pole veel kinnitatud.") + _ek_allikad(
            "podcastide-allikad", pod_al, "Usaldatud podcastid",
            "Kokkuvõte tehakse avalikust transkriptist valitud lõigu kohta; transkripti teksti saidil ei hoita. "
            "Külalise arvamus on märgitud arvamusena. Uus osa läheb saidile pärast kinnitamist.") + "</div>",
    }


# ---------------------------------------------------------------- Hanked: litsentsid (Kadri 8.11.2026)

# Käsitsi pimeülevaatus (Kadri 5.–8.11.2026, koondtulemus hangete tuvastuse lõimest 8.11.2026; märgendusfailid
# ei ole selles repos). Klassifikaator ja leht.json ei ole uute reeglite järgi veel uuendatud.
# 8.11 12:37 lõplik viitevalim: 83 EI, 15 ANDMED, 2 AI; „kokku“ = masinmärgendid vs viide, „kasitsi“ = Kadri esmamärgendid vs viide.
KASITSI = {"n": 100, "valim": 782, "kuupaev": "2026-11-08", "kokku": 83, "kappa": "0,57",
           "kasitsi": 91, "kappa_kasitsi": "0,66", "viide": {"ei": 83, "andmed": 15, "ai": 2}, "ootel": 0}
KASITSI_LAUSE = (f'{KASITSI["n"]} hanget vaadati käsitsi pimesi üle ja neile pandi lõplik viitemärgend ({kp(KASITSI["kuupaev"])}). '
                 f'Masinmärgendid langevad viitega kokku {KASITSI["kokku"]}% (kappa {KASITSI["kappa"]}). Klassifikaatorit uuendatakse; '
                 'kuni selleni on arvud masinmärgistus.')

LITS_SISSE = re.compile(r"litsents|licen[cs]|kasutusõigus|tarkvarateenus|tarkvara\w* (?:soet|ost|rent|hankimine)"
                        r"|tableau|snowflake|vertica|veeam|cohesity", re.I)
LITS_VALJA = re.compile(r"alkomeetr|arendus(?!.*litsents)", re.I)
LITS_TOOTED = [("Tableau", r"tableau"), ("Qlik", r"qlik"), ("SAP", r"\bsap\b"), ("Snowflake", r"snowflake"),
               ("Vertica", r"vertica"), ("Accurity", r"accurity"), ("Cohesity", r"cohesity"), ("Veeam", r"veeam"),
               ("Trend AI", r"trend ai"), ("Progress", r"progress")]
# Eesmärk tuleb hanke kirjeldusest („eesmärk on …“), kui see on kirjas; muidu toote liigist. Järjekord loeb.
LITS_EESM = [("Andmeanalüüs ja aruanded", r"tableau|qlik|ärianalüüs|analüütika"),
             ("Varundus ja andmekaitse", r"cohesity|veeam"),
             ("Andmeladu", r"snowflake|vertica|andmela"),
             ("Andmehaldus ja -kvaliteet", r"accurity|andmekataloog|andmehaldus|andmekvaliteet|kvaliteeditarkvara"),
             ("Majandustarkvara", r"\bsap\b"),
             ("Tehisaru rakendus", r"tehisintellekt")]


def litsentsid(loend):
    """Litsentsi- ja tarkvarakasutuse hanked tuvastatud tehisaru- ja andmehangete hulgast: [(rida, toode, eesmärk, kirjeldusest)]."""
    out = []
    for r in loend:
        if not LITS_SISSE.search(r["t"]) or LITS_VALJA.search(r["t"]):
            continue
        tl = r["t"].lower()
        toode = next((n for n, m in LITS_TOOTED if re.search(m, tl)), "")
        ees = next((n for n, m in LITS_EESM if re.search(m, tl)), "Muu või pole kirjas")
        m = re.search(r"[Ee]esmärk on ([^.]{10,160})", r.get("k") or "")
        out.append((r, toode, ees, m.group(1).strip() if m else ""))
    return out


# ---------------------------------------------------------------- Hanked

def _tulbad_kihiti(read, lopp, silt_osa):
    """Püsttulbad kahe kihiga: tehisaru (sinine, all) ja andmed (hall). read: [(aasta, ai, andmed, poolik)]"""
    t = []
    for aasta, ai, andm, poolik in read:
        kokku = (ai + andm) or 1
        t.append(f'<div class="at2{" poolik" if poolik else ""}"><span class="v">{ai + andm}</span>'
                 f'<span class="tulp2" style="height:{(ai + andm) / lopp * 100:.2f}%"><i class="k-and" style="height:{andm / kokku * 100:.2f}%"></i>'
                 f'<i class="k-ai" style="height:{ai / kokku * 100:.2f}%"></i></span><span class="a">{aasta}{"*" if poolik else ""}</span></div>')
    return f'<div class="tulbad2" role="img" aria-label="{e(silt_osa)}">{"".join(t)}</div>'


def _viis_rida(nimi, vaartused, uhik="%", k=1):
    """Üks hankimise viisi näitaja kolme rühma kohta. vaartused: [(rühm, väärtus, fookus)]"""
    lopp = max(v for _, v, _ in vaartused) or 1
    read = "".join(f'<div class="vr{" f" if f else ""}"><span class="vr-n">{e(r)}</span><span class="vr-r"><i style="width:{v / lopp * 100:.1f}%"></i></span>'
                   f'<span class="vr-v">{pr(v, k)}{uhik}</span></div>' for r, v, f in vaartused)
    return f'<div class="viis"><p class="gt">{e(nimi)}</p>{read}</div>'


def hanked(A, vaade, vaated=None):
    H = _vaja(A, "hanked_leht", "hanked-leht.json")
    aastad = H["aastad"]
    seis = H.get("seis", {}).get("kuupaev", "")
    viimane_t = max(r["aasta"] for r in aastad)
    poolik = seis[:4] == str(viimane_t) and seis[5:] != "12-31"
    if max(r["ai_andmed_osakaal"] for r in aastad) >= 1:
        raise AndmeViga("Hangete pealkiri ütleb „alla 1%“, aga osa on 1% või rohkem")
    V = H["hankimise_viis"]
    kv = {g: 100 - V[g]["ainult_hind_osakaal"] for g in ("ai_andmed", "it_muud", "koik")}
    if not kv["ai_andmed"] > kv["it_muud"]:
        raise AndmeViga("Pealkiri ütleb, et kvaliteeti hinnatakse sagedamini kui teistes IT-hangetes, andmed ei näita seda")
    kontrolli(vaade, "alla 1%", "sagedamini kui teistes IT-hangetes")
    K = H["kontsentratsioon"]
    hind = H["hindamine"]
    val = hind["hindamine"]["valitud"]
    tul = hind["hindamine"]["tulemused"][val]
    lev = hind["levimus"]

    # KPI-plaadid hk-* läksid 19.11.2026 ära: leht algab tahvliga (Kadri valis näidistest „A ja C koos“)
    lead = ("Tehisaru = "
            "pealkirjas või kirjelduses on tehisaru märksõna; andmed = andmeladu, -haldus, -analüüs jms. "
            "Tehisaru uuringute ja mõjuanalüüside hankeid eraldi veel ei loeta.")

    # 1. Ainult viimane aasta (sisuloogika 6.11.2026, Kadri otsus 5): aastate võrdlust ei näidata, kuni vähemalt
    # 100 hanget on inimese pimesi märgistatud (lõplik viitevalim 8.11.2026).
    u = aastad[-1]
    sec_aastad = f"""
<section class="pn sp5" id="aastad" aria-labelledby="h-aastad">
  <div class="pn-h"><h2 id="h-aastad">Klassifikaator leidis {u["aasta"]}. aastal <b>{u["ai_andmed"]} tehisaru- ja andmehanget</b> ¦ {"seisuga " + kp(seis) + "; " if poolik else ""}see on {pr(u["ai_andmed_osakaal"])}% kõigist hangetest</h2></div>
  <p class="ps">Neist {u["ai_marksonaga"]} on tehisaru märksõnaga ja {u["ai_andmed"] - u["ai_marksonaga"]} andmehanked. Aastate võrdlust ei näidata enne, kui klassifikaator on uuendatud pärast seda, kui 100 hanget oli pimesi üle vaadatud.</p>
  {_viis_rida(f"Klassifikaatori leitud hanked {u['aasta']}, arv", [("tehisaru", u["ai_marksonaga"], True), ("andmed", u["ai_andmed"] - u["ai_marksonaga"], False)], uhik="", k=0)}
</section>"""

    # 2. Innovatsioonimärk vs 2% siht
    inn = [r for r in aastad if r.get("innovatsioonimark_osakaal") is not None]
    inn_read = "".join(
        f'<div class="vr{" f" if r["aasta"] == inn[-1]["aasta"] else ""}"><span class="vr-n">{r["aasta"]}{"*" if (poolik and r["aasta"] == viimane_t) or r is inn[0] else ""}</span>'
        f'<span class="vr-r"><i style="width:{r["innovatsioonimark_osakaal"] / 2.5 * 100:.1f}%"></i></span>'
        f'<span class="vr-v">{pr(r["innovatsioonimark_osakaal"])}%</span></div>' for r in inn)
    sec_inn = f"""
<section class="pn sp7" id="innovatsioon" aria-labelledby="h-innovatsioon">
  <div class="pn-h"><h2 id="h-innovatsioon">Innovatsioonimärgiga hankeid oli {inn[-1]["aasta"]}. aastal <b>{pr(inn[-1]["innovatsioonimark_osakaal"])}%</b> ¦ teised allikad annavad teise arvu</h2></div>
  <p class="ps">Osa eForms-hangetest, millele hankija märkis innovatsiooni; * osaline aasta (eForms algas septembris 2023). Märge on hankija enda linnuke ja selle määratlus on kontrollimata.</p>
  <div class="viis">{inn_read}</div>
  <p class="allikas">Sihijoont joonisel ei ole. Riigi siht on 2% aastaks 2027 ({a(OECD_URL, "OECD 2026")}), aga allikad mõõdavad eri asja: OECD aruande järgi on innovatsioonihankeid alla 1% hangete arvust ja {pr(float(A["avalik"]["hanked-innovatsioon"]["vaartus"]), 1)}% hangete eelarvest, Rahandusministeeriumi järgi 0,2% (2023). Kas siht käib märke, arvu või eelarve kohta, pole kontrollitud.</p>
</section>"""

    # 3. Kuidas hangitakse: lehe tunnuspilt (hanked_tahvel.sec_kuidas), siin enam ei korrata

    # 4. Hankijad
    top = H["hankijad_top"][:10]
    tmax = top[0][1]
    la0, la1 = min(r["a"] for r in H["loend"]), max(r["a"] for r in H["loend"])
    t_read = "".join(f'<div class="vr"><span class="vr-n" title="{e(n)}">{e(n)}</span><span class="vr-r"><i style="width:{c / tmax * 100:.1f}%"></i></span><span class="vr-v">{c}</span></div>' for n, c in top)
    sec_hankijad = f"""
<section class="pn sp12" id="hankijad" aria-labelledby="h-hankijad">
  <div class="pn-h"><h2 id="h-hankijad">{sonaga(K["top10_protsenti_hankijaid"]).capitalize()} hankijat {K["hankijaid"]}-st teeb <b>{pr(K["nende_osakaal"], 0)}%</b> tehisaru- ja andmehangetest</h2></div>
  <p class="ps">Kõik leitud hanked {la0}–{la1}. {K["uks_hange_hankijaid"]} hankijat tegi ainult ühe sellise hanke. Kümme suurimat:</p>
  <div class="viis hk">{t_read}</div>
</section>"""

    # 4b. Litsentsid: kes milliseid litsentse hangib ja milleks (Kadri 8.11.2026)
    LI = litsentsid(H["loend"])
    sec_lits = ""
    if LI:
        lyh = {"Andmeanalüüs ja aruanded": "Analüüs ja aruanded", "Andmehaldus ja -kvaliteet": "Andmehaldus",
               "Majandustarkvara": "Majandus­tarkvara", "Varundus ja andmekaitse": "Varundus",
               "Tehisaru rakendus": "Tehisaru", "Muu või pole kirjas": "Muu"}
        ees_n = collections.Counter(x[2] for x in LI)
        veerud = sorted(ees_n, key=lambda k: (k == "Muu või pole kirjas", -ees_n[k]))
        as_n = collections.Counter(x[0]["h"] for x in LI)
        ridu = [h for h, c in as_n.most_common() if c >= 2]
        muud = [h for h in as_n if h not in ridu]
        tooted = collections.Counter(x[1] for x in LI if x[1])
        top_e = veerud[0]
        top_t = collections.Counter(x[1] for x in LI if x[2] == top_e and x[1]).most_common(1)
        top_t = top_t[0][0] if top_t else ""
        t_asutusi = len({x[0]["h"] for x in LI if x[1] == top_t})
        a0, a1 = min(x[0]["a"] for x in LI), max(x[0]["a"] for x in LI)
        # Pikendamine: sama asutus, sama toode, mitu aastat
        pik = collections.Counter()
        for h, td in {(x[0]["h"], x[1]) for x in LI if x[1]}:
            pik[(h, td)] = len({x[0]["a"] for x in LI if x[0]["h"] == h and x[1] == td})
        (p_h, p_t), p_k = pik.most_common(1)[0]
        emax = ees_n[top_e]
        b_read = "".join(f'<div class="vr{" f" if k == top_e else ""}"><span class="vr-n" title="{e(k)}">{e(k)}</span>'
                         f'<span class="vr-r"><i style="width:{c / emax * 100:.1f}%"></i></span><span class="vr-v">{c}</span></div>'
                         for k, c in ees_n.most_common())
        cmax = max(collections.Counter((x[0]["h"], x[2]) for x in LI).values())

        def _rakk(hs, k):
            xs = [x for x in LI if x[0]["h"] in hs and x[2] == k]
            if not xs:
                return '<td class="lm-0"></td>'
            td = collections.Counter(x[1] or "nimetamata" for x in xs)
            tt = ", ".join(f"{n} {c}" for n, c in td.most_common())
            pea_t = td.most_common(1)[0][0]
            return (f'<td class="lm" style="--s:{12 + 58 * min(len(xs), cmax) / cmax:.0f}%" title="{e(tt)}">'
                    f'{len(xs)}{f"<small>{e(pea_t)}</small>" if pea_t != "nimetamata" else ""}</td>')
        lyh_as = {"Rahandusministeeriumi Infotehnoloogiakeskus": "Rahandusministeeriumi IT-keskus (RMIT)",
                  "Siseministeeriumi infotehnoloogia- ja arenduskeskus": "Siseministeeriumi IT-keskus (SMIT)",
                  "Keskkonnaministeeriumi Infotehnoloogiakeskus": "Keskkonnaministeeriumi IT-keskus",
                  "Tervise ja Heaolu Infosüsteemide Keskus": "TEHIK", "sihtasutus Põhja-Eesti Regionaalhaigla": "Regionaalhaigla",
                  "Ettevõtluse Arendamise Sihtasutus": "EAS", "Ettevõtluse ja Innovatsiooni Sihtasutus": "EIS (endine EAS)",
                  "Haridus- ja Teadusministeerium": "Haridus- ja Teadusministeerium", "Riigi Tugiteenuste Keskus": "RTK"}
        m_read = "".join(f'<tr><th scope="row" title="{e(h)}">{e(lyh_as.get(h, h))}</th>' + "".join(_rakk([h], k) for k in veerud)
                         + f'<td class="v">{as_n[h]}</td></tr>' for h in ridu)
        if muud:
            m_read += (f'<tr class="muud"><th scope="row">Muud asutused ({len(muud)}, igaüks 1 hange)</th>'
                       + "".join(_rakk(muud, k) for k in veerud) + f'<td class="v">{len(muud)}</td></tr>')
        m_pais = "".join(f'<th scope="col" title="{e(k)}">{lyh.get(k, e(k))}</th>' for k in veerud)
        l_rows = []
        for r, td, ees, kirj in sorted(LI, key=lambda x: (x[0]["kp"] or str(x[0]["a"])), reverse=True):
            pealk = f'<a href="{e(r["url"])}">{e(r["t"])}</a>' if r.get("url") else e(r["t"])
            ees_t = f'{e(ees)}<small>{e(kirj)}</small>' if kirj else e(ees)
            l_rows.append(f'<tr><td class="n">{r["a"]}</td><td>{pealk}<small>{e(r["h"])}</small></td>'
                          f'<td>{e(td) or "—"}</td><td>{ees_t}</td><td class="v">{_eur(r.get("v"))}</td></tr>')
        n_kirj = sum(1 for x in LI if x[3])
        sec_lits = f"""
<div class="g12">
<section class="pn sp12" id="litsentsid" aria-labelledby="h-litsentsid">
  <div class="pn-h"><h2 id="h-litsentsid">{len(LI)} litsentsihankest {ees_n[top_e]} on {e(top_e.lower())}: <b>{e(top_t)} litsentse hangib {t_asutusi} asutust</b></h2></div>
  <p class="ps">{a0}–{a1}, {len(as_n)} asutust. Sama litsentsi pikendatakse sageli igal aastal uue hankega: {e(p_h)} hankis {e(p_t)} litsentse {p_k} aastal.</p>
  <div class="lits">
    <div>
      <p class="gt" id="g-lits-ees">Litsentsihanked eesmärgi järgi</p>
      <div class="viis lits-ees" aria-describedby="g-lits-ees">{b_read}</div>
    </div>
    <div class="lits-tooted">
      <p class="gt">Tooted pealkirjas</p>
      <p class="gs">{", ".join(f"<b>{e(n)}</b> {c}" for n, c in tooted.most_common())}. {len(LI) - sum(tooted.values())} hanke pealkirjas toodet pole.</p>
    </div>
    <div class="lits-mx">
      <p class="gt" id="g-lits-as">Kes milliseid litsentse hangib: hangete arv asutuse ja eesmärgi järgi</p>
      {tbl_div("1:36%", "tl")}<table class="lits-m" aria-describedby="g-lits-as"><thead><tr><th scope="col">Asutus</th>{m_pais}<th scope="col" class="v">Kokku</th></tr></thead>
      <tbody>{m_read}</tbody></table></div>
      <p class="gs">Lahtris on hangete arv ja peamine toode.</p>
    </div>
  </div>
  <details>
    <summary>Näita kõiki {len(LI)} litsentsihanget koos eesmärgiga</summary>
    {tbl_div("-4 1:3.8em 3:22% 5:6.2em")}<table data-piir><thead><tr><th scope="col">Aasta</th><th scope="col">Hange ja hankija</th><th scope="col">Toode</th><th scope="col">Eesmärk</th><th scope="col" class="v">Eeldatav maksumus</th></tr></thead>
    <tbody>{"".join(l_rows)}</tbody></table></div>
  </details>
  <details>
    <summary>Kuidas litsentsihanked leiti ja mida see ei näita</summary>
    <p class="ps">Litsentsihange on tuvastatud tehisaru- ja andmehange, mille pealkirjas on litsents, kasutusõigus, tarkvarateenus, tarkvara ost või rent või tuntud tootenimi. Arenduse hanked ei ole sees, kui pealkiri litsentsi ei nimeta.
    Eesmärk on võetud hanke kirjeldusest, kui seal on lause „eesmärk on …“ ({n_kirj} hankel), muidu toote liigist (nt Tableau = andmeanalüüs ja aruanded).
    8.11.2026 täpsustatud märgendusjuhendi järgi ei ole litsentsiost tehisaru- ega andmehange; klassifikaatori uuendus võtab need koondarvust välja, siin on need eraldi.
    IT-majad (Rahandusministeeriumi, Siseministeeriumi ja Keskkonnaministeeriumi IT-keskus, TEHIK, RTK) hangivad ka teiste asutuste jaoks, seega hankija ei pruugi olla kasutaja.
    Tehisaru tööriistade litsentsid, mille hanke pealkiri ei viita tehisarule ega andmetele (nt üldised kontoritarkvara paketid), siia ei jõua.</p>
  </details>
</section>
</div>"""

    # 5. Leia hea näide
    loend = sorted(H["loend"], key=lambda r: r["kp"] or "", reverse=True)
    l_read = []
    for r in loend:
        if r.get("ah"):
            hind_t = "ainult hind"
        elif r.get("kv") is not None:
            hind_t = f'kvaliteet {pr(r["kv"], 0)}%'
        else:
            hind_t = "—"
        tunnused = []
        if r.get("hea") == 3:
            tunnused.append('<span class="u-t s">hea näide</span>')
        if r.get("inn"):
            # Kadri 11.11.2026: märge on hankija enda linnuke eVormil (BT-06 'inn-pur' või BT-776), mitte meie hinnang;
            # nt Töötukassa märgib igal aastal Tableau litsentside pikendamise innovatsiooniks.
            tunnused.append('<span class="u-t" title="Hankija märkis eVormil innovatsiooni. Seda, kas hange on sisult uuenduslik, keegi ei kontrolli.">'
                            'hankija märge: innovatsioon</span>')
        if r.get("pk") is not None:
            tunnused.append(f'<span class="u-t">{r["pk"]} pakkumust</span>')
        pealk = (f'<a href="{e(r["url"])}">{e(r["t"])}</a>' if r.get("url")
                 else f'{e(r["t"])} <small class="vn">viitenumber {e(r.get("vn") or "")}</small>')
        l_read.append(f'<tr data-hea="{1 if r.get("hea") == 3 else 0}" data-ruhm="{"ai" if r.get("ai") else "andmed"}" data-otsi="{e((r["t"] + " " + (r.get("h") or "") + " " + (r.get("k") or "")).lower())}">'
                      f'<td class="n">{kp(r["kp"]) if r.get("kp") else r["a"]}</td>'
                      f'<td>{pealk}<small>{e(r.get("h") or "")}</small></td>'
                      f'<td>{"tehisaru" if r.get("ai") else "andmed"}</td><td class="v">{_eur(r.get("v"))}</td>'
                      f'<td>{hind_t}</td><td>{"".join(tunnused)}</td></tr>')
    n_hea = sum(1 for r in loend if r.get("hea") == 3)
    sec_loend = f"""
<div class="g12">
<section class="pn sp12" id="loend" aria-labelledby="h-loend">
  <div class="pn-h"><h2 id="h-loend">Otsi sarnast hanget: {len(loend)} tehisaru- ja andmehanget, uuemad eespool</h2></div>
  <div class="h-otsing"><input type="search" placeholder="nt andmeladu, kõnetuvastus, Tableau" aria-label="Otsi hangetest">
    <div class="u-f" role="group" aria-label="Rühm"><button type="button" data-r="" aria-pressed="true">kõik</button><button type="button" data-r="ai">tehisaru</button><button type="button" data-r="andmed">andmed</button><button type="button" data-r="hea">head näited</button></div>
    <span class="h-loe" aria-live="polite"></span></div>
  {tbl_div("-3 -5 -6 1:6.6em 4:6.4em")}<table class="h-tabel" data-piir><thead><tr><th scope="col">Kuupäev</th><th scope="col">Hange ja hankija</th><th scope="col">Rühm</th><th scope="col" class="v">Eeldatav maksumus</th><th scope="col">Hindamine</th><th scope="col">Tunnused</th></tr></thead>
  <tbody>{"".join(l_read)}</tbody></table></div>
</section>
</div>"""

    # 6. Kui täpne
    nimed = {"marksonaloend": "märksõnaloend", "mudel": "mudel üksi", "mudel_voi_marksona": "mudel või märksõna", "oecd_laadne": "OECD-laadne märksõnad"}
    t_rows = []
    for k, t in hind["hindamine"]["tulemused"].items():
        t_rows.append(f'<tr{" class=fookus" if k == val else ""}><td>{e(nimed.get(k, k))}{" (kasutusel)" if k == val else ""}</td>'
                      f'<td class="v">{pr(t["tapsus"] * 100, 0)}% <small>{pr(t["tapsus_95"][0] * 100, 0)}–{pr(t["tapsus_95"][1] * 100, 0)}</small></td>'
                      f'<td class="v">{pr(t["saagis"] * 100, 0)}% <small>{pr(t["saagis_95"][0] * 100, 0)}–{pr(t["saagis_95"][1] * 100, 0)}</small></td>'
                      f'<td class="v">{pr(t["f1"], 2)}</td></tr>')
    vmin, vmax = lev["valimi_pohjal"]["vahemik_95"]
    sec_tapsus = f"""
<div class="g12">
<section class="pn sp12" id="tapsus" aria-labelledby="h-tapsus">
  <div class="pn-h"><h2 id="h-tapsus">Klassifikaator leiab umbes <b>{pr(tul["saagis"] * 100, 0)}%</b> tehisaru- ja andmehangetest ning {pr(tul["tapsus"] * 100, 0)}% leitutest on õiged masinmärgendite järgi</h2></div>
  <p class="ps">Testitud {hind["hindamine"]["test"]} hankel alates {hind["hindamine"]["testi_alates"]}. aastast. Märgendid ({hind["margendid"]["kokku"]}) tegi Claude; {KASITSI["n"]} neist vaadati käsitsi pimesi üle: lõplikus viitevalimis on {KASITSI["viide"]["ei"]} ei, {KASITSI["viide"]["andmed"]} andmehanget ja {KASITSI["viide"]["ai"]} tehisaruhanget. Masinmärgendid langevad viitega kokku {KASITSI["kokku"]}% (kappa {KASITSI["kappa"]}), käsitsi esmamärgendid {KASITSI["kasitsi"]}% (kappa {KASITSI["kappa_kasitsi"]}). Täpsus ja saagis on veel mõõdetud masina märgendite vastu. eForms-hangetest ({_arv(lev["hankeid"])}) on valimi põhjal umbes {lev["valimi_pohjal"]["hinnang"]} tehisaru- või andmehanget (95% vahemik {vmin}–{vmax}); klassifikaator leidis {lev["valitud_leidis"]}.</p>
  {tbl_div("1:30% 4:2.8em")}<table><thead><tr><th scope="col">Meetod</th><th scope="col" class="v">Täpsus (95%)</th><th scope="col" class="v">Saagis (95%)</th><th scope="col" class="v">F1</th></tr></thead>
  <tbody>{"".join(t_rows)}</tbody></table></div>
</section>
</div>"""
    # Kadri otsus 6.11.2026 22:11: Hanked jääb menüüsse, aga selge hoiatussildiga, kuni 100 hanget on käsitsi kontrollitud
    # Kadri 8.11.2026 (kommentaar lehel): „käsitsi ülevaatus on tehtud, uuenda lehte“
    # Kadri 8.11.2026 16:29: pimeülevaatus tehtud, katselisusele viitav ära; meetodi lause jääb tavalise märkusena
    # Kadri 14.11.2026: meetodi märkus on ploki all samas „Kuidas lugeda“ vormis nagu teised hoiatused
    markus = faktid([("Meetod", "", e(KASITSI_LAUSE) + " Aastaid võrreldakse pärast klassifikaatori uuendamist.")])
    # Teemamall A (Kadri 8.11.2026): andmed sakkides, siis uuringud, väited, reeglid, allikad
    import teemamall as tm
    from lehed_ulevaade import vaite_teema
    sec_andmed = tm.andmesakid("hanked", tm.kys("Kuidas riik tehisaru ostab?", "Kvaliteeti hinnatakse sagedamini kui teistes IT-hangetes"),
                               "Riigihangete registri ja TEDi hanked, märgistatud masinaga. Sakkides on aastad, hankijad, litsentsid ja klassifikaatori täpsus.", [
        ("aastad", "Aastad", '<div class="g12">' + sec_aastad + sec_inn + "</div>"),
        ("hankijad-sakk", "Hankijad", '<div class="g12">' + sec_hankijad + "</div>"),
        ("litsentsid", "Litsentsid", sec_lits),
        ("tapsus", "Täpsus", sec_tapsus),
    ])
    t_uuringud = tm.uuringute_plokk(vaated, [], [("avalik-sektor", "Avalik sektor (OECD 2026)", "")])
    t_vaited = tm.vaidete_plokk(A, vaated, "hanked", vaite_teema)
    t_reeglid = tm.reeglite_plokk(A, vaated, ["ai-uldkohaldamine"])  # kehtib juba ostetavatele süsteemidele
    t_allikad = tm.allikate_plokk([
        ("Riigihangete register ja TED", HANKED_URL, H["seis"]["kuupaev"], "uuendatakse GitHub Actionsiga"),
        ("Käsitsi pimeülevaatus, 100 hanget", "", KASITSI["kuupaev"], f'kokkulangevus {KASITSI["kokku"]}%, kappa {KASITSI["kappa"]}'),
    ])
    # Kadri 11.11.2026 (ülesehituse kontroll F): head näited (pikk loend) on oma lehel „Riik › Hangete näited“.
    # „Seotud“ rida jäi ära (D): Riigi alamlehtede rida viib samadele lehtedele.
    from abi import alam_h1
    alam_h1(vaade, "hanked-naited.html", f"Eeskujuks sobib **{n_hea} hanget {len(loend)}-st** ¦ "
            "hea näide: kvaliteeti hinnati, pakkumusi oli vähemalt kaks ja hange ei katkenud")
    # Töölaud (Kadri 19.11.2026 valis näidistest „A ja C koos“): tahvel, kuidas hangitakse, head näited, siis plokid kokkupandult.
    import datetime
    import hanked_tahvel as ht
    import teema_tahvel as tt
    D = ht.Andmed(H, KASITSI, float(A["avalik"]["hanked-innovatsioon"]["vaartus"]))
    uks = tt.uksikasjad([
        ("andmed", "Kuidas riik tehisaru ostab?", "aastad, innovatsioonimärk, hankijad, litsentsid, täpsus", sec_andmed + markus),
        ("lopp", "Reeglid ja allikad", "1 reegel · 2 allikat", tm.teema_lopp(t_uuringud, t_vaited, t_reeglid, t_allikad)),
    ])
    return jaga(A, vaade, lead, [], [
        ("tahvel", [("tahvel", "Ülevaade")], ht.tahvel(D)),
        ("kuidas", [("kuidas", "Kuidas hangitakse?")], ht.sec_kuidas(D, a(HANKED_URL, "Riigihangete register") + " ja TED")),
        ("naited-kokku", [("naited-kokku", "Head näited")], ht.sec_naited(D)),
        ("uksikasjad", [("andmed", "Andmed"), ("t-allikad", "Allikad")], uks),
        ("naited", [("loend", "Näited")], sec_loend),
    ])


# ---------------------------------------------------------------- Töö: mida uuritakse

# Kadri MKUS-i kommentaar 9.11.2026: „siin võiks olla enim tsiteeritud alates 2026“ (oli: alates 2023)
TSIT_ALATES = 2026


def alates_aastast(P, aasta):
    """Enim tsiteeritud tööd, mis ilmusid alates antud aastast. OpenAlexi kogujal on kaks tsiteeritute loendit:
    50 enim tsiteeritut 12 kuu jooksul („aasta“) ja alates 2023 („koik“). Mõlemad on tsiteeringute järgi tipp,
    seega nende ühendist alates antud aastast ilmunud tööd on selle aasta enim tsiteeritud tööd kuni
    12 kuu loendi lõikepiirini. Sama töö on ainult ühe korra."""
    nahtud, read = set(), []
    for r in P["tood"]:
        if r["grupp"] in ("aasta", "koik") and int(r["avaldatud"][:4]) >= aasta and r.get("url") not in nahtud:
            nahtud.add(r.get("url"))
            read.append(r)
    return read


def uuringud_too(A):
    """Töö vaate jaotis: publikatsioonid tehisarust ja tööst (OpenAlex) ning Eesti allikad. Tühi, kui andmeid pole toodud."""
    P = A.get("publikatsioonid")
    if not P:
        return ""
    aastad = P["aastad"]
    tais = [r for r in aastad if not r["poolik"]]
    a1 = tais[-1]
    a0 = next(r for r in tais if r["aasta"] == a1["aasta"] - 2)
    kord = a1["koik"] / a0["koik"]
    lopp = max(r["koik"] for r in aastad) * 1.12
    tulbad = "".join(f'<div class="at{" prognoos" if r["poolik"] else ""}"><span class="v">{_arv(r["koik"])}</span>'
                     f'<span class="tulp" style="height:{r["koik"] / lopp * 100:.2f}%"></span><span class="a">{str(r["aasta"])[2:]}{"*" if r["poolik"] else ""}</span></div>'
                     for r in aastad)
    teemad = sorted(P["teemad"], key=lambda t: t["osa2026"], reverse=True)
    t_read = "".join(f'<div class="vr"><span class="vr-n">{e(t["nimi"])}</span><span class="vr-r"><i style="width:{t["osa2026"] / max(x["osa2026"] for x in teemad) * 100:.1f}%"></i></span>'
                     f'<span class="vr-v">{pr(t["osa2026"])}%</span></div>' for t in teemad)
    sec_a = f"""
<section class="pn sp12" id="uuritakse" aria-labelledby="h-uuritakse">
  <div class="pn-h"><h2 id="h-uuritakse"><span class="kys">Millest kirjutatakse?</span> <b>Suurim teema on „{e(teemad[0]["nimi"])}“, {pr(teemad[0]["osa2026"])}% {aastad[-1]["aasta"]}. aasta töödest</b></h2></div>
  <p class="ps">Teadusartiklid ja töödokumendid aastas ({a(OPENALEX_URL, "OpenAlex")}, otsing seisuga {kp(P["meta"]["aeg"][:10])}). * aasta pole läbi.</p>
  <div class="uu-kaks">
    <div><p class="gt">Publikatsioone aastas</p><div class="aastatulbad">{tulbad}</div></div>
    <div><p class="gt">Teema osa {aastad[-1]["aasta"]}. aasta publikatsioonidest</p><div class="viis teemad">{t_read}</div></div>
  </div>
</section>"""
    grupid = [("uusimad", "Uusimad"), ("aasta", "Enim tsiteeritud, 12 kuud"), ("alates", f"Enim tsiteeritud alates {TSIT_ALATES}"), ("eesti", "Eesti autorid")]
    nupud, osad = [], []
    for i, (g, nimi) in enumerate(grupid):
        read = alates_aastast(P, TSIT_ALATES) if g == "alates" else [r for r in P["tood"] if r["grupp"] == g]
        if g == "uusimad":
            read.sort(key=lambda r: r["avaldatud"], reverse=True)
        elif g == "eesti":
            read.sort(key=lambda r: (r["avaldatud"], r["viiteid"]), reverse=True)
        else:
            read.sort(key=lambda r: r["viiteid"], reverse=True)
        # Tsiteeringute arv kohe pealkirja kõrval, mitte tabeli paremas servas (Kadri MKUS-i kommentaar 7.11.2026 08:50)
        li = "".join(f'<tr><td class="n">{kp(r["avaldatud"])}</td><td class="v pub-ts{" t" if not r["viiteid"] else ""}">{_arv(r["viiteid"])}</td>'
                     f'<td><a href="{e(r["url"])}">{e(r["pealkiri"])}</a><small>{e(r.get("kanal") or "")}</small></td></tr>' for r in read if r.get("url"))
        nupud.append(f'<button type="button" role="tab" aria-selected="{"true" if i == 0 else "false"}" aria-controls="pub-{g}" id="tab-{g}">{e(nimi)} ({len(read)})</button>')
        osad.append(f'<div role="tabpanel" id="pub-{g}" aria-labelledby="tab-{g}"{"" if i == 0 else " hidden"}>{tbl_div("-2 1:6.4em")}<table data-piir><thead><tr><th scope="col">Avaldatud</th><th scope="col" class="v">Tsiteeritud</th><th scope="col">Publikatsioon ja kanal</th></tr></thead><tbody>{li}</tbody></table></div></div>')
    sec_t = f"""
<section class="pn sp12" id="publikatsioonid" aria-labelledby="h-publikatsioonid">
  <div class="pn-h"><h2 id="h-publikatsioonid"><span class="kys">Mida tasub lugeda?</span> <b>Uusimad ja enim tsiteeritud tööd</b></h2></div>
  <div class="p-tabs" role="tablist" aria-label="Publikatsioonide valik">{"".join(nupud)}</div>
  <p class="ps">Tsiteeringud: {a(OPENALEX_URL, "OpenAlex")}, seisuga {kp(P["meta"]["aeg"][:10])}.</p>
  {"".join(osad)}
</section>"""
    # Põhinumbrid (KPI) töö kaupa, kontrollitud allika lehelt (Kadri MKUS-i kommentaar 7.11.2026 08:53).
    # Üks töö võib katta mitu rida; numbrid on selle töö allikalingi real, teised read viitavad sinna.
    kpi = (P.get("eesti_kpi") or {}).get("tood") or []
    ee = sorted((r for r in P["eesti_allikad"] if r.get("teemas")), key=lambda r: r["avaldatud"] or "", reverse=True)
    ee_url = [r["url"] for r in ee]
    too_url, peamine = {}, {}
    for t in kpi:
        meie = [u for u in t["urlid"] if u in ee_url]
        if not meie:
            continue
        p0 = t["allikas_url"] if t["allikas_url"] in meie else min(meie, key=ee_url.index)
        peamine[p0] = t
        for u in meie:
            too_url[u] = t
    ee.sort(key=lambda r: r["url"] not in peamine)  # põhinumbritega tööd eespool, muidu uusimad eespool
    nimi = {"arenguseire": "Arenguseire Keskus", "oska": "OSKA", "novaator": "Novaator", "err": "ERR", "etis": "ETIS"}

    def _kpi(r):
        t = peamine.get(r["url"])
        if t:
            return ("".join(f'<div class="ee-k"><span>{e(k["nimi"])}</span> <b>{e(k["vaartus"])}</b><small>{e(k["selgitus"])}</small></div>' for k in t["kpi"])
                    + f'<small class="ee-t">{e(t["too"])}</small>')
        if r["url"] in too_url:
            return f'<span class="kr-pole">sama töö: {e(too_url[r["url"]]["too"])}, numbrid ülal</span>'
        return '<span class="kr-pole">—</span>'
    e_read = "".join(f'<tr><td class="n">{kp(r["avaldatud"]) if r.get("avaldatud") else "—"}</td><td><a href="{e(r["url"])}">{e(r["pealkiri"])}</a></td>'
                     f'<td class="ee-kpi">{_kpi(r)}</td><td>{e(nimi.get(r["allikas"], r["allikas"]))}</td></tr>' for r in ee if r.get("url"))
    n_kpi = len({id(t) for t in peamine.values()})
    kpi_t = (f' Põhinumbrid on {ARVSONAD.get(n_kpi, n_kpi)} töö kohta, igaüks kontrollitud allika lehelt '
             f'({kp(P["eesti_kpi"]["kontrollitud"])}); need tööd on eespool.') if peamine else ""
    sec_e = f"""
<div class="g12">
<section class="pn sp12" id="eesti-allikad" aria-labelledby="h-eesti-allikad">
  <div class="pn-h"><h2 id="h-eesti-allikad"><span class="kys">Mida on Eestis uuritud?</span> <b>{len(ee)} uuringut ja raportit</b></h2></div>
  <p class="ps">Arenguseire Keskuse, OSKA ja teiste Eesti allikate tööd, mis käsitlevad tehisaru, tootlikkust või oskusi.{kpi_t or " Uusimad eespool."}</p>
  {tbl_div("-4 1:6.6em")}<table data-piir class="ee-tbl"><thead><tr><th scope="col">Avaldatud</th><th scope="col">Töö</th><th scope="col">Põhinumbrid</th><th scope="col">Allikas</th></tr></thead><tbody>{e_read}</tbody></table></div>
</section>
</div>"""
    # Kaks visuaali kõrvuti oma real, publikatsioonide tabel oma real (Kadri MKUS-i kommentaar 7.11.2026 08:52)
    return '<div class="g12">' + sec_a + '</div><div class="g12">' + sec_t + "</div>" + sec_e


# ---------------------------------------------------------------- Töö: keda koondajad otsivad

def palkamine(A):
    """Keda samad ettevõtted, kes koondavad, praegu tööle otsivad (Kadri 6.11.2026). Tühi, kui andmeid pole toodud."""
    F = (A.get("koondajad") or {}).get("firmad")
    K = (A.get("koondamised") or {}).get("juhtumid") or []
    if not F or not K:
        return ""
    from lehed_ulevaade import ROLL_NIMI, koondamise_arv
    jarjestus, read, selgitused = [], [], []
    K = sorted(K, key=lambda r: r["kuupaev"], reverse=True)
    for j in K:
        if j["ettevote"] not in jarjestus:
            jarjestus.append(j["ettevote"])
    puudu = [f for f in jarjestus if f not in F]
    kontrollitud = [f for f in jarjestus if f in F and F[f]["otsib"].get("kontrollitud")]
    otsivad = [f for f in kontrollitud if F[f]["otsib"]["ametid"]]
    kuulutusi = sum(len(F[f]["otsib"]["ametid"]) for f in kontrollitud)
    sama = [f for f in otsivad if set(F[f]["kaotatud"]) & {a["liik"] for a in F[f]["otsib"]["ametid"]} - {"teadmata", "muu"}]
    kp_min = min(F[f]["otsib"]["kontrollitud"] for f in kontrollitud)
    for f in jarjestus:
        # Koondamise arv, põhjus ja uudise link tulid kaartidelt (Kadri MKUS-i kommentaar 7.11.2026 08:48)
        js = [j for j in K if j["ettevote"] == f]
        arvud = "".join(
            f'<div class="pk-k" id="pk-{e(j["id"])}"><b>{e(koondamise_arv(j))}</b> <span class="pk-d">{j["kuupaev"][5:7]}.{j["kuupaev"][:4]}</span>'
            f'<small>tehisaru: {e(ROLL_NIMI[j["roll"]])}</small>'
            + (f'<small>esimeses teates {e(koondamise_arv(j["arv_varem"]))}</small>' if j.get("arv_uuendus") else "") + '</div>' for j in js)
        pohjused = "".join(
            f'<div class="pk-k"><p>{e(j["pohjus"])}</p><small>{a(j["url"], j["allikas"])}'
            f'{" · uudisest, kontrollimata" if j.get("kandidaat") else ""}'
            + (f' · uus arv: {a(j["arv_uuendus"]["url"], j["arv_uuendus"]["allikas"])}, {kp(j["arv_uuendus"]["kuupaev"])}' if j.get("arv_uuendus") else "")
            + '</small></div>' for j in js)
        x = F.get(f)
        if x is None:
            read.append(f'<tr><td><b>{e(f)}</b><small>{e(js[0]["sektor"])}</small></td><td>{arvud}</td><td>{pohjused}</td>'
                        f'<td><span class="kr-pole">taust puudub</span></td><td><span class="kr-pole">pole kontrollitud</span></td></tr>')
            continue
        o = x["otsib"]
        kaot = set(x["kaotatud"])
        kaotatud = "".join(f'<span class="u-t">{e(k)}</span>' for k in x["kaotatud"])
        if not o.get("kontrollitud"):
            otsib = f'<span class="kr-pole">{e(o["tekst"])}</span>'
        elif not o["ametid"]:
            otsib = f'<b>0</b> <span class="kr-pole">{e(o["tekst"])}</span>'
        else:
            otsib = f'<b>{len(o["ametid"])}</b> ' + "".join(
                f'<span class="pk-a">{e(a["nimi"])} <span class="u-t{" s" if a["liik"] in kaot and a["liik"] not in ("teadmata", "muu") else ""}">{e(a["liik"])}</span></span>'
                for a in o["ametid"])
        link_ = f'<small>{a(o["url"], "tööpakkumiste leht")}</small>' if o.get("url") else ""
        # Viis veergu kuue asemel ja ametiliikide pikk selgitus tabeli all (Kadri 7.11.2026: liiga palju infot ühel taustal)
        read.append(f'<tr><td><b>{e(f)}</b><small>{e(x["sektor"])} · {e(x["omand"])}</small></td><td>{arvud}</td><td>{pohjused}</td>'
                    f'<td>{kaotatud}</td><td>{otsib}{link_}</td></tr>')
        if x.get("kaotatud_tekst"):
            selgitused.append(f'<li><b>{e(f)}</b>: {e(x["kaotatud_tekst"])}</li>')
    n_k = len(kontrollitud)
    h2 = f'{SEESTYTLEV.get(n_k, str(n_k) + "-st").capitalize()} kontrollitud koondajast'
    sama_t = (f"; {ARVSONAD.get(len(sama), len(sama))} otsib sama ametiliiki, mida koondab" if sama else "; mitte ükski ei otsi sama ametiliiki, mida koondab")
    return f"""
<div class="g12">
<section class="pn sp12" id="palkamine" aria-labelledby="h-palkamine">
  <div class="pn-h"><h2 id="h-palkamine">{h2} otsib praegu Eestis töötajaid <b>{ARVSONAD.get(len(otsivad), len(otsivad))}</b> (kokku {sonaga(kuulutusi)} kuulutust){sama_t}</h2></div>
  <p class="ps">Tööpakkumiste lehed on kontrollitud {kp(kp_min)}. Sinise äärega ametiliik on sama, mida koondatakse.</p>
  {tbl_div("-3 -4")}<table class="pk"><thead><tr><th scope="col">Ettevõte</th><th scope="col">Koondab Eestis</th><th scope="col">Põhjus ettevõtte sõnul</th><th scope="col">Kaotab</th><th scope="col">Otsib praegu Eestis</th></tr></thead>
  <tbody>{"".join(read)}</tbody></table></div>
  <details><summary>Täpsustused: ametiliigid ja mida tabel ei näita</summary><div>
    <ul>{"".join(selgitused)}</ul>
    <p>Tabel ei näita sisemisi ümberpaigutusi ega kuulutusi, mis on ainult LinkedInis.{" Taustata: " + ", ".join(e(p) for p in puudu) + "." if puudu else ""}</p>
  </div></details>
</section>
</div>"""


# ---------------------------------------------------------------- Töö: tööportaalide kuulutused

LISASILDID = {"Sobib ka ukrainlastele", "Hooaja-/ajutine töö", "Praktika", "Vabatahtlik töö"}
KAUGTOO = {"Osaline kaugtöö", "Kodukontor", "Kaugtöö", "Töö välismaal", "Välismaa"}


def _arvt(n):
    return f"{n:,}".replace(",", " ")


# Pikad tööandjanimed lühendina, täisnimi hõljutades (Kadri 11.11.2026: SMIT)
TOOANDJA_LYHEND = {"Siseministeeriumi infotehnoloogia- ja arenduskeskus": "SMIT"}


def lyhenda(html):
    for nimi, l in TOOANDJA_LYHEND.items():
        html = html.replace(f'<span class="n" title="{e(nimi)}">{e(nimi)}</span>',
                            f'<span class="n" title="{e(nimi)}"><abbr title="{e(nimi)}">{e(l)}</abbr></span>')
    return html


def toopakkumised(A):
    """Tööportaalide kuulutuste arv ning portaali enda jaotused ameti, asukoha ja tööandja järgi (Kadri 7.11.2026 09:38).
    Iga portaal eraldi; arve ei liideta, sest sama kuulutus võib olla mitmes portaalis. Tühi, kui andmeid pole."""
    T = A.get("toopakkumised")
    if not T or not T.get("portaalid"):
        return ""
    from komponendid import lihtribad
    P = sorted(T["portaalid"], key=lambda p: -p["kuulutusi_kokku"])
    kp_ = max(p["kontrollitud"] for p in P)
    def kus(p):
        return {"CV.ee": "CV.ee-s", "CV Keskus": "CV Keskuses", "Töötukassa": "Töötukassas"}.get(p["portaal"], p["portaal"] + ": ")
    osad_ = [f'{kus(p)} {_arvt(p["kuulutusi_kokku"])}' for p in P]
    loendid = ", ".join(osad_[:-1]) + " ja " + osad_[-1] if len(osad_) > 1 else osad_[0]

    def valdkonnad(p):
        v = p.get("ametivaldkond")
        return [r for r in v if r["nimi"] not in LISASILDID] if isinstance(v, list) else []
    suurim = [f'{valdkonnad(p)[0]["nimi"].lower()} ({e(p["portaal"])})' for p in P if valdkonnad(p)]
    h2 = (f'{kp(kp_)} oli {loendid} <b>tööpakkumist</b>; suurim valdkond oli '
          + (", ".join(suurim[:-1]) + " ja " + suurim[-1] if len(suurim) > 1 else "".join(suurim)))

    def ribad(read, n=12):
        read = read[:n]
        lopp = max(r["arv"] for r in read)
        samm = next(s for s in (50, 100, 200, 250, 500, 1000) if lopp / s <= 5)
        lopp = -(-lopp // samm) * samm
        return lihtribad([(r["nimi"], r["arv"], _arvt(r["arv"])) for r in read], lopp, samm=samm, uhik="", fookus=0)

    nupud, osad = [], []
    jaotusega = [p for p in P if valdkonnad(p)]
    for i, p in enumerate(jaotusega):
        pid = "tp-" + "".join(c for c in p["portaal"].lower() if c.isalnum())
        mk = [r for r in p.get("asukoht_maakond") or [] if r["nimi"] not in KAUGTOO] if isinstance(p.get("asukoht_maakond"), list) else []
        kaug = [r for r in p.get("asukoht_maakond") or [] if r["nimi"] in KAUGTOO] if isinstance(p.get("asukoht_maakond"), list) else []
        linn = p.get("asukoht_linn") if isinstance(p.get("asukoht_linn"), list) else []
        top = p.get("top_tooandjad") if isinstance(p.get("top_tooandjad"), list) else None
        # Töötukassa jaotus tuleb CV.ee kaudu vahendatud kuulutustest (tööturu-uudiste kogumine 11.11.2026): link sinna
        alus = p.get("jaotuse_allikas")
        kat_l = a(p["ametivaldkond_url"], "portaali kategooriad") if p.get("ametivaldkond_url") else (a(alus.split(" ")[0], "CV.ee kaudu") if alus else "")
        kus_l = a(p["asukoht_url"], "portaali asukohad") if p.get("asukoht_url") else (a(alus.split(" ")[0], "CV.ee kaudu") if alus else "")

        def kolm(fookus=0, vk=None, valitav=()):
            """Kolm veergu. vk = valitud valdkond (Kadri 11.11.2026: linnad ja tööandjad valdkonna järgi).
            valitav = valdkonnad, mille tulbal klõpsates näeb selle valdkonna linnu ja tööandjaid."""
            linn_v = vk.get("linnad") if vk else (linn or mk)
            top_v = vk.get("tooandjad") if vk else top
            kelle = f', valdkonnas {e(vk["nimi"].lower())}' if vk else ""
            if valitav:
                g = klikitav(lihtribad_v(valdkonnad(p), vk["nimi"] if vk else None), valitav, vk["nimi"] if vk else "")
                vihje = (f'<button type="button" class="tp-koik" data-vk="">kõik valdkonnad</button>' if vk
                         else "klõpsa valdkonnal, et filtreerida")
                veerud = [f'<div><p class="gt">Mis ametivaldkonnas</p><p class="ps">{kat_l}, 12 suuremat; {vihje}</p>{g}</div>']
            else:
                veerud = [f'<div><p class="gt">Mis ametivaldkonnas</p><p class="ps">{kat_l}, 12 suuremat</p>{ribad(valdkonnad(p)) if not vk else lihtribad_v(valdkonnad(p), vk["nimi"])}</div>']
            if linn_v:
                kt = ("; " + ", ".join(f'{e(r["nimi"]).lower()} {_arvt(r["arv"])}' for r in kaug)) if kaug and not vk else ""
                veerud.append(f'<div><p class="gt">Kus: linnad{kelle}</p><p class="ps">{kus_l}{kt}</p>{ribad(linn_v, 10)}</div>')
            if top_v:
                veerud.append(f'<div><p class="gt">Kes: enim kuulutusi avaldanud tööandjad{kelle}</p><p class="ps">{a(p["top_tooandjad_url"], "portaali tööandjad")}, 12 suuremat</p>{lyhenda(ribad(top_v))}</div>')
            else:
                veerud.append(f'<div><p class="gt">Kes: tööandjad</p><p class="ps">{e(p.get("top_tooandjad_pohjus") or "Tööandjate arve ei õnnestunud lugeda.")}</p></div>')
            return f'<div class="tp-kolm">{"".join(veerud)}</div>'

        def lihtribad_v(read, nimi):
            read = read[:12]
            lopp = max(r["arv"] for r in read)
            samm = next(s for s in (50, 100, 200, 250, 500, 1000) if lopp / s <= 5)
            lopp = -(-lopp // samm) * samm
            return lihtribad([(r["nimi"], r["arv"], _arvt(r["arv"])) for r in read], lopp, samm=samm, uhik="", fookus=nimi)

        def klikitav(html, nimed, valitud):
            """Valdkonna tulp on ise filter (Kadri 11.11.2026: „valdkonna visuaalile klikkides saab filtreid muuta“;
            eraldi nupurida raiskas ruumi). Valitud tulba uus klõps viib tagasi kõigi valdkondade juurde."""
            html = html.replace('<div class="ribad lihtne" aria-hidden="true">',
                                '<div class="ribad lihtne tp-vk" role="group" aria-label="Vali valdkond">', 1)
            for n in nimed:
                vana = f'"><span class="n" title="{e(n)}">'
                uus = (f' tp-v" data-vk="{e(n)}" role="button" tabindex="0" aria-pressed="{"true" if n == valitud else "false"}"'
                       f' title="{e(n)}: näita linnu ja tööandjaid"><span class="n">')
                html = html.replace(vana, uus, 1)
            return html

        # Valdkonna filter (Kadri 11.11.2026): kui kogumine andis iga suurema valdkonna linnad ja tööandjad
        # (`valdkonniti`), saab valdkonna valida ja kõik kolm veergu näitavad selle valdkonna jaotust.
        VK = [v for v in (p.get("valdkonniti") or []) if v.get("linnad") or v.get("tooandjad")]
        if VK:
            nimed = {r["nimi"] for r in valdkonnad(p)[:12]}
            VK = [v for v in VK if v["nimi"] in nimed]
        if VK:
            vn = [v["nimi"] for v in VK]
            vk_kp = f' ({kp(p["valdkonniti_kuupaev"])})' if p.get("valdkonniti_kuupaev") else ""
            sisu_ = (f'<div data-vk-sisu="">{kolm(valitav=vn)}</div>'
                     + "".join(f'<div data-vk-sisu="{e(v["nimi"])}" hidden>{kolm(vk=v, valitav=vn)}</div>' for v in VK)
                     + f'<p class="ps">Valdkonna linnad ja tööandjad on loetud kuulutustest{vk_kp}: üks kuulutus võib olla mitmes valdkonnas.</p>')
        else:
            sisu_ = kolm()
        if p.get("jaotuse_kuulutusi"):
            # Kogu arv ja jaotus mõõdavad eri asja; lugeja peab seda nägema enne graafikut
            sisu_ = (f'<p class="ps tp-alus">Jaotused on {_arvt(p["jaotuse_kuulutusi"])} kuulutusest, mida {e(p["portaal"])} vahendas CV.ee kaudu'
                     f'{" (" + kp(p["valdkonniti_kuupaev"]) + ")" if p.get("valdkonniti_kuupaev") else ""}; need on ka CV.ee arvudes. '
                     f'{e(p["portaal"])} enda lehel oli {_arvt(p["kuulutusi_kokku"])} kuulutust. Need arvud mõõdavad eri asja ega pea klappima.</p>' + sisu_)
        mk_t = ""
        if mk:
            mk_t = ('<details><summary>Maakonnad</summary><div>' + "".join(f'<span class="tp-m">{e(r["nimi"])} <b>{_arvt(r["arv"])}</b></span>' for r in mk) + '</div></details>')
        nupud.append(f'<button type="button" role="tab" aria-selected="{"true" if i == 0 else "false"}" aria-controls="{pid}" id="tab-{pid}">{e(p["portaal"])} ({_arvt(p["kuulutusi_kokku"])})</button>')
        osad.append(f'<div role="tabpanel" id="{pid}" aria-labelledby="tab-{pid}"{"" if i == 0 else " hidden"}>{sisu_}{mk_t}</div>')
    ilma = [p for p in P if not valdkonnad(p)]
    def _pohj(p):
        t = (p.get("puudub_pohjus") or "jaotust pole").rstrip(".")
        return t[:1].lower() + t[1:]
    ilma_t = "".join(f' {e(p["portaal"])} näitab ainult kogu arvu: {e(_pohj(p))}.' for p in ilma)
    pt = "".join(f'<tr><td>{a(p["url"], p["portaal"])}</td><td class="v">{_arvt(p["kuulutusi_kokku"])}</td><td>{kp(p["kontrollitud"])}</td><td><small>{e(p.get("allikas_text") or p.get("allikas_tekst") or "")}</small></td></tr>' for p in P)
    return f"""
<div class="g12">
<section class="pn sp12" id="toopakkumised" aria-labelledby="h-toopakkumised">
  <div class="pn-h"><h2 id="h-toopakkumised">{h2}</h2></div>
  <p class="ps">Portaalide avalikud arvud, loetud iga päev. Portaale ei liideta, sest sama kuulutus võib olla mitmes.</p>
  <div class="p-tabs" role="tablist" aria-label="Tööportaal">{"".join(nupud)}</div>
  {"".join(osad)}
  <details><summary>Kõik portaalid ja kuidas arv loeti</summary><div><p>Kategooriad on portaali omad; üks kuulutus võib olla mitmes kategoorias.{ilma_t}</p>{tbl_div("-3 1:26% 2:5.8em")}<table><thead><tr><th scope="col">Portaal</th><th scope="col" class="v">Kuulutusi</th><th scope="col">Loetud</th><th scope="col">Lehel oli</th></tr></thead><tbody>{pt}</tbody></table></div></div></details>
</section>
</div>"""


# ---------------------------------------------------------------- Töö: tehisaru- ja andmetööde kuulutused

TK_TOOANDJA = {"Töötukassa vahendatud pakkumised": "Töötukassa kaudu (eri tööandjad)"}
TK_NIMI = {"ai_amet": "Tehisaru amet", "andmeamet": "Andmeamet", "ai_oskus": "Tehisaru muus ametis",
           "ai_firma_noue": "Firma üldnõue"}


def _tk_leiud(A, K, R, kp_, url):
    """Kaks leidu kuulutuste andmetest (Kadri 9.11.2026 kinnitas mustandi leiud 1 ja 2, artefakt Pp2Qxyqu5V1Fjh76rKnfHt).
    Numbrid arvutatakse iga ehitusega samadest failidest, mitte käsitsi."""
    from komponendid import allikarida, lihtribad
    TP = A.get("toopakkumised") or {}
    CV = next((p for p in TP.get("portaalid", []) if p["portaal"] == "CV.ee"), None)
    kuul = K.get("kuulutused", [])
    if not CV or not CV.get("asukoht_maakond") or not kuul:
        return ""
    pohi = ("ai_amet", "andmeamet", "ai_oskus")
    pk = [r for r in kuul if r["ruhm"] in pohi]
    if len(pk) != sum(R[g]["arv"] for g in pohi):
        raise AndmeViga("ai-tookuulutused.json: kuulutuste loend ja rühmade arvud ei klapi")
    n_pk, kokku = len(pk), CV["kuulutusi_kokku"]
    mk_ai = collections.Counter(r.get("maakond") for r in pk)
    mk_koik = sorted(CV["asukoht_maakond"], key=lambda r: -r["arv"])[:5]
    suurim = mk_koik[0]["nimi"]
    o_ai, o_koik = mk_ai[suurim] / n_pk * 100, mk_koik[0]["arv"] / kokku * 100
    read_a = [(r["nimi"], mk_ai.get(r["nimi"], 0) / n_pk * 100,
               f'{pr(mk_ai.get(r["nimi"], 0) / n_pk * 100, 0)}% ({mk_ai.get(r["nimi"], 0)})') for r in mk_koik]
    read_k = [(r["nimi"], r["arv"] / kokku * 100, None) for r in mk_koik]
    cvkp = (CV.get("kontrollitud") or kp_)[:10]
    kus = f"""
<section class="pn sp12" id="tk-kus" aria-labelledby="h-tk-kus">
  <div class="pn-h"><h2 id="h-tk-kus">Tehisaru- ja andmetöödest <b>{pr(o_ai, 0)}% on {e(suurim)}l</b>, kõigist töökuulutustest {pr(o_koik, 0)}%</h2></div>
  <p class="ps">CV.ee, {kp(kp_)}. Osa kuulutustest maakonna järgi, %. Väljaspool {e(suurim)}d on {n_pk - mk_ai[suurim]} tehisaru- ja andmetööd {n_pk}-st.</p>
  <div class="kaks vordne">
    <div><p class="gt">Tehisaru- ja andmetööd ({n_pk} kuulutust)</p>{lihtribad(read_a, 100, samm=25, fookus=0)}</div>
    <div><p class="gt">Kõik kuulutused ({_arvt(kokku)})</p>{lihtribad(read_k, 100, samm=25, fookus=0)}</div>
  </div>
  <details><summary>Täpsustused</summary><div>
    <p>Tehisaru- ja andmetööd on kolm rühma: pealkirjas tehisaru ({R["ai_amet"]["arv"]}), pealkirjas andmed ({R["andmeamet"]["arv"]}) ja muu amet, mille kuulutus mainib tehisaru ({R["ai_oskus"]["arv"]}). Rühm „Firma üldnõue“ ei ole sees. {mk_ai.get("Eesti (täpsustamata)", 0)} kuulutusel maakonda pole.</p>
    <p>Kõigi kuulutuste maakonnad on CV.ee enda jaotus ({kp(cvkp)}). Üks kuulutus võib olla mitmes maakonnas, seega osad on ligikaudsed. Liigitus on märksõnapõhine ja inimene pole seda kontrollinud. See on ühe päeva seis, mitte trend.</p>
  </div></details>
  {allikarida([("CV.ee avalik otsing", url, "loetud " + kp(kp_))])}
</section>"""
    TN = {"ai_amet": "Pealkirjas tehisaru", "andmeamet": "Pealkirjas andmed", "ai_oskus": "Mainib tehisaru",
          "ai_firma_noue": "Firma üldnõue"}
    ta, n_k = collections.Counter(r.get("tooandja") for r in kuul), len(kuul)
    top, n_top = ta.most_common(1)[0]
    koik_r = collections.Counter(r["ruhm"] for r in kuul)
    top_r = collections.Counter(r["ruhm"] for r in kuul if r.get("tooandja") == top)
    read2 = sorted(((TN[g], top_r[g] / koik_r[g] * 100, f"{top_r[g]} / {koik_r[g]}") for g in TN if koik_r.get(g)),
                   key=lambda x: -x[1])
    read2.insert(0, ("Kõik neli rühma", n_top / n_k * 100, f"{n_top} / {n_k}"))
    ilma = n_k - n_top
    top_cv = next((r["arv"] for r in CV.get("top_tooandjad", []) if r["nimi"] == top), None)
    top_koht = next((i for i, r in enumerate(CV.get("top_tooandjad", []), 1) if r["nimi"] == top), None)
    lisa = (f" {e(top)} on ka kõigi CV.ee kuulutuste seas {top_koht}. suurim avaldaja ({top_cv} kuulutust)." if top_cv else "")
    yks = f"""
<section class="pn sp12" id="tk-yks" aria-labelledby="h-tk-yks">
  <div class="pn-h"><h2 id="h-tk-yks">Tehisaru mainivatest kuulutustest <b>{pr(n_top / n_k * 100, 0)}% on ühelt tööandjalt</b> ({e(top)})</h2></div>
  <p class="ps">CV.ee, {kp(kp_)}. {e(top)} kuulutuste osa igas rühmas, %.</p>
  {lihtribad(read2, 100, samm=25, fookus=0)}
  <p>Kui {e(top)} kuulutused välja jätta, jääb {ilma} kuulutust ehk {pr(ilma / kokku * 100)}% kõigist {_arvt(kokku)} kuulutusest. Kui {e(top)} kuulutusi lisab või eemaldab, muutub kogu arv palju, kuigi tööturul muud ei muutu.</p>
  <details><summary>Täpsustused</summary><div><p>{e(top)} kuulutustest {top_r["ai_firma_noue"]} on rühmas „Firma üldnõue“: tehisaru on ainult firma ühises lauses, mis kordub kuulutusest kuulutusse.{lisa}</p></div></details>
  {allikarida([("CV.ee avalik otsing", url, "loetud " + kp(kp_))])}
</section>"""
    return kus + yks


def ai_kuulutused(A):
    """CV.ee tehisaru- ja andmetööde kuulutused rühmade kaupa (Kadri 8.11.2026, andmed TOOELU igapäevasest tööst).
    Rühmad ei kattu, seega neid võib liita. „Firma üldnõue“ on eraldi, et üks firma ei paisutaks oskuste rühma."""
    K = A.get("ai_kuulutused")
    if not K or not K.get("ruhmad"):
        return ""
    from lehed_ulevaade import kpi_plaat
    from komponendid import lihtribad
    R = K["ruhmad"]
    for g in ("ai_amet", "andmeamet", "ai_oskus"):
        if g not in R:
            raise AndmeViga(f"ai-tookuulutused.json: rühm {g} puudub")
    kp_ = K["uuendatud"][:10]
    url = "https://www.cv.ee/et/search"
    pohi = ("ai_amet", "andmeamet", "ai_oskus")
    kirj = {"ai_amet": "pealkirjas AI, ML, LLM, andmeteadlane jms",
            "andmeamet": "pealkirjas andmed, data, BI, analytics",
            "ai_oskus": "muu amet, kuulutus <b>mainib tehisaru</b>"}
    plaadid = "".join(
        kpi_plaat({"ai_amet": "tk-ai", "andmeamet": "tk-andmed", "ai_oskus": "tk-oskus"}[g], TK_NIMI[g], _arvt(R[g]["arv"]), "",
                  {"muutus": (f'<span class="u-l uus">+{R[g]["uusi"]} uut</span> nädalaga', ""), "tekst": kirj[g]},
                  a(url, "CV.ee"), fookus=(g == "ai_oskus"))
        for g in pohi)
    tooandjad, maakonnad = {}, {}
    n_tk = 0  # Kadri 11.11.2026: „Töötukassa kaudu“ ei ole tööandja ja tulp ei ütle midagi; see on graafiku all märkusena
    for g in pohi:
        for r in R[g].get("tooandjad", []):
            if r["nimi"] in TK_TOOANDJA:
                n_tk += r["arv"]
                continue
            tooandjad[r["nimi"]] = tooandjad.get(r["nimi"], 0) + r["arv"]
        for r in R[g].get("maakonnad", []):
            maakonnad[r["nimi"]] = maakonnad.get(r["nimi"], 0) + r["arv"]

    def ribad(d, n=10):
        read = sorted(d.items(), key=lambda x: -x[1])[:n]
        if not read:
            return ""
        lopp = max(v for _, v in read)
        samm = next(s for s in (2, 5, 10, 20, 50, 100) if lopp / s <= 5)
        lopp = -(-lopp // samm) * samm
        return lihtribad([(nm, v, str(v)) for nm, v in read], lopp, samm=samm, uhik="", fookus=0)
    kokku3 = sum(R[g]["arv"] for g in pohi)
    rows = []
    for r in sorted(K.get("kuulutused", []), key=lambda r: (r.get("avaldatud") or ""), reverse=True):
        uus = ' <span class="u-l uus">uus</span>' if r.get("uus") else ""
        kaug = {"FULLY_REMOTE": "kaugtöö", "HYBRID": "hübriid"}.get(r.get("kaugtoo") or "", "")
        otsi = " ".join([r["pealkiri"], r.get("tooandja") or "", r.get("maakond") or "", TK_NIMI.get(r["ruhm"], "")]).lower()
        rows.append(f'<tr data-ruhm="{e(r["ruhm"])}" data-kus="{e(r.get("maakond") or "")}" data-otsi="{e(otsi)}">'
                    f'<td class="n">{kp(r["avaldatud"]) if r.get("avaldatud") else ""}</td>'
                    f'<td><a href="{e(r["url"])}">{e(r["pealkiri"])}</a>{uus}<small>{e(TK_TOOANDJA.get(r.get("tooandja") or "", r.get("tooandja") or ""))}</small></td>'
                    f'<td>{e(TK_NIMI.get(r["ruhm"], r["ruhm"]))}</td><td>{e(r.get("maakond") or "")}{f"<small>{kaug}</small>" if kaug else ""}</td></tr>')
    ruhmad_k = collections.Counter(r["ruhm"] for r in K.get("kuulutused", []))
    r_nupud = "".join(f'<button type="button" data-r="{g}" aria-pressed="false">{e(TK_NIMI[g].lower())} ({ruhmad_k[g]})</button>'
                      for g in TK_NIMI if ruhmad_k.get(g))
    kus_k = collections.Counter(r.get("maakond") for r in K.get("kuulutused", []) if r.get("maakond"))
    kus_val = "".join(f'<option value="{e(m)}">{e(m)} ({c})</option>' for m, c in kus_k.most_common())
    fn = R.get("ai_firma_noue")
    fn_t = ""
    if fn:
        top_fn = ", ".join(f'{e(x["nimi"])} {x["arv"]}' for x in fn.get("tooandjad", [])[:5])
        fn_t = (f'<p>Lisaks on <b>{_arvt(fn["arv"])} kuulutust</b> ({fn["uusi"]} uut), kus tehisaru on ainult tööandja ühises lauses, '
                f'mis kordub firma eri kuulutustes (nt „AI tööriistade igapäevane kasutus on ootus“). Need on loendis rühmana „Firma üldnõue“, '
                f'mitte oskuste all. Enim: {top_fn}.</p>')
    return f"""
<div class="g12">
<section class="pn sp12" id="ai-kuulutused" aria-labelledby="h-ai-kuulutused">
  <div class="pn-h"><h2 id="h-ai-kuulutused">{_arvt(K["kuulutusi_kokku"])} kuulutusest {R["ai_amet"]["arv"] + R["andmeamet"]["arv"]} on tehisaru- või andmeametid, aga <b>{R["ai_oskus"]["arv"]} muu ameti kuulutust mainib tehisaru</b></h2></div>
  <p class="ps">CV.ee, {kp(kp_)}. „Uus“ = avaldatud viimase 7 päeva jooksul.</p>
  <div class="plaadid kaks">{plaadid}</div>
  <div class="kaks tk-ribad">
    <div><p class="gt">Kes otsib: enim kuulutusi ({kokku3} kuulutust kolmes rühmas)</p>{ribad(tooandjad)}{f'<p class="ps">Lisaks {n_tk} kuulutust Töötukassa kaudu: CV.ee neis tööandjat ei nimeta, need on loendis allpool.</p>' if n_tk else ""}</div>
    <div><p class="gt">Kus: maakond</p>{ribad(maakonnad, 8)}</div>
  </div>
  <p class="gt">Kõik kuulutused</p>
  <div class="h-otsing" data-uhik="kuulutust"><input type="search" placeholder="nt analüütik, Bolt, Tartu" aria-label="Otsi kuulutustest">
    <div class="u-f" role="group" aria-label="Rühm"><button type="button" data-r="" aria-pressed="true">kõik</button>{r_nupud}</div>
    <select data-kus aria-label="Maakond"><option value="">kõik maakonnad</option>{kus_val}</select>
    <span class="h-loe" aria-live="polite"></span></div>
  {tbl_div("-4 1:6.6em 3:6.6em")}<table class="h-tabel" data-piir><thead><tr><th scope="col">Avaldatud</th><th scope="col">Kuulutus ja tööandja</th><th scope="col">Rühm</th><th scope="col">Kus</th></tr></thead>
  <tbody>{"".join(rows)}</tbody></table></div>
  <details><summary>Täpsustused: firma üldnõue ja mida see ei näita</summary><div>{fn_t}<p>{e(K.get("piirangud", ""))} Liigitus on märksõnapõhine, inimene pole seda kontrollinud.</p></div></details>
</section>
{_tk_leiud(A, K, R, kp_, url)}
</div>"""
