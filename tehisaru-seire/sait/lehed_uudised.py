"""Uudised, Hanked ja Töö publikatsioonid (Kadri 5.11.2026 23:17: need olid uuelt saidilt puudu).

Andmed tulevad Kadri loal projekti kaustast toodud avalikust hetkeseisust (sait/vota_kaasa.py):
sisu/uudised.jsonl, sisu/uudiste-vaited.json, sisu/uudiste-olek.json, sisu/hanked-leht.json, sisu/publikatsioonid.json.
Iga pealkirja number tuleb andmetest; pealkirjad, mida mall ei kata, kontrollitakse abi.kontrolli() abil.
"""
import collections
import datetime
import re

from abi import ARVSONAD, SEESTYTLEV, a, kontrolli, link, jaga, pea, seotud
from andmekiht import AndmeViga
from komponendid import e, kp, pr

HANKED_URL = "https://riigihanked.riik.ee/"
OPENALEX_URL = "https://openalex.org/"
OECD_URL = "https://doi.org/10.1787/c2c09a06-en"

LIIK = {"uudis": ("uudis", "vaikne"), "aruanne": ("aruanne", ""), "uuring": ("uuring", ""),
        "arvamus": ("arvamus", "arv"), "eksitav": ("eksitav", "risk")}
TEEMA = {"koondamine": "koondamine", "ai_too": "tehisaru ja töö", "ai_uldine": "tehisaru", "andmed": "andmed",
         "uuring": "uuring", "eksitav": "eksitav"}
ROLL = {"otsene": "tehisaru otsene põhjus", "osaline": "tehisaru üks põhjus", "kaudne": "tehisaru kaudselt",
        "tulevikus": "tehisaru võib tulevikus", "ei_mainita": "tehisaru ei mainita", "statistika": "statistika"}
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

def _uudis(r):
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
    if jatk:
        sildid.append('<span class="u-t">jätkulugu</span>')
    if r.get("_uus"):
        sildid.insert(0, '<span class="u-l uus">uus</span>')  # oranž (Kadri 7.11.2026)
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
    return (f'<li data-teema="{e(r.get("teema", ""))}" data-liik="{e(r["liik"])}">'
            f'<span class="d">{kp(r["kuupaev"])}</span>'
            f'<div><a href="{e(r["url"])}">{e(r["pealkiri"])}</a>'
            f'<p class="u-k">{arv}{e(pohjus)}</p>'
            f'<p class="u-m">{"".join(sildid)}<span class="u-a">{e(r["allikas"])}</span></p></div></li>')


def _seis(read, kontroll):
    """Kas viimasel kontrollil lisandus selle piirkonna uudiseid (Kadri 6.11: tühi päev ei tohi paista nagu katkine leht)."""
    if not kontroll:
        return ""
    paev = kontroll[:10]
    uued = sum(1 for r in read if r.get("lisatud") == paev)
    if uued:
        return f'<p class="ps u-seis">Viimane kontroll {kp(paev)} kell {kontroll[11:16]}. Sel päeval lisandus <b>{uued}</b>, märgitud „uus“.</p>'
    return f'<p class="ps u-seis">Viimane kontroll {kp(paev)} kell {kontroll[11:16]}. Sel päeval uusi uudiseid ei lisandunud.</p>'


def _uudiste_paneel(rid, pealkiri, read, sp, kontroll=None):
    teemad = []
    for r in read:
        t = r.get("teema")
        if t in TEEMA and t not in teemad:
            teemad.append(t)
    filter_ = "".join(f'<button type="button" data-f="{e(t)}">{e(TEEMA[t])}</button>' for t in teemad)
    return f"""
<section class="pn {sp}" id="{rid}" aria-labelledby="h-{rid}">
  <div class="pn-h"><h2 id="h-{rid}">{pealkiri}</h2></div>
  {_seis(read, kontroll)}
  <div class="u-f" role="group" aria-label="Vali teema"><button type="button" data-f="" aria-pressed="true">kõik ({len(read)})</button>{filter_}</div>
  <ul class="u-voog" data-piir-li="12">{"".join(_uudis(r) for r in read)}</ul>
</section>"""


