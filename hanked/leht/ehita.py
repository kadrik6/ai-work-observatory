"""Ehitab tulemuste lehe (üks HTML-fail) koondfailist leht.json.

    python hanked/leht/ehita.py valjund/leht.json valjund/ai-hanked.html [--seis 2026-11-04]

Leht on Sinine Fookus disainisüsteemis (avalik sektor). Graafikud joonistatakse siin SVG-na, et leht oleks
loetav ka ilma JavaScriptita; JavaScript teeb ainult vahekaardid, teema nupu ja sarnaste hangete otsingu.

Lehe neli rida (andmesaidi-ulesehitus):
- Kes loeb: hankespetsialist või sisuinimene, kes kirjutab AI- või andmehanke lähteülesannet; analüütik ja
  juht, kes jälgib innovatsioonihangete sihti; kursuse hindaja.
- Küsimus: kui palju AI- ja andmehankeid riik teeb, kuidas neid hangitakse ja kust leida hea näide?
- Pärast teab või teeb: leiab sarnase hea hanke eeskujuks; teab, kui kaugel on 2% siht; teab, kui täpne
  tuvastus on ja mida see ei näita.
- Põhiline: aastanäitaja ja 2% siht. Toetav: hankimise viis, otsing. Valikuline: hindamine ja meetod.
"""
import argparse
import collections
import datetime as dt
import html
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import tellija as T  # noqa: E402

REEGLI_NIMI = {
    "mudel": "Mudel (masinõpe)",
    "marksonaloend": "Märksõnaloend",
    "mudel_voi_marksona": "Mudel või märksõna",
    "oecd_laadne": "OECD-laadne loend (AI-sõnad ja „algoritm“)",
}
OECD = "https://doi.org/10.1787/c2c09a06-en"
REGISTER = "https://riigihanked.riik.ee/rhr-web/#/opendata"
SIHT = 2.0
ALGUS_AASTA = 2017  # registri avaandmed algavad 09/2017


def e(x):
    return html.escape(str(x), quote=True)


def arv(x, k=0):
    """Eesti kirjaviis: tühik tuhandete vahel, koma kümnendkohas."""
    if x is None:
        return "–"
    s = f"{x:,.{k}f}".replace(",", " ").replace(".", ",")
    return s


def protsent(x, k=1):
    return "–" if x is None else arv(x, k) + "%"


# ---------------------------------------------------------------- graafikud (SVG)

def tulbad_aastad(aastad, fookus_aasta, osalised):
    """Vertikaalsed tulbad: AI- ja andmehangete arv aastas. Üks fookustulp, teised hallid."""
    w, h, vasak, all, ules = 560, 220, 8, 34, 26
    n = len(aastad)
    samm = (w - vasak * 2) / max(n, 1)
    tl = samm * 0.62
    mx = max([a["ai_andmed"] for a in aastad] + [1])
    osad = [f'<svg viewBox="0 0 {w} {h}" role="img" aria-labelledby="g1-p g1-k" class="graafik">']
    for i, a in enumerate(aastad):
        x = vasak + i * samm + (samm - tl) / 2
        kh = (h - all - ules) * a["ai_andmed"] / mx
        y = h - all - kh
        klass = "m-fookus" if a["aasta"] == fookus_aasta else "m-kontekst"
        osad.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{tl:.1f}" height="{kh:.1f}" class="{klass}"/>')
        tekst_klass = "t-fookus" if a["aasta"] == fookus_aasta else "t-silt"
        osad.append(f'<text x="{x + tl / 2:.1f}" y="{y - 7:.1f}" text-anchor="middle" class="{tekst_klass}">'
                    f'{arv(a["ai_andmed"])}</text>')
        silt = f'{a["aasta"]}*' if a["aasta"] in osalised else str(a["aasta"])
        osad.append(f'<text x="{x + tl / 2:.1f}" y="{h - 12}" text-anchor="middle" class="t-telg">{silt}</text>')
    osad.append(f'<line x1="{vasak}" x2="{w - vasak}" y1="{h - all}" y2="{h - all}" class="telg"/>')
    osad.append("</svg>")
    return "".join(osad)


