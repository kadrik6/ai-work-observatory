"""Seire saidi lisaosa „Mis toimub“ (toimub.html): tööturu olukord, Eesti koondamised, AI- ja andmehanked, tehisaru uudised.

Kadri 5.11.2026: „lisa ai uudised ja tööolukorra statistika koos koondamistega ka suurele seire lehele“.
Kasutus: python3 lisalehed.py HTML_KAUST   (pärast raportid/koosta.py-d; uuenda_seire.sh kutsub)
- Tööturg: Eurostat une_rt_m (töötuse määr kuu kaupa, sesoonselt kohandatud), Eesti ja EL27, kõik ja alla 25-aastased.
- Koondamised ja uudised: /mnt/project-files/tooelu-uudised (uudised.jsonl, vaited.json, olek.json + repo koondamised_ee.json).
- Koondajate taust (sektor, firma liik, kaotatud ja pakutavad ametid): tooelu-uudised/koondajad.json.
- Lisab kõigi lehtede saidiosade ribale viienda osa „Mis toimub“.
Lehe kujundus tuleb seire stiil.css-ist; päis ja jalus võetakse koosta.py tehtud lehelt otsused.html.
"""
import html
import json
import os
import re
import sys
import urllib.request
from datetime import date, datetime
from pathlib import Path

SIIN = Path(__file__).resolve().parent
_ANDMED = os.environ.get("UUENDUS_ANDMED", "/mnt/project-files")
UUDISED = Path(os.environ.get("UUDISED", os.path.join(_ANDMED, "tooelu-uudised")))
KAUST = None  # main() seab: ehitatud saidi kaust
UUDISTELEHT = "https://claude.ai/artifact/3HsbSix5f2FRFpGHEQG4pU"
FAIL = "toimub.html"
e = html.escape
KUUD = ["jaanuar", "veebruar", "märts", "aprill", "mai", "juuni", "juuli", "august", "september", "oktoober", "november", "detsember"]
ROLLID = {"otsene": "Tehisaru teeb tööd inimeste asemel", "osaline": "Tehisaru üks põhjustest",
          "kaudne": "Tehisaru muutis turgu, inimesi ei asenda", "tulevikus": "Tehisaru võib tulevikus koondamisi tuua",
          "ei_mainita": "Tehisaru ei mainita"}
LIIK = {"arvamus": "arvamus", "aruanne": "aruanne", "uuring": "uuring", "eksitav": "eksitav"}
HINNANG = {"vale": ("risk", "Vale"), "osaliselt": ("warn", "Osaliselt õige"), "oige": ("ok", "Vastab allikale"),
           "õige": ("ok", "Vastab allikale")}


def arv(x, k=1):
    return f"{x:.{k}f}".replace(".", ",")


def kp(s):
    return f"{int(s[8:10])}.{int(s[5:7])}.{s[:4]}"


# ---------- Tööturg (Eurostat) ----------
def eurostat():
    url = ("https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/une_rt_m?geo=EE&geo=EU27_2020"
           "&s_adj=SA&sex=T&unit=PC_ACT&age=TOTAL&age=Y_LT25&sinceTimePeriod=2023-01")
    d = json.load(urllib.request.urlopen(url, timeout=60))
    dims = d["id"]
    suurus = d["size"]
    idx = {k: d["dimension"][k]["category"]["index"] for k in dims}
    flag = d.get("status", {})
    seeria = {}
    for k, v in d["value"].items():
        lipp = flag.get(k, "")
        k = int(k)
        koht = {}
        for dim, n in zip(reversed(dims), reversed(suurus)):
            koht[dim] = k % n
            k //= n
        nimi = {dim: next(c for c, i in idx[dim].items() if i == koht[dim]) for dim in ("geo", "age", "time")}
        seeria.setdefault((nimi["geo"], nimi["age"]), {})[nimi["time"]] = (v, lipp)
    return seeria, d.get("updated", "")[:10]


def kuu(t):
    return f"{KUUD[int(t[5:7]) - 1]} {t[:4]}"


