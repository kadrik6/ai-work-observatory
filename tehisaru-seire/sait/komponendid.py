"""Lehe komponendid: skaala (tulbad ja hantlid), tabel, allikarida, faktid, „Mida see ei näita“.

Graafikud tehakse ehitamise ajal staatiliseks HTML-iks (div-tulbad, mitte JS). Nii jääb tekst päris suuruseks ka
390 px laiusel, töötab ilma JavaScriptita ja on testitav. Skaala keeldub panemast eri võrreldavusklassi numbreid
samale teljele: jaga_klassid() paneb võrdlusaluse skaalale ja teised loendisse skaala alla.
"""
import html
import json
import re
from pathlib import Path

from andmekiht import EL, JUUR, AndmeViga

RIIGID = {
    "EE": "Eesti", "FI": "Soome", "SE": "Rootsi", "DK": "Taani", "NO": "Norra", "DE": "Saksamaa", "NL": "Holland",
    EL: "EL keskmine", "UK": "Ühendkuningriik", "US": "USA", "CA": "Kanada",
    "AT": "Austria", "BE": "Belgia", "BG": "Bulgaaria", "CY": "Küpros", "CZ": "Tšehhi", "EL": "Kreeka",
    "ES": "Hispaania", "FR": "Prantsusmaa", "HR": "Horvaatia", "HU": "Ungari", "IE": "Iirimaa", "IT": "Itaalia",
    "LT": "Leedu", "LU": "Luksemburg", "LV": "Läti", "MT": "Malta", "PL": "Poola", "PT": "Portugal",
    "RO": "Rumeenia", "SI": "Sloveenia", "SK": "Slovakkia",
}
MARGENDID = {"b": "aegrea katkestus", "p": "esialgne", "e": "hinnang", "d": "määratlus erineb", "ep": "hinnang, esialgne"}
KUUD = ["jaanuar", "veebruar", "märts", "aprill", "mai", "juuni", "juuli", "august", "september", "oktoober",
        "november", "detsember"]


class VorreldavusViga(AndmeViga):
    """Eri võrreldavusklassi numbrid ühel teljel."""


def e(t):
    return html.escape(str(t), quote=True)


def pr(x, k=1):
    """Eesti kirjaviis, ümardus pooled üles (19,95 → 20,0), mitte kahendmurru järgi."""
    from decimal import ROUND_HALF_UP, Decimal
    d = Decimal(str(x)).quantize(Decimal(1).scaleb(-k), rounding=ROUND_HALF_UP)
    return f"{d:.{k}f}".replace(".", ",").replace("-", "−")


def kp(iso):
    """2026-09-16 → 16.09.2026; 2026-06 → juuni 2026"""
    osad = str(iso).split("-")
    if len(osad) == 3:
        return f"{int(osad[2])}.{osad[1]}.{osad[0]}"
    if len(osad) == 2:
        return f"{KUUD[int(osad[1]) - 1]} {osad[0]}"
    return str(iso)


def riik(g):
    return RIIGID.get(g, g)


def margend(m):
    return f' <small>{e(MARGENDID.get(m, m))}</small>' if m else ""


def uks_klass(vaatlused):
    klassid = {v["klass"] for v in vaatlused}
    if len(klassid) > 1:
        raise VorreldavusViga(f"Ühel teljel on eri võrreldavusklassid: {sorted(klassid)} "
                              f"({sorted({(v['naitaja'], v['geo'], v['aasta']) for v in vaatlused})})")


def jaga_klassid(vaatlused, klass="alus"):
    """Skaalale ainult üks klass, teised loendina skaala alla märkega „ei ole otse võrreldav“."""
    return [v for v in vaatlused if v["klass"] == klass], [v for v in vaatlused if v["klass"] != klass]


def _telg(alg, lopp, samm, uhik, k=0):
    tick, x = [], alg
    while x <= lopp + 1e-9:
        tick.append(f'<span style="left:{(x - alg) / (lopp - alg) * 100:.2f}%">{pr(x, k)}</span>')
        x += samm
    return f'<div class="telg" aria-hidden="true"><span></span><span class="rada">{"".join(tick)}</span><span>{e(uhik)}</span></div>'