def tulbad_innovatsioon(read):
    """Innovatsioonimärkega hangete osakaal eVormide aastatel ja 2% siht katkendjoonena."""
    w, h, vasak, all, ules, parem = 560, 220, 8, 34, 30, 104
    mx = max([r["innovatsioonimark_osakaal"] or 0 for r in read] + [SIHT]) * 1.15
    n = len(read)
    samm = (w - vasak - parem) / max(n, 1)
    tl = samm * 0.5
    y_ = lambda v: h - all - (h - all - ules) * v / mx  # noqa: E731
    osad = [f'<svg viewBox="0 0 {w} {h}" role="img" aria-labelledby="g2-p g2-k" class="graafik">']
    ys = y_(SIHT)
    for i, r in enumerate(read):
        v = r["innovatsioonimark_osakaal"] or 0
        x = vasak + i * samm + (samm - tl) / 2
        viimane = i == n - 1
        osad.append(f'<rect x="{x:.1f}" y="{y_(v):.1f}" width="{tl:.1f}" height="{h - all - y_(v):.1f}" '
                    f'class="{"m-fookus" if viimane else "m-kontekst"}"/>')
        osad.append(f'<text x="{x + tl / 2:.1f}" y="{y_(v) - 7:.1f}" text-anchor="middle" '
                    f'class="{"t-fookus" if viimane else "t-silt"}">{protsent(v)}</text>')
        silt = f'{r["aasta"]}*' if r.get("_osaline") else str(r["aasta"])
        osad.append(f'<text x="{x + tl / 2:.1f}" y="{h - 12}" text-anchor="middle" class="t-telg">{silt}</text>')
    osad.append(f'<line x1="{vasak}" x2="{w - parem + 10}" y1="{ys:.1f}" y2="{ys:.1f}" class="siht"/>')
    osad.append(f'<text x="{w - parem + 16}" y="{ys + 5:.1f}" class="t-siht">siht 2%</text>')
    osad.append(f'<text x="{w - parem + 16}" y="{ys + 23:.1f}" class="t-telg">aastaks 2027</text>')
    osad.append(f'<line x1="{vasak}" x2="{w - parem + 10}" y1="{h - all}" y2="{h - all}" class="telg"/>')
    osad.append("</svg>")
    return "".join(osad)


def vordlusribad(naitajad, grupid):
    """Väikesed horisontaalsed ribad: iga näitaja kohta kolm rühma. AI ja andmed on fookuses."""
    plokid = []
    for nimi, vali, yhik, mx in naitajad:
        read = []
        for g_id, g_nimi in grupid:
            v = vali(g_id)
            laius = 0 if v is None else max(0.5, 100 * v / mx)
            klass = "riba-fookus" if g_id == "ai_andmed" else "riba-kontekst"
            vaartus = "–" if v is None else (arv(v) if yhik == "" else protsent(v, 0) if yhik == "%" else arv(v) + yhik)
            read.append(
                f'<div class="v-rida"><span class="v-nimi">{e(g_nimi)}</span>'
                f'<span class="v-rada"><span class="{klass}" style="width:{laius:.1f}%"></span></span>'
                f'<span class="v-arv{" v-arv-fookus" if g_id == "ai_andmed" else ""}">{vaartus}</span></div>')
        plokid.append(f'<div class="v-plokk"><h4>{e(nimi)}</h4>{"".join(read)}</div>')
    return f'<div class="vordlus">{"".join(plokid)}</div>'


def hankijate_ribad(top, fookus=lambda nimi: False, mx=None):
    """Horisontaalsed ribad. Fookusvärv ainult ridadel, mille kohta fookus(nimi) on tõene."""
    mx = mx or max([n for _, n in top] + [1])
    read = []
    for nimi, n in top:
        klass = "riba-fookus" if fookus(nimi) else "riba-kontekst"
        read.append(f'<div class="v-rida v-rida-lai"><span class="v-nimi">{e(nimi)}</span>'
                    f'<span class="v-rada"><span class="{klass}" style="width:{100 * n / mx:.1f}%"></span></span>'
                    f'<span class="v-arv">{arv(n)}</span></div>')
    return "".join(read)


