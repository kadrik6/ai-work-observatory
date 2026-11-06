"""Ülevaade (avaleht) töölauana (Kadri valikud 5.11.2026, suundade leht 9EWSmGTPNJRapX5z9CoEc6).

Ülesehitus: pealkiri, kuus numbriplaati, ELi kaart koos järjestusega omaette real, siis töötuse prognoos ja
ettevõtete trend, siis „Mis muutus“, sihid ja hanked (katseline), lõpuks väidete tabel. Koondamised on ainult
Töö vaates (Kadri 5.11 22:22: soovitused 1–5 kehtivad).

Iga pealkirja number tuleb andmetest. Mallist väljas olevad osad kontrollitakse abi.kontrolli() abil.
"""
import csv
from pathlib import Path

import andmekiht as andmed
from abi import ARVSONAD, SEESTYTLEV, a, kontrolli, link
from andmekiht import EL, AndmeViga
from komponendid import KUUD, aastatulbad, allikarida, e, kaart, kp, pr, riik, sihiriba
from lehed_usaldus import RASKUS, _raskus
from pealkiri import taida

SISU = Path(__file__).resolve().parent / "sisu"
IN, EB, DS = "inimeste-tehisaru-kasutus", "ettevotete-tehisaru-kasutus", "inimeste-digioskused"
UNE_URL = "https://ec.europa.eu/eurostat/databrowser/view/une_rt_m/default/table"
UNE_UUENDATUD = "2026-10-30"
HANKED_URL = "https://riigihanked.riik.ee/"
VOO_PAEVI, VOO_RIDU = 14, 8


