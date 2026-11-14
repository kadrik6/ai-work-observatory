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

def tahvel(hid, kysimus, vastus, selgitus, read, usaldus=""):
    """read: [dict(kys, ank, arv, all, pilt, mrk, liik, allikas, kuup)]. kys/all/allikas on tekst, arv/pilt/mrk/kuup HTML."""
    for r in read:
        if r["liik"] not in LIIK:
            raise AndmeViga(f"Tahvli rida „{r['kys']}“: tundmatu tõendi liik {r['liik']}")
    liik = lambda r: f'<span class="tt-liik {LIIK[r["liik"]]}">{e(r["liik"])}</span>'  # noqa: E731
    laud = "".join(
        f'<tr><th scope="row"><a href="#{r["ank"]}">{e(r["kys"])}</a></th>'
        f'<td class="tv-num"><span class="tv-arv">{r["arv"]}</span><small>{e(r["all"])}</small></td>'
        f'<td class="tt-pilt">{r["pilt"]}</td><td class="tt-mrk">{r["mrk"]}</td><td>{liik(r)}</td>'
        f'<td class="tt-src">{e(r["allikas"])}<small>{r["kuup"]}</small></td></tr>' for r in read)
    tel = "".join(
        f'<details class="tv-r"><summary><span class="tv-t">{e(r["kys"])}</span>'
        f'<span class="tv-n"><b>{r["arv"]}</b><small>{e(r["all"])}</small></span><span class="tt-tvis">{r["pilt"]}</span></summary>'
        f'<dl><dt>Märkus</dt><dd>{r["mrk"]}</dd><dt>Tõend</dt><dd>{liik(r)}</dd><dt>Allikas</dt><dd>{e(r["allikas"])}, {r["kuup"]}</dd></dl>'
        f'<p class="tv-ava"><a href="#{r["ank"]}">Ava plokk →</a></p></details>' for r in read)
    return f"""
<section class="jaotis tv tt" id="{hid}" aria-labelledby="h-{hid}">
  <header>
    <h2 id="h-{hid}"><span class="kys">{kysimus}</span> <b>{vastus}</b></h2>
    <p class="alam">{selgitus}</p>
  </header>
  <div class="tbl tv-laud tt-laud"><table><caption class="peidus">{kysimus}</caption>
    <thead><tr><th scope="col">Küsimus</th><th scope="col">Vastus</th><th scope="col">Pilt</th><th scope="col">Märkus</th><th scope="col">Tõend</th><th scope="col">Allikas</th></tr></thead>
    <tbody>{laud}</tbody></table></div>
  <div class="tv-tel tt-tel"><div class="tv-pea" aria-hidden="true"><span>Küsimus</span><span>Vastus</span><span>Pilt</span></div>{tel}</div>
  {usaldus}
</section>"""


def usaldusriba(n_vaiteid, n_muud, reeglid, n_allikaid, uusim):
    """Väited, reeglid ja allikad ühel real tahvli all; lingid viivad lehe lõppu. reeglid: [(nimi, kehtib)]."""
    v = "ükski ei ütle muud kui allikas" if not n_muud else f"{n_muud} ütleb muud kui allikas"
    k = sum(1 for _, keh in reeglid if keh)
    r = (f'<a href="#t-reeglid">Reeglid: <b>{k} kehtib</b> ({e(", ".join(n for n, _ in reeglid))})</a>' if reeglid else "")
    return (f'<p class="tt-us"><a href="#t-vaited">Väited: <b>{n_vaiteid} kontrollitud</b>, {v}</a>{r}'
            f'<a href="#t-allikad">Allikad: <b>{n_allikaid}</b>, uusim {kp(uusim)}</a></p>')


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


def katse_kiibid(uuringud):
    """Iga katse oma kiibina; numbreid ei liideta (eri ülesanded ja mõõdikud)."""
    out = []
    for r in uuringud:
        n, hea = katse_number(r["leid"])
        out.append(f'<li class="{"hea" if hea else "halb"}"><b>{e(n)}</b><small>{e(r["uuring"])}</small></li>')
    return f'<ul class="tt-kiibid">{"".join(out)}</ul>'


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

