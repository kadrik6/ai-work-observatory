"""Teemalehe tahvel (Kadri 14.11.2026 valis Ettevõtete lehele näidise „B koos C maatriksiga“).

Lehe algus on üks tabel, kus iga rida on lugeja küsimus: vastus, väike pilt, märkus, tõendi liik ja allikas.
Rida viib oma plokki. Selle all on Põhjamaade maatriks (näitaja × riik, iga rida oma skaalal) ja seejärel
praegused plokid kokkupandult („Üksikasjad“). Telefonis on tabelil kolm veergu ja rida avaneb puudutusega
(sama muster nagu avalehe signaalitahvlil). Võrreldamatuid numbreid ei liideta ega panda samale teljele.
Värvid tulevad CSS-ist (stiil.css, plokk „Teemalehe tahvel“).
"""
import datetime
import re
from collections import Counter

from andmekiht import AndmeViga
from komponendid import e, kp, pr

# Tõendi liik: sõna lugejale ja CSS klass
LIIK = {"mõõdetud": "m", "arvutatud": "a", "katse": "k", "uudised": "u"}


# ---------------------------------------------------------------- tahvel

# Vastus sõnaga (Kadri 25.11.2026: oluline enne valikulist). Sõna arvutatakse numbrist kindla piiriga; piirid on siin ühes kohas.
OSA_PIIRID = [(15, None), (22.5, "Umbes iga viies"), (29.2, "Umbes veerand"), (37.5, "Umbes kolmandik"), (45, "Alla poole"),
              (55, "Umbes pooled"), (62, "Üle poole"), (71, "Umbes kaks kolmandikku"), (80, "Umbes kolmveerand"), (95, "Enamik")]


def sona_osa(p):
    """Osakaal protsentides → sõna („Umbes kolmandik“). Alla 15% → „Umbes iga N.“ (N ümardatud: kuni 12 täpselt, kuni 50 viieni, edasi ühe tüvenumbrini)."""
    try:
        p = float(p)
    except (TypeError, ValueError):
        raise AndmeViga(f"Osakaal ei ole arv: {p!r}")
    if not 0 <= p <= 100:
        raise AndmeViga(f"Osakaal peab olema 0–100, on {p}")
    if p < 15:
        if p <= 0:
            return "Mitte ükski"
        n = 100 / p
        if n > 50:
            aste = 10 ** (len(str(int(n))) - 1)
            n = round(n / aste) * aste
        elif n > 12:
            n = round(n / 5) * 5
        return f"Umbes iga {round(n)}."
    for piir, sona in OSA_PIIRID:
        if p < piir:
            return sona
    return "Peaaegu kõik"


def sona_koht(koht, n):
    """Koht järjestuses → sõna. Esikolmik eraldi, muidu kolmandikud."""
    if not 1 <= koht <= n:
        raise AndmeViga(f"Koht {koht} ei mahu vahemikku 1–{n}")
    return ("Esikolmikus" if koht <= 3 else "Esimeses kolmandikus" if koht <= n / 3 else
            "Keskmiste seas" if koht <= 2 * n / 3 else "Viimases kolmandikus")


def sona_muutus(vahe, piir, kasv, kahanemine, sama):
    """Muutus → üks kolmest sõnast; |vahe| alla piiri loetakse samaks."""
    return sama if abs(vahe) < piir else kasv if vahe > 0 else kahanemine


def vastustahvel(hid, kysimus, hoiatus, read):
    """Kadri 25.11.2026: oluline enne valikulist. Rida = küsimus, vastus sõnaga, number ja väike pilt.
    Märkus, tõendi liik ja allikas avanevad real (sama muster igal laiusel), link viib graafiku juurde.
    read: [dict(kys, ank, sona, arv, all, pilt, mrk, liik, allikas, kuup, ava)]. sona on arvutatud andmetest, mitte käsitsi kirjutatud.
    Valikuline `leht` (nt „inimesed.html“): graafik on teisel lehel ja link viib sinna, `ank` on selle lehe ankur."""
    for r in read:
        if r["liik"] not in LIIK:
            raise AndmeViga(f"Tahvli rida „{r['kys']}“: tundmatu tõendi liik {r['liik']}")
        if not r["sona"].strip():
            raise AndmeViga(f"Tahvli rida „{r['kys']}“: vastus sõnaga puudub")
    rida = "".join(
        f'<details class="vt-r"><summary><span class="vt-k">{e(r["kys"])}</span>'
        f'<span class="vt-v"><span class="vt-s"><b>{e(r["sona"])}</b><span class="vt-n">{r["arv"]}</span></span><small>{e(r["all"])}</small></span>'
        f'<span class="vt-p">{r["pilt"]}</span></summary>'
        f'<div class="vt-d"><dl><dt>Märkus</dt><dd>{r["mrk"]}</dd><dt>Tõend</dt><dd><span class="tt-liik {LIIK[r["liik"]]}">{e(r["liik"])}</span></dd>'
        f'<dt>Allikas</dt><dd>{e(r["allikas"])}, {r["kuup"]}</dd></dl>'
        f'<p class="vt-ava"><a href="{e(r.get("leht", ""))}#{r["ank"]}">{e(r["ava"])} →</a></p></div></details>' for r in read)
    return f"""
<section class="jaotis vt" id="{hid}" aria-labelledby="h-{hid}">
  <header>
    <h2 id="h-{hid}">{kysimus}</h2>
    <p class="alam">{hoiatus}</p>
  </header>
  <div class="vt-read">{rida}</div>
</section>"""


