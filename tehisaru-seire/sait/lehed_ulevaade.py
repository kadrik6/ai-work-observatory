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
NBSP = "\u00a0"


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

def plaat(lbl, big, small="", cmp="", src="", fookus=False, lisa="", href=""):
    """href: plaadi nimi on link oma jaotisele (sisuloogika 6.11.2026 osa 4, struktuuri kontroll leid 7)."""
    nimi = f'<a href="{e(href)}">{e(lbl)}</a>' if href else e(lbl)
    return (f'<div class="plaat"><span class="lbl">{nimi}</span>'
            f'<span class="big{" s" if fookus else ""}">{big}{f"<small>{small}</small>" if small else ""}</span>'
            f'{lisa}{f"<span class=cmp>{cmp}</span>" if cmp else ""}<span class="src">{src}</span></div>')


def jarjestus(vaatlused, lopp, viide, viite_nimi, fookus="EE", uhik="%", piir=10):
    """Kõik ELi riigid järjestuses, punkt joonel. data-n seob rea kaardi riigiga (sait.js).

    piir: vaikimisi näidatakse esimesed piir riiki, ülejäänud nupust „kõik“ (Kadri kommentaar 7.11.2026:
    „näita siin defaultina top kümmet“). Fookusriik jääb alati nähtavale. Peitmine käib sait.js-is."""
    jarjest = sorted(vaatlused, key=lambda v: -v["vaartus"])
    pos = lambda x: x / lopp * 100  # noqa: E731
    out = [f'<div class="jrj" role="list" aria-label="ELi riigid järjestuses" data-piir="{piir}">'
           f'<div class="jrj-r pais" aria-hidden="true"><span></span><span class="rada"><span class="viit-s" style="left:{pos(viide):.2f}%">{e(viite_nimi)}</span></span><span></span></div>']
    for i, v in enumerate(jarjest, 1):
        f = " fookus" if v["geo"] == fookus else ""
        out.append(f'<div class="jrj-r{f}" role="listitem" data-n="{e(riik(v["geo"]))}"><span class="n">{i}. {e(riik(v["geo"]))}</span>'
                   f'<span class="rada"><i class="kesk" style="left:{pos(viide):.2f}%"></i><i class="joon" style="width:{pos(v["vaartus"]):.2f}%"></i>'
                   f'<i class="tapp" style="left:{pos(v["vaartus"]):.2f}%"></i>'
                   f'<span class="v" style="left:{pos(v["vaartus"]):.2f}%">{pr(v["vaartus"])}</span></span><span></span></div>')  # number punkti kõrval (Kadri 6.11)
    margid = "".join(f'<span style="left:{pos(x):.2f}%">{x}{uhik if x == 0 else ""}</span>' for x in range(0, int(lopp) + 1, 10))
    out.append(f'<div class="jrj-r telg" aria-hidden="true"><span></span><span class="rada">{margid}</span><span></span></div></div>')
    return '<div class="jrj-k">' + "".join(out) + "</div>"  # ümbris: nupurida „Näita“ tuleb järjestuse alla samasse veergu


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
    # h1 ei sisalda enam töötust (5.11 sisuloogika, Kadri kinnitas 6.11): kõrvutus kutsus põhjuslikule lugemisele
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
    lahti = sum(1 for l in A["lahknevused"] if l["staatus"] == "selgitamata")  # Kadri 6.11 21:38: lahknevused nähtavale
    menuu = lambda vid, t, ank="": link(vaated, vid, t, ank)  # noqa: E731

    # 1. Numbriplaadid
    plaadid = "".join([
        plaat("Inimesed, kes kasutasid tehisaru (16–74)", f"{pr(ein['vaartus'])}%", str(ein["aasta"]),
              f"EL {ein_el['aasta']}: {pr(ein_el['vaartus'])}% (Eurostat, teine skaala)",
              f"{a(ein['url'], ein['allikas'])}, {kp(ein['avaldatud'])}", fookus=True, href="inimesed.html#kasutus"),
        plaat("Ettevõtted, kes kasutavad tehisaru, ja riigi siht", f"{pr(eeb['vaartus'])}%",
              f"{eeb['aasta']} · siht {pr(float(siht['siht']), 0)}%",
              "", f"{a(eeb['url'], eeb['allikas'])}; siht: {a(siht['url'], 'DYAK 2035')}",
              lisa=sihiriba(eeb["vaartus"], float(siht["siht"]), 100, "%", fookus=True), href="ettevotted.html#kasutus"),
        plaat("Vähemalt baastaseme digioskused", f"{pr(ds['vaartus'])}%", str(ds["aasta"]),
              f"{ds23['aasta']}: {pr(ds23['vaartus'])}% · EL {pr(ds_el['vaartus'])}%", e(ds["allikas"]), href="inimesed.html#digi"),
        plaat("Töötuse määr, sesoonselt tasandatud", f"{pr(t_ee)}%", f"{KUUD[int(kuu[5:]) - 1]} {kuu[:4]}",
              f"EL {pr(t_el)}% · prognoos {p_aasta}: {pr(prog[p_aasta]['protsent'])}%",
              f"{a(UNE_URL, 'Eurostat une_rt_m')}, {kp(UNE_UUENDATUD)}", href="too.html#tootus-kuud"),
        plaat("Tehisaru- ja andmehanked", str(h_uus["ai_ja_andmed"]), f"{h_uus['periood']} {h_uus['aasta']}",
              f"{pr(h_uus['osa'])}% kõigist hangetest",
              f"Riigihangete register <span class=\"chip exp\">katseline</span>", href="hanked.html#aastad"),
        plaat("Kontrollitud väited tehisaru kohta", str(len(V)), "",
              f'{len(v_muud)} ütleb muud kui allikas · {menuu("kas-tosi", f"{lahti} allikate lahknevust selgitamata", "lahknevused")}',
              menuu("kas-tosi", "Väited"), href="kas-see-on-tosi.html#vaited"),
    ])

    # 2. ELi kaart ja järjestus omaette real
    y = andmed.leia(A, EB, "EE", "uusim:alus")["aasta"]
    el_v = [v for v in andmed.vali(A, EB, aasta=y, klass="alus") if v["geo"] in A["el_riigid"]]
    eu = andmed.leia(A, EB, EL, y)
    koht = andmed.koht(A, EB, "EE", y)
    kaart_html = kaart(el_v, (0, 10, 20, 30, 40), viide=eu["vaartus"], viite_nimi=f"EL {pr(eu['vaartus'])}")
    bump = el_jarjestus(EB, koht_praegu=koht, aasta_praegu=y)
    if bump:
        # Kadri 7.11.2026: järjestuse muutus ajas loendi asemel (kaart jääb vasakule)
        b_g, b_k, b_a, b_tbl, _ = bump
        k0 = b_k.get(b_a[0])
        h2_el = (f"Ettevõtete tehisaru kasutuses tõusis Eesti ELis {b_a[0]}. aasta {k0}. kohalt <b>{koht}. kohale</b> ({y})"
                 if k0 and k0 > koht else f"Ettevõtete tehisaru kasutuses on Eesti ELis <b>{koht}. kohal</b> ({y})")
        ps_el = (f"Kaart: tehisaru kasutavate ettevõtete osakaal {y}, %. Paremal: koht ELis igal aastal"
                 f"{' (' + ', '.join(str(a) for a in range(b_a[0], b_a[-1]) if a not in b_a) + ' ei mõõdetud)' if len(b_a) < b_a[-1] - b_a[0] + 1 else ''}."
                 " Klõpsa real, et see esile tõsta.")
        parem = f'<div class="el-bump">{b_g}<details><summary>Näita andmetabelit</summary><div>{b_tbl}</div></details></div>'
    else:
        h2_el = f"Ettevõtete tehisaru kasutuses on Eesti ELis <b>{koht}. kohal</b>, ELi keskmisest ees ja Põhjamaadest taga ({y})"
        ps_el = f"Tehisaru kasutavate ettevõtete osakaal, %, vähemalt 10 hõivatuga ettevõtted, {y}."
        parem = jarjestus(el_v, 45, eu["vaartus"], f"EL {pr(eu['vaartus'])}")
    sec_el = f"""
<section class="pn sp12" id="el" aria-labelledby="h-el">
  <div class="pn-h"><h2 id="h-el">{h2_el}</h2></div>
  <p class="ps">{ps_el}</p>
  <div class="el-rida"><div class="el-kaart">{kaart_html}</div>{parem}</div>
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
  <div class="pn-h"><h2 id="h-tootus">Eesti töötus oli {kuu_seesytlev(kuu)} <b>{pr(t_ee)}%</b>; {p_aasta}. aasta keskmise prognoos on {pr(prog[p_aasta]['protsent'])}%, see on teine mõõdik</h2></div>
  <div class="g2"><div><p class="gt">Aasta keskmine, tegelik ja prognoos</p>{aastatulbad([(r["aasta"], r["protsent"], r["tegelik"]) for r in prog.values()], 10, 2)}</div>
  <div><p class="gt">Kuu kaupa, sesoonselt tasandatud, {k0[5:]}/{k0[:4]}–{kuu[5:]}/{kuu[:4]}</p>{kuujoon}</div></div>
  <p class="drift">Prognoos on aasta keskmine, kuunumber sesoonselt tasandatud. Tehisaru mõju prognoos eraldi ei arvesta.</p>
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
    voog = sorted(sorted(set(voog), key=lambda r: (r[1], r[3])), key=lambda r: r[0], reverse=True)  # kindel järjekord
    viimane = voog[0][0]
    from datetime import date
    d = lambda iso: date.fromisoformat(iso[:10])  # noqa: E731
    uued = sum(1 for r in voog if (d(viimane) - d(r[0])).days <= VOO_PAEVI)
    read = "".join(f'<li><span class="d">{kp(r[0])}</span><span class="t {r[2]}">{e(r[1])}</span>'
                   f'<span>{f"<a href={chr(34)}{e(r[4])}{chr(34)}>{r[3]}</a>" if r[4] else r[3]}</span></li>' for r in voog[:VOO_RIDU])
    sec_voog = f"""
