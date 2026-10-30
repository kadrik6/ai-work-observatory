"""Väikesed korduvkasutatavad graafikud (HTML ja SVG) raporti lehtedele.

Iga funktsioon saab valmis numbrid ja vormistatud tekstid ning tagastab HTML-i.
Värvid tulevad stiil.css-i märkidest: Eesti = signaal (lilla), ELi keskmine = tume hall,
teised riigid = hall, vastupidine suund = --counter (oranž).
Kohtspikker: data-tip="väärtus|silt" (analüütiku lehel JS) või title (mujal).
"""

import html

e = html.escape


def _tip(vaartus, sild, title=False):
    if title:
        return f' title="{e(sild)}: {e(vaartus)}"'
    return f' data-tip="{e(vaartus)}|{e(sild)}"'


def asukoht(punktid, el=None, vahemik=None, title=False, sildid=True):
    """Üks rida: riigid oma kohal skaalal.

    punktid: [(nimi, väärtus, tekst, on_fookus)], el: (väärtus, tekst) või None,
    vahemik: (min, max) hall vöö (näiteks Põhjamaad) või None.
    """
    vv = [v for _, v, _, _ in punktid] + ([el[0]] if el else [])
    lo, hi = min(vv), max(vv)
    pad = (hi - lo) * 0.06 or 1

    def X(x):
        return (x - lo + pad) / (hi - lo + 2 * pad) * 100

    osad = []
    if vahemik:
        osad.append(f'<span class="band" style="left:{X(vahemik[0]):.1f}%;width:{X(vahemik[1]) - X(vahemik[0]):.1f}%"></span>')
    if el:
        osad.append(f'<span class="eu" style="left:{X(el[0]):.1f}%"{_tip(el[1], "ELi keskmine", title)}></span>')
    for nimi, v, tekst, fookus in sorted(punktid, key=lambda p: p[3]):
        osad.append(f'<span class="pt{" ee" if fookus else ""}" style="left:{X(v):.1f}%"{_tip(tekst, nimi, title)}></span>')
    rida = f'<span class="prof-line">{"".join(osad)}</span>'
    if not sildid:
        return rida
    ee = next((p for p in punktid if p[3]), None)
    vaike = min(punktid, key=lambda p: p[1])
    suur = max(punktid, key=lambda p: p[1])
    return (f'<div class="loc">{rida}<div class="loc-scale" aria-hidden="true">'
            f'<span>{e(vaike[0])} {e(vaike[2])}</span><span>{e(suur[0])} {e(suur[2])}</span></div></div>')


def tulbad(read, ref=None, title=False):
    """Horisontaalsed tulbad. read: [(silt, väärtus, tekst, klass)], klass: "ee", "eu", "risk" või "".
    ref: (väärtus, silt) püstjoon kõigi tulpade kohal või None."""
    tipp = max([v for _, v, _, _ in read] + ([ref[0]] if ref else [])) or 1
    rid = []
    for silt, v, tekst, klass in read:
        rid.append(f'<li class="{klass}"><span class="lab">{e(silt)}</span>'
                   f'<span class="track"{_tip(tekst, silt, title)}><span class="bar" style="width:{v / tipp * 100:.1f}%"></span>'
                   + (f'<span class="ref" style="left:{ref[0] / tipp * 100:.1f}%"></span>' if ref else "")
                   + f'</span><span class="val">{e(tekst)}</span></li>')
    leg = (f'<p class="mbars-ref"><i></i>{e(ref[1])}</p>' if ref else "")
    return f'<ul class="mbars" role="list">{"".join(rid)}</ul>{leg}'


def hantlid(read, a_silt, b_silt, title=False):
    """Muutus kahe punkti vahel. read: [(silt, a, b, muutuse_tekst, klass, a_tekst, b_tekst)]."""
    vv = [x for r in read for x in (r[1], r[2])]
    lo, hi = min(vv), max(vv)
    pad = (hi - lo) * 0.08 or 1

    def X(x):
        return (x - lo + pad) / (hi - lo + 2 * pad) * 100

    rid = []
    for silt, a, b, muutus, klass, at, bt in read:
        l, r = sorted((X(a), X(b)))
        kl = {"ee": "is-focus", "eu": "is-ref"}.get(klass, "")
        rid.append(f'<li class="{kl}"><span class="lab">{e(silt)}</span><span class="db-track">'
                   f'<span class="db-line" style="left:{l:.1f}%;width:{r - l:.1f}%"></span>'
                   f'<span class="db-a" style="left:{X(a):.1f}%"{_tip(at, f"{silt} {a_silt}", title)}></span>'
                   f'<span class="db-b" style="left:{X(b):.1f}%"{_tip(bt, f"{silt} {b_silt}", title)}></span></span>'
                   f'<span class="val">{e(muutus)}</span></li>')
    leg = (f'<div class="an-legend" aria-hidden="true"><span><i class="k-db-a"></i>{e(a_silt)}</span>'
           f'<span><i class="k-db-b"></i>{e(b_silt)}</span></div>')
    return f'{leg}<div class="dumb"><ul role="list">{"".join(rid)}</ul></div>'