def uksikasjad(plokid):
    """plokid: [(ploki id, küsimus, mis sees on, html)]. Kokkupandud plokid; ankur sees avab ploki (sait.js avaAnkur)."""
    out = "".join(f'<details class="tt-pl" id="d-{sid}"><summary><b>{e(k)}</b><span>{e(t)}</span></summary>{h}</details>'
                  for sid, k, t, h in plokid if h.strip())
    return f'<section class="tt-det" aria-labelledby="h-uksikasjad"><h2 id="h-uksikasjad" class="tt-h2s">Üksikasjad</h2>{out}</section>'


# ---------------------------------------------------------------- Põhjamaade maatriks

def maatriks(P, riigid, nimed, arvt):
    """P: lehed.pohjamaade_profiil(A). Iga rida on oma skaalal (tumedam = selles reas parem); Eesti veerg raamitud."""
    pm = ("FI", "SE", "DK", "NO")
    pea = "".join(f'<th scope="col" class="{"ee" if g == "EE" else ("pm" if g in pm else "")}">{e(nimed[g])}</th>' for g in riigid)
    read = []
    for p in P:
        vv = [p["v"][g] for g in riigid if g in p["v"]]
        lo, hi = min(vv), max(vv)
        u = "%" if p["uhik"].startswith("%") else ""
        lahtrid = []
        for g in riigid:
            if g not in p["v"]:
                lahtrid.append('<td class="tuhi">–</td>')
                continue
            z = (p["v"][g] - lo) / ((hi - lo) or 1)
            if p["vp"]:
                z = 1 - z
            lahtrid.append(f'<td class="{"ee" if g == "EE" else ""}" style="--z:{8 + z * 42:.0f}%">{arvt(p["v"][g], p["k"])}{u}</td>')
        ok = p["hinnang"] in ("yle", "vahemik")
        read.append(f'<tr><th scope="row">{e(p["nimi"])}<small>{e(p["uhik"])} · {p["a"]}</small></th>{"".join(lahtrid)}'
                    f'<td class="tt-h {"ok" if ok else "maas"}">{"tasemel" if ok else "maas"}<small>{p["koht"]}./{p["n"]}</small></td></tr>')
    return (f'<div class="tbl tt-mx"><table><caption class="peidus">Eesti ja kuus võrdlusriiki üheksas näitajas</caption>'
            f'<thead><tr><th scope="col">Näitaja</th>{pea}<th scope="col">Hinnang</th></tr></thead><tbody>{"".join(read)}</tbody></table></div>')


# ---------------------------------------------------------------- ettevõtete väikesed joonised

def koha_joon(koht, w=200, h=50):
    """Eesti koht ELis aastate kaupa (1. koht üleval)."""
    ys = sorted(koht)
    X = lambda y: 12 + (y - ys[0]) / ((ys[-1] - ys[0]) or 1) * (w - 30)  # noqa: E731
    Yk = lambda k: 12 + (k - 1) / 26 * (h - 24)  # noqa: E731
    d = " ".join(f"{X(y):.1f},{Yk(koht[y]):.1f}" for y in ys)
    pts = "".join(f'<circle class="tv-pf" cx="{X(y):.1f}" cy="{Yk(koht[y]):.1f}" r="3"/>'
                  f'<text class="tt-t b" x="{X(y):.1f}" y="{Yk(koht[y]) - 6:.1f}" text-anchor="middle">{koht[y]}.</text>' for y in ys)
    aa = "".join(f'<text class="tt-t" x="{X(y):.1f}" y="{h - 1}" text-anchor="middle">{y}</text>' for y in (ys[0], ys[-1]))
    return (f'<svg class="tt-svg tv-joon" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-label="Koht ELis: '
            + ", ".join(f"{y} {koht[y]}." for y in ys) + f'"><polyline class="tv-lf" points="{d}"/>{pts}{aa}</svg>')