<section class="pn sp5" id="muutus" aria-labelledby="h-muutus">
  <div class="pn-h"><h2 id="h-muutus">Mis muutus: viimati <b>{kp(viimane)}</b></h2></div>
  <p class="ps">{VOO_PAEVI} päevaga lisandus {uued}.</p>
  <ul class="voog">{read}</ul>
  <p class="allikas">Kogu loend: {menuu("kas-tosi", "Usaldus › Värskus", "muutused")}. Tehisaru ja töö uudised Eestist ja maailmast: {menuu("uudised", "Uudised")}.</p>
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
  <p class="allikas">Iga siht oma allika ja skaalaga; ELi sihid on ELi kui terviku kohta. Üksikasjad: {menuu("ettevotted", "Ettevõtted", "kasutus")}, {menuu("inimesed", "Inimesed", "digi")}.</p>
</section>"""

    sec_hanked = f"""
<section class="pn sp4" id="hanked" aria-labelledby="h-hanked">
  <div class="pn-h"><h2 id="h-hanked">Tehisaru- ja andmehangete osa on <b>alla 1%</b> kõigist hangetest</h2><span class="chip exp">katseline</span></div>
  <p class="ps">{h_uus["aasta"]} ({e(h_uus["periood"])}): <b>{h_uus["ai_ja_andmed"]}</b> hanget, {pr(h_uus["osa"])}% kõigist. Aastaid ei võrrelda enne, kui 100 hanget on inimese pimesi märgistatud.</p>
  <p class="allikas">Allikas: {a(HANKED_URL, "riigihangete register")} ja TED; masinmärgistus, inimene pole kontrollinud. Kõik hanked: {menuu("hanked", "Hanked")}.</p>
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
  <div class="pn-h"><h2 id="h-vaited">IMF-i ja Goldman Sachsi <b>„puudutab“ on pealkirjades muutunud sõnaks „kaob“</b></h2></div>
  <div class="tbl"><table><thead><tr><th scope="col" style="width:38%">Väide ja väljaanne</th><th scope="col" style="width:13%">Hinnang</th><th scope="col">Mida allikas tegelikult ütleb</th></tr></thead><tbody>{v_read}</tbody></table></div>
  <p class="allikas">Väide kuulub väljaandele. Siin {min(4, len(V))} väidet {len(V)}-st; kõik: {menuu("kas-tosi", "Väited")}.</p>