def ribad(vaatlused, lopp, fookus="EE", viide=None, viite_nimi="", samm=10, uhik="%", viite_liik=""):
    """Sorditud horisontaalsed tulbad nullist. vaatlused peavad olema ühes võrreldavusklassis."""
    uks_klass(vaatlused)
    jarjest = sorted(vaatlused, key=lambda v: -v["vaartus"])
    out = ['<div class="ribad" aria-hidden="true">']
    for v in jarjest:
        liik = "fookus" if v["geo"] == fookus else ""
        joon = f'<i class="joon {viite_liik}" style="left:{viide / lopp * 100:.2f}%"></i>' if viide is not None else ""
        pealkiri = f'{riik(v["geo"])} {v["aasta"]}: {pr(v["vaartus"])}{uhik} ({v["allikas"]})'
        out.append(f'<div class="rida {liik}" title="{e(pealkiri)}"><span class="n">{e(riik(v["geo"]))}</span><span class="rada">'
                   f'<span class="tulp" style="width:{v["vaartus"] / lopp * 100:.2f}%"></span>{joon}</span>'
                   f'<span class="v">{pr(v["vaartus"])}</span></div>')
    out.append(_telg(0, lopp, samm, uhik))
    out.append("</div>")
    if viide is not None:
        out.append(f'<p class="margis"><i class="{viite_liik}"></i>{e(viite_nimi)}</p>')
    return "".join(out)


def hantlid(paarid, alg, lopp, samm, uhik, k=1, fookus="EE", ref=EL, viide=None, viite_nimi="", lisa=None):
    """Kaks aastat ühel teljel. paarid: [(vana, uus)] vaatlusi; kõik ühes klassis. lisa: {geo: vaatlus} kriipsring."""
    koik = [v for p in paarid for v in p] + list((lisa or {}).values())
    uks_klass(koik)
    pos = lambda x: (x - alg) / (lopp - alg) * 100  # noqa: E731
    out = ['<div class="ribad hantlid" aria-hidden="true">']
    for v0, v1 in sorted(paarid, key=lambda p: -p[1]["vaartus"]):
        g = v1["geo"]
        liik = "fookus" if g == fookus else ("ref" if g == ref else "")
        a, b = sorted((pos(v0["vaartus"]), pos(v1["vaartus"])))
        joon = f'<i class="joon siht" style="left:{pos(viide):.2f}%"></i>' if viide is not None else ""
        lv = (lisa or {}).get(g)
        lisa_html = f'<span class="tapp lisa" style="left:{pos(lv["vaartus"]):.2f}%"></span>' if lv else ""
        pealkiri = f'{riik(g)}: {v0["aasta"]} {pr(v0["vaartus"], k)} → {v1["aasta"]} {pr(v1["vaartus"], k)} {uhik}'
        out.append(f'<div class="rida {liik}" title="{e(pealkiri)}"><span class="n">{e(riik(g))}</span><span class="rada">{joon}'
                   f'<span class="hant" style="left:{a:.2f}%;width:{b - a:.2f}%"></span>'
                   f'<span class="tapp vana" style="left:{pos(v0["vaartus"]):.2f}%"></span>'
                   f'<span class="tapp uus" style="left:{pos(v1["vaartus"]):.2f}%"></span>{lisa_html}</span>'
                   f'<span class="v">{pr(v0["vaartus"], k)} → {pr(v1["vaartus"], k)}</span></div>')
    out.append(_telg(alg, lopp, samm, uhik, 0 if samm >= 1 else 1))
    out.append("</div>")
    if viide is not None:
        out.append(f'<p class="margis"><i class="siht"></i>{e(viite_nimi)}</p>')
    return "".join(out)


def leiu_ribad(read, lopp, fookus_silt, samm=10, uhik="%"):
    """Uuringu numbrid (mitte statistika vaatlused). read: [(silt, väärtus või None, olulisus)]."""
    out = []
    for silt, v, ol in read:
        liik = "fookus" if silt == fookus_silt else ""
        vt = "ei olnud oluline" if v is None else "+" + pr(v) + ("*" if ol == "nõrk" else "")
        out.append(f'<div class="rida {liik}"><span class="n">{e(silt)}</span><span class="rada">'
                   f'<span class="tulp" style="width:{(v or 0) / lopp * 100:.2f}%"></span></span>'
                   f'<span class="v">{e(vt)}</span></div>')
    return "".join(out)


def telg(alg, lopp, samm, uhik):
    return _telg(alg, lopp, samm, uhik)


def tabel(pais, read, fookus_rida=None, piir=False, pealdis="", numbrid=None):
    """numbrid: veergude indeksid, mis joondatakse paremale (vaikimisi kõik peale esimese)."""
    numbrid = set(range(1, len(pais))) if numbrid is None else set(numbrid)
    th = "".join(f'<th scope="col"{" class=v" if i in numbrid else ""}>{e(p)}</th>' for i, p in enumerate(pais))
    tr = []
    for i, r in enumerate(read):
        kl = ' class="fookus"' if fookus_rida is not None and i == fookus_rida else ""
        tr.append(f"<tr{kl}>" + "".join(f'<td{" class=v" if j in numbrid else ""}>{c}</td>' for j, c in enumerate(r)) + "</tr>")
    cap = f'<caption class="peidus">{e(pealdis)}</caption>' if pealdis else ""
    return (f'<div class="tbl"><table{" data-piir" if piir else ""}>{cap}<thead><tr>{th}</tr></thead>'
            f'<tbody>{"".join(tr)}</tbody></table></div>')