GRUPP = {"avab_koigile": "ava", "avab_ehitamise_piirab_avaldamise": "ava", "piirab_rolliga": "pii", "keelab": "kee"}
GRUPI_NIMI = {"ava": "avas kõigile", "pii": "piirab rolliga", "kee": "keelas"}


def otsuste_aeg(sundmused, nimi, w=200, h=50):
    """Ettevõtete ligipääsuotsused ajateljel, värv = rühm (avab, piirab, keelab)."""
    aastad = sorted({int(r["kuupaev"][:4]) for r in sundmused})
    t0, t1 = datetime.date(aastad[0], 1, 1), datetime.date(aastad[-1], 12, 31)
    X = lambda d: 6 + (d - t0).days / (t1 - t0).days * (w - 12)  # noqa: E731
    virn, out = {}, [f'<line class="tv-ax" x1="6" x2="{w - 6}" y1="{h - 16}" y2="{h - 16}"/>']
    for r in sorted(sundmused, key=lambda r: r["kuupaev"]):
        d = datetime.date.fromisoformat(r["kuupaev"])
        k = round(X(d) / 9)
        n = virn[k] = virn.get(k, -1) + 1
        out.append(f'<circle class="tt-o {GRUPP[r["ligipaas"]]}" cx="{X(d):.1f}" cy="{h - 22 - n * 9}" r="3.5">'
                   f'<title>{e(r["ettevote"])} {kp(r["kuupaev"])}: {e(nimi[r["ligipaas"]])}</title></circle>')
    for a in (aastad[0], aastad[-1]):
        out.append(f'<text class="tt-t" x="{X(datetime.date(a, 7, 1)):.1f}" y="{h - 3}" text-anchor="middle">{a}</text>')
    return (f'<svg class="tt-svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" '
            f'aria-label="{len(sundmused)} ettevõtte otsust ajateljel {aastad[0]}–{aastad[-1]}">{"".join(out)}</svg>')


def otsuste_legend(sundmused):
    c = Counter(GRUPP[r["ligipaas"]] for r in sundmused)
    return " · ".join(f'<span class="tt-lg {k}"></span>{c[k]} {GRUPI_NIMI[k]}' for k in ("ava", "pii", "kee") if c[k])


def katse_number(leid):
    """Katse peamine number leiu tekstist. Kui muster ei leia, kukub ehitus (number ei tohi vaikselt kaduda)."""
    for muster, silt in [(r"(\d+)% rohkem töid", "+{} % lõpetatud töid"), (r"tunnis (\d+)% rohkem", "+{} % pöördumisi tunnis"),
                         (r"tehti (\d+)% rohkem", "+{} % tööd sobivas ülesandes"), (r"ajakulu kasvas (\d+)%", "+{} % ajakulu")]:
        m = re.search(muster, leid)
        if m:
            return silt.format(m.group(1)), "ajakulu" not in silt
    raise AndmeViga(f"Katse numbrit ei leitud: {leid[:80]}")


def katse_ruudud(uuringud, r=12):
    """Üks ruut = üks katse: täidetud = tootlikkus kasvas, tühi = ei kasvanud. Numbreid ei liideta (eri ülesanded ja mõõdikud)."""
    out, n = [], 0
    for i, u in enumerate(uuringud):
        silt, hea = katse_number(u["leid"])
        n += hea
        out.append(f'<rect class="tt-r9 {"ok" if hea else "maas"}" x="{i * (r + 4)}" y="1" width="{r}" height="{r}" rx="2"><title>{e(silt)}, {e(u["uuring"])}</title></rect>')
    w = len(uuringud) * (r + 4)
    return (f'<svg class="tt-svg" viewBox="0 0 {w} {r + 2}" width="{w}" height="{r + 2}" role="img" '
            f'aria-label="{n} katses {len(uuringud)}-st tootlikkus kasvas">{"".join(out)}</svg>')


def katse_loend(uuringud):
    """Katsete numbrid lausena rea märkusesse: iga katse oma number ja viide."""
    return "; ".join(f'{e(katse_number(u["leid"])[0])} ({e(u["uuring"])})' for u in uuringud) + "."