</section>"""

    pea = f"""
<div class="pea-t">
  <h1>{taida(vaade["h1"], A)}</h1>
  <p class="seis-t">Andmed: Statistikaamet {kp(ein["avaldatud"])} ja {kp(eeb["avaldatud"])}, Eurostat {kp(UNE_UUENDATUD)}</p>
</div>
<nav aria-label="Sellel lehel"><ul class="sellel"><li><a href="#el">Eesti ELis</a></li><li><a href="#tootus">Töö ja töötus</a></li><li><a href="#trend">Ettevõtted</a></li><li><a href="#muutus">Mis muutus</a></li><li><a href="#sihid">Sihid</a></li><li><a href="#hanked">Hanked</a></li><li><a href="#vaited">Väited</a></li></ul></nav>
<div class="plaadid" aria-label="Peamised numbrid">{plaadid}</div>"""
    return (pea + '<div class="g12">' + sec_el + "</div>"
            # ettevõtete trend ELi koha järel, siis töötus (Kadri 6.11.2026 22:27, ettepanek 9)
            + '<div class="g12">' + sec_trend + sec_prog + "</div>"
            + '<div class="g12">' + sec_voog + sec_sihid + sec_hanked + "</div>"
            + '<div class="g12">' + sec_vaited + "</div>")


# ---------------------------------------------------------------- Töö vaate Eesti rida

ROLL_NIMI = {"otsene": "otsene põhjus", "osaline": "üks põhjus", "kaudne": "kaudne", "tulevikus": "võib tulevikus",
             "ei_mainita": "ei mainita"}


def koondamise_arv(r):
    """Koondatute arv Eestis tekstina: täpne, „vähemalt“, „kuni“ või „arv pole teada“."""
    if r.get("arv_eestis") is not None:
        return ("vähemalt " if r.get("arv_vahemalt") else "") + str(r["arv_eestis"])
    return f'kuni {r["arv_ulem"]}' if r.get("arv_ulem") else "arv pole teada"


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
    arvsona = SEESTYTLEV.get(len(juhtumid), f"{len(juhtumid)}-st")
    otse = "mitte ükski" if otsene == 0 else ARVSONAD.get(otsene, str(otsene))
    # USA statistikaameti firmauuring: otsene mõõt firmadelt (sisuloogika 6.11.2026)
    bon = (A.get("uuringud") or {}).get("bonney2026")
    bonney_rida = (f'<p class="ps">Võrdluseks USA: ametlikus ettevõtete uuringus teatas tehisaruga seotud töötajate vähendamisest '
                   f'<b>2% firmadest</b>, tehisaru kasutas 18% (<a href="{e(bon["url"])}">USA statistikaamet, Bonney jt {bon["aasta"]}</a>).</p>'
                   if bon and "2% firmadest" in bon["leid"] and "18% firmadest" in bon["leid"] else "")
    k_pea = f'<div class="pn-h"><h2 id="h-koondamised">{arvsona.capitalize()} Eesti koondamisest: tehisaru otsese põhjusena <b>{otse}</b>, ühe põhjusena {ARVSONAD.get(mainib, str(mainib))}</h2></div>'
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
<div class="kk-vis" id="koondamised-visuaal">
  <h3 class="kk-h3" id="h-koondamised-v">Tehisaru nimetati üheks põhjuseks <b>{pohjus} töökoha</b> juures {piir}{kokku}-st</h3>
  <p class="ps">Teatatud töökohad ettevõtte kaupa. Ainult koondamised, mille puhul uudis küsis tehisaru kohta; nimekiri pole täielik (kontrollitud {kp(K["kontrollitud"])}).</p>
  <div class="kr-ribad" role="list" aria-label="Koondatavad töökohad ettevõtte kaupa">{ribad}</div>
  <p class="kr-leg">{legend}</p>
  <p class="allikas">Allikas: uudised, lingid tabelis <a href="#palkamine">Keda koondajad otsivad</a>. Ettevõtte enda selgitus ei tõenda põhjust. Katkendäärega tulp on teatatud ülempiir{"; + tähendab, et lõplik arv pole veel teada" if alam else ""}.</p>
  {bonney_rida}
</div>"""
    # Kaardid võeti maha; arv, põhjus ja link on tabelis „Keda koondajad otsivad“ (Kadri MKUS-i kommentaar 7.11.2026 08:48)
    sec_kv = f"""
<section class="pn sp9" id="koondamised" aria-labelledby="h-koondamised">
  {k_pea}
  {sec_v}
</section>"""
    return f'<div class="g12">{sec_t}{sec_kv}</div>'