def lahknev(read, title=False):
    """Tulbad nullist kahes suunas. read: [(silt, väärtus, tekst)]; negatiivne = maas (oranž)."""
    m = max(abs(v) for _, v, _ in read) or 1
    rid = []
    for silt, v, tekst in read:
        w = abs(v) / m * 50
        x0 = 50 - w if v < 0 else 50
        rid.append(f'<li><span class="lab">{e(silt)}</span><span class="idx-track"{_tip(tekst, silt, title)}>'
                   f'<span class="idx-bar {"down" if v < 0 else "up"}" style="left:{x0:.1f}%;width:{w:.1f}%"></span></span>'
                   f'<span class="val">{e(tekst)}</span></li>')
    return f'<ul class="idx idx-mini" role="list">{"".join(rid)}</ul>'


def numbrid(paarid):
    """Suured numbrid kõrvuti: [(silt, enne, pärast, selgitus)]."""
    osad = "".join(
        f'<div><dt>{e(s)}</dt><dd><span class="from">{e(a)}</span><span aria-hidden="true"> → </span>'
        f'<b>{e(b)}</b></dd><dd class="small">{e(sel)}</dd></div>' for s, a, b, sel in paarid)
    return f'<dl class="an-nums">{osad}</dl>'


def jooned(seeriad, fmt, vahemik=None, sihid=(), markused=(), ymax=None, kirjeldus=""):
    """Väike joongraafik. seeriad: [(nimi, {aasta: v}, klass)], klass "focus" | "ref" | "".
    vahemik: {aasta: (lo, hi)} hall ala. sihid: [(väärtus, silt)] katkendjoon.
    markused: [(aasta, v1, v2, tekst)] püstine klamber kahe väärtuse vahel."""
    W, H = 380, 200
    ml, mr, mt, mb = 34, 112, 12, 24
    aastad = sorted({a for _, s, _ in seeriad for a in s})
    a0, a1 = aastad[0], aastad[-1]
    tipp = max([v for _, s, _ in seeriad for v in s.values()] + [v for v, _ in sihid]
               + ([hi for _, hi in vahemik.values()] if vahemik else []))
    if ymax:
        samm = ymax / 4
    else:
        # Ilus samm (1, 2, 5 × 10^n), nii et telg algab nullist ja jaotisi on 3–5.
        samm = next(m * 10 ** p for p in range(-2, 6) for m in (1, 2, 2.5, 5) if tipp / (m * 10 ** p) <= 4)
        ymax = -(-tipp // samm) * samm

    def X(a):
        return ml + (a - a0) / ((a1 - a0) or 1) * (W - ml - mr)

    def Y(v):
        return mt + (1 - v / ymax) * (H - mt - mb)

    o = []
    for i in range(int(round(ymax / samm)) + 1):
        t = samm * i
        o.append(f'<line class="gridline" x1="{ml}" x2="{W - mr}" y1="{Y(t):.1f}" y2="{Y(t):.1f}"/>')
        o.append(f'<text x="{ml - 6}" y="{Y(t) + 4:.1f}" text-anchor="end">{fmt(t, 0)}</text>')
    for a in aastad:
        o.append(f'<text x="{X(a):.1f}" y="{H - 6}" text-anchor="middle">{a}</text>')
    if vahemik:
        aa = sorted(vahemik)
        ylem = " ".join(f"{X(a):.1f},{Y(vahemik[a][1]):.1f}" for a in aa)
        alum = " ".join(f"{X(a):.1f},{Y(vahemik[a][0]):.1f}" for a in reversed(aa))
        o.append(f'<polygon class="area" points="{ylem} {alum}"/>')
    sildid = []
    for v, silt in sihid:
        o.append(f'<line class="target" x1="{ml}" x2="{W - mr}" y1="{Y(v):.1f}" y2="{Y(v):.1f}"/>')
        sildid.append([Y(v), silt, "target"])
    for nimi, s, kl in sorted(seeriad, key=lambda t: t[2] == "focus"):
        aa = sorted(s)
        d = " ".join(("M" if i == 0 else "L") + f"{X(a):.1f},{Y(s[a]):.1f}" for i, a in enumerate(aa))
        o.append(f'<path class="ln {kl}" d="{d}"/>')
        for a in aa:
            o.append(f'<circle class="dot {kl}" cx="{X(a):.1f}" cy="{Y(s[a]):.1f}" r="{3.5 if kl == "focus" else 2.5}"/>')
            o.append(f'<circle class="hit" cx="{X(a):.1f}" cy="{Y(s[a]):.1f}" r="8"{_tip(fmt(s[a]), f"{nimi} {a}")}/>')
        sildid.append([Y(s[aa[-1]]), f"{nimi} {fmt(s[aa[-1]])}", kl])
    sildid.sort(key=lambda t: t[0])
    for i in range(1, len(sildid)):
        sildid[i][0] = max(sildid[i][0], sildid[i - 1][0] + 14)
    for y, t, kl in sildid:
        o.append(f'<text class="lab-{kl or "ref"}" x="{X(a1) + 8:.1f}" y="{y + 4:.1f}">{e(t)}</text>')
    # Klambri silt on halo-ga, et joon selle alt läbi ei paistaks.
    for a, v1, v2, t in markused:
        x = X(a) + (-10 if a == a1 else 10)
        o.append(f'<path class="brace" d="M{x:.1f},{Y(v1):.1f} L{x:.1f},{Y(v2):.1f}"/>')
        ty = (Y(v1) + Y(v2)) / 2 + 4
        anchor = "end" if a == a1 else "start"
        o.append(f'<text class="ann-strong" x="{x + (-5 if a == a1 else 5):.1f}" y="{ty:.1f}" text-anchor="{anchor}">{e(t)}</text>')
    return (f'<svg class="an-svg" viewBox="0 0 {W} {H}" role="img" aria-label="{e(kirjeldus)}">{"".join(o)}</svg>')


def oige_vale(oige, vale):
    return ('<div class="ov">'
            f'<p class="ov-ok"><span class="ov-ic" aria-hidden="true">✓</span><span><b>Õige</b>{e(oige)}</span></p>'
            f'<p class="ov-no"><span class="ov-ic" aria-hidden="true">✕</span><span><b>Vale</b>{e(vale)}</span></p></div>')


OLEKU_KLASS = {"seires": "t-seires", "andmed": "t-andmed", "kavandatud": "t-kav", "allikas_leidmata": "t-puudu"}


OLEKU_JARJEKORD = ["seires", "andmed", "kavandatud", "allikas_leidmata"]


def kataloogi_teemad(K):
    """[(teema, [(mõiste id, nimi, olek, mõõdikute arv)])] kataloogi järjekorras.
    Küsimuse olek on tema parima mõõdiku olek (seires > andmed > kavandatud > leidmata)."""
    tulem = []
    kat = K["kategooriad"]
    for kood, teema in kat.items():
        if teema["ulem"]:
            continue
        alad = [ak for ak, ala in kat.items() if ala["ulem"] == kood]
        kk = []
        for m in K["moisted"].values():
            if m["kategooria"] not in alad:
                continue
            mood = [x for x in K["moodikud"].values() if x["moiste"] == m["id"]]
            olek = min((x["olek"] for x in mood), key=OLEKU_JARJEKORD.index) if mood else "allikas_leidmata"
            kk.append((m["id"], m["nimi"], olek, len(mood)))
        tulem.append((teema["nimi"], kk))
    return tulem


def kattuvus(teemad, olekud, link="", kompaktne=False):
    """Kataloogi kaart: iga teema rida, iga küsimus üks ruut olekuvärviga.
    teemad: [(teema_nimi, [(id, nimi, olek, allikate_arv)])], olekud: {olek: silt}."""
    read = []
    for nimi, kk in teemad:
        ruudud = "".join(
            f'<a class="tile {OLEKU_KLASS[o]}" href="{link}#{e(i)}" title="{e(n)}: {e(olekud[o])}, {a} allikat">'
            + ("" if kompaktne else f'<span>{e(n)}</span><small>{a} allik{"as" if a == 1 else "at"}</small>')
            + '</a>' for i, n, o, a in kk)
        read.append(f'<div class="cov-row"><p class="cov-name">{e(nimi)}<small>{sum(1 for _, _, o, _ in kk if o in ("seires", "andmed"))}/{len(kk)} andmetega</small></p>'
                    f'<div class="cov-tiles">{ruudud}</div></div>')
    leg = "".join(f'<span><i class="tile-key {OLEKU_KLASS[o]}"></i>{e(s)}</span>' for o, s in olekud.items())
    return f'<div class="an-legend" aria-hidden="true">{leg}</div><div class="cov{" cov-compact" if kompaktne else ""}">{"".join(read)}</div>'