def allikarida(osad):
    """osad: [(tekst, url, lisatekst)]"""
    jupid = []
    for tekst, url, lisa in osad:
        if not url:
            raise AndmeViga(f"Allikal „{tekst}“ puudub link")
        jupid.append(f'<a href="{e(url)}">{e(tekst)}</a>' + (f" ({e(lisa)})" if lisa else ""))
    return '<p class="allikas">Allikas: ' + "; ".join(jupid) + ".</p>"


def faktid(read):
    """read: [(märgis, klass, html)]; klass ∈ {"", "risk", "s"}."""
    return '<ul class="faktid">' + "".join(
        f'<li><span class="mark-l {k}">{e(m)}</span><span>{t}</span></li>' for m, k, t in read) + "</ul>"


def vastavus(hinnang, tekst):
    """„Kas andmed vastavad küsimusele?“ jah / osaliselt / ei, joon ja sõna."""
    return (f'<p class="vastab {e(hinnang)}"><span>Kas andmed vastavad küsimusele?</span> '
            f'<b>{e(hinnang.capitalize())}.</b> {tekst}</p>')


def ei_naita(piirangud, lisa=""):
    return f'<ul>{"".join(f"<li>{e(p)}</li>" for p in piirangud)}</ul>{lisa}'


# ---------------------------------------------------------------- ELi kaart

KUJU = JUUR / "raportid" / "euroopa.json"  # Natural Earth (avalik omand), tehtud raportid/tee_euroopa_kaart.py
_kuju = None


def _dp(pts, tol):
    """Douglas–Peucker: jätab alles punktid, mis muudavad kuju rohkem kui tol ühikut."""
    if len(pts) < 3:
        return pts
    (x0, y0), (x1, y1) = pts[0], pts[-1]
    dx, dy = x1 - x0, y1 - y0
    pikk = (dx * dx + dy * dy) ** 0.5 or 1e-9
    kaugus = [abs(dy * x - dx * y + x1 * y0 - y1 * x0) / pikk for x, y in pts[1:-1]]
    i = max(range(len(kaugus)), key=kaugus.__getitem__)
    if kaugus[i] <= tol:
        return [pts[0], pts[-1]]
    return _dp(pts[:i + 2], tol)[:-1] + _dp(pts[i + 1:], tol)


def _ala(pts):
    return abs(sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]))) / 2