# ---------------------------------------------------------------- Töö: kus ja mis valdkonnas palgatakse

PAV_URL = "https://andmed.stat.ee/et/stat/majandus__palk-ja-toojeukulu__vabad-ametikohad"
LUHI = {"Hulgi- ja jaekaubandus; mootorsõidukite ja mootorrataste remont": "Kaubandus ja autoremont",
        "Avalik haldus ja riigikaitse; kohustuslik sotsiaalkindlustus": "Avalik haldus ja riigikaitse",
        "Elektrienergia, gaasi, auru ja konditsioneeritud õhuga varustamine": "Energeetika",
        "Veevarustus; kanalisatsioon; jäätme- ja saastekäitlus": "Vesi ja jäätmed",
        "Põllumajandus, metsamajandus ja kalapüük": "Põllu- ja metsamajandus",
        "Kutse-, teadus- ja tehnikaalane tegevus": "Kutse-, teadus- ja tehnikaala",
        "Tervishoid ja sotsiaalhoolekanne": "Tervishoid ja hoolekanne",
        "Kunst, meelelahutus ja vaba aeg": "Kunst ja meelelahutus",
        "Harju maakond, v.a Tallinn": "Harjumaa (v.a Tallinn)"}


def _kv(p):
    """„2026 II kvartal“ → (2026, 2)."""
    a, k, _ = p.split()
    return int(a), {"I": 1, "II": 2, "III": 3, "IV": 4}[k]


