"""Uudised, Hanked ja Töö publikatsioonid (Kadri 5.11.2026 23:17: need olid uuelt saidilt puudu).

Andmed tulevad Kadri loal projekti kaustast toodud avalikust hetkeseisust (sait/vota_kaasa.py):
sisu/uudised.jsonl, sisu/uudiste-vaited.json, sisu/uudiste-olek.json, sisu/hanked-leht.json, sisu/publikatsioonid.json.
Iga pealkirja number tuleb andmetest; pealkirjad, mida mall ei kata, kontrollitakse abi.kontrolli() abil.
"""
import datetime

from abi import ARVSONAD, SEESTYTLEV, a, kontrolli, link, pea
from andmekiht import AndmeViga
from komponendid import e, kp, pr

HANKED_URL = "https://riigihanked.riik.ee/"
OPENALEX_URL = "https://openalex.org/"
OECD_URL = "https://doi.org/10.1787/c2c09a06-en"

LIIK = {"uudis": ("uudis", ""), "aruanne": ("aruanne", ""), "uuring": ("uuring", ""),
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
    if r.get("teema") in TEEMA and r.get("teema") != r.get("liik"):
        sildid.append(f'<span class="u-t">{e(TEEMA[r["teema"]])}</span>')
    if r.get("teema") == "koondamine" and r.get("ai_roll") in ROLL:
        sildid.append(f'<span class="u-t{" s" if r["ai_roll"] in ("otsene", "osaline") else ""}">{e(ROLL[r["ai_roll"]])}</span>')
    if r.get("_jatk"):
        sildid.append(f'<span class="u-t s">jätkulugu</span>')
    if r.get("_uus"):
        sildid.insert(0, '<span class="u-l suur">uus</span>')
    if r.get("suur"):
        sildid.append('<span class="u-l suur">suur uudis</span>')
    lv = r.get("levik")
    if lv and isinstance(lv.get("arv"), int) and lv["arv"] > 1:
        # Populaarsus = mitu väljaannet sama lugu kajastas (klikke väljaanded ei avalda; Kadri 6.11.2026)
        kellelt = ", ".join(lv.get("allikad") or [])
        sildid.append(f'<span class="u-t lv" title="Kajastasid: {e(kellelt)} (kontrollitud {e(kp(lv.get("kontrollitud", "")) if lv.get("kontrollitud") else "")})">{lv["arv"]} väljaannet</span>')
    if not r.get("kontrollitud"):
        sildid.append('<span class="u-t">loetud ainult pealkiri</span>')
    arv = f' <b>{e(r["arv_tekst"])}.</b>' if r.get("arv_tekst") else ""
    return (f'<li data-teema="{e(r.get("teema", ""))}" data-liik="{e(r["liik"])}">'
            f'<span class="d">{kp(r["kuupaev"])}</span>'
            f'<div><a href="{e(r["url"])}">{e(r["pealkiri"])}</a>'
            f'<p>{e(r.get("pohjus", ""))}{arv}</p>'
            f'<p class="u-m">{"".join(sildid)}<span class="u-a">{e(r["allikas"])}</span></p></div></li>')


def _seis(read, kontroll):
    """Kas viimasel kontrollil lisandus selle piirkonna uudiseid (Kadri 6.11: tühi päev ei tohi paista nagu katkine leht)."""
    if not kontroll:
        return ""
    paev = kontroll[:10]
    uued = sum(1 for r in read if r.get("lisatud") == paev)
    if uued:
        return f'<p class="ps u-seis">Viimane kontroll {kp(paev)} {kontroll[11:16]}: lisandus <b>{uued}</b>, märgitud „uus“.</p>'
    return f'<p class="ps u-seis">Viimane kontroll {kp(paev)} {kontroll[11:16]}: uusi uudiseid ei lisandunud.</p>'


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
    nahtud = set()
    for r in reversed(U):  # vanimast uuemani: sama ettevõtte hilisem lugu on jätkulugu
        if r.get("ettevote"):
            r["_jatk"] = r["ettevote"] in nahtud
            nahtud.add(r["ettevote"])
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
    ree = [
        (f'{len(ee)}', f'Eesti uudist; uusim {kp(ee[0]["kuupaev"])}.' if ee else "Eesti uudiseid pole.",
         e(ee_s["pealkiri"]) if ee_s else ""),
        (f'{len(m)}', f'maailma uudist, aruannet või uuringut; uusim {kp(m[0]["kuupaev"])}.' if m else "Maailma uudiseid pole.",
         e(m_s["pealkiri"]) if m_s else ""),
        (f'{len(suured)}', 'suurt uudist (koondamine üle 50 inimese, riigi otsus, uus ametlik statistika).',
         f'{arvamusi} on arvamused, mitte tõendid'),
        (f'{vk.day}.{vk.month:02d} {vk:%H:%M}', f'viimane kontroll; {korras} allikat {len(O["allikad"])}-st vastas.',
         "Uueneb iga päev, kui sait ühendatakse igapäevase kogumisega"),
    ]
    lead = ("Tehisaru, andmete ja tööturu uudised usaldusväärsetest allikatest. Iga uudis on märgitud liigiga: "
            "uudis, aruanne, uuring, arvamus või eksitav. Arvamus ei ole tõend. Hoiame pealkirja, linki ja oma sõnadega kokkuvõtet.")

    v_read = []
    for v in sorted(V, key=lambda x: x["kuupaev"], reverse=True):
        h, kl = HINNANG.get(v["hinnang"], (v["hinnang"], "warn"))
        toend = "".join(f'<li>{a(t["url"], t["nimi"]) if t.get("url") else e(t["nimi"])}: {e(t["naitab"])} <small>({e(t["tugevus"])})</small></li>' for t in v["toendid"])
        v_read.append(f'<tr><td>„{e(v["vaide"])}“<small>{a(v["kes_url"], v["kes"])}</small></td>'
                      f'<td><span class="verd {kl}">{e(h)}</span></td><td>{e(v["kokkuvote"])}<ul class="u-toend">{toend}</ul></td></tr>')
    n_v = len(V)
    vale = sum(v["hinnang"] in ("vale", "eksitav") for v in V)
    sec_v = f"""
<div class="g12">
<section class="pn sp12" id="uudiste-vaited" aria-labelledby="h-uudiste-vaited">
  <div class="pn-h"><h2 id="h-uudiste-vaited">Uudistes kontrollitud väited: {ARVSONAD.get(n_v, n_v)}, neist <b>{ARVSONAD.get(vale, vale)} vale või eksitav</b></h2></div>
  <p class="ps">Väide kuulub väljaandele. Hinnang tuleb esmasest allikast. Kõik kontrollitud väited: {link(vaated, "kas-tosi", "Kas see on tõsi?")}.</p>
  <div class="tbl"><table class="u-vaited"><thead><tr><th scope="col">Väide ja väljaanne</th><th scope="col">Hinnang</th><th scope="col">Mida allikas ütleb</th></tr></thead>
  <tbody>{"".join(v_read)}</tbody></table></div>
</section>
</div>"""
    allikad = "".join(f'<li><span class="{"ok" if s["ok"] else "risk"}">{"vastas" if s["ok"] else "ei vastanud"}</span> {e(s["nimi"])}</li>' for s in O["allikad"])
    sec_k = f"""
<div class="g12">
<section class="pn sp12" id="uudiste-allikad" aria-labelledby="h-uudiste-allikad">
  <div class="pn-h"><h2 id="h-uudiste-allikad">Kust uudised tulevad</h2></div>
  <div class="g2 u-kuidas">
    <ul class="u-allikad">{allikad}</ul>
    <p class="ps">Allikad on ERR (eesti ja inglise keeles), uudisteotsing Eestis ja maailmas ning Challengeri kuuaruanne. Tasulise artikli puhul hoiame ainult pealkirja. „N väljaannet“ näitab, mitu eri väljaannet sama lugu kajastas. See asendab populaarsust, sest klikke väljaanded avalikult ei jaga. „Loetud ainult pealkiri“ tähendab, et artiklit ei avatud. Koondamise juures on see, mida ettevõte ise tehisaru kohta ütles, mitte meie hinnang. Kinnitatud Eesti koondamised on vaates {link(vaated, "too", "Töö", "koondamised")}.</p>
  </div>
</section>
</div>"""
    return (pea(A, vaade, lead, [("eesti-uudised", "Eesti"), ("maailma-uudised", "Maailm"), ("uudiste-vaited", "Väited"), ("uudiste-allikad", "Allikad")], ree)
            + '<div class="g12">'
            + _uudiste_paneel("eesti-uudised", f"Eesti: <b>{len(ee)} uudist</b>, neist {sum(r['liik'] == 'arvamus' for r in ee)} arvamust", ee, "sp6", viimane)
            + _uudiste_paneel("maailma-uudised", f"Maailm: <b>{len(m)} uudist</b>, aruannet ja uuringut", m, "sp6", viimane)
            + "</div>" + sec_v + sec_k)


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
    tais = [r for r in aastad if not (poolik and r["aasta"] == viimane_t)]
    a_t = tais[-1]
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

    ree = [
        (f'{a_t["ai_andmed"]} <small>{a_t["aasta"]}</small>', f'tehisaru- ja andmehanget ehk {pr(a_t["ai_andmed_osakaal"])}% kõigist {_arv(a_t["hankeid"])} hankest.',
         a(HANKED_URL, "riigihangete register")),
        (f'{pr(kv["ai_andmed"], 0)}%', f'neist hindas ka kvaliteeti ({p0}–{p1}); teistes IT-hangetes {pr(kv["it_muud"], 0)}%, kõigis {pr(kv["koik"], 0)}%.',
         "hindamiskriteeriumid registris"),
        (f'{pr(V["ai_andmed"]["uks_pakkuja_osakaal"], 0)}%', f'said ainult ühe pakkumuse; teistes IT-hangetes {pr(V["it_muud"]["uks_pakkuja_osakaal"], 0)}%, kõigis {pr(V["koik"]["uks_pakkuja_osakaal"], 0)}%.',
         f'pakkumuste arv teada {V["ai_andmed"]["pakkumusi_teada"]} hankel'),
        (f'{pr(tul["tapsus"] * 100, 0)}%', f'leitud hangetest on päriselt tehisaru- või andmehanked (täpsus); leitakse {pr(tul["saagis"] * 100, 0)}% neist (saagis).',
         "katseline klassifikaator, märgendid pole inimese kontrollitud"),
    ]
    lead = ("Riigihangete registri hanked, mille katseline klassifikaator märkis tehisaru- või andmetööks. Tehisaru = "
            "pealkirjas või kirjelduses on tehisaru märksõna; andmed = andmeladu, -haldus, -analüüs jms. "
            "Tehisaru uuringute ja mõjuanalüüside hankeid eraldi veel ei loeta.")

    # 1. Aastad
    rr = [(r["aasta"], r["ai_marksonaga"], r["ai_andmed"] - r["ai_marksonaga"], poolik and r["aasta"] == viimane_t) for r in aastad]
    lopp = max(x[1] + x[2] for x in rr) * 1.15
    ai_v = {r["aasta"]: r["ai_marksonaga"] for r in aastad}
    eelmised = [v for k, v in ai_v.items() if k < viimane_t]
    if ai_v[viimane_t] > max(eelmised):
        h_aastad = f'Tehisaruhankeid oli {viimane_t}. aastal juba <b>{ai_v[viimane_t]}</b>, rohkem kui ühelgi varasemal aastal'
    else:
        h_aastad = f'Tehisaru- ja andmehankeid oli {a_t["aasta"]}. aastal <b>{a_t["ai_andmed"]}</b>'
    sec_aastad = f"""
<section class="pn sp7" id="aastad" aria-labelledby="h-aastad">
  <div class="pn-h"><h2 id="h-aastad">{h_aastad}</h2><span class="chip exp">katseline</span></div>
  <p class="ps">Hangete arv aastas. Sinine = tehisaru märksõnaga, hall = andmehanked. {"* " + str(viimane_t) + " kuni " + kp(seis) + "." if poolik else ""}</p>
  {_tulbad_kihiti(rr, lopp, "Tehisaru- ja andmehanked aastas")}
  <p class="kr-leg"><span><i class="kr-t s"></i>tehisaru märksõnaga</span><span><i class="kr-t m"></i>andmehanked</span></p>
</section>"""

    # 2. Innovatsioonimärk vs 2% siht
    inn = [r for r in aastad if r.get("innovatsioonimark_osakaal") is not None]
    inn_read = "".join(
        f'<div class="vr{" f" if r["aasta"] == inn[-1]["aasta"] else ""}"><span class="vr-n">{r["aasta"]}{"*" if (poolik and r["aasta"] == viimane_t) or r is inn[0] else ""}</span>'
        f'<span class="vr-r"><i style="width:{r["innovatsioonimark_osakaal"] / 2.5 * 100:.1f}%"></i><b class="vr-siht" style="left:{2 / 2.5 * 100:.1f}%"></b></span>'
        f'<span class="vr-v">{pr(r["innovatsioonimark_osakaal"])}%</span></div>' for r in inn)
    sec_inn = f"""
<section class="pn sp5" id="innovatsioon" aria-labelledby="h-innovatsioon">
  <div class="pn-h"><h2 id="h-innovatsioon">Innovatsioonimärgiga hankeid oli {inn[-1]["aasta"]}. aastal <b>{pr(inn[-1]["innovatsioonimark_osakaal"])}%</b>, siht on 2%</h2></div>
  <p class="ps">Osa kõigist eForms-vormil hangetest, millele hankija märkis innovatsiooni. eForms algas 09/2023, seega {inn[0]["aasta"]} on osaline aasta; * = osaline aasta. Siht 2% aastaks 2027 on {a(OECD_URL, "OECD 2026 raportis")}.</p>
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
  <div class="pn-h"><h2 id="h-loend">Leia sarnane hange, mida eeskujuks võtta: <b>{n_hea} head näidet</b> {len(loend)}-st</h2><span class="chip exp">katseline</span></div>
  <p class="ps">Hea näide: kvaliteeti hinnati, pakkumusi oli vähemalt kaks ja hange ei katkenud. Otsi sõna järgi pealkirjast, hankijast või kirjeldusest.</p>
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
  <div class="pn-h"><h2 id="h-tapsus">Klassifikaator leiab umbes <b>{pr(tul["saagis"] * 100, 0)}%</b> tehisaru- ja andmehangetest ning {pr(tul["tapsus"] * 100, 0)}% leitutest on õiged</h2><span class="chip exp">katseline</span></div>
  <p class="ps">Testitud {hind["hindamine"]["test"]} hankel alates {hind["hindamine"]["testi_alates"]}. aastast. Märgendid ({hind["margendid"]["kokku"]}) tegi Claude, inimene pole neid veel kontrollinud. eForms-hangetest ({_arv(lev["hankeid"])}) on valimi põhjal umbes {lev["valimi_pohjal"]["hinnang"]} tehisaru- või andmehanget (95% vahemik {vmin}–{vmax}); klassifikaator leidis {lev["valitud_leidis"]}.</p>
  <div class="tbl"><table><thead><tr><th scope="col">Meetod</th><th scope="col" class="v">Täpsus (95%)</th><th scope="col" class="v">Saagis (95%)</th><th scope="col" class="v">F1</th></tr></thead>
  <tbody>{"".join(t_rows)}</tbody></table></div>
</section>
</div>"""
    return (pea(A, vaade, lead, [("aastad", "Aastad"), ("viis", "Kuidas hangitakse"), ("hankijad", "Hankijad"), ("loend", "Leia hea näide"), ("tapsus", "Kui täpne")], ree)
            + '<div class="g12">' + sec_aastad + sec_inn + "</div>"
            + '<div class="g12">' + sec_viis + sec_hankijad + "</div>"
            + sec_loend + sec_tapsus)


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
<section class="pn sp5" id="uuritakse" aria-labelledby="h-uuritakse">
  <div class="pn-h"><h2 id="h-uuritakse">Tehisarust ja tööst ilmus {a1["aasta"]}. aastal <b>{_arv(a1["koik"])} publikatsiooni</b>, {pr(kord)} korda rohkem kui {a0["aasta"]}</h2></div>
  <p class="ps">Teadusartiklid ja töödokumendid aastas ({a(OPENALEX_URL, "OpenAlex")}, otsing seisuga {kp(P["meta"]["aeg"][:10])}). * aasta pole läbi.</p>
  <div class="aastatulbad">{tulbad}</div>
  <p class="gt" style="margin-top:22px">Teema osa {aastad[-1]["aasta"]}. aasta publikatsioonidest</p>
  <div class="viis teemad">{t_read}</div>
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
        li = "".join(f'<tr><td class="n">{kp(r["avaldatud"])}</td><td><a href="{e(r["url"])}">{e(r["pealkiri"])}</a><small>{e(r.get("kanal") or "")}</small></td>'
                     f'<td class="v">{_arv(r["viiteid"])}</td></tr>' for r in read if r.get("url"))
        nupud.append(f'<button type="button" role="tab" aria-selected="{"true" if i == 0 else "false"}" aria-controls="pub-{g}" id="tab-{g}">{e(nimi)} ({len(read)})</button>')
        osad.append(f'<div role="tabpanel" id="pub-{g}" aria-labelledby="tab-{g}"{"" if i == 0 else " hidden"}><div class="tbl"><table data-piir><thead><tr><th scope="col">Avaldatud</th><th scope="col">Publikatsioon ja kanal</th><th scope="col" class="v">Viiteid</th></tr></thead><tbody>{li}</tbody></table></div></div>')
    sec_t = f"""
<section class="pn sp7" id="publikatsioonid" aria-labelledby="h-publikatsioonid">
  <div class="pn-h"><h2 id="h-publikatsioonid">Mida maailmas ja Eestis uuritakse: uusimad ja enim tsiteeritud tööd</h2></div>
  <div class="p-tabs" role="tablist" aria-label="Publikatsioonide valik">{"".join(nupud)}</div>
  {"".join(osad)}
</section>"""
    ee = sorted((r for r in P["eesti_allikad"] if r.get("teemas")), key=lambda r: r["avaldatud"] or "", reverse=True)
    nimi = {"arenguseire": "Arenguseire Keskus", "oska": "OSKA", "novaator": "Novaator", "err": "ERR", "etis": "ETIS"}
    e_read = "".join(f'<tr><td class="n">{kp(r["avaldatud"]) if r.get("avaldatud") else "—"}</td><td><a href="{e(r["url"])}">{e(r["pealkiri"])}</a></td>'
                     f'<td>{e(nimi.get(r["allikas"], r["allikas"]))}</td></tr>' for r in ee if r.get("url"))
    sec_e = f"""
<div class="g12">
<section class="pn sp12" id="eesti-allikad" aria-labelledby="h-eesti-allikad">
  <div class="pn-h"><h2 id="h-eesti-allikad">Eesti uuringud ja raportid tehisarust ja tööst: <b>{len(ee)}</b></h2></div>
  <p class="ps">Arenguseire Keskuse, OSKA ja teiste Eesti allikate tööd, mis käsitlevad tehisaru, tootlikkust või oskusi. Uusimad eespool.</p>
  <div class="tbl"><table data-piir><thead><tr><th scope="col">Avaldatud</th><th scope="col">Töö</th><th scope="col">Allikas</th></tr></thead><tbody>{e_read}</tbody></table></div>
</section>
</div>"""
    return '<div class="g12">' + sec_a + sec_t + "</div>" + sec_e


# ---------------------------------------------------------------- Töö: keda koondajad otsivad

def palkamine(A):
    """Keda samad ettevõtted, kes koondavad, praegu tööle otsivad (Kadri 6.11.2026). Tühi, kui andmeid pole toodud."""
    F = (A.get("koondajad") or {}).get("firmad")
    K = (A.get("koondamised") or {}).get("juhtumid") or []
    if not F or not K:
        return ""
    jarjestus, read = [], []
    for j in sorted(K, key=lambda r: r["kuupaev"], reverse=True):
        if j["ettevote"] in F and j["ettevote"] not in jarjestus:
            jarjestus.append(j["ettevote"])
    puudu = [j["ettevote"] for j in K if j["ettevote"] not in F]
    kontrollitud = [f for f in jarjestus if F[f]["otsib"].get("kontrollitud")]
    otsivad = [f for f in kontrollitud if F[f]["otsib"]["ametid"]]
    kuulutusi = sum(len(F[f]["otsib"]["ametid"]) for f in kontrollitud)
    sama = [f for f in otsivad if set(F[f]["kaotatud"]) & {a["liik"] for a in F[f]["otsib"]["ametid"]} - {"teadmata", "muu"}]
    kp_min = min(F[f]["otsib"]["kontrollitud"] for f in kontrollitud)
    for f in jarjestus:
        x = F[f]
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
        link_ = f' · {a(o["url"], "tööpakkumised")}' if o.get("url") else ""
        read.append(f'<tr><td><b>{e(f)}</b><small>{e(x["sektor"])} · {e(x["omand"])}</small></td>'
                    f'<td>{kaotatud}<small>{e(x["kaotatud_tekst"])}</small></td><td>{otsib}</td>'
                    f'<td class="n">{kp(o["kontrollitud"]) if o.get("kontrollitud") else "—"}<small>{link_.lstrip(" · ")}</small></td></tr>')
    n_k = len(kontrollitud)
    h2 = f'{SEESTYTLEV.get(n_k, str(n_k) + "-st").capitalize()} kontrollitud koondajast'
    sama_t = (f"; {ARVSONAD.get(len(sama), len(sama))} otsib sama ametiliiki, mida koondab" if sama else "; mitte ükski ei otsi sama ametiliiki, mida koondab")
    return f"""
<div class="g12">
<section class="pn sp12" id="palkamine" aria-labelledby="h-palkamine">
  <div class="pn-h"><h2 id="h-palkamine">{h2} otsib praegu Eestis töötajaid <b>{ARVSONAD.get(len(otsivad), len(otsivad))}</b> (kokku {kuulutusi} kuulutust){sama_t}</h2></div>
  <p class="ps">Samad ettevõtted, kes koondavad: mida nad koondamisuudise järgi kaotavad ja keda nende enda tööpakkumiste leht praegu Eestis otsib (kontrollitud {kp(kp_min)}). Sinise äärega ametiliik = sama liik, mida koondatakse. Leht ei näita sisemisi ümberpaigutusi ega ainult LinkedInis avaldatud kuulutusi.{" Taustata: " + ", ".join(e(p) for p in puudu) + "." if puudu else ""}</p>
  <div class="tbl"><table class="pk"><thead><tr><th scope="col">Ettevõte</th><th scope="col">Koondab (ametiliigid)</th><th scope="col">Otsib praegu Eestis</th><th scope="col">Kontrollitud</th></tr></thead>
  <tbody>{"".join(read)}</tbody></table></div>
</section>
</div>"""