def tellijad(loend):
    """Lisab loendi ridadele tellija (kj) ja selle allika (kja) ning loendab korraldajad ja tellijad."""
    nimed = T.asutused(r.get("h") for r in loend)
    korr, tell = collections.Counter(), collections.Counter()
    for r in loend:
        r["kj"], r["kja"] = T.kelle_jaoks(r.get("t"), r.get("h"), nimed)
        korr[r.get("h") or "?"] += 1
        tell[r["kj"].split("; ")[0]] += 1
    teise_jaoks = sum(r["kja"] != "sama" for r in loend)
    kesksete = sum(r.get("h") in T.KESKSED for r in loend)
    jarjest = tell.most_common()
    top10 = max(1, round(len(jarjest) * 0.1))
    return {"korraldajad": korr.most_common(), "tellijad": jarjest, "teise_jaoks": teise_jaoks,
            "kesksete": kesksete, "pealkirjast": sum(r["kja"] == "pealkiri" for r in loend),
            "tellijaid": len(jarjest), "top10_tellijaid": top10,
            "top10_osakaal": round(100 * sum(n for _, n in jarjest[:top10]) / max(len(loend), 1), 1)}


# ---------------------------------------------------------------- leht

def ehita(d, seis):
    aastad = d["aastad"]
    ef_aastad = d.get("eforms_aastad") or []
    jooksev = int(seis[:4])
    osaline = jooksev if any(a["aasta"] == jooksev for a in aastad) else None
    taisaastad = [a for a in aastad if a["aasta"] != osaline]
    fookus = taisaastad[-1] if taisaastad else aastad[-1]
    hindamine = d["hindamine"]
    hm = hindamine.get("hindamine", {})
    valitud = hm.get("valitud", "marksonaloend")
    tul = hm.get("tulemused", {})
    lev = hindamine.get("levimus", {})
    viis = d["hankimise_viis"]
    ko = d["kontsentratsioon"]

    # innovatsioon: ainult eVormide aastad; esimene eVormide aasta on osaline (alates 09/2023)
    inn = [dict(a) for a in aastad if a["aasta"] in ef_aastad and a.get("innovatsioonimark_osakaal") is not None]
    for i, r in enumerate(inn):
        r["_osaline"] = (i == 0) or r["aasta"] == osaline
    inn_viimane = inn[-1] if inn else None

    ai = viis["ai_andmed"]
    muu = viis["koik"]
    kval_ai = None if ai["ainult_hind_osakaal"] is None else 100 - ai["ainult_hind_osakaal"]
    kval_koik = None if muu["ainult_hind_osakaal"] is None else 100 - muu["ainult_hind_osakaal"]
    p0, p1 = viis.get("periood") or [None, None]

    # pealkirjad ütlevad leiu
    g1_pealkiri = (f'AI- ja andmehankeid tehti {fookus["aasta"]}. aastal <b>{arv(fookus["ai_andmed"])}</b>, '
                   f'see on {protsent(fookus["ai_andmed_osakaal"])} kõigist hangetest')
    if inn_viimane:
        vahe = SIHT - (inn_viimane["innovatsioonimark_osakaal"] or 0)
        g2_pealkiri = (f'Innovatsioonihankeks märgiti {inn_viimane["aasta"]}. aastal '
                       f'<b>{protsent(inn_viimane["innovatsioonimark_osakaal"])}</b> hangetest, '
                       + ("sihini 2% jääb " + arv(vahe, 1) + " protsendipunkti" if vahe > 0 else "siht 2% on täidetud"))
    else:
        g2_pealkiri = "Innovatsioonimärget saab lugeda alles eVormidest"
    if kval_ai is not None and kval_koik is not None:
        sonad = "sagedamini" if kval_ai > kval_koik + 3 else ("harvemini" if kval_ai < kval_koik - 3 else "sama sageli")
        g3_pealkiri = (f'AI- ja andmehangetes on kvaliteedikriteerium <b>{protsent(kval_ai, 0)}</b> hangetest, '
                       f'{sonad} kui hangetes keskmiselt ({protsent(kval_koik, 0)})')
    else:
        g3_pealkiri = "Kuidas AI- ja andmehankeid hinnatakse"
    tl = tellijad(d["loend"])
    n_loend_kokku = max(len(d["loend"]), 1)
    g4_pealkiri = (f'<b>{protsent(100 * tl["teise_jaoks"] / n_loend_kokku, 0)}</b> AI- ja andmehangetest '
                   f'tehakse teise asutuse jaoks, kui lugeda pealkirja')
    mx4 = max([n for _, n in tl["korraldajad"][:12] + tl["tellijad"][:12]] + [1])

    vastus = [
        f'Riigihangete registris on {arv(sum(a["ai_andmed"] for a in aastad))} AI- või andmehanget '
        f'({aastad[0]["aasta"]}–{aastad[-1]["aasta"]}). {fookus["aasta"]}. aastal oli neid '
        f'{arv(fookus["ai_andmed"])}, ehk {protsent(fookus["ai_andmed_osakaal"])} kõigist hangetest.',
    ]
    if inn_viimane:
        vastus.append(f'Innovatsioonihankeks märgitakse {protsent(inn_viimane["innovatsioonimark_osakaal"])} '
                      f'hangetest ({inn_viimane["aasta"]}). OECD raportis on siht 2% aastaks 2027.')
    if kval_ai is not None:
        vastus.append(f'AI- ja andmehangetest {protsent(kval_ai, 0)} hindab ka kvaliteeti, mitte ainult hinda. '
                      f'Ühe pakkujaga on {protsent(ai["uks_pakkuja_osakaal"], 0)} ({p0}–{p1}).')

    # hindamise tabel
    hind_read = []
    for k in ("marksonaloend", "mudel_voi_marksona", "mudel", "oecd_laadne"):
        t = tul.get(k)
        if not t:
            continue
        v95 = lambda x: f'<span class="vahemik">{arv(100 * x[0])}–{arv(100 * x[1])}</span>' if x else ""  # noqa: E731
        kl = ' class="valitud"' if k == valitud else ""
        hind_read.append(
            f'<tr{kl}><th scope="row">{e(REEGLI_NIMI[k])}'
            f'{"<span class=alam>kasutusel lehel</span>" if k == valitud else ""}</th>'
            f'<td>{arv(100 * (t["tapsus"] or 0))}% {v95(t.get("tapsus_95"))}</td>'
            f'<td>{arv(100 * (t["saagis"] or 0))}% {v95(t.get("saagis_95"))}</td>'
            f'<td>{arv(t["f1"] or 0, 2)}</td><td>{arv(t["tp"])} / {arv(t["fp"])} / {arv(t["fn"])}</td></tr>')
    vp = lev.get("valimi_pohjal", {})
    t_val = tul.get(valitud, {})
    tapsus_pealkiri = (f'Kasutusel olev reegel leiab <b>{arv(100 * (t_val.get("saagis") or 0))}%</b> '
                       f'AI- ja andmehangetest ja {arv(100 * (t_val.get("tapsus") or 0))}% leitutest on õiged'
                       if t_val else "Tuvastuse täpsus")

    # andmetabel graafiku alla
    tabel_aastad = "".join(
        f'<tr><th scope="row">{a["aasta"]}{"*" if a["aasta"] in (osaline, ALGUS_AASTA) else ""}</th><td>{arv(a["hankeid"])}</td>'
        f'<td>{arv(a["ai_andmed"])}</td><td>{protsent(a["ai_andmed_osakaal"], 2)}</td>'
        f'<td>{arv(a["ai_marksonaga"])}</td>'
        f'<td>{"–" if a.get("innovatsioonimark") is None else arv(a["innovatsioonimark"])}</td>'
        f'<td>{protsent(a.get("innovatsioonimark_osakaal"), 2)}</td></tr>' for a in aastad)

    grupid = [("ai_andmed", "AI- ja andmehanked"), ("it_muud", "Muud IT-hanked"), ("koik", "Kõik hanked")]
    g = lambda gid, k: viis[gid][k]  # noqa: E731
    vordlus = vordlusribad([
        ("Kvaliteet on hindamiskriteeriumide hulgas",
         lambda gid: None if g(gid, "ainult_hind_osakaal") is None else 100 - g(gid, "ainult_hind_osakaal"), "%", 100),
        ("Kvaliteedi kaal, mediaan", lambda gid: g(gid, "kvaliteedi_kaal_mediaan"), "%", 100),
        ("Ainult üks pakkumus", lambda gid: g(gid, "uks_pakkuja_osakaal"), "%", 100),
        ("Hange katkes või jäi lepinguta", lambda gid: g(gid, "katkes_osakaal"), "%", 100),
    ], grupid)

    loend = d["loend"]
    jargmised = hindamine.get("margenda_jargmiseks", {}).get("read", [])
    andmed = {"loend": loend}
    seis_kuva = dt.date.fromisoformat(seis).strftime("%d.%m.%Y")

    return taida(MALL,
        seis=e(seis_kuva), vastus="".join(f"<li>{x}</li>" for x in vastus),
        g1_pealkiri=g1_pealkiri, g1=tulbad_aastad(aastad, fookus["aasta"], {osaline, ALGUS_AASTA}),
        g1_alam=(f'Hangete arv aastas, mille põhiese on tehisintellekti- või andmelahendus. Tuvastus: '
                 f'{e(REEGLI_NIMI[valitud].lower())}. Hange on loetud esimese teate aasta järgi.'),
        osaline_markus=(f'* {ALGUS_AASTA} algab septembrist. ' if aastad[0]["aasta"] == ALGUS_AASTA else "")
        + (f'{osaline} on pooleli (andmed {seis_kuva} seisuga). ' if osaline else "")
        + (f'Kuni {min(ef_aastad)}. aasta augustini on teated vanas vormingus ja neis on vähem välju.'
           if ef_aastad else ""),
        g2_pealkiri=g2_pealkiri, g2=tulbad_innovatsioon(inn) if inn else "",
        tabel_aastad=tabel_aastad,
        g3_pealkiri=g3_pealkiri, vordlus=vordlus, periood=f"{p0}–{p1}",
        n_ai=arv(ai["hankeid"]), n_pakk_ai=arv(ai.get("pakkumusi_teada")), n_koik=arv(muu["hankeid"]),
        kval_mediaan_ai=arv(ai["kvaliteedi_kaal_mediaan"]) if ai["kvaliteedi_kaal_mediaan"] is not None else "–",
        g4_pealkiri=g4_pealkiri,
        korraldajad=hankijate_ribad(tl["korraldajad"][:12], lambda n: n in T.KESKSED, mx4),
        tellijad=hankijate_ribad([(n.replace(" (pealkirjast ei selgu)", "*"), x) for n, x in tl["tellijad"][:12]], mx=mx4),
        n_teise=arv(tl["teise_jaoks"]), n_pealkirjast=arv(tl["pealkirjast"]),
        n_kesksed=arv(tl["kesksete"]), n_kokku4=arv(len(d["loend"])),
        hankijaid=arv(ko["hankijaid"]), top10_h=arv(ko["top10_protsenti_hankijaid"]),
        top10_h_osa=protsent(ko["nende_osakaal"], 0),
        tellijaid=arv(tl["tellijaid"]), top10_t=arv(tl["top10_tellijaid"]), top10_t_osa=protsent(tl["top10_osakaal"], 0),
        tapsus_pealkiri=tapsus_pealkiri, hind_read="".join(hind_read),
        test_alates=hm.get("testi_alates", "–"), treening=arv(hm.get("treening")), test=arv(hm.get("test")),
        test_pos=arv(hm.get("test_pos")), treening_pos=arv(hm.get("treening_pos")),
        lev_hinnang=arv(vp.get("hinnang")),
        lev_vahemik=f'{arv((vp.get("vahemik_95") or [None, None])[0])}–{arv((vp.get("vahemik_95") or [None, None])[1])}',
        lev_hankeid=arv(lev.get("hankeid")), lev_leidis=arv(lev.get("valitud_leidis")),
        margendeid=arv(hindamine.get("margendid", {}).get("leitud_registrist")),
        positiivseid=arv(hindamine.get("margendid", {}).get("positiivseid")),
        jargmised="".join(f'<li>{e(r["pealkiri"])} <span class="alam">tõenäosus {arv(r["p"], 2)}</span></li>'
                          for r in jargmised[:8]),
        n_loend=arv(len(loend)),
        andmed=json.dumps(andmed, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/"),
        oecd=OECD, register=REGISTER,
    )


MALL = open(Path(__file__).with_name("mall.html"), encoding="utf-8").read()


def taida(mall, **kw):
    """Asendab mallis %%nimi%% kohad. Puuduv nimi on viga, et poolik leht ei läheks avaldamisele."""
    for k, v in kw.items():
        mall = mall.replace(f"%%{k}%%", str(v))
    if "%%" in mall:
        jaak = mall[mall.index("%%"):mall.index("%%") + 40]
        raise ValueError(f"mallis on täitmata koht: {jaak}")
    return mall


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sisend")
    ap.add_argument("valjund")
    ap.add_argument("--seis", default=dt.date.today().isoformat())
    a = ap.parse_args()
    d = json.loads(Path(a.sisend).read_text(encoding="utf-8"))
    Path(a.valjund).write_text(ehita(d, a.seis), encoding="utf-8")
    print("kirjutatud", a.valjund, file=sys.stderr)


if __name__ == "__main__":
    main()