def el_jarjestus(naitaja, fookus="EE", kahanevalt=True, koht_praegu=None, aasta_praegu=None, lai=(720, 130, 140)):
    """ELi riikide koht aastate kaupa sisu/el-jarjestus.csv põhjal (lae_el_jarjestus.py, Eurostat).
    Kadri 7.11.2026: järjestuse muutus ajas. koht_praegu: kui antud, peab viimase aasta koht registriga klappima.
    Tagastab (graafik, koht {aasta: koht}, aastad, tabel, uuendatud) või None, kui faili pole."""
    from komponendid import jarjestuse_muutus
    if not (SISU / "el-jarjestus.csv").exists():
        return None
    R = [r for r in _loe("el-jarjestus.csv") if r["naitaja"] == naitaja]
    if not R:
        return None
    v = {}
    for r in R:
        v.setdefault(r["geo"], {})[int(r["aasta"])] = float(r["vaartus"])
    aastad = sorted({a for x in v.values() for a in x})
    koht = {g: {} for g in v}
    for a in aastad:
        for i, g in enumerate(sorted((g for g in v if a in v[g]), key=lambda g: -v[g][a] if kahanevalt else v[g][a]), 1):
            koht[g][a] = i
    if koht_praegu is not None and koht[fookus].get(aasta_praegu) != koht_praegu:
        raise AndmeViga(f"el-jarjestus.csv: {naitaja} {fookus} {aasta_praegu} koht {koht[fookus].get(aasta_praegu)}, "
                        f"registris {koht_praegu}; käivita python3 sait/lae_el_jarjestus.py")
    jarjest = sorted(koht, key=lambda g: koht[g].get(aastad[-1], 99))
    nimed = {g: riik(g) for g in jarjest}
    g = jarjestuse_muutus({nimed[x]: koht[x] for x in jarjest}, aastad, nimed[fookus], None, piirid=(5, 10, 15),
                          silt=R[0]["kirjeldus"], lai=lai, kitsas=(358, 24, 130))
    from komponendid import tabel
    tbl = tabel(["Riik"] + [str(a) for a in aastad],
                [[e(nimed[x])] + [f"{pr(v[x][a])} ({koht[x][a]}.)" if a in v[x] else "–" for a in aastad] for x in jarjest],
                fookus_rida=jarjest.index(fookus), pealdis=R[0]["kirjeldus"] + " (sulgudes koht ELis)")
    return g, koht[fookus], aastad, tbl, R[0]["uuendatud"]