def uudised(A, vaade, vaated=None):
    U = _vaja(A, "uudised", "uudised.jsonl")
    V = _vaja(A, "uudiste_vaited", "uudiste-vaited.json")
    O = _vaja(A, "uudiste_olek", "uudiste-olek.json")
    kontrolli(vaade, "Eestist ja maailmast", "arvamus")
    U = sorted((dict(r, _uus=r.get("lisatud") == O["viimane_kontroll"][:10]) for r in U), key=lambda r: r["kuupaev"], reverse=True)
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
    korjaja = "Seire uudistekogumine"
    aside = kpi_pais(
        kpi_plaat("ud-ee", "Eesti uudised", str(len(ee)), "",
                  {"muutus": (f"+{uusi(ee)} nädalaga", f'uusim {kp(ee[0]["kuupaev"])}' if ee else "")}, korjaja, fookus=True),
        kpi_plaat("ud-maailm", "Maailma uudised, aruanded ja uuringud", str(len(m)), "",
                  {"muutus": (f"+{uusi(m)} nädalaga", f'uusim {kp(m[0]["kuupaev"])}' if m else "")}, korjaja),
        kpi_plaat("ud-suured", "Suured uudised", str(len(suured)), "",
                  {"tekst": f"üle 50 koondatu, riigi otsus, statistika · <b>{arvamusi} arvamuslugu</b>"}, korjaja),
        kpi_plaat("ud-kontroll", "Viimane kontroll", f"{vk.day}.{vk.month:02d}", f"{vk:%H:%M}",
                  {"tekst": f'<b>{korras}/{len(O["allikad"])}</b> allikat vastas · 7.23 ja 17.53'}, korjaja),
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
    sec_u = ('<div class="g12">'
             + _uudiste_paneel("eesti-uudised", f"Eesti: <b>{len(ee)} uudist</b>, neist {sum(r['liik'] == 'arvamus' for r in ee)} arvamust", ee, "sp6", viimane)
             + _uudiste_paneel("maailma-uudised", f"Maailm: <b>{len(m)} uudist</b>, aruannet ja uuringut", m, "sp6", viimane)
             + "</div>")
    return jaga(A, vaade, lead, [], [
        ("uudised", [("eesti-uudised", "Eesti"), ("maailma-uudised", "Maailm")], sec_u),
        ("allikad", [("uudiste-allikad", "Allikad")], sec_k),
    ], aside=aside)


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
    p0, p1 = V["periood"]
    K = H["kontsentratsioon"]
    hind = H["hindamine"]
    val = hind["hindamine"]["valitud"]
    tul = hind["hindamine"]["tulemused"][val]
    lev = hind["levimus"]

    from lehed_ulevaade import kpi_pais, kpi_plaat, kpi_riba
    h1, h0 = aastad[-1], aastad[-2]
    yks = {g: V[g]["uks_pakkuja_osakaal"] for g in ("ai_andmed", "it_muud", "koik")}
    katseline = ""  # Kadri 8.11.2026 16:29: pimeülevaatus tehtud, katselisuse märgid ära
    aside = kpi_pais(
        kpi_plaat("hk-arv", "Tehisaru- ja andmehanked", str(h1["ai_andmed"]), f'{h1["aasta"]}{"*" if poolik else ""}',
                  {"muutus": (f'{h0["aasta"]} kokku {h0["ai_andmed"]}',
                              f'{pr(h1["ai_andmed_osakaal"])}% kõigist hangetest' + (" · * aasta pooleli" if poolik else ""))},
                  a(HANKED_URL, "Riigihangete register") + katseline, fookus=True),
        kpi_plaat("hk-kvaliteet", "Hindas ka kvaliteeti, mitte ainult hinda", f'{pr(kv["ai_andmed"], 0)}%', f"{p0}–{p1}",
                  {"tekst": f'kõigis hangetes {pr(kv["koik"], 0)}%',
                   "riba": kpi_riba(kv["ai_andmed"], 100, vrd=round(kv["it_muud"]), vrd_nimi="teised IT-hanked")},
                  "Hindamiskriteeriumid registris"),
        kpi_plaat("hk-uks", "Said ainult ühe pakkumuse", f'{pr(yks["ai_andmed"], 0)}%', f"{p0}–{p1}",
                  {"tekst": f'kõigis hangetes {pr(yks["koik"], 0)}%',
                   "riba": kpi_riba(yks["ai_andmed"], 100, vrd=round(yks["it_muud"]), vrd_nimi="teised IT-hanked")},
                  f'Pakkumuste arv teada {V["ai_andmed"]["pakkumusi_teada"]} hankel'),
        kpi_plaat("hk-tapsus", "Tuvastuse täpsus", f'{pr(tul["tapsus"] * 100, 0)}%', "",
                  {"tekst": f'leiab <b>{pr(tul["saagis"] * 100, 0)}%</b> hangetest (saagis)'},
                  f'Masina vs masina märgendid; käsitsi kokkulangevus {KASITSI["kokku"]}%' + katseline),
    )
    lead = ("Tehisaru = "
            "pealkirjas või kirjelduses on tehisaru märksõna; andmed = andmeladu, -haldus, -analüüs jms. "
            "Tehisaru uuringute ja mõjuanalüüside hankeid eraldi veel ei loeta.")

    # 1. Ainult viimane aasta (sisuloogika 6.11.2026, Kadri otsus 5): aastate võrdlust ei näidata, kuni vähemalt
    # 100 hanget on inimese pimesi märgistatud (lõplik viitevalim 8.11.2026).
    u = aastad[-1]
    sec_aastad = f"""
<section class="pn sp5" id="aastad" aria-labelledby="h-aastad">
  <div class="pn-h"><h2 id="h-aastad">Klassifikaator leidis {u["aasta"]}. aastal{" kuni " + kp(seis) if poolik else ""} <b>{u["ai_andmed"]} tehisaru- ja andmehanget</b>, {pr(u["ai_andmed_osakaal"])}% kõigist</h2></div>
  <p class="ps">Neist {u["ai_marksonaga"]} on tehisaru märksõnaga ja {u["ai_andmed"] - u["ai_marksonaga"]} andmehanked. Aastate võrdlust ei näidata enne, kui klassifikaator on uuendatud pärast 100 hanke pimesi ülevaatust.</p>
  {_viis_rida(f"Klassifikaatori leitud hanked {u['aasta']}, arv", [("tehisaru", u["ai_marksonaga"], True), ("andmed", u["ai_andmed"] - u["ai_marksonaga"], False)], uhik="", k=0)}
</section>"""

    # 2. Innovatsioonimärk vs 2% siht
    inn = [r for r in aastad if r.get("innovatsioonimark_osakaal") is not None]
    inn_read = "".join(
        f'<div class="vr{" f" if r["aasta"] == inn[-1]["aasta"] else ""}"><span class="vr-n">{r["aasta"]}{"*" if (poolik and r["aasta"] == viimane_t) or r is inn[0] else ""}</span>'
        f'<span class="vr-r"><i style="width:{r["innovatsioonimark_osakaal"] / 2.5 * 100:.1f}%"></i><b class="vr-siht" style="left:{2 / 2.5 * 100:.1f}%"></b></span>'
        f'<span class="vr-v">{pr(r["innovatsioonimark_osakaal"])}%</span></div>' for r in inn)
    sec_inn = f"""
<section class="pn sp7" id="innovatsioon" aria-labelledby="h-innovatsioon">
  <div class="pn-h"><h2 id="h-innovatsioon">Innovatsioonimärgiga hankeid oli {inn[-1]["aasta"]}. aastal <b>{pr(inn[-1]["innovatsioonimark_osakaal"])}%</b>, siht on 2%; märgi määratlus on kontrollimata</h2></div>
  <p class="ps">Osa eForms-hangetest, millele hankija märkis innovatsiooni; * osaline aasta (eForms algas 09/2023). Siht: {a(OECD_URL, "OECD 2026")}. Rahandusministeeriumi 0,2% (2023) võib olla teise määratlusega.</p>
  <div class="viis">{inn_read}</div>
  <p class="kr-leg"><span><i class="kr-t siht"></i>siht 2%</span></p>
</section>"""

    # 3. Kuidas hangitakse
    G = [("tehisaru ja andmed", "ai_andmed", True), ("muud IT-hanked", "it_muud", False), ("kõik hanked", "koik", False)]
    viisid = "".join([
        _viis_rida("Hindas ka kvaliteeti, %", [(n, kv[g], f) for n, g, f in G], k=0),
        _viis_rida("Ainult üks pakkumus, %", [(n, V[g]["uks_pakkuja_osakaal"], f) for n, g, f in G], k=0),
        _viis_rida("Hange katkes, %", [(n, V[g]["katkes_osakaal"], f) for n, g, f in G], k=0),
        _viis_rida("Pakkumusi (mediaan)", [(n, V[g]["pakkumusi_mediaan"], f) for n, g, f in G], uhik="", k=0),
    ])
    sec_viis = f"""
<section class="pn sp8" id="viis" aria-labelledby="h-viis">
  <div class="pn-h"><h2 id="h-viis">Tehisaru- ja andmehangetes hinnatakse kvaliteeti <b>sagedamini kui teistes IT-hangetes</b> ({p0}–{p1})</h2></div>
  <p class="ps">Hankeid: tehisaru ja andmed {V["ai_andmed"]["hankeid"]}, muud IT {_arv(V["it_muud"]["hankeid"])}, kõik {_arv(V["koik"]["hankeid"])}. Pakkumuste arv on teada osal hangetest; {p1}. aasta pakkumusi registri avaandmetes pole.</p>
  <div class="viisid">{viisid}</div>
</section>"""

    # 4. Hankijad
    top = H["hankijad_top"][:10]
    tmax = top[0][1]
    t_read = "".join(f'<div class="vr"><span class="vr-n" title="{e(n)}">{e(n)}</span><span class="vr-r"><i style="width:{c / tmax * 100:.1f}%"></i></span><span class="vr-v">{c}</span></div>' for n, c in top)
    sec_hankijad = f"""
<section class="pn sp4" id="hankijad" aria-labelledby="h-hankijad">
  <div class="pn-h"><h2 id="h-hankijad">{K["top10_protsenti_hankijaid"]} hankijat {K["hankijaid"]}-st teevad <b>{pr(K["nende_osakaal"], 0)}%</b> tehisaru- ja andmehangetest</h2></div>
  <p class="ps">{p0}–{p1}. {K["uks_hange_hankijaid"]} hankijat tegi ainult ühe sellise hanke. Kümme suurimat:</p>
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
      <div class="tbl"><table class="lits-m" aria-describedby="g-lits-as"><thead><tr><th scope="col">Asutus</th>{m_pais}<th scope="col" class="v">Kokku</th></tr></thead>
      <tbody>{m_read}</tbody></table></div>
      <p class="gs">Lahtris on hangete arv ja peamine toode.</p>
    </div>
  </div>
  <details>
    <summary>Näita kõiki {len(LI)} litsentsihanget koos eesmärgiga</summary>
    <div class="tbl"><table data-piir><thead><tr><th scope="col">Aasta</th><th scope="col">Hange ja hankija</th><th scope="col">Toode</th><th scope="col">Eesmärk</th><th scope="col" class="v">Eeldatav maksumus</th></tr></thead>
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
            tunnused.append('<span class="u-t">innovatsioon</span>')
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
  <div class="pn-h"><h2 id="h-loend">Leia sarnane hange, mida eeskujuks võtta: <b>{n_hea} head näidet</b> {len(loend)}-st</h2></div>
  <p class="ps">Hea näide: kvaliteeti hinnati, pakkumusi oli vähemalt kaks ja hange ei katkenud.</p>
  <div class="h-otsing"><input type="search" placeholder="nt andmeladu, kõnetuvastus, Tableau" aria-label="Otsi hangetest">
    <div class="u-f" role="group" aria-label="Rühm"><button type="button" data-r="" aria-pressed="true">kõik</button><button type="button" data-r="ai">tehisaru</button><button type="button" data-r="andmed">andmed</button><button type="button" data-r="hea">head näited</button></div>
    <span class="h-loe" aria-live="polite"></span></div>
  <div class="tbl"><table class="h-tabel" data-piir><thead><tr><th scope="col">Kuupäev</th><th scope="col">Hange ja hankija</th><th scope="col">Rühm</th><th scope="col" class="v">Eeldatav maksumus</th><th scope="col">Hindamine</th><th scope="col">Tunnused</th></tr></thead>
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
  <div class="pn-h"><h2 id="h-tapsus">Klassifikaator leiab umbes <b>{pr(tul["saagis"] * 100, 0)}%</b> tehisaru- ja andmehangetest ning {pr(tul["tapsus"] * 100, 0)}% leitutest on õiged</h2></div>
  <p class="ps">Testitud {hind["hindamine"]["test"]} hankel alates {hind["hindamine"]["testi_alates"]}. aastast. Märgendid ({hind["margendid"]["kokku"]}) tegi Claude; {KASITSI["n"]} neist vaadati käsitsi pimesi üle: lõplikus viitevalimis on {KASITSI["viide"]["ei"]} ei, {KASITSI["viide"]["andmed"]} andmehanget ja {KASITSI["viide"]["ai"]} tehisaruhanget. Masinmärgendid langevad viitega kokku {KASITSI["kokku"]}% (kappa {KASITSI["kappa"]}), käsitsi esmamärgendid {KASITSI["kasitsi"]}% (kappa {KASITSI["kappa_kasitsi"]}). Täpsus ja saagis on veel mõõdetud masina märgendite vastu. eForms-hangetest ({_arv(lev["hankeid"])}) on valimi põhjal umbes {lev["valimi_pohjal"]["hinnang"]} tehisaru- või andmehanget (95% vahemik {vmin}–{vmax}); klassifikaator leidis {lev["valitud_leidis"]}.</p>
  <div class="tbl"><table><thead><tr><th scope="col">Meetod</th><th scope="col" class="v">Täpsus (95%)</th><th scope="col" class="v">Saagis (95%)</th><th scope="col" class="v">F1</th></tr></thead>
  <tbody>{"".join(t_rows)}</tbody></table></div>
</section>
</div>"""
    # Kadri otsus 6.11.2026 22:11: Hanked jääb menüüsse, aga selge hoiatussildiga, kuni 100 hanget on käsitsi kontrollitud
    # Kadri 8.11.2026 (kommentaar lehel): „käsitsi ülevaatus on tehtud, uuenda lehte“
    hoiatus = ('<div class="hoiatus" role="note"><p><b>Masinmärgistus, käsitsi osaliselt kontrollitud.</b> ' + e(KASITSI_LAUSE)
               + ' Aastate võrdlus ja kindlad järeldused tulevad pärast klassifikaatori uuendamist.</p></div>')
    return (pea(A, vaade, lead, [("aastad", "Viimane aasta"), ("viis", "Kuidas hangitakse"), ("hankijad", "Hankijad"), ("litsentsid", "Litsentsid"), ("loend", "Leia hea näide"), ("tapsus", "Kui täpne")], [], aside=aside) + hoiatus
            + '<div class="g12">' + sec_aastad + sec_inn + "</div>"
            + '<div class="g12">' + sec_viis + sec_hankijad + "</div>"
            + sec_lits
            + sec_loend + sec_tapsus
            + seotud(vaated, [("avalik-sektor", "Avalik sektor: kas uuendused jõuavad laiendamiseni"), ("reeglid", "Tehisaru määrus: tähtajad")]))


# ---------------------------------------------------------------- Töö: mida uuritakse

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
  <div class="pn-h"><h2 id="h-uuritakse">Tehisarust ja tööst ilmus {a1["aasta"]}. aastal <b>{_arv(a1["koik"])} publikatsiooni</b>, {pr(kord)} korda rohkem kui {a0["aasta"]}</h2></div>
  <p class="ps">Teadusartiklid ja töödokumendid aastas ({a(OPENALEX_URL, "OpenAlex")}, otsing seisuga {kp(P["meta"]["aeg"][:10])}). * aasta pole läbi.</p>
  <div class="uu-kaks">
    <div><p class="gt">Publikatsioone aastas</p><div class="aastatulbad">{tulbad}</div></div>
    <div><p class="gt">Teema osa {aastad[-1]["aasta"]}. aasta publikatsioonidest</p><div class="viis teemad">{t_read}</div></div>
  </div>
</section>"""
    grupid = [("uusimad", "Uusimad"), ("aasta", "Enim tsiteeritud, 12 kuud"), ("koik", "Enim tsiteeritud alates 2023"), ("eesti", "Eesti autorid")]
    nupud, osad = [], []
    for i, (g, nimi) in enumerate(grupid):
        read = [r for r in P["tood"] if r["grupp"] == g]
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
        osad.append(f'<div role="tabpanel" id="pub-{g}" aria-labelledby="tab-{g}"{"" if i == 0 else " hidden"}><div class="tbl"><table data-piir><thead><tr><th scope="col">Avaldatud</th><th scope="col" class="v">Tsiteeritud</th><th scope="col">Publikatsioon ja kanal</th></tr></thead><tbody>{li}</tbody></table></div></div>')
    sec_t = f"""
<section class="pn sp12" id="publikatsioonid" aria-labelledby="h-publikatsioonid">
  <div class="pn-h"><h2 id="h-publikatsioonid">Mida maailmas ja Eestis uuritakse: uusimad ja enim tsiteeritud tööd</h2></div>
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
  <div class="pn-h"><h2 id="h-eesti-allikad">Eesti uuringud ja raportid tehisarust ja tööst: <b>{len(ee)}</b></h2></div>
  <p class="ps">Arenguseire Keskuse, OSKA ja teiste Eesti allikate tööd, mis käsitlevad tehisaru, tootlikkust või oskusi.{kpi_t or " Uusimad eespool."}</p>
  <div class="tbl"><table data-piir class="ee-tbl"><thead><tr><th scope="col">Avaldatud</th><th scope="col">Töö</th><th scope="col">Põhinumbrid</th><th scope="col">Allikas</th></tr></thead><tbody>{e_read}</tbody></table></div>
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
            f'<small>tehisaru: {e(ROLL_NIMI[j["roll"]])}</small></div>' for j in js)
        pohjused = "".join(
            f'<div class="pk-k"><p>{e(j["pohjus"])}</p><small>{a(j["url"], j["allikas"])}'
            f'{" · uudisest, kontrollimata" if j.get("kandidaat") else ""}</small></div>' for j in js)
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
  <div class="pn-h"><h2 id="h-palkamine">{h2} otsib praegu Eestis töötajaid <b>{ARVSONAD.get(len(otsivad), len(otsivad))}</b> (kokku {kuulutusi} kuulutust){sama_t}</h2></div>
  <p class="ps">Tööpakkumiste lehed on kontrollitud {kp(kp_min)}. Sinise äärega ametiliik on sama, mida koondatakse.</p>
  <div class="tbl"><table class="pk"><thead><tr><th scope="col">Ettevõte</th><th scope="col">Koondab Eestis</th><th scope="col">Põhjus ettevõtte sõnul</th><th scope="col">Kaotab</th><th scope="col">Otsib praegu Eestis</th></tr></thead>
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
    h2 = (f'{kp(kp_)} oli {loendid} <b>tööpakkumist</b>; suurim valdkond oli ' + " ja ".join(suurim))

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
        veerud = [f'<div><p class="gt">Mis ametivaldkonnas</p><p class="ps">{a(p["ametivaldkond_url"], "portaali kategooriad")}, 12 suuremat</p>{ribad(valdkonnad(p))}</div>']
        if linn or mk:
            kt = ("; " + ", ".join(f'{e(r["nimi"]).lower()} {_arvt(r["arv"])}' for r in kaug)) if kaug else ""
            veerud.append(f'<div><p class="gt">Kus: linnad</p><p class="ps">{a(p["asukoht_url"], "portaali asukohad")}{kt}</p>{ribad(linn or mk, 10)}</div>')
        if top:
            veerud.append(f'<div><p class="gt">Kes: enim kuulutusi avaldanud tööandjad</p><p class="ps">{a(p["top_tooandjad_url"], "portaali tööandjad")}, 12 suuremat</p>{ribad(top)}</div>')
        else:
            pohjus = p.get("top_tooandjad_pohjus") or p.get("puudub_pohjus") or ""
            veerud.append(f'<div><p class="gt">Kes: tööandjad</p><p class="ps">Tööandjate arve ei õnnestunud lugeda.</p></div>')
        mk_t = ""
        if mk:
            mk_t = ('<details><summary>Maakonnad</summary><div>' + "".join(f'<span class="tp-m">{e(r["nimi"])} <b>{_arvt(r["arv"])}</b></span>' for r in mk) + '</div></details>')
        nupud.append(f'<button type="button" role="tab" aria-selected="{"true" if i == 0 else "false"}" aria-controls="{pid}" id="tab-{pid}">{e(p["portaal"])} ({_arvt(p["kuulutusi_kokku"])})</button>')
        osad.append(f'<div role="tabpanel" id="{pid}" aria-labelledby="tab-{pid}"{"" if i == 0 else " hidden"}><div class="tp-kolm">{"".join(veerud)}</div>{mk_t}</div>')
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
  <details><summary>Kõik portaalid ja kuidas arv loeti</summary><div><p>Kategooriad on portaali omad; üks kuulutus võib olla mitmes kategoorias.{ilma_t}</p><div class="tbl"><table><thead><tr><th scope="col">Portaal</th><th scope="col" class="v">Kuulutusi</th><th scope="col">Loetud</th><th scope="col">Lehel oli</th></tr></thead><tbody>{pt}</tbody></table></div></div></details>