def aasta(uuring):
    """Uuringu aasta viite tekstist („Cui jt, Management Science 2026“)."""
    m = re.findall(r"\b(?:19|20)\d\d\b", uuring["uuring"])
    if not m:
        raise AndmeViga(f"Uuringu aastat ei leitud: {uuring['uuring']}")
    return m[-1]


def ruudud(P, r=12):
    """Üheksa ruutu: täidetud = Põhjamaade tasemel, tühi = maas."""
    out = []
    for i, p in enumerate(P):
        ok = p["hinnang"] in ("yle", "vahemik")
        out.append(f'<rect class="tt-r9 {"ok" if ok else "maas"}" x="{i * (r + 4)}" y="1" width="{r}" height="{r}" rx="2"><title>{e(p["nimi"])}</title></rect>')
    n = sum(p["hinnang"] in ("yle", "vahemik") for p in P)
    return (f'<svg class="tt-svg" viewBox="0 0 {len(P) * (r + 4)} {r + 2}" width="{len(P) * (r + 4)}" height="{r + 2}" role="img" '
            f'aria-label="{n} näitajat {len(P)}-st Põhjamaade tasemel">{"".join(out)}</svg>')



# ---------------------------------------------------------------- inimeste joonised (Kadri 14.11.2026 valis „A ja B koos“)

def p1(v):
    """Täisarv ilma komakohata (65%), muidu üks koht (36,9%): ümardus ei tohi muuta võrdlust märkusega."""
    return pr(v, 0) if round(v, 1) == round(v) else pr(v)


def mini_hantlid(paarid, riik, lo=30, hi=80, w=200, h=50):
    """Kasv aastaga riikide kaupa: [(vana, uus)] vaatlused; joon vanast uueni, Eesti sinine."""
    X = lambda v: 4 + (v - lo) / (hi - lo) * (w - 40)  # noqa: E731
    out = []
    for i, (v0, v1) in enumerate(paarid):
        yy = 8 + i * (h - 12) / max(1, len(paarid) - 1)
        k = "f" if v1["geo"] == "EE" else "r"
        out.append(f'<line class="tv-l{k}" x1="{X(v0["vaartus"]):.1f}" x2="{X(v1["vaartus"]):.1f}" y1="{yy:.1f}" y2="{yy:.1f}" stroke-width="2"/>'
                   f'<circle class="tv-p{k}" cx="{X(v1["vaartus"]):.1f}" cy="{yy:.1f}" r="3"/>'
                   f'<text class="tt-t{" b" if k == "f" else ""}" x="{X(v1["vaartus"]) + 6:.1f}" y="{yy + 4:.1f}">{v1["geo"]}</text>')
    silt = ", ".join(f'{riik(v1["geo"])} {pr(v0["vaartus"], 0)} → {pr(v1["vaartus"], 0)}' for v0, v1 in paarid)
    return f'<svg class="tt-svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-label="{e(silt)}">{"".join(out)}</svg>'


VAHVLI_RUHM = {"tool": "kasutas tööl", "kas": "kasutas, aga mitte tööl", "oska": "ei kasutanud, sest ei osanud", "muu": "ei kasutanud muul põhjusel"}


def vahvel(osad, silt, n=10, r=14, g=3):
    """osad: [(rühm, osakaal %)] järjekorras; ruut = 1%; ülejäänu on rühm „muu“.
    Kasuta ainult rühmade puhul, mis on samast küsitlusest ja ei kattu (osad kokku ≤ 100)."""
    if sum(v for _, v in osad) > 100.5:
        raise AndmeViga(f"Vahvli osad on kokku üle 100%: {osad}")
    piirid, s = [], 0
    for k, v in osad:
        s += v
        piirid.append((k, s))
    out = []
    for j in range(100):
        k = next((k for k, p in piirid if j + 0.5 <= p), "muu")
        out.append(f'<rect class="tt-w {k}" x="{(j % n) * (r + g)}" y="{(j // n) * (r + g)}" width="{r}" height="{r}" rx="2"/>')
    w = n * (r + g) - g
    return f'<svg class="tt-svg" viewBox="0 0 {w} {w}" width="{w}" height="{w}" role="img" aria-label="{e(silt)}">{"".join(out)}</svg>'


def vahvli_legend(arvud):
    """arvud: {rühm: osakaal %}; ümardatud täisarvuni."""
    return ('<ul class="tt-wleg">' + "".join(f'<li><i class="tt-w {k}"></i><b>{pr(arvud[k], 0)}</b> {e(VAHVLI_RUHM[k])}</li>'
                                              for k in VAHVLI_RUHM if k in arvud) + "</ul>")