def tootus_el():
    """Eesti koht ELi riikide töötuse määras aastate kaupa (Kadri 7.11.2026: järjestuse muutus ajas). 1 = kõrgeim töötus."""
    b = el_jarjestus("tootuse-maar", lai=(1000, 150, 160))
    if not b:
        return ""
    g, k, aastad, tbl, uuendatud = b
    a0, a1 = aastad[0], aastad[-1]
    h2 = (f"Eesti töötus on ELis <b>{k[a1]}. kõrgeim</b> ({a1}); {a0}. aastal oli Eesti {k[a0]}. kohal"
          if k.get(a0) else f"Eesti töötus on ELis <b>{k[a1]}. kõrgeim</b> ({a1})")
    return f"""
<div class="g12">
<section class="pn sp12" id="tootus-el" aria-labelledby="h-tootus-el">
  <div class="pn-h"><h2 id="h-tootus-el">{h2}</h2></div>
  <p class="ps">ELi riikide järjestus töötuse määra järgi, aasta keskmine, 15–74-aastased; 1. koht on kõrgeim töötus. Klõpsa real, et see esile tõsta. Järjestus ei ütle, kas põhjus on tehisaru.</p>
  <div class="el-bump yksi">{g}</div>
  <details><summary>Näita andmetabelit</summary><div>{tbl}</div></details>
  {allikarida([("Eurostat une_rt_a", "https://ec.europa.eu/eurostat/databrowser/view/une_rt_a/default/table", f"uuendatud {kp(uuendatud)}")])}
</section>
</div>"""