</section>
</div>"""


# ---------------------------------------------------------------- Töö: tehisaru- ja andmetööde kuulutused

TK_TOOANDJA = {"Töötukassa vahendatud pakkumised": "Töötukassa kaudu (eri tööandjad)"}
TK_NIMI = {"ai_amet": "Tehisaru amet", "andmeamet": "Andmeamet", "ai_oskus": "Tehisaru muus ametis",
           "ai_firma_noue": "Firma üldnõue"}


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
    for g in pohi:
        for r in R[g].get("tooandjad", []):
            nm = TK_TOOANDJA.get(r["nimi"], r["nimi"])
            tooandjad[nm] = tooandjad.get(nm, 0) + r["arv"]
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
    <div><p class="gt">Kes otsib: enim kuulutusi ({kokku3} kuulutust kolmes rühmas)</p>{ribad(tooandjad)}</div>
    <div><p class="gt">Kus: maakond</p>{ribad(maakonnad, 8)}</div>
  </div>
  <p class="gt">Kõik kuulutused</p>
  <div class="h-otsing" data-uhik="kuulutust"><input type="search" placeholder="nt analüütik, Bolt, Tartu" aria-label="Otsi kuulutustest">
    <div class="u-f" role="group" aria-label="Rühm"><button type="button" data-r="" aria-pressed="true">kõik</button>{r_nupud}</div>
    <select data-kus aria-label="Maakond"><option value="">kõik maakonnad</option>{kus_val}</select>
    <span class="h-loe" aria-live="polite"></span></div>
  <div class="tbl"><table class="h-tabel" data-piir><thead><tr><th scope="col">Avaldatud</th><th scope="col">Kuulutus ja tööandja</th><th scope="col">Rühm</th><th scope="col">Kus</th></tr></thead>
  <tbody>{"".join(rows)}</tbody></table></div>
  <details><summary>Täpsustused: firma üldnõue ja mida see ei näita</summary><div>{fn_t}<p>{e(K.get("piirangud", ""))} Liigitus on märksõnapõhine, inimene pole seda kontrollinud.</p></div></details>
</section>
</div>"""