def hajuvus(pts, eu_x, eu_y, x_silt, y_silt, nimi, sildid, x0=30, x1=90, y0=10, y1=60, w=640, h=380):
    """ELi riigid kahel teljel (kaks eri mõõdikut, neid ei liideta). pts: [(geo, x, y)].
    Tagastab (svg, Eesti kaugus riikide üldisest seosest punktides). Seos (vähimruutude joon) ei näita põhjust."""
    if not all(x0 <= x <= x1 and y0 <= y <= y1 for _, x, y in pts):
        raise AndmeViga("Hajuvusgraafiku punkt on teljest väljas")
    n = len(pts)
    mx, my = sum(p[1] for p in pts) / n, sum(p[2] for p in pts) / n
    b = sum((p[1] - mx) * (p[2] - my) for p in pts) / sum((p[1] - mx) ** 2 for p in pts)
    c = my - b * mx
    X = lambda v: 50 + (v - x0) / (x1 - x0) * (w - 80)  # noqa: E731
    Y = lambda v: h - 36 - (v - y0) / (y1 - y0) * (h - 60)  # noqa: E731
    o = []
    for v in range(x0, x1 + 1, 10):
        o.append(f'<line class="tv-ax" x1="{X(v):.1f}" x2="{X(v):.1f}" y1="{Y(y0):.1f}" y2="{Y(y1):.1f}" opacity=".5"/>'
                 f'<text class="tt-t" x="{X(v):.1f}" y="{h - 18}" text-anchor="middle">{v}%</text>')
    for v in range(y0, y1 + 1, 10):
        o.append(f'<line class="tv-ax" x1="{X(x0):.1f}" x2="{X(x1):.1f}" y1="{Y(v):.1f}" y2="{Y(v):.1f}" opacity=".5"/>'
                 f'<text class="tt-t" x="44" y="{Y(v) + 4:.1f}" text-anchor="end">{v}%</text>')
    o.append(f'<line class="tt-elk" x1="{X(eu_x):.1f}" x2="{X(eu_x):.1f}" y1="{Y(y0):.1f}" y2="{Y(y1):.1f}"/>'
             f'<line class="tt-elk" x1="{X(x0):.1f}" x2="{X(x1):.1f}" y1="{Y(eu_y):.1f}" y2="{Y(eu_y):.1f}"/>'
             f'<text class="tt-t" x="{X(eu_x) + 4:.1f}" y="{Y(y1) + 10:.1f}">ELi keskmine</text>')
    xa, xb = min(p[1] for p in pts), max(p[1] for p in pts)
    o.append(f'<line class="tv-lr" x1="{X(xa):.1f}" x2="{X(xb):.1f}" y1="{Y(c + b * xa):.1f}" y2="{Y(c + b * xb):.1f}" stroke-width="1.5"/>'
             f'<text class="tt-t" x="{X(xa) + 4:.1f}" y="{Y(c + b * xa) + 18:.1f}">riikide üldine seos</text>')
    for g, xv, yv in sorted(pts, key=lambda p: p[0] == "EE"):
        ee = g == "EE"
        o.append(f'<circle class="{"tv-ee" if ee else "tv-c"}" cx="{X(xv):.1f}" cy="{Y(yv):.1f}" r="{6 if ee else 4.5}">'
                 f'<title>{e(nimi(g))}: {e(y_silt)} {pr(yv)}%, {e(x_silt)} {pr(xv)}%</title></circle>')
        if g in sildid:
            o.append(f'<text class="tt-t{" b f" if ee else ""}" x="{X(xv) + 8:.1f}" y="{Y(yv) + 4:.1f}">{e(nimi(g)) if ee else g}</text>')
    o.append(f'<text class="tt-t" x="{X(x1):.1f}" y="{h - 2}" text-anchor="end">{e(x_silt)} →</text>'
             f'<text class="tt-t" x="6" y="12">↑ {e(y_silt)}</text>')
    ee = next(p for p in pts if p[0] == "EE")
    kaugus = ee[2] - (c + b * ee[1])
    suund = "kõrgemal" if kaugus >= 0 else "madalamal"
    silt = f"ELi {n} riiki: {y_silt} ja {x_silt}; Eesti {pr(ee[2])}% ja {pr(ee[1])}%, riikide üldisest seosest {pr(abs(kaugus), 0)} punkti {suund}"
    return f'<svg class="tt-svg tt-sc" viewBox="0 0 {w} {h}" width="100%" role="img" aria-label="{e(silt)}">{"".join(o)}</svg>', kaugus