def _loe(nimi):
    with open(SISU / nimi, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def kuu_seesytlev(kuu):
    """„2026-09“ → „septembris“."""
    return ["jaanuaris", "veebruaris", "märtsis", "aprillis", "mais", "juunis", "juulis", "augustis", "septembris",
            "oktoobris", "novembris", "detsembris"][int(kuu[5:7]) - 1]


def tootus():
    read = _loe("eurostat-tootus-kuud.csv")
    s = {}
    for r in read:
        s.setdefault(r["geo"], []).append((r["kuu"], float(r["protsent"])))
    for g in s:
        s[g].sort()
    if "EE" not in s or EL not in s:
        raise AndmeViga("sisu/eurostat-tootus-kuud.csv: Eesti või ELi rida puudub")
    return s


def hanked():
    read = [{**r, "koik": int(r["koik"]), "ai_ja_andmed": int(r["ai_ja_andmed"])} for r in _loe("hanked-aastad.csv")]
    for r in read:
        r["osa"] = r["ai_ja_andmed"] / r["koik"] * 100
    return read


# ---------------------------------------------------------------- komponendid

def plaat(lbl, big, small="", cmp="", src="", fookus=False, lisa=""):
    return (f'<div class="plaat"><span class="lbl">{e(lbl)}</span>'
            f'<span class="big{" s" if fookus else ""}">{big}{f"<small>{small}</small>" if small else ""}</span>'
            f'{lisa}{f"<span class=cmp>{cmp}</span>" if cmp else ""}<span class="src">{src}</span></div>')


def jarjestus(vaatlused, lopp, viide, viite_nimi, fookus="EE", uhik="%"):
    """Kõik ELi riigid järjestuses, punkt joonel. data-n seob rea kaardi riigiga (sait.js)."""
    jarjest = sorted(vaatlused, key=lambda v: -v["vaartus"])
    pos = lambda x: x / lopp * 100  # noqa: E731
    out = [f'<div class="jrj" role="list" aria-label="ELi riigid järjestuses">'
           f'<div class="jrj-r pais" aria-hidden="true"><span></span><span class="rada"><span class="viit-s" style="left:{pos(viide):.2f}%">{e(viite_nimi)}</span></span><span></span></div>']
    for i, v in enumerate(jarjest, 1):
        f = " fookus" if v["geo"] == fookus else ""
        out.append(f'<div class="jrj-r{f}" role="listitem" data-n="{e(riik(v["geo"]))}"><span class="n">{i}. {e(riik(v["geo"]))}</span>'
                   f'<span class="rada"><i class="kesk" style="left:{pos(viide):.2f}%"></i><i class="joon" style="width:{pos(v["vaartus"]):.2f}%"></i>'
                   f'<i class="tapp" style="left:{pos(v["vaartus"]):.2f}%"></i>'
                   f'<span class="v" style="left:{pos(v["vaartus"]):.2f}%">{pr(v["vaartus"])}</span></span><span></span></div>')  # number punkti kõrval (Kadri 6.11)
    margid = "".join(f'<span style="left:{pos(x):.2f}%">{x}{uhik if x == 0 else ""}</span>' for x in range(0, int(lopp) + 1, 10))
    out.append(f'<div class="jrj-r telg" aria-hidden="true"><span></span><span class="rada">{margid}</span><span></span></div></div>')
    return "".join(out)


def _svg_tekst(x, y, t, kl="", ankur="start"):
    return f'<text x="{x:.1f}" y="{y:.1f}" class="{kl}" text-anchor="{ankur}">{e(t)}</text>'


def joon(seeriad, x0, x1, y1, samm, w=440, h=170, ml=26, mr=86, mt=10, mb=22, x_margid=None, x_silt=str, silt="",
         lihtne=False):
    """Joondiagramm SVG-na. seeriad: [(nimi, [(x, y)], liik)], liik ∈ {"fookus", "ref", ""}. Otsasildid paremal.

    lihtne=True: ruudustikku ega y-telge pole, ainult jooned, lõppväärtused ja esimene ning viimane kuu (Kadri 5.11 22:49).
    Siis algab y vahemik andmete miinimumi lähedalt, sest telge ega tulpa, mille pikkust lugeda, pole."""
    import math
    y0 = 0
    if lihtne:
        koik = [py for _, pts, _ in seeriad for _, py in pts]
        y0, y1 = max(0, math.floor(min(koik)) - 1), math.ceil(max(koik)) + 1
    X = lambda x: ml + (x - x0) / (x1 - x0) * (w - ml - mr)  # noqa: E731
    Y = lambda y: mt + (1 - (y - y0) / (y1 - y0)) * (h - mt - mb)  # noqa: E731
    osad = []
    y = 0
    while not lihtne and y <= y1 + 1e-9:
        osad.append(f'<line class="v" x1="{ml}" x2="{w - mr}" y1="{Y(y):.1f}" y2="{Y(y):.1f}"/>')
        osad.append(_svg_tekst(ml - 6, Y(y) + 4, pr(y, 0), "t", "end"))
        y += samm
    for x in (x_margid or [x0, x1]):
        osad.append(_svg_tekst(X(x), h - 6, x_silt(x), "t", "start" if lihtne and x == x0 else "end" if lihtne and x == x1 else "middle"))
    otsad = []
    for nimi, pts, liik in sorted(seeriad, key=lambda s: {"": 0, "ref": 1, "fookus": 2}[s[2]]):
        d = " ".join(f"{X(px):.1f},{Y(py):.1f}" for px, py in pts)
        osad.append(f'<polyline class="s {liik}" points="{d}"/>')
        lx, ly = pts[-1]
        osad.append(f'<circle class="s {liik}" cx="{X(lx):.1f}" cy="{Y(ly):.1f}" r="{3 if liik else 2.2}"/>')
        otsad.append([Y(ly) + 4, f"{nimi} {pr(ly)}", liik])
    otsad.sort()
    for i in range(1, len(otsad)):  # sildid ei kattu
        if otsad[i][0] - otsad[i - 1][0] < 12:
            otsad[i][0] = otsad[i - 1][0] + 12
    for yy, t, liik in otsad:
        osad.append(_svg_tekst(w - mr + 7, yy, t, f"o {liik}"))
    return (f'<svg class="joon-g" viewBox="0 0 {w} {h}" role="img" aria-label="{e(silt)}" style="max-width:{w}px">'
            f'{"".join(osad)}</svg>')


# ---------------------------------------------------------------- vaade

def avaleht(A, vaade, vaated):
    ein, eeb = andmed.leia(A, IN, "EE", "uusim"), andmed.leia(A, EB, "EE", "uusim")
    ein_el = andmed.leia(A, IN, EL, "uusim:alus")
    ds, ds23 = andmed.leia(A, DS, "EE", "uusim:alus"), andmed.leia(A, DS, "EE", 2023)
    ds_el = andmed.leia(A, DS, EL, ds["aasta"])
    T = tootus()
    kuu, t_ee = T["EE"][-1]
    t_el = dict(T[EL]).get(kuu)
    if t_el is None:
        raise AndmeViga(f"ELi töötus puudub kuul {kuu}")
    kontrolli(vaade, f"{kuu_seesytlev(kuu)} {pr(t_ee)}%")
    rm = A["uuringud"]["rm2026"]
    prog = {r["aasta"]: r for r in A["tooelu"]["tulevik"]["tootus_ee"]["read"]}
    p_aasta = int(kuu[:4])
    if p_aasta not in prog or prog[p_aasta]["tegelik"]:
        raise AndmeViga(f"Töötuse prognoos aastaks {p_aasta} puudub")
    siht = A["sihid"]["ee-ettevotted-75"]
    H = hanked()
    h_uus = H[-1]
    V = A["vaited"]
    v_muud = [v for v in V if _raskus(v) == 0]
    menuu = lambda vid, t: link(vaated, vid, t)  # noqa: E731

    # 1. Numbriplaadid
    plaadid = "".join([
        plaat("Inimesed, kes kasutasid tehisaru (16–74)", f"{pr(ein['vaartus'])}%", str(ein["aasta"]),
              f"EL {ein_el['aasta']}: {pr(ein_el['vaartus'])}% (Eurostat, teine skaala)",
              f"{a(ein['url'], ein['allikas'])}, {kp(ein['avaldatud'])}", fookus=True),
        plaat("Ettevõtted, kes kasutavad tehisaru, ja riigi siht", f"{pr(eeb['vaartus'])}%",
              f"{eeb['aasta']} · siht {pr(float(siht['siht']), 0)}%",
              "", f"{a(eeb['url'], eeb['allikas'])}; siht: {a(siht['url'], 'DYAK 2035')}",
              lisa=sihiriba(eeb["vaartus"], float(siht["siht"]), 100, "%", fookus=True)),
        plaat("Vähemalt baastaseme digioskused", f"{pr(ds['vaartus'])}%", str(ds["aasta"]),
              f"{ds23['aasta']}: {pr(ds23['vaartus'])}% · EL {pr(ds_el['vaartus'])}%", e(ds["allikas"])),
        plaat("Töötuse määr, sesoonselt tasandatud", f"{pr(t_ee)}%", f"{KUUD[int(kuu[5:]) - 1]} {kuu[:4]}",
              f"EL {pr(t_el)}% · prognoos {p_aasta}: {pr(prog[p_aasta]['protsent'])}%",
              f"{a(UNE_URL, 'Eurostat une_rt_m')}, {kp(UNE_UUENDATUD)}"),
        plaat("Tehisaru- ja andmehanked", str(h_uus["ai_ja_andmed"]), f"{h_uus['periood']} {h_uus['aasta']}",
              f"{pr(h_uus['osa'])}% kõigist hangetest",
              f"Riigihangete register <span class=\"chip exp\">katseline</span>"),
        plaat("Kontrollitud väited tehisaru kohta", str(len(V)), "",
              f"{len(v_muud)} ütleb muud kui allikas", menuu("kas-tosi", "Kas see on tõsi?")),
    ])

    # 2. ELi kaart ja järjestus omaette real
    y = andmed.leia(A, EB, "EE", "uusim:alus")["aasta"]
    el_v = [v for v in andmed.vali(A, EB, aasta=y, klass="alus") if v["geo"] in A["el_riigid"]]
    eu = andmed.leia(A, EB, EL, y)
    koht = andmed.koht(A, EB, "EE", y)
    kaart_html = kaart(el_v, (0, 10, 20, 30, 40), viide=eu["vaartus"], viite_nimi=f"EL {pr(eu['vaartus'])}")
    sec_el = f"""
<section class="pn sp12" id="el" aria-labelledby="h-el">
  <div class="pn-h"><h2 id="h-el">Ettevõtete tehisaru kasutuses on Eesti ELis <b>{koht}. kohal</b>, ELi keskmisest ees ja Põhjamaadest taga ({y})</h2></div>
  <p class="ps">Tehisaru kasutavate ettevõtete osakaal, %, vähemalt 10 hõivatuga ettevõtted, {y}. Vii hiir riigile kaardil või loendis.</p>
  <div class="el-rida"><div class="el-kaart">{kaart_html}</div>{jarjestus(el_v, 45, eu["vaartus"], f"EL {pr(eu['vaartus'])}")}</div>
  {allikarida([(eu["allikas"], eu["url"], f"uuendatud {kp(eu['avaldatud'])}")])}
</section>"""

    # 3. Prognoos ja kuunumber | ettevõtete trend
    viimased = T["EE"][-12:]
    k0 = viimased[0][0]
    idx = {k: i for i, (k, _) in enumerate(viimased)}
    kuujoon = joon([("Eesti", [(idx[k], v) for k, v in viimased], "fookus"),
                    ("EL", [(idx[k], v) for k, v in T[EL] if k in idx], "ref")],
                   0, 11, 10, 2, w=340, h=90, ml=4, mr=60, x_margid=[0, 11], lihtne=True,
                   x_silt=lambda i: viimased[int(i)][0][5:] + "/" + viimased[int(i)][0][2:4], silt="Töötus viimased 12 kuud")
    sec_prog = f"""
<section class="pn sp7" id="tootus" aria-labelledby="h-tootus">
  <div class="pn-h"><h2 id="h-tootus">Prognoos ootab {p_aasta}. aastaks <b>{pr(prog[p_aasta]['protsent'])}%</b> töötust, kuunumber oli {kuu_seesytlev(kuu)} {pr(t_ee)}%</h2></div>
  <div class="g2"><div><p class="gt">Aasta keskmine, tegelik ja prognoos</p>{aastatulbad([(r["aasta"], r["protsent"], r["tegelik"]) for r in prog.values()], 10, 2)}</div>
  <div><p class="gt">Kuu kaupa, sesoonselt tasandatud, {k0[5:]}/{k0[:4]}–{kuu[5:]}/{kuu[:4]}</p>{kuujoon}</div></div>
  <p class="drift">Eri mõõdikud: prognoos on aasta keskmine, kuunumber sesoonselt tasandatud. Prognoos ei arvesta tehisaru mõju eraldi. Aasta keskmine selgub {p_aasta + 1}. aasta alguses.</p>
  {allikarida([(rm["pealkiri"], rm["url"], kp(rm["avaldatud"])), ("Eurostat une_rt_m", UNE_URL, f"uuendatud {kp(UNE_UUENDATUD)}")])}
</section>"""

    riigid = [("EE", "Eesti", "fookus"), (EL, "EL27", "ref"), ("FI", "Soome", ""), ("SE", "Rootsi", "")]
    seeriad = []
    for g, nimi, liik in riigid:
        pts = sorted((int(v["aasta"]), v["vaartus"]) for v in andmed.vali(A, EB, geo=g, klass="alus"))
        seeriad.append((nimi, pts, liik))
    ee_pts = seeriad[0][1]
    kordaja = ee_pts[-1][1] / ee_pts[0][1]
    kontrolli_kordaja = int(kordaja)
    trend = joon(seeriad, ee_pts[0][0], ee_pts[-1][0], 40, 10, h=140, x_margid=[p[0] for p in ee_pts], silt="Ettevõtete tehisaru kasutus")
    sec_trend = f"""
<section class="pn sp5" id="trend" aria-labelledby="h-trend">
  <div class="pn-h"><h2 id="h-trend">Eesti ettevõtete tehisaru kasutus <b>kasvas {ee_pts[0][0]}–{ee_pts[-1][0]} üle {kontrolli_kordaja} korra</b></h2></div>
  <p class="ps">% ettevõtetest, vähemalt 10 hõivatut. 2022 küsimust ei olnud.</p>
  {trend}
  {allikarida([(eu["allikas"], eu["url"], f"uuendatud {kp(eu['avaldatud'])}")])}
</section>"""

    # 4. Mis muutus | sihid | hanked
    voog = []
    for s in A["sundmused"]:
        if s["liik"] == "allikas":
            voog.append((s["kuupaev"], "uus number", "s", e(s["tekst"]), s["url"]))
    for v in V:
        if v["kuupaev"]:
            voog.append((v["kuupaev"], "väide", "", f'{e(v["valjaanne"])}: {e(RASKUS[_raskus(v)][0].lower())}', ""))
    voog.append((UNE_UUENDATUD, "uus number", "s", f"Eesti töötus {kuu_seesytlev(kuu)} {pr(t_ee)}% (Eurostat)", UNE_URL))
    voog.append((ein["avaldatud"], "uus number", "s", f"Inimeste tehisaru kasutus {pr(ein['vaartus'])}% (Statistikaamet)", ein["url"]))
    voog.append((eeb["avaldatud"], "uus number", "s", f"Ettevõtete tehisaru kasutus {pr(eeb['vaartus'])}% (Statistikaamet)", eeb["url"]))
    voog = sorted(set(voog), key=lambda r: r[0], reverse=True)
    viimane = voog[0][0]
    from datetime import date
    d = lambda iso: date.fromisoformat(iso[:10])  # noqa: E731
    uued = sum(1 for r in voog if (d(viimane) - d(r[0])).days <= VOO_PAEVI)
    read = "".join(f'<li><span class="d">{kp(r[0])}</span><span class="t {r[2]}">{e(r[1])}</span>'
                   f'<span>{f"<a href={chr(34)}{e(r[4])}{chr(34)}>{r[3]}</a>" if r[4] else r[3]}</span></li>' for r in voog[:VOO_RIDU])
    sec_voog = f"""
<section class="pn sp5" id="muutus" aria-labelledby="h-muutus">
  <div class="pn-h"><h2 id="h-muutus">Mis muutus: viimati <b>{kp(viimane)}</b></h2></div>
  <p class="ps">{ARVSONAD[VOO_RIDU].capitalize()} viimast muutust allikates ja väidetes; {VOO_PAEVI} päeva jooksul enne {kp(viimane)} lisandus {uued}.</p>
  <ul class="voog">{read}</ul>
  <p class="allikas">Kogu loend: {menuu("kas-tosi", "Kas see on tõsi? › Mis muutus")}. Tehisaru ja töö uudised Eestist ja maailmast: {menuu("uudised", "Uudised")}.</p>
</section>"""

    sihid = [(A["sihid"]["ee-ettevotted-75"], eeb, True)]
    for sid in ("el-digioskused-80", "el-digiintensiivsus-90"):
        s_ = A["sihid"][sid]
        sihid.append((s_, andmed.leia(A, s_["naitaja"], s_["tase"], "uusim:alus"), False))
    kaugus = [(float(s_["siht"]) - v["vaartus"], s_["id"]) for s_, v, _ in sihid]
    if max(kaugus)[1] != "ee-ettevotted-75":
        raise AndmeViga("Sihtide pealkiri eeldab, et ettevõtete siht on kõige kaugemal")
    s_read = "".join(
        f'<div class="siht{" f" if f else ""}"><div class="r"><span>{e(s_["nimi"])}, {"Eesti" if s_["tase"] == "EE" else "EL27"}</span>'
        f'<b>{pr(v["vaartus"])}% <small>{v["aasta"]} · siht {pr(float(s_["siht"]), 0)}% ({s_["aasta"]})</small></b></div>'
        f'{sihiriba(v["vaartus"], float(s_["siht"]), 100, "%", fookus=f)}</div>' for s_, v, f in sihid)
    sec_sihid = f"""
<section class="pn sp3" id="sihid" aria-labelledby="h-sihid">
  <div class="pn-h"><h2 id="h-sihid">Kolmest sihist on <b>ettevõtete kasutus</b> kõige kaugemal</h2></div>
  <div class="sihid">{s_read}</div>
  <p class="allikas">Iga siht oma allika ja skaalaga: Eesti siht on Statistikaameti numbril, ELi sihid ELi kui terviku kohta. {menuu("reeglid", "Reeglid ja sihid")}.</p>
</section>"""

    sec_hanked = f"""
<section class="pn sp4" id="hanked" aria-labelledby="h-hanked">
  <div class="pn-h"><h2 id="h-hanked">Tehisaru- ja andmehangete osa on <b>alla 1%</b> kõigist hangetest</h2><span class="chip exp">katseline</span></div>
  <p class="ps">% kõigist riigihangetest aastas; {h_uus["aasta"]} = {h_uus["periood"]}</p>
  {aastatulbad([(r["aasta"], r["osa"], True) for r in H], 1, 0.25, k=2)}
  <p class="allikas">Allikas: {a(HANKED_URL, "riigihangete register")} ja TED. Katseline klassifikaator: täpsus 71%, saagis 69% Claude'i märgendatud valimil, inimene pole kontrollinud. Kõik hanked ja head näited: {menuu("hanked", "Hanked")}.</p>
</section>"""
    if max(r["osa"] for r in H) >= 1:
        raise AndmeViga("Hangete pealkiri ütleb „alla 1%“, aga osa on 1% või rohkem")

    # 5. Väited
    V_jrj = sorted(V, key=lambda v: (_raskus(v), v["kuupaev"]), reverse=False)
    v_read = "".join(
        f'<tr><td>{e(v["vaide"])}<small>{e(v["valjaanne"])}, {kp(v["kuupaev"]) if v["kuupaev"] else "kuupäev puudub"}</small></td>'
        f'<td><span class="verd {RASKUS[_raskus(v)][1]}">{e(v["hinnang"])}</span></td><td>{e(v["oige_lause"] or v["selgitus"])}</td></tr>'
        for v in V_jrj[:4])
    sec_vaited = f"""
<section class="pn sp12" id="vaited" aria-labelledby="h-vaited">
  <div class="pn-h"><h2 id="h-vaited">{ARVSONAD[len(V)].capitalize() if len(V) in ARVSONAD else len(V)} kontrollitud väidet: <b>{ARVSONAD.get(len(v_muud), len(v_muud))} ütleb muud kui allikas</b></h2></div>
  <div class="tbl"><table><thead><tr><th scope="col" style="width:38%">Väide ja väljaanne</th><th scope="col" style="width:13%">Hinnang</th><th scope="col">Mida allikas tegelikult ütleb</th></tr></thead><tbody>{v_read}</tbody></table></div>
  <p class="allikas">Väide kuulub väljaandele. Siin {min(4, len(V))} väidet {len(V)}-st; kõik: {menuu("kas-tosi", "Kas see on tõsi?")}.</p>
</section>"""

    pea = f"""
<div class="pea-t">
  <h1>{taida(vaade["h1"], A)}</h1>
  <p class="seis-t">Andmed: Statistikaamet {kp(ein["avaldatud"])} ja {kp(eeb["avaldatud"])}, Eurostat {kp(UNE_UUENDATUD)}</p>
</div>
<nav aria-label="Sellel lehel"><ul class="sellel"><li><a href="#el">Eesti ELis</a></li><li><a href="#tootus">Töö ja töötus</a></li><li><a href="#trend">Ettevõtted</a></li><li><a href="#muutus">Mis muutus</a></li><li><a href="#sihid">Sihid</a></li><li><a href="#hanked">Hanked</a></li><li><a href="#vaited">Väited</a></li></ul></nav>
<div class="plaadid" aria-label="Peamised numbrid">{plaadid}</div>"""
    return (pea + '<div class="g12">' + sec_el + "</div>"
            + '<div class="g12">' + sec_prog + sec_trend + "</div>"
            + '<div class="g12">' + sec_voog + sec_sihid + sec_hanked + "</div>"
            + '<div class="g12">' + sec_vaited + "</div>")


# ---------------------------------------------------------------- Töö vaate Eesti rida

ROLL_NIMI = {"otsene": "otsene põhjus", "osaline": "üks põhjus", "kaudne": "kaudne", "tulevikus": "võib tulevikus",
             "ei_mainita": "ei mainita"}


def too_eesti(A):
    """Töö vaate esimene rida: Eesti töötus kuu kaupa ja Eesti koondamised, kus küsiti tehisaru rolli."""
    T = tootus()
    K = A.get("koondamised") or {}
    juhtumid = sorted(K.get("juhtumid", []), key=lambda r: r["kuupaev"], reverse=True)
    if not juhtumid:
        raise AndmeViga("Töö vaade vajab faili tooelu-seire/koondamised_ee.json")
    for r in juhtumid:
        if r["roll"] not in ROLL_NIMI:
            raise AndmeViga(f"koondamised_ee.json: tundmatu roll {r['roll']} ({r['id']})")
    kuu, t_ee = T["EE"][-1]
    t_el = dict(T[EL])[kuu]
    k0 = T["EE"][0][0]
    idx = {k: i for i, (k, _) in enumerate(T["EE"])}
    n = len(T["EE"]) - 1
    margid = [i for i, (k, _) in enumerate(T["EE"]) if k[5:7] in ("01",)] + [0, n]
    joonis = joon([("Eesti", [(idx[k], v) for k, v in T["EE"]], "fookus"),
                   ("EL", [(idx[k], v) for k, v in T[EL] if k in idx], "ref")],
                  0, n, 10, 2, w=300, h=130, ml=4, mr=60, x_margid=[0, n], lihtne=True,
                  x_silt=lambda i: T["EE"][int(i)][0][5:] + "/" + T["EE"][int(i)][0][2:4], silt="Töötuse määr kuu kaupa")
    aasta_tagasi = dict(T["EE"]).get(f"{int(kuu[:4]) - 1}{kuu[4:]}")
    muutus = "" if aasta_tagasi is None else (
        f"Aasta varem {pr(aasta_tagasi)}%, muutus {'+' if t_ee >= aasta_tagasi else '−'}{pr(abs(t_ee - aasta_tagasi))} punkti. ")
    sec_t = f"""
<section class="pn sp3" id="tootus-kuud" aria-labelledby="h-tootus-kuud">
  <div class="pn-h"><h2 id="h-tootus-kuud">Eesti töötus oli {kuu_seesytlev(kuu)} {kuu[:4]} <b>{pr(t_ee)}%</b>, ELis {pr(t_el)}%</h2></div>
  <p class="ps">Töötuse määr, %, sesoonselt tasandatud, {k0[5:]}/{k0[:4]}–{kuu[5:]}/{kuu[:4]}. {muutus}Kuunumber ei ütle, kas põhjus on tehisaru.</p>
  {joonis}
  {allikarida([("Eurostat une_rt_m", UNE_URL, f"uuendatud {kp(UNE_UUENDATUD)}")])}
</section>"""

    otsene = sum(r["roll"] == "otsene" for r in juhtumid)
    mainib = sum(r["roll"] in ("otsene", "osaline") for r in juhtumid)
    kaardid = []
    for r in juhtumid:
        arv = (("vähemalt " if r.get("arv_vahemalt") else "") + str(r["arv_eestis"])) if r.get("arv_eestis") is not None else (f'kuni {r["arv_ulem"]}' if r.get("arv_ulem") else "arv pole teada")
        kand = '<span class="u-t">uudisest, kontrollimata</span>' if r.get("kandidaat") else ""
        klass = " s" if r["roll"] in ("otsene", "osaline") else ""
        kaardid.append(f'<li class="kk" data-k="{e(r["id"])}"><div class="kk-r"><b>{e(r["ettevote"])}</b><span class="kk-n{'' if r.get('arv_eestis') is not None or r.get('arv_ulem') else ' t'}">{e(arv)}</span></div>'
                       f'<div class="kk-r"><span class="roll{klass}">tehisaru: {e(ROLL_NIMI[r["roll"]])}</span><span class="kk-d">{kp(r["kuupaev"])} · {e(r["sektor"])}</span></div>'
                       f'<p title="{e(r["pohjus"])}">{e(r["pohjus"])}</p><a href="{e(r["url"])}">{e(r["allikas"])}</a>{kand}</li>')
    arvsona = SEESTYTLEV.get(len(juhtumid), f"{len(juhtumid)}-st")
    otse = "mitte ükski" if otsene == 0 else ARVSONAD.get(otsene, str(otsene))
    sec_k = f"""
<section class="pn sp5" id="koondamised" aria-labelledby="h-koondamised">
  <div class="pn-h"><h2 id="h-koondamised">{arvsona.capitalize()} Eesti koondamisest: tehisaru otsese põhjusena <b>{otse}</b>, ühe põhjusena {ARVSONAD.get(mainib, str(mainib))}</h2></div>
  <p class="ps">Koondamised, mille kohta uudis küsis, kas tehisaru oli põhjus. Roll on see, mida ettevõte ise ütles. See ei ole täielik nimekiri; kontrollitud {kp(K["kontrollitud"])}.</p>
  <ul class="kk-v" aria-live="polite">{"".join(kaardid)}</ul>
  <div class="kk-nav" hidden><button type="button" class="kk-e" aria-label="Eelmine ettevõte">‹</button><span class="kk-tapid"></span><button type="button" class="kk-j" aria-label="Järgmine ettevõte">›</button><span class="kk-loe"></span></div>
  <p class="ps">Number on Eesti töökohad, kui see teatati. Ettevõtte enda selgitus ei tõenda põhjust.</p>
</section>"""
    # Keskel: töökohad ettevõtte kaupa, värv näitab, mida ettevõte tehisaru kohta ütles (Kadri 5.11 23:06)
    RYHM = {"otsene": ("s", "nimetas tehisaru põhjusena"), "osaline": ("s", "nimetas tehisaru põhjusena"),
            "kaudne": ("m", "mainis tehisaru muul moel"), "tulevikus": ("m", "mainis tehisaru muul moel"),
            "ei_mainita": ("t", "tehisaru ei mainitud")}
    def _arv(r):
        return r["arv_eestis"] if r.get("arv_eestis") is not None else r.get("arv_ulem")
    teada = sorted((r for r in juhtumid if _arv(r)), key=_arv, reverse=True)
    pole = [r for r in juhtumid if not _arv(r)]
    suurim = max(_arv(r) for r in teada)
    kokku = sum(_arv(r) for r in teada)
    pohjus = sum(_arv(r) for r in teada if RYHM[r["roll"]][0] == "s")
    ulem = any(r.get("arv_eestis") is None for r in teada)
    alam = any(r.get("arv_vahemalt") for r in teada)
    piir = "kuni " if ulem and not alam else ("vähemalt " if alam and not ulem else "umbes ")
    ribad = "".join(
        f'<div class="kr" data-k="{e(r["id"])}" role="listitem"><span class="kr-n">{e(r["ettevote"])}<small>{r["kuupaev"][5:7]}.{r["kuupaev"][:4]}</small></span>'
        f'<span class="kr-rada"><i class="kr-t {RYHM[r["roll"]][0]}{" ulem" if r.get("arv_eestis") is None else ""}" style="width:{_arv(r) / suurim * 100:.1f}%"></i></span>'
        f'<span class="kr-a">{"kuni " if r.get("arv_eestis") is None else ""}{_arv(r)}{"+" if r.get("arv_vahemalt") else ""}</span></div>' for r in teada)
    ribad += "".join(f'<div class="kr" data-k="{e(r["id"])}" role="listitem"><span class="kr-n">{e(r["ettevote"])}<small>{r["kuupaev"][5:7]}.{r["kuupaev"][:4]}</small></span>'
                     f'<span class="kr-rada"><span class="kr-pole">arv pole teada</span></span><span class="kr-a"></span></div>' for r in pole)
    legend = "".join(f'<span><i class="kr-t {k}"></i>{e(t)}</span>' for k, t in [("s", "nimetas tehisaru põhjusena"), ("m", "mainis tehisaru muul moel"), ("t", "tehisaru ei mainitud")])
    sec_v = f"""
<section class="pn sp4" id="koondamised-visuaal" aria-labelledby="h-koondamised-v">
  <div class="pn-h"><h2 id="h-koondamised-v">Tehisaru nimetati põhjusena <b>{pohjus} töökoha</b> juures {piir}{kokku}-st</h2></div>
  <p class="ps">Teatatud töökohad Eestis ettevõtte kaupa. Värv näitab, mida ettevõte ise tehisaru kohta ütles. Vali ettevõte, et näha selle kaarti.</p>
  <div class="kr-ribad" role="list" aria-label="Koondatavad töökohad ettevõtte kaupa; vali ettevõte, et näha selle kaarti">{ribad}</div>
  <p class="kr-leg">{legend}</p>
  <p class="allikas">Allikas: uudised, lingid kaartidel. Katkendäärega tulp on teatatud ülempiir{"; + tähendab, et lõplik arv pole veel teada" if alam else ""}.</p>
</section>"""
    return f'<div class="g12">{sec_t}{sec_v}{sec_k}</div>'


# ---------------------------------------------------------------- Avaliku sektori hanked

def mida_riik_ostab(A):
    """Avalik sektor › „Mida riik ostab“: tehisaru- ja andmehanked aastas (katseline klassifikaator)."""
    H = hanked()
    uus = H[-1]
    taisaastad = [r for r in H if r["periood"] == "aasta"]
    if max(r["osa"] for r in H) >= 1:
        raise AndmeViga("Hangete pealkiri ütleb „alla 1%“, aga osa on 1% või rohkem")
    a0, a1 = taisaastad[0], taisaastad[-1]
    kord = a1["ai_ja_andmed"] / a0["ai_ja_andmed"]
    mark = [(r["aasta"], int(r["ai_marksonaga"]), r["periood"] == "aasta") for r in H]
    return f"""
<div class="g12">
<section class="pn sp12" id="hanked" aria-labelledby="h-hanked">
  <div class="pn-h"><h2 id="h-hanked">Tehisaru- ja andmehankeid oli {a1["aasta"]}. aastal <b>{a1["ai_ja_andmed"]}</b>, {a0["aasta"]}. aastaga võrreldes {pr(kord, 1)} korda rohkem, aga see on alla 1% kõigist hangetest</h2><span class="chip exp">katseline</span></div>
  <p class="ps">Riigihangete registri hanked, mille klassifikaator märkis tehisaru või andmetööks. {uus["aasta"]} = {uus["periood"]}. Tehisaru uuringute ja mõjuanalüüside hankeid eraldi veel ei loeta; see rühm on töös. Kuidas hangitakse ja head näited: <a href="hanked.html">Hanked</a>.</p>
  <div class="g3">
    <div><p class="gt">Tehisaru- ja andmehanked, arv</p>{aastatulbad([(r["aasta"], r["ai_ja_andmed"], r["periood"] == "aasta") for r in H], 70, 20, uhik="", k=0)}</div>
    <div><p class="gt">Neist pealkirjas tehisaru märksõna, arv</p>{aastatulbad(mark, 30, 10, uhik="", k=0)}</div>
    <div><p class="gt">Osa kõigist hangetest, %</p>{aastatulbad([(r["aasta"], r["osa"], r["periood"] == "aasta") for r in H], 1, 0.25, k=2)}</div>
  </div>
  <p class="allikas">Allikas: {a(HANKED_URL, "riigihangete register")} ja TED. Katseline klassifikaator: täpsus 71%, saagis 69% Claude'i märgendatud valimil, inimene pole kontrollinud. Hele tulp = aasta pole veel läbi.</p>
</section>
</div>"""