def lihtsusta(tee, tol=1.6, min_ala=6.0):
    """Lihtsam piir (Kadri kommentaar 4.11.2026: kaart minimalistlikum). Väikesed saared kaovad, aga iga riigi
    suurim osa jääb alles, nii et ka Malta ja Luksemburg on kaardil. Koordinaadid täisarvudeni."""
    osad = []
    for alam in re.findall(r"M[^M]*", tee):
        n = [float(x) for x in re.findall(r"-?\d+(?:\.\d+)?", alam)]
        pts = list(zip(n[0::2], n[1::2]))
        if len(pts) >= 3:
            osad.append(pts)
    if not osad:
        return ""
    suurim = max(osad, key=_ala)
    out = []
    for pts in osad:
        if pts is not suurim and _ala(pts) < min_ala:
            continue
        # rõngas kaheks pooleks, et Douglas–Peucker ei ahendaks seda üheks jooneks
        k = len(pts) // 2
        lihtne = _dp(pts[:k + 1], tol)[:-1] + _dp(pts[k:] + pts[:1], tol)[:-1]
        if len(lihtne) < 3:
            lihtne = pts if len(pts) <= 8 else pts[::max(1, len(pts) // 6)]
        ymar = []
        for x, y in lihtne:
            p = (round(x), round(y)) if pts is not suurim or _ala(pts) > 40 else (round(x, 1), round(y, 1))
            if not ymar or ymar[-1] != p:
                ymar.append(p)
        if len(ymar) >= 3:
            out.append("M" + "L".join(f"{x:g},{y:g}" for x, y in ymar) + "Z")
    return "".join(out)


def lae_kuju(fail=KUJU, tol=1.6, tol_taust=2.5):
    global _kuju
    if _kuju is None:
        d = json.loads(Path(fail).read_text(encoding="utf-8"))
        _kuju = {"viewBox": d["viewBox"],
                 "el": {g: lihtsusta(t, tol) for g, t in d["el"].items()},
                 "taust": {g: lihtsusta(t, tol_taust, 20.0) for g, t in d["taust"].items()}}
    return _kuju


def _kast(tee):
    n = [float(x) for x in re.findall(r"-?\d+(?:\.\d+)?", tee)]
    xs, ys = n[0::2], n[1::2]
    return min(xs), min(ys), max(xs), max(ys)


def kaart(vaatlused, piirid, fookus="EE", viide=None, viite_nimi="", uhik="%", kuju=None):
    """ELi riikide kaart, värv näitab suurust (üks toon, hele → tume). Kõik vaatlused ühes klassis.

    piirid: klasside alumised piirid, nt (0, 10, 20, 30, 40); viimane klass on „ja üle“.
    Eesti silt ja legend on HTML-is, et tekst jääks päris suuruseks ka telefonis. Riigi nimi ja number on
    hõljudes (title). Taustariikidel nime ei ole: need ei ole ELi skaalal.
    """
    uks_klass(vaatlused)
    kuju = kuju or lae_kuju()
    vv = {v["geo"]: v for v in vaatlused}
    puudu = sorted(set(vv) - set(kuju["el"]))
    if puudu:
        raise AndmeViga(f"Kaardil pole kuju: {puudu}")
    if min(v["vaartus"] for v in vaatlused) < piirid[0]:
        raise AndmeViga("Kaardi klassid ei kata kõiki väärtusi")
    klass = lambda x: max(i for i, p in enumerate(piirid) if x >= p)  # noqa: E731
    _, _, W, H = (float(x) for x in kuju["viewBox"].split())
    osad = [f'<path class="bg" d="{t}"/>' for _, t in sorted(kuju["taust"].items())]
    viimane = ""
    for g, tee in sorted(kuju["el"].items()):
        v = vv.get(g)
        if v is None:
            osad.append(f'<path class="na" d="{tee}" data-n="{e(riik(g))}" data-v="andmeid pole" data-a=""/>')
            continue
        # Hõljuksilt (sait.js): riik ja number suurelt, aasta ja allikas väikselt. Ilma JS-ita on number tabelis.
        tk = (f'<path class="k{klass(v["vaartus"])}{" fookus" if g == fookus else ""}" d="{tee}" data-n="{e(riik(g))}" '
              f'data-v="{pr(v["vaartus"])}{e(uhik)}" data-a="{v["aasta"]} · {e(v["allikas"])}"/>')
        if g == fookus:
            viimane = tk  # Eesti viimasena, et piirjoon jääks peale
        else:
            osad.append(tk)
    osad.append(viimane)

    silt = ""
    if fookus in vv:
        x0, y0, x1, y1 = _kast(kuju["el"][fookus])
        silt = (f'<span class="kaart-silt" style="left:{x1 / W * 100:.2f}%;top:{(y0 + y1) / 2 / H * 100:.2f}%">'
                f'<b>{e(riik(fookus))} {pr(vv[fookus]["vaartus"])}{uhik}</b></span>')

    # Legend: astmeline riba 0 … ülemine piir, peal ELi keskmine ja Eesti
    lopp = piirid[-1] + (piirid[-1] - piirid[-2])
    pos = lambda x: min(x, lopp) / lopp * 100  # noqa: E731
    lahtrid = "".join(f'<i class="k{i}" style="left:{pos(p):.2f}%;width:{pos(piirid[i + 1] if i + 1 < len(piirid) else lopp) - pos(p):.2f}%"></i>'
                      for i, p in enumerate(piirid))
    margid = "".join(f'<span style="left:{pos(p):.2f}%">{pr(p, 0)}</span>' for p in piirid)
    margid += f'<span class="lopp" style="left:100%">{e(uhik)}</span>'
    noolid = ""
    ee = vv[fookus]["vaartus"] if fookus in vv else None
    if viide is not None:
        pool = "v" if ee is None or ee >= viide else "p"  # sildid lähevad eri suunda, et ei kattuks
        noolid += f'<em class="viit {pool}" style="left:{pos(viide):.2f}%"><span>{e(viite_nimi)}</span></em>'
    if ee is not None:
        pool = "p" if viide is None or ee >= viide else "v"
        noolid += f'<em class="viit fookus {pool}" style="left:{pos(ee):.2f}%"><span>{e(riik(fookus))}</span></em>'
    legend = (f'<div class="kaart-legend" aria-hidden="true"><div class="riba">{lahtrid}{noolid}</div>'
              f'<div class="margid">{margid}</div></div>')
    return (f'<div class="kaart-ala"><div class="kaart"><div class="kaart-vihje" hidden></div><svg viewBox="{kuju["viewBox"]}" aria-hidden="true" focusable="false">'
            f'{"".join(osad)}</svg>{silt}</div>{legend}</div>')