def _vabad_jarjestus():
    """Tegevusalade koht vabade ametikohtade arvu järgi, sama kvartal igal aastal (sisu/vabad-jarjestus.csv).
    Kadri 7.11.2026: tulpade asemel järjestuse muutus aastate kaupa, mitu aastat. Tagastab (graafik, pealkiri, tabel)."""
    from komponendid import jarjestuse_muutus, tabel
    if not (SISU / "vabad-jarjestus.csv").exists():
        return "", "", ""
    R = [r for r in _loe("vabad-jarjestus.csv") if not r["nimi"].startswith("Kokku")]
    arv = {}
    for r in R:
        arv.setdefault(LUHI.get(r["nimi"], r["nimi"]), {})[int(r["periood"][:4])] = float(r["vaartus"])
    aastad = sorted({a for v in arv.values() for a in v})
    kv = R[0]["periood"].split(" ", 1)[1]
    # alles jäävad tegevusalad, mille arv on avaldatud vähemalt pooltel aastatel; koht arvutatakse nende seas
    arv = {n: v for n, v in arv.items() if len(v) * 2 >= len(aastad)}
    koht = {n: {} for n in arv}
    for a in aastad:
        for i, n in enumerate(sorted((n for n in arv if a in arv[n]), key=lambda n: -arv[n][a]), 1):
            koht[n][a] = i
    a0, a1 = aastad[0], aastad[-1]
    fookus = next(n for n in koht if koht[n].get(a1) == 1)
    teine = next((n for n in koht if koht[n].get(a0) == 1 and n != fookus), None)
    jarjest = sorted(koht, key=lambda n: koht[n].get(a1, 99))
    g = jarjestuse_muutus({n: koht[n] for n in jarjest}, aastad, fookus, teine,
                          silt=f"Tegevusalade koht vabade ametikohtade arvu järgi, {a0}–{a1}")
    f0 = koht[fookus].get(a0)
    lause = f"<b>{e(fookus)}</b> tõusis {a0}. aasta {f0}. kohalt 1. kohale" if f0 and f0 > 1 else f"<b>{e(fookus)}</b> on 1. kohal"
    if teine and koht[teine].get(a1):
        lause += f", {e(teine.lower())} langes 1. kohalt {koht[teine][a1]}. kohale"
    gt = (f'<p class="gt">Mis valdkonnas on kõige rohkem vabu ametikohti: {lause}</p>'
          f'<p class="ps">Tegevusala koht vabade ametikohtade arvu järgi, iga aasta {kv}. Klõpsa real, et see esile tõsta.'
          f'{" Tühi koht: Statistikaamet ei avaldanud." if any(len(v) < len(aastad) for v in koht.values()) else ""}</p>')
    nb = lambda v: f"{v:,.0f}".replace(",", NBSP)  # noqa: E731
    tbl = tabel(["Tegevusala"] + [str(a) for a in aastad],
                [[e(n)] + [f"{nb(arv[n][a])} ({koht[n][a]}.)" if a in arv[n] else "–" for a in aastad] for n in jarjest],
                pealdis=f"Vabad ametikohad tegevusala järgi, iga aasta {kv} (sulgudes koht)")
    return g, gt, tbl