def joonis(ee, el, sildid):
    """Kuu joondiagramm: Eesti fookusjoon, EL võrdlusjoon. Viimased 33 kuud."""
    kuud = sorted(set(ee) | set(el))[-33:]
    W, H, ml, mr, mt, mb = 480, 210, 30, 96, 12, 28
    tipp = max(v for s in (ee, el) for t, (v, _) in s.items() if t in kuud)
    samm = 2 if tipp <= 12 else 5
    ymax = int(-(-tipp // samm) * samm)
    X = lambda i: ml + i / (len(kuud) - 1) * (W - ml - mr)
    Y = lambda v: mt + (1 - v / ymax) * (H - mt - mb)
    o = []
    for t in range(0, ymax + 1, samm):
        o.append(f'<line class="gridline" x1="{ml}" x2="{W - mr}" y1="{Y(t):.1f}" y2="{Y(t):.1f}"/>'
                 f'<text x="{ml - 8}" y="{Y(t) + 5:.1f}" text-anchor="end">{t}</text>')
    for i, t in enumerate(kuud):
        if t[5:7] == "01":
            o.append(f'<text x="{X(i):.1f}" y="{H - 8}" text-anchor="middle">{t[:4]}</text>')
    lab = []
    for s, klass, nimi in ((el, "ref", sildid[1]), (ee, "focus", sildid[0])):
        pp = [(i, s[t][0]) for i, t in enumerate(kuud) if t in s]
        o.append(f'<path class="ln {klass}" d="' + " ".join(f'{"M" if j == 0 else "L"}{X(i):.1f},{Y(v):.1f}' for j, (i, v) in enumerate(pp)) + '"/>')
        i, v = pp[-1]
        o.append(f'<circle class="dot {klass}" cx="{X(i):.1f}" cy="{Y(v):.1f}" r="{4.5 if klass == "focus" else 3.5}"/>')
        lab.append([Y(v), f"{nimi} {arv(v)}%", klass])
    lab.sort(key=lambda t: t[0])
    if len(lab) == 2 and lab[1][0] - lab[0][0] < 17:
        lab[1][0] = lab[0][0] + 17
    for y, t, k in lab:
        o.append(f'<text x="{W - mr + 10}" y="{y + 5:.1f}" class="lab-{k}">{e(t)}</text>')
    return (f'<div class="kuujoon"><svg viewBox="0 0 {W} {H}" role="img" aria-label="{e(sildid[0])} ja {e(sildid[1])} '
            f'töötuse määr kuu kaupa {kuu(kuud[0])} kuni {kuu(kuud[-1])}.">{"".join(o)}</svg></div>')


def tooturg():
    s, uuendatud = eurostat()
    kaardid, h1_osa = [], None
    for vanus, nimi in (("TOTAL", "Töötus"), ("Y_LT25", "Noorte (alla 25) töötus")):
        ee, el = s[("EE", vanus)], s[("EU27_2020", vanus)]
        t = max(ee)
        v_ee, v_el = ee[t][0], el.get(t, (None,))[0]
        aasta_tagasi = f"{int(t[:4]) - 1}{t[4:]}"
        muutus = v_ee - ee[aasta_tagasi][0] if aasta_tagasi in ee else None
        suund = ("" if muutus is None else
                 f" Aasta varem oli see {arv(ee[aasta_tagasi][0])}%." if abs(muutus) >= 0.05 else " Aasta varem oli see sama.")
        vord = "kõrgem" if v_el is not None and v_ee > v_el + 0.05 else "madalam" if v_el is not None and v_ee < v_el - 0.05 else "sama"
        pealk = (f"{nimi} Eestis on {arv(v_ee)}%, ELis {arv(v_el)}%" if v_el is not None else f"{nimi} Eestis on {arv(v_ee)}%")
        if vanus == "TOTAL":
            h1_osa = (v_ee, t, vord)
        kaardid.append(
            '<div class="card"><div class="chart">'
            f'<h3 class="chart-title">{e(pealk)}</h3>'
            f'<p class="chart-sub">Töötuse määr, % tööjõust, sesoonselt kohandatud, kuu kaupa, viimane {kuu(t)}.{e(suund)}</p>'
            f'{joonis(ee, el, ("Eesti", "EL"))}</div></div>')
    return kaardid, h1_osa, uuendatud


# ---------- Koondamised ja uudised ----------
def uudised():
    sys.path.insert(0, str(SIIN))
    import ehita_leht  # noqa: E402  (sama liitmine nagu uudistelehel)
    return ehita_leht.loe()


def koondamiste_plokk(koond):
    loend = {}
    for k in koond:
        loend[k["ai_roll"]] = loend.get(k["ai_roll"], 0) + 1
    tipp = max(loend.values())
    read = "".join(
        f'<li class="{"is-focus" if r != "ei_mainita" else ""}"><span class="lab">{e(ROLLID[r])}</span>'
        f'<span class="track"><span class="bar" style="width:{loend[r] / tipp * 100:.1f}%"></span></span>'
        f'<span class="val">{loend[r]}</span></li>'
        for r in ROLLID if r in loend)
    ai = sum(v for r, v in loend.items() if r != "ei_mainita")
    rida = []
    for k in koond:
        rida.append(
            f'<li><span class="when">{kp(k["kuupaev"])}</span><div class="body">'
            f'<div class="row"><h4>{e(k["ettevote"])}</h4><span class="tag{" focus" if k["ai_roll"] != "ei_mainita" else ""}">{e(ROLLID[k["ai_roll"]])}</span></div>'
            f'<p>{e(k.get("arv_tekst") or "")}</p>'
            f'<p class="small">{e(k.get("pohjus") or "")}</p>'
            f'<p class="small">Allikas: <a href="{e(k["url"])}">{e(k["allikas"])}: {e(k["pealkiri"])}</a></p></div></li>')
    return f'''<section id="koondamised"><div class="section-head"><p class="eyebrow">Koondamised Eestis</p>
<h2>{len(koond)} koondamisest {ai} puhul räägiti tehisarust</h2></div>
<div class="card"><div class="chart"><h3 class="chart-title">Mida ettevõte tehisaru kohta ütles</h3>
<p class="chart-sub">Koondamiste arv uudistes alates oktoobrist 2026. Liigitus näitab ettevõtte enda sõnu, mitte meie hinnangut.</p>
<ul class="bars" role="list">{read}</ul></div></div>
<ol class="list decisions">{"".join(rida)}</ol>
<p class="small">Koondamised on kogutud uudistest (ERR, ERR News jt) ja kontrollitud artikli järgi. See ei ole täielik nimekiri: kõigi kollektiivsete koondamiste arvu annaks Töötukassa statistika, mida see leht veel automaatselt ei loe.</p></section>'''


def koondajate_plokk(koond):
    """Kes koondab (sektor, firma liik), milliseid ameteid ja keda samad firmad praegu otsivad (Kadri 5.11.2026)."""
    try:
        andmed = json.loads((UUDISED / "koondajad.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return ""
    firmad = andmed["firmad"]
    jarjekord, nahtud = [], set()
    for k in koond:
        if k["ettevote"] in firmad and k["ettevote"] not in nahtud:
            jarjekord.append(k["ettevote"])
            nahtud.add(k["ettevote"])
    puudu = [k["ettevote"] for k in koond if k["ettevote"] not in firmad]
    if not jarjekord:
        return ""
    kontrollitud = [firmad[f]["otsib"] for f in jarjekord if firmad[f]["otsib"].get("kontrollitud")]
    kuulutusi = sum(len(o["ametid"]) for o in kontrollitud)
    nullis = sum(1 for o in kontrollitud if not o["ametid"])
    # Ametiliikide võrdlus: mitu firmat koondab seda liiki ameteid ja mitu kuulutust samadelt firmadelt praegu on
    liigid = []
    for liik in andmed["ametiliigid"]:
        koondab = sum(1 for f in jarjekord if liik in firmad[f]["kaotatud"])
        otsib = sum(1 for f in jarjekord for a in firmad[f]["otsib"]["ametid"] if a["liik"] == liik)
        if koondab or otsib:
            liigid.append((liik, koondab, otsib))
    liigid.sort(key=lambda r: (-r[1], -r[2]))
    liigiread = "".join(f'<tr><td>{e(l)}</td><td class="r">{k or "–"}</td><td class="r">{o or "–"}</td></tr>' for l, k, o in liigid)
    firmaread = []
    for f in jarjekord:
        d = firmad[f]
        o = d["otsib"]
        if o.get("kontrollitud"):
            nimed = "; ".join(a["nimi"] for a in o["ametid"])
            otsib = (e(nimed) + ". " if nimed else "") + e(o["tekst"]) + (f' <a href="{e(o["url"])}">Vaata</a>' if o.get("url") else "")
        else:
            otsib = e(o["tekst"])
        firmaread.append(
            f'<tr><th scope="row">{e(f)}</th><td>{e(d["sektor"])}<br><span class="small">{e(d["firma_liik"])}</span></td>'
            f'<td>{e(d["kaotatud_tekst"])} <a href="{e(d["kaotatud_allikas"])}">Allikas</a></td><td>{otsib}</td></tr>')
    pais = (f"Koondajad otsivad praegu kokku {kuulutusi} inimest, {nullis} firmat ei otsi kedagi"
            if kuulutusi else "Koondajatel pole praegu ühtegi avatud tööpakkumist")
    rühmad = {}
    for f in jarjekord:
        rühmad.setdefault(firmad[f].get("omand", "muu"), []).append(f"{f.split(' (')[0]} ({firmad[f]['sektor']})")
    kes = "; ".join(f"{r}: {', '.join(v)}" for r, v in sorted(rühmad.items(), key=lambda x: -len(x[1])))
    kp_k = max((o["kontrollitud"] for o in kontrollitud), default=None)
    lisa = (f' Taustaandmeid pole veel: {e(", ".join(puudu))}.' if puudu else "")
    return f'''<section id="koondajad"><div class="section-head"><p class="eyebrow">Kes koondab ja keda samad firmad otsivad</p>
<h2>{e(pais)}</h2></div>
<p><b>Kes koondab.</b> {e(kes)}.</p>
<p><b>Mis ametid.</b> Koondatakse peamiselt kontori-, IT- ja tugiameteid. Tootmise põhitöötajaid (näiteks jaamade operaatoreid) ei koondata.</p>
<div class="card"><h3 class="chart-title">Ametiliigid: kaotatud ja pakutavad</h3>
<p class="chart-sub">Mitu firmat koondab seda liiki ameteid ja mitu kuulutust samadel firmadel praegu Eestis avatud on.</p>
<div class="table-wrap"><table><thead><tr><th>Ametiliik</th><th class="r">Koondab (firmasid)</th><th class="r">Otsib (kuulutusi)</th></tr></thead>
<tbody>{liigiread}</tbody></table></div></div>
<details class="koondajad-detail"><summary>Firma kaupa: sektor, firma liik, kaotatud ja pakutavad ametid</summary>
<div class="table-wrap"><table class="koondajad-firmad"><thead><tr><th>Firma</th><th>Sektor ja liik</th><th>Mis ametid kaovad</th><th>Keda otsib praegu</th></tr></thead>
<tbody>{"".join(firmaread)}</tbody></table></div></details>
<p class="small">Kaotatud ametid on koondamisuudisest; firmad ei avalda alati täpset nimekirja. Pakutavad ametid on firma enda tööpakkumiste lehelt seisuga {kp(kp_k) if kp_k else "–"}: leht ei näita sisemisi ümberpaigutusi ega ainult LinkedInis avaldatud kuulutusi. Väike valim, mitte terve tööturu pilt.{lisa}</p></section>'''


def uudiste_plokk(uud, olek):
    tana = date.today()
    suured = [u for u in uud if u.get("suur") and (tana - date.fromisoformat(u["kuupaev"])).days <= 3]
    banner = "".join(
        f'<div class="note"><p><b>Suur uudis:</b> <a href="{e(u["url"])}">{e(u.get("pealkiri") or u.get("ettevote", ""))}</a> '
        f'({e(u["allikas"])}, {kp(u["kuupaev"])}). {e(u.get("suur_pohjus", ""))}</p></div>' for u in suured)

    def loend(piirkond):
        rr = [u for u in uud if u["piirkond"] == piirkond]
        out = []
        for i, u in enumerate(rr):
            pea = u.get("pealkiri") or f'{u.get("ettevote", "")}: koondamine'
            silt = f' <span class="tag warn">{LIIK[u["liik"]]}</span>' if u.get("liik") in LIIK else ""
            out.append(
                f'<li{" hidden" if i >= 12 else ""}><span class="when">{kp(u["kuupaev"])}</span><div class="body">'
                f'<p><a href="{e(u["url"])}">{e(pea)}</a>{silt}</p>'
                f'<p class="small">{e(u["allikas"])}{" · " + e(u["kes_utles"]) if u.get("kes_utles") else ""}</p>'
                + (f'<p class="small">{e(u["pohjus"])}</p>' if u.get("pohjus") else "") + '</div></li>')
        nupp = (f'<button type="button" class="nupp-koik" data-ava="{piirkond}">Näita kõiki ({len(rr)})</button>' if len(rr) > 12 else "")
        return f'<ol class="list" data-loend="{piirkond}">{"".join(out)}</ol>{nupp}', len(rr)

    ee, nee = loend("EE")
    ml, nml = loend("maailm")
    aeg = olek.get("viimane_kontroll", "")[:16].replace("T", " ")
    return f'''<section id="uudised"><div class="section-head"><p class="eyebrow">Uudised</p>
<h2>Tehisaru ja töö uudised: Eesti {nee}, maailm {nml}</h2></div>
{banner}
<h3>Eesti</h3>{ee}
<h3>Maailm</h3>{ml}
<p class="small">Uudised kogutakse iga päev ERR-i uudisvoost ja uudisteotsingust, viimati {e(aeg)}. Eesti ja maailm on eraldi. Arvamus on märgitud. Artikli teksti ei kopeerita, ainult pealkiri, link ja lühike sisu oma sõnadega. <a href="{UUDISTELEHT}">Kõik uudised ja väidete kontroll eraldi lehel</a>.</p></section>'''


def vaidete_plokk(vaited):
    if not vaited:
        return ""
    rr = []
    for v in vaited:
        k, silt = HINNANG.get(v.get("hinnang", ""), ("warn", v.get("hinnang", "")))
        rr.append(f'<li class="claim"><div class="row"><blockquote>„{e(v["vaide"])}“</blockquote><span class="tag {k}">{e(silt)}</span></div>'
                  f'<p class="small">Ütles: <a href="{e(v.get("kes_url", ""))}">{e(v.get("kes", ""))}</a></p>'
                  f'<p>{e(v.get("kokkuvote", ""))}</p></li>')
    return (f'<section id="vaited-uudistes"><div class="section-head"><p class="eyebrow">Uudistes kõlanud väited</p>'
            f'<h2>Kontrollitud {len(vaited)} väidet</h2></div><ul class="items claims">{"".join(rr)}</ul>'
            f'<p class="small">Tõendid ja allikad iga väite kohta on <a href="{UUDISTELEHT}#vaited">uudistelehel</a>. Ametliku statistika kohta käivad väited on osas <a href="vaited.html">Mida väidetakse</a>.</p></section>')


# ---------- Tehisaru- ja andmehanked (KURSUS-i tuvastus, hanked.yml logist) ----------
HANKED = Path(os.environ.get("SEIRE_UUENDUS", os.path.join(_ANDMED, "seire-uuendus"))) / "hanked"
OECD = "https://doi.org/10.1787/c2c09a06-en"


def aastajoon(read, kuni):
    """Aasta joondiagramm kahe seeriaga (tehisaru = fookus, andmed = võrdlus), väärtus = hangete arv."""
    W, H, ml, mr, mt, mb = 480, 210, 30, 118, 12, 28
    aastad = [r[0] for r in read]
    tipp = max(max(r[1], r[2]) for r in read)
    samm = 10 if tipp <= 60 else 20
    ymax = int(-(-tipp // samm) * samm)
    X = lambda i: ml + i / (len(aastad) - 1) * (W - ml - mr)
    Y = lambda v: mt + (1 - v / ymax) * (H - mt - mb)
    o = []
    for t in range(0, ymax + 1, samm):
        o.append(f'<line class="gridline" x1="{ml}" x2="{W - mr}" y1="{Y(t):.1f}" y2="{Y(t):.1f}"/>'
                 f'<text x="{ml - 8}" y="{Y(t) + 5:.1f}" text-anchor="end">{t}</text>')
    for i, a in enumerate(aastad):
        if i % 2 == 0 or i == len(aastad) - 1:
            o.append(f'<text x="{X(i):.1f}" y="{H - 8}" text-anchor="middle">{a}{"*" if i == len(aastad) - 1 else ""}</text>')
    lab = []
    for j, klass, nimi in ((2, "ref", "Andmed"), (1, "focus", "Tehisaru")):
        o.append(f'<path class="ln {klass}" d="' + " ".join(f'{"M" if i == 0 else "L"}{X(i):.1f},{Y(r[j]):.1f}' for i, r in enumerate(read)) + '"/>')
        v = read[-1][j]
        o.append(f'<circle class="dot {klass}" cx="{X(len(read) - 1):.1f}" cy="{Y(v):.1f}" r="{4.5 if klass == "focus" else 3.5}"/>')
        lab.append([Y(v), f"{nimi} {v}", klass])
    lab.sort(key=lambda t: t[0])
    if lab[1][0] - lab[0][0] < 17:
        lab[1][0] = lab[0][0] + 17
    for y, t, k in lab:
        o.append(f'<text x="{W - mr + 10}" y="{y + 5:.1f}" class="lab-{k}">{e(t)}</text>')
    return (f'<div class="kuujoon"><svg viewBox="0 0 {W} {H}" role="img" aria-label="Tehisaru- ja andmehangete arv aastas '
            f'{aastad[0]} kuni {aastad[-1]} (viimane aasta kuni {kp(kuni)}).">{"".join(o)}</svg></div>')


def hangete_plokk():
    try:
        d = json.loads((HANKED / "leht.json").read_text(encoding="utf-8"))
        seis = json.loads((HANKED / "seis.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return ""
    # Tegelik tellija pealkirjast (KURSUS-i hanked/tellija.py; uuenda_seire.sh toob selle repost). Kui faili pole, näita korraldajat.
    try:
        sys.path.insert(0, str(HANKED))
        import tellija as T
        nimed = T.asutused(r.get("h") for r in d["loend"])
        for r in d["loend"]:
            r["kj"], r["kja"] = T.kelle_jaoks(r.get("t"), r.get("h"), nimed)
    except ImportError:
        for r in d["loend"]:
            r["kj"], r["kja"] = r.get("h") or "", "sama"
    # Tehisaru = tehisaru märksõnaga hange (koonda.py ai_marksonaga / loendi "ai"); andmed = ülejäänud andmehanked.
    aastad = [a for a in d["aastad"] if a["aasta"] >= 2018]
    viim = aastad[-1]
    loend = sorted((r for r in d["loend"] if r.get("kp")), key=lambda r: r["kp"], reverse=True)
    kuni = loend[0]["kp"] if loend else ""
    read = [(a["aasta"], a["ai_marksonaga"], a["ai_andmed"] - a["ai_marksonaga"]) for a in aastad]
    ai_v, an_v = read[-1][1], read[-1][2]
    esimest = ai_v > an_v and all(r[1] <= r[2] for r in read[:-1])
    if ai_v > an_v:
        pais = (f"{viim['aasta']}. aastal on tehisaruhankeid {'esimest korda ' if esimest else ''}rohkem kui andmehankeid: {ai_v} ja {an_v}")
    elif ai_v < an_v:
        pais = f"{viim['aasta']}. aastal on andmehankeid rohkem kui tehisaruhankeid: {an_v} ja {ai_v}"
    else:
        pais = f"{viim['aasta']}. aastal on tehisaru- ja andmehankeid sama palju: {ai_v}"

    def summa(a, ai):
        rr = [r for r in d["loend"] if r["a"] == a and bool(r.get("ai")) == ai and r.get("v")]
        return sum(r["v"] for r in rr), len(rr)

    def eur(v):
        return f"{v / 1e6:.1f}".replace(".", ",") + " mln €" if v >= 1e6 else f"{v:,.0f}".replace(",", " ") + " €"
    tabel = []
    for (aasta, ai, an), a in zip(reversed(read), reversed(aastad)):
        fookus = ' class="is-focus"' if a is viim else ""
        tabel.append(f'<tr{fookus}><td>{aasta}{" (kuni " + kp(kuni) + ")" if a is viim and kuni else ""}</td>'
                     f'<td class="r">{ai}</td><td class="r">{an}</td><td class="r">{a["ai_andmed"]}</td><td class="r">{arv(a["ai_andmed_osakaal"])}%</td></tr>')
    s_ai, n_ai = summa(viim["aasta"], True)
    s_an, n_an = summa(viim["aasta"], False)
    raha = (f'Eeldatav maksumus {viim["aasta"]}. aastal: tehisaruhanked {eur(s_ai)} ({n_ai} hanke põhjal, kus see on teada), '
            f'andmehanked {eur(s_an)} ({n_an} hanke põhjal).')
    inn = [a for a in aastad if a.get("innovatsioonimark_osakaal") is not None]
    inn_lause = (f' Innovatsioonihanke märkega hankeid oli {viim["aasta"]}. aastal {arv(viim["innovatsioonimark_osakaal"])}% kõigist '
                 f'(siht 2% aastaks 2027, <a href="{OECD}">OECD 2026</a>); see on eraldi mõõdik, mitte tehisaruhangete osa.'
                 if inn and inn[-1] is viim else "")
    t = d["hindamine"].get("hindamine", {})
    tul = t.get("tulemused", {}).get(t.get("valitud", ""), {})
    tapsus = (f'Tuvastus on automaatne (masinõppemudel või märksõna). Märgendatud valimil ({d["hindamine"]["margendid"]["kokku"]} hanget, '
              f'märgendanud Claude, inimene pole veel üle kontrollinud) leidis see {round(tul["saagis"] * 100)}% õigetest ja '
              f'{round(tul["tapsus"] * 100)}% leitutest olid õiged. Arvud on suunanäitaja, mitte täpne loendus.') if tul else ""

    def nimekiri(ai, voti):
        rr = []
        for i, r in enumerate([r for r in loend if bool(r.get("ai")) == ai][:30]):
            hankija = (r["kj"] if r["kja"] == "sama" else f'Kelle jaoks: {r["kj"]} · korraldaja: {r.get("h") or ""}')
            pealkiri = e(r["t"] or "")
            if r.get("url"):
                pealkiri = '<a href="' + e(r["url"]) + '">' + pealkiri + "</a>"
            raha = (" · eeldatav maksumus " + "{:,.0f}".format(r["v"]).replace(",", " ") + " €") if r.get("v") else ""
            peidus = " hidden" if i >= 12 else ""
            rr.append(f'<li{peidus}><span class="when">{kp(r["kp"])}</span><div class="body">'
                      f'<p>{pealkiri}</p><p class="small">{e(hankija)}{raha}</p></div></li>')
        nupp = f'<button type="button" class="nupp-koik" data-ava="{voti}">Näita kõiki ({len(rr)})</button>' if len(rr) > 12 else ""
        return f'<ol class="list" data-loend="{voti}">{"".join(rr)}</ol>{nupp}'
    import collections

    def tellijad(ai):
        c = collections.Counter(r["kj"].split("; ")[0] for r in d["loend"] if r["kja"] != "keskne" and bool(r.get("ai")) == ai)
        return ", ".join(f"{e(n)} ({k})" for n, k in c.most_common(3))
    return f'''<section id="hanked"><div class="section-head"><p class="eyebrow">Tehisaru- ja andmehanked</p>
<h2>{e(pais)}</h2></div>
<div class="card"><div class="chart"><h3 class="chart-title">Tehisaru- ja andmehangete arv aastas</h3>
<p class="chart-sub">Riigihangete registri avaandmed, kõik hankijad. Tehisaruhange = hanke tekstis on tehisaru märksõna; andmehange = muu andmetega seotud hange. *{viim["aasta"]} kuni {kp(kuni)}.</p>
{aastajoon(read, kuni)}</div></div>
<details><summary>Arvud aasta kaupa ja raha</summary><div class="table-wrap"><table><thead><tr><th>Aasta</th><th class="r">Tehisaru</th><th class="r">Andmed</th><th class="r">Kokku</th><th class="r">Osa kõigist hangetest</th></tr></thead>
<tbody>{"".join(tabel)}</tbody></table></div><p class="small">{raha}</p></details>
<p class="small">Suurimad tellijad (kesksed hankijad, nt Riigi Tugiteenuste Keskus, välja jäetud): tehisaru {tellijad(True)}; andmed {tellijad(False)}.{inn_lause}</p>
<div class="grid-2"><div><h3>Viimased tehisaruhanked</h3>{nimekiri(True, "hanked-ai")}</div>
<div><h3>Viimased andmehanked</h3>{nimekiri(False, "hanked-andmed")}</div></div>
<p class="small">{tapsus} Andmed: <a href="https://riigihanked.riik.ee/rhr-web/#/opendata">riigihangete register</a>, laaditud {kp(seis["kuupaev"])}.</p></section>'''


# ---------- Leht ja saidiosade riba ----------
OSA_LINK = '<a href="toimub.html" title="uudised ja tööturg"{kohal}><b>Mis toimub</b> <span>uudised ja tööturg</span></a>'


def lisa_osa_ribale(s, kohal=False):
    s = s.replace(OSA_LINK.format(kohal=""), "").replace(OSA_LINK.format(kohal=' aria-current="page"'), "")
    i = s.find('<nav class="osad"')
    if i < 0:
        return s
    j = s.index("</nav>", i)
    if s[j - 6:j] == "</div>":
        j -= 6
    return s[:j] + OSA_LINK.format(kohal=' aria-current="page"' if kohal else "") + s[j:]


def main():
    global KAUST
    KAUST = Path(sys.argv[1])
    mall = (KAUST / "otsused.html").read_text(encoding="utf-8")
    pea = mall[:mall.index('<main id="sisu">')]
    jalus = mall[mall.index("</main>") + len("</main>"):]
    pea = pea.replace("<title>Mida otsustatakse · Tehisaru seire</title>", "<title>Mis toimub · Tehisaru seire</title>")
    pea = pea.replace(' aria-current="page"><b>Mida otsustatakse', '><b>Mida otsustatakse')
    pea = lisa_osa_ribale(pea, kohal=True)

    kaardid, (v_ee, t, vord), uuendatud = tooturg()
    uud, vaited, olek, koond = uudised()
    hd = None
    try:
        hd = json.loads((HANKED / "leht.json").read_text(encoding="utf-8"))["aastad"][-1]
    except (OSError, ValueError, KeyError, IndexError):
        pass
    ai_k = sum(1 for k in koond if k["ai_roll"] != "ei_mainita")
    plaadid = [("#tooturg", "Töötus Eestis", f"{arv(v_ee)}%", kuu(t)),
               ("#koondamised", "Koondamised uudistes", f"{ai_k} / {len(koond)}", "neist tehisaruga seotud"),
               ("#hanked", "Tehisaru- / andmehanked", f"{hd['ai_marksonaga']} / {hd['ai_andmed'] - hd['ai_marksonaga']}" if hd else "–", f"{hd['aasta']}. aastal, kokku {arv(hd['ai_andmed_osakaal'])}% hangetest" if hd else ""),
               ("#uudised", "Uudised", f"{len(uud)}", "Eesti ja maailm")]
    plaadid_html = '<ul class="kokku">' + "".join(
        f'<li><a href="{h}"><span class="small">{e(n)}</span><b>{e(v)}</b><span class="small">{e(x)}</span></a></li>' for h, n, v, x in plaadid) + "</ul>"
    h1 = f"Eesti töötus on {arv(v_ee)}%, {'kõrgem kui' if vord == 'kõrgem' else 'madalam kui' if vord == 'madalam' else 'sama mis'} ELis"
    sisu = f'''<main id="sisu"><div class="wrap"><div><p class="eyebrow">Mis toimub</p><h1>{e(h1)}</h1>
<p class="lead">Tööturu olukord ametliku statistika järgi, Eesti koondamised, tehisaru- ja andmehanked ning tehisaru uudised ühes kohas. Leht uueneb iga päev.</p></div>
{plaadid_html}
<section id="tooturg"><div class="section-head"><p class="eyebrow">Tööturg</p><h2>Töötus kuu kaupa</h2></div>
<div class="grid-2">{"".join(kaardid)}</div>
<p class="small">Allikas: <a href="https://ec.europa.eu/eurostat/databrowser/view/une_rt_m/default/table">Eurostat une_rt_m</a>, uuendatud {kp(uuendatud) if uuendatud else "–"}. Eesti kuu arvud on hinnang tööjõu-uuringu põhjal ja võivad kuust kuusse kõikuda: ära loe ühe kuu muutust suunaks. Töötuse määr ei näita, kas töö kadus tehisaru tõttu: seda ei mõõda keegi eraldi.</p></section>
{koondamiste_plokk(koond)}
{koondajate_plokk(koond)}
{hangete_plokk()}
{uudiste_plokk(uud, olek)}
{vaidete_plokk(vaited)}
</div></main>'''
    skript = ('<script>document.querySelectorAll(".nupp-koik").forEach(function(b){b.addEventListener("click",function(){'
              'document.querySelectorAll("[data-loend=\\"" + b.dataset.ava + "\\"] > li[hidden]").forEach(function(li){li.hidden=false;});b.remove();});});</script>')
    stiil = ('<style>.kuujoon svg{display:block;width:100%;height:auto}.grid-2{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,420px),1fr));gap:var(--space-4)}'
             '#sisu h3{margin:var(--space-5) 0 var(--space-2)}.nupp-koik{margin-top:var(--space-3);font:inherit;font-size:15px;'
             'padding:8px 14px;border-radius:var(--radius-pill);border:1px solid var(--control-border);background:transparent;color:var(--ink);cursor:pointer}'
             '#sisu section{margin-top:var(--space-6)}.list>li[hidden]{display:none}#hanked .kuujoon{max-width:560px}.koondajad-firmad th[scope=row]{color:var(--ink)}.koondajad-detail{margin-top:var(--space-4)}.koondajad-detail summary{cursor:pointer;font-weight:600}.kokku{list-style:none;margin:var(--space-5) 0 0;padding:0;display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,150px),1fr));gap:var(--space-3)}.kokku a{display:flex;flex-direction:column;gap:4px;padding:var(--space-3) var(--space-4);border-radius:var(--radius-m);background:var(--surface-raised);color:var(--ink);text-decoration:none}.kokku b{font-family:var(--font-display);font-size:28px;color:var(--signal)}.kokku a:hover b{text-decoration:underline}</style>')
    (KAUST / FAIL).write_text(pea.replace("</head>", stiil + "</head>", 1) + sisu + jalus.replace("</body>", skript + "</body>", 1), encoding="utf-8")

    n = 0
    for p in KAUST.glob("*.html"):
        if p.name == FAIL:
            continue
        s = p.read_text(encoding="utf-8")
        uus = lisa_osa_ribale(s)
        if uus != s:
            p.write_text(uus, encoding="utf-8")
            n += 1
    print(f"{FAIL}: töötus EE {arv(v_ee)}% ({t}), koondamisi {len(koond)}, uudiseid {len(uud)}; osade riba uuendatud {n} lehel")


if __name__ == "__main__":
    main()