def vabad_ametikohad():
    """Statistikaameti vabad ametikohad tegevusala ja maakonna järgi (Kadri 7.11.2026: „mida ja kus palgatakse“).
    Tühi, kui faili sisu/vabad-ametikohad.csv pole (python3 sait/lae_vabad.py)."""
    if not (SISU / "vabad-ametikohad.csv").exists():
        return ""
    R = _loe("vabad-ametikohad.csv")
    for r in R:
        r["vaartus"] = float(r["vaartus"])
    viimane = max((r["periood"] for r in R if r["tabel"] == "PAV011"), key=_kv)
    a, k = _kv(viimane)
    aasta_tagasi = f'{a - 1} {["I", "II", "III", "IV"][k - 1]} kvartal'
    arv = {(r["nimi"], r["periood"]): r["vaartus"] for r in R if r["tabel"] == "PAV011" and r["naitaja"] == "Vabade ametikohtade arv"}
    voetud = {(r["nimi"], r["periood"]): r["vaartus"] for r in R if r["tabel"] == "PAV011" and r["naitaja"] == "Tööle võetud töötajate arv"}
    KOKKU = "Kokku – kõik tegevusalad"
    kokku, kokku0 = arv[(KOKKU, viimane)], arv.get((KOKKU, aasta_tagasi))
    alad = sorted(((n, v) for (n, p), v in arv.items() if p == viimane and n != KOKKU), key=lambda x: -x[1])
    if not alad or kokku0 is None:
        raise AndmeViga("vabad-ametikohad.csv: viimase kvartali või aasta varasema kvartali rida puudub")
    muut = (kokku - kokku0) / kokku0 * 100
    from komponendid import jarjestuse_muutus, lihtribad, tabel
    bump, bump_gt, bump_tbl = _vabad_jarjestus()
    # maakonnad: osatähtsus kõigist vabadest ametikohtadest; Harju maakond on jagatud Tallinnaks ja ülejäänud Harjumaaks
    kv14 = max((r["periood"] for r in R if r["tabel"] == "PAV014"), key=_kv)
    osa = {r["nimi"]: r["vaartus"] for r in R if r["tabel"] == "PAV014" and r["periood"] == kv14 and r["naitaja"] == "Vabade ametikohtade osatähtsus, %"}
    maak = sorted(((n, v) for n, v in osa.items() if n not in ("Eesti", "Harju maakond")), key=lambda x: -x[1])
    read_m = [(LUHI.get(n, n), v, pr(v) + "%") for n, v in maak]
    g_m = lihtribad(read_m, 80 if maak[0][1] <= 80 else 100, samm=20, uhik="%", fookus=0)
    teadmata = 100 - osa.get("Eesti", 100)
    koik_m = {r["nimi"] for r in R if r["tabel"] == "PAV014"} - {"Eesti", "Harju maakond"}
    puudu = sorted(n.replace(" maakond", "") for n in koik_m - set(osa))
    uuendatud = R[0]["uuendatud"]
    kokku_v = voetud.get((KOKKU, viimane))
    yks, kaks = alad[0], alad[1]
    n_kokku = f"{kokku:,.0f}".replace(",", "\u00a0")
    h2 = (f'{a}. aasta {viimane.split()[1]} kvartalis oli Eestis <b>{n_kokku} vaba ametikohta</b>, '
          f'{abs(muut):.0f}% {"vähem" if muut < 0 else "rohkem"} kui aasta varem; enim hariduses ja avalikus halduses')
    if (yks[0], kaks[0]) != ("Haridus", "Avalik haldus ja riigikaitse; kohustuslik sotsiaalkindlustus"):
        h2 = h2.split("; enim")[0] + f"; enim: {LUHI.get(yks[0], yks[0]).lower()} ja {LUHI.get(kaks[0], kaks[0]).lower()}"
    tbl = bump_tbl or tabel(["Tegevusala", viimane, aasta_tagasi],
                [[e(n), f"{v:,.0f}".replace(",", "\u00a0"), f"{arv.get((n, aasta_tagasi), 0):,.0f}".replace(",", "\u00a0")] for n, v in alad],
                pealdis="Vabad ametikohad tegevusala järgi")
    # Python 3.10: f-stringi avaldises ei tohi olla kaldkriipsu, seepärast arvutatakse lause enne
    v_lause = f" Samas kvartalis võeti tööle {kokku_v:,.0f} inimest.".replace(",", NBSP) if kokku_v else ""
    return f"""
<div class="g12">
<section class="pn sp12" id="vabad-kohad" aria-labelledby="h-vabad-kohad">
  <div class="pn-h"><h2 id="h-vabad-kohad">{h2}</h2></div>
  <p class="ps">Vaba ametikoht on koht, mille täitmiseks tööandja otsib aktiivselt töötajat väljastpoolt (Statistikaameti tööandjate uuring, kvartali keskmine).{v_lause}</p>
  <div class="vk-bump">{bump_gt}{bump}</div>
  <div class="vk-kus">
    <div><p class="gt">Kus: osa kõigist vabadest ametikohtadest maakonna järgi, %, {kv14}</p><p class="ps">Harjumaa on jagatud Tallinnaks ja ülejäänud Harjumaaks.{f" {pr(teadmata)}% kohtadest asukohta ei määratud." if teadmata > 0.05 else ""}{" Statistikaamet ei avaldanud seda kvartalit: " + ", ".join(puudu) + "." if puudu else ""}</p>{g_m}</div>
  </div>
  <details><summary>Näita andmetabelit</summary><div>{tbl}</div></details>
  {allikarida([("Statistikaamet PAV011 ja PAV014", PAV_URL, f"avaldatud {kp(uuendatud)}")])}
</section>
</div>"""
