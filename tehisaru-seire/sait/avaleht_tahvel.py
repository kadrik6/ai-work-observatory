"""Avalehe signaalitahvel (Kadri 14.11.2026 valis näidise C: „teeme c selle uue suunaga“).

Avaleht on töölaud: üks tabel, kus iga teema on üks rida (praegu, kulg, muutus, koht ELis, väited, siht, värskus),
ja ajajoon „mis muutus ja mis tuleb“. Telefonis on tabelil neli kitsast veergu ja rida avaneb puudutusega;
ajajoon on seal kaks loendit. Iga rida on oma skaalal; võrreldamatuid numbreid samale teljele ei panda.
Värvid tulevad CSS-ist (stiil.css, plokk „Avalehe signaalitahvel“).
"""
import collections
import datetime
import re

import andmekiht as andmed
from abi import link
from andmekiht import EL, AndmeViga
from komponendid import KUUD, e, kp, pr, riik
from lehed_usaldus import RASKUS, _raskus

VARSKE_PAEVI = 92
VOO_PAEVI = 30


# ---------------------------------------------------------------- andmed

def el_jaotus(A, nid, vaiksem_parem=False):
    """ELi riikide väärtused Eesti uusima alusaasta kohta: {v, ee, eu, y, koht, n}."""
    ee = andmed.leia(A, nid, "EE", "uusim:alus")
    y = ee["aasta"]
    vv = {v["geo"]: v["vaartus"] for v in andmed.vali(A, nid, aasta=y, klass="alus") if v["geo"] in A["el_riigid"]}
    if "EE" not in vv:
        raise AndmeViga(f"{nid}: Eesti {y} puudub ELi jaotusest")
    jrj = sorted(vv, key=lambda g: vv[g], reverse=not vaiksem_parem)
    return {"v": vv, "ee": vv["EE"], "eu": andmed.leia(A, nid, EL, y)["vaartus"], "y": y, "koht": jrj.index("EE") + 1, "n": len(vv)}


# ---------------------------------------------------------------- väikesed joonised (SVG, värvid CSS-ist)

def ribarida(j, w=140, h=20):
    """ELi riigid punktidena ühel teljel; Eesti sinine, ELi keskmine kriips. Punktdiagramm: telg ei alga nullist."""
    vv = list(j["v"].values())
    pad = (max(vv) - min(vv)) * 0.04 or 1
    lo, hi = min(vv) - pad, max(vv) + pad
    x = lambda z: 6 + (z - lo) / (hi - lo) * (w - 12)  # noqa: E731
    y = h / 2
    p = "".join(f'<circle class="tv-c" cx="{x(z):.1f}" cy="{y:.1f}" r="3.5"><title>{e(riik(g))} {pr(z)}</title></circle>'
                for g, z in sorted(j["v"].items()) if g != "EE")
    return (f'<svg class="tv-riba" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" '
            f'aria-label="Eesti {pr(j["ee"])}%, ELi keskmine {pr(j["eu"])}%, {j["koht"]}. koht {j["n"]} riigi seas ({j["y"]})">'
            f'<line class="tv-ax" x1="6" x2="{w - 6}" y1="{y:.1f}" y2="{y:.1f}"/>{p}'
            f'<line class="tv-eu" x1="{x(j["eu"]):.1f}" x2="{x(j["eu"]):.1f}" y1="{y - 8:.1f}" y2="{y + 8:.1f}"/>'
            f'<circle class="tv-ee" cx="{x(j["ee"]):.1f}" cy="{y:.1f}" r="5.5"><title>Eesti {pr(j["ee"])}</title></circle></svg>')


def kulujoon(seeriad, y0, y1, silt, w=120, h=34):
    """Väike joon: seeriad [(punktid [(x, y)], "f" fookus | "r" võrdlus)]. Kriipsud ei skaleeru (CSS)."""
    xs = [x for pts, _ in seeriad for x, _ in pts]
    x0, x1 = min(xs), max(xs)
    X = lambda v: 3 + (v - x0) / ((x1 - x0) or 1) * (w - 8)  # noqa: E731
    Y = lambda v: h - 4 - (v - y0) / ((y1 - y0) or 1) * (h - 8)  # noqa: E731
    out = []
    for pts, kl in seeriad:
        out.append(f'<polyline class="tv-l{kl}" points="{" ".join(f"{X(a):.1f},{Y(b):.1f}" for a, b in pts)}"/>')
        out.append(f'<circle class="tv-p{kl}" cx="{X(pts[-1][0]):.1f}" cy="{Y(pts[-1][1]):.1f}" r="{3 if kl == "f" else 2}"/>')
    return f'<svg class="tv-joon" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-label="{e(silt)}">{"".join(out)}</svg>'


def osariba(v, skaala, siht=None, eu=None, w=120, silt=""):
    """Riba 0…skaala; siht oranž kriips, ELi keskmine must kriips. Iga rida on oma skaalal."""
    x = lambda z: max(0.0, min(w, z / skaala * w))  # noqa: E731
    return (f'<svg class="tv-osa" viewBox="0 0 {w} 14" width="{w}" height="14" role="img" aria-label="{e(silt)}">'
            f'<rect class="tv-bg" x="0" y="4" width="{w}" height="6" rx="3"/><rect class="tv-v" x="0" y="4" width="{x(v):.1f}" height="6" rx="3"/>'
            + (f'<line class="tv-eu" x1="{x(eu):.1f}" x2="{x(eu):.1f}" y1="1" y2="13"/>' if eu is not None else "")
            + (f'<line class="tv-siht" x1="{x(siht):.1f}" x2="{x(siht):.1f}" y1="0" y2="14"/>' if siht is not None else "")
            + "</svg>")


def vahvel(osa, silt, n=100, rida=25, r=5):
    """100 ruutu = kõik hanked; täidetud osa = tehisaru- ja andmehanked (osa %)."""
    s = []
    for i in range(n):
        cx, cy = (i % rida) * r, (i // rida) * r
        s.append(f'<rect class="tv-bg" x="{cx}" y="{cy}" width="{r - 1}" height="{r - 1}"/>')
        tais = min(1, max(0, osa - i))
        if tais > 0:
            s.append(f'<rect class="tv-v" x="{cx}" y="{cy}" width="{(r - 1) * tais:.2f}" height="{r - 1}"/>')
    return f'<svg class="tv-vahvel" viewBox="0 0 {rida * r} {n // rida * r}" width="{rida * r}" height="{n // rida * r}" role="img" aria-label="{e(silt)}">{"".join(s)}</svg>'


# ---------------------------------------------------------------- tahvel

def _vaited(vv, vaated, ll=()):
    """vv: teema väited; ll: teema selgitamata lahknevused (Kadri 6.11.2026: lahknevused nähtavale)."""
    lk = (f'<small>{link(vaated, "kas-tosi", ("lahknevus " if len(ll) == 1 else "lahknevused ") + ", ".join(x["kood"] for x in ll), "lahknevused")} selgitamata</small>'
          if ll else "")
    if not vv:
        return (lk or '<small class="tv-tuhi">–</small>'), "–"
    muud = sum(_raskus(v) == 0 for v in sorted(vv, key=_raskus))
    tapid = "".join(f'<i class="{RASKUS[_raskus(v)][1]}" title="{e(RASKUS[_raskus(v)][0])}"></i>' for v in sorted(vv, key=_raskus))
    n = len(vv)
    tekst = f'{n} {"väide" if n == 1 else "väidet"}' + (f", {muud} {'erineb' if muud == 1 else 'erinevad'} allikast" if muud else ", kõik vastavad allikale")
    return (f'<span class="tv-tapid" aria-hidden="true">{tapid}</span>{link(vaated, "kas-tosi", tekst)}{lk}', tekst)


def _muutus(d, tekst, all=""):
    nool = "" if d is None else f'<span class="tv-nool" aria-hidden="true">{"▲" if d > 0 else ("▼" if d < 0 else "■")}</span> '
    return f'{nool}{tekst}' + (f"<small>{all}</small>" if all else "")


def _varskus(kuup, viimane):
    vana = (datetime.date.fromisoformat(viimane) - datetime.date.fromisoformat(kuup)).days > VARSKE_PAEVI
    return f'<span class="v-tapp{" vana" if vana else ""}" aria-hidden="true"></span>{kp(kuup)}<small>{"vanem kui 3 kuud" if vana else "värske"}</small>'


def tahvel(A, vaated, d, vaite_teema, tootus_el_koht):
    """d: avalehel arvutatud numbrid (ein, ein25, eeb, ds, T, kuu, t_ee, t_el, t_aasta_eest, h_uus).
    Tagastab (jaotis, read) – read on testide ja telefonivaate jaoks."""
    from lehed_teemad import _o
    menuu = lambda vid, tekst, ank="": link(vaated, vid, tekst, ank)  # noqa: E731
    ein, ein25, eeb, ds = d["ein"], d["ein25"], d["eeb"], d["ds"]
    T, kuu, t_ee, t_el, t_ae = d["T"], d["kuu"], d["t_ee"], d["t_el"], d["t_aasta_eest"]
    h_uus = d["h_uus"]
    IN, EB = ein["naitaja"], eeb["naitaja"]
    J_in, J_eb = el_jaotus(A, IN), el_jaotus(A, EB)
    if (J_in["y"], J_eb["y"]) != (andmed.leia(A, IN, "EE", "uusim:alus")["aasta"], andmed.leia(A, EB, "EE", "uusim:alus")["aasta"]):
        raise AndmeViga("Tahvli ELi koht ja h1 ELi aasta erinevad")
    siht_ee, siht_ds = A["sihid"]["ee-ettevotted-75"], A["sihid"]["el-digioskused-80"]
    ds_el = andmed.leia(A, ds["naitaja"], EL, ds["aasta"])
    kr = next(r for r in A["otsused"] if r["id"] == "ai-korge-risk-iii")
    gk = _o(A, "genai-kesk")
    HL = A["hanked_leht"]
    inn = [r for r in HL["aastad"] if r.get("innovatsioonimark_osakaal") is not None][-1]
    INN_SIHT = 2.0  # riigihangete innovatsioonisiht aastaks 2027 (OECD aruanne 2026, lk 41 ja 49)
    from lehed_ulevaade import LAHK_TEEMA
    vt, lahk = collections.defaultdict(list), collections.defaultdict(list)
    for v in A["vaited"]:
        vt[vaite_teema(v)].append(v)
    for x in A["lahknevused"]:
        if x["staatus"] == "selgitamata":
            lahk[LAHK_TEEMA.get(x["naitaja"], "")].append(x)

    eb_ts = {g: sorted((int(v["aasta"]), v["vaartus"]) for v in andmed.vali(A, EB, geo=g, klass="alus")) for g in ("EE", EL)}
    t12 = T["EE"][-12:]
    idx = {k: i for i, (k, _) in enumerate(t12)}
    k0 = t12[0][0]

    R = [  # (tid, nimi, ankur, arv, selgitus, kulg, kulg_all, muutus, el (laud), el (telefon: arv, all), (väited html, tekst), siht, kuupäev)
        ("inimesed", "Inimesed", "kasutus", f"{pr(ein['vaartus'])}%", f"kasutas tehisaru · {ein['aasta']}",
         kulujoon([([(ein25["aasta"], ein25["vaartus"]), (ein["aasta"], ein["vaartus"])], "f")], 0, 100,
                  f"Eesti {ein25['aasta']} {pr(ein25['vaartus'])}%, {ein['aasta']} {pr(ein['vaartus'])}%"),
         f"{ein25['aasta']}–{ein['aasta']}",
         _muutus(ein["vaartus"] - ein25["vaartus"], f"{'+' if ein['vaartus'] >= ein25['vaartus'] else '−'}{pr(abs(ein['vaartus'] - ein25['vaartus']))} p aastaga", "küsimus võib erineda"),
         f'<b>{J_in["koht"]}.</b> <small>{J_in["n"]}st · {J_in["y"]}</small>{ribarida(J_in)}', (f'{J_in["koht"]}.', f'{J_in["n"]}st'),
         _vaited(vt["inimesed"], vaated, lahk["inimesed"]),
         menuu("inimesed", f'digioskused {pr(ds["vaartus"])}% → ELi siht {pr(float(siht_ds["siht"]), 0)}% ({siht_ds["aasta"]})', "digi")
         + osariba(ds["vaartus"], 100, float(siht_ds["siht"]), ds_el["vaartus"], silt=f"Digioskused {pr(ds['vaartus'])}%, EL {pr(ds_el['vaartus'])}%, siht {pr(float(siht_ds['siht']), 0)}%"),
         ein["avaldatud"]),
        ("ettevotted", "Ettevõtted", "kasutus", f"{pr(eeb['vaartus'])}%", f"kasutab tehisaru · {eeb['aasta']}",
         kulujoon([(eb_ts["EE"], "f"), (eb_ts[EL], "r")], 0, max(v for s in eb_ts.values() for _, v in s) * 1.1,
                  f"Eurostat {eb_ts['EE'][0][0]}–{eb_ts['EE'][-1][0]}: Eesti {pr(eb_ts['EE'][0][1])}% → {pr(eb_ts['EE'][-1][1])}%, EL {pr(eb_ts[EL][-1][1])}%"),
         f"Eurostat {eb_ts['EE'][0][0]}–{eb_ts['EE'][-1][0]}, ┄ EL",
         _muutus(None, f"{eeb['aasta'] - 1}. aastaga ei võrrelda", "uus tegevusalade klassifikaator (EMTAK 2025)"),
         f'<b>{J_eb["koht"]}.</b> <small>{J_eb["n"]}st · {J_eb["y"]}</small>{ribarida(J_eb)}', (f'{J_eb["koht"]}.', f'{J_eb["n"]}st'),
         _vaited(vt["ettevotted"], vaated, lahk["ettevotted"]),
         menuu("ettevotted", f'{pr(eeb["vaartus"])}% → siht {pr(float(siht_ee["siht"]), 0)}% ({siht_ee["aasta"]})', "kasutus")
         + osariba(eeb["vaartus"], 100, float(siht_ee["siht"]), silt=f"Ettevõtted {pr(eeb['vaartus'])}%, siht {pr(float(siht_ee['siht']), 0)}%"),
         eeb["avaldatud"]),
        ("too", "Töö", "tootus-kuud", f"{pr(t_ee)}%", f"töötus · {KUUD[int(kuu[5:]) - 1]} {kuu[:4]}",
         kulujoon([([(idx[k], v) for k, v in t12], "f"), ([(idx[k], v) for k, v in T[EL] if k in idx], "r")],
                  min(v for k, v in T[EL] + T["EE"] if k in idx) - 0.5, max(v for k, v in T[EL] + T["EE"] if k in idx) + 0.5,
                  f"Töötus {k0[5:]}.{k0[:4]}–{kuu[5:]}.{kuu[:4]}: Eesti {pr(t_ee)}%, EL {pr(t_el)}%"),
         f"12 kuud, ┄ EL {pr(t_el)}%",
         _muutus(t_ee - t_ae, f"{'+' if t_ee >= t_ae else '−'}{pr(abs(t_ee - t_ae))} p aastaga", "põhjust kuunumber ei ütle"),
         f'<small>{e(tootus_el_koht[0])}</small>', tootus_el_koht[1],
         _vaited(vt["too"], vaated, lahk["too"]),
         menuu("reeglid", f'värbamise suure riskiga süsteemide reeglid alates {kp(kr["kuupaev"])}', "tahtajad"),
         d["une_uuendatud"]),
        ("avalik-sektor", "Avalik sektor", "tehisaru", f'{gk["vaartus"]}%', "uuendajatest kasutas generatiivset tehisaru",
         osariba(float(gk["vaartus"]), 100, silt=f'{gk["vaartus"]}% ehk {gk["lugeja"]} uuendajat {gk["nimetaja"]}-st'),
         f'{gk["lugeja"]} / {gk["nimetaja"]}, OECD 2026',
         _muutus(None, "esimene mõõtmine"),
         '<small class="tv-tuhi">–</small>', ("–", ""),
         _vaited(vt["avalik-sektor"], vaated, lahk["avalik-sektor"]),
         menuu("avalik-sektor", "OECD 8 soovitust", "soovitused"),
         d["oecd_kuupaev"]),
        ("hanked", "Hanked", "aastad", str(h_uus["ai_ja_andmed"]), f'tehisaru- ja andmehanget {h_uus["periood"]} · {pr(h_uus["osa"])}% kõigist',
         vahvel(h_uus["osa"], f'{pr(h_uus["osa"])}% kõigist hangetest'),
         "100 ruutu = kõik hanked",
         _muutus(None, "aastaid veel ei võrrelda", "klassifikaator uueneb pärast pimekontrolli"),
         '<small class="tv-tuhi">–</small>', ("–", ""),
         _vaited(vt["hanked"], vaated, lahk["hanked"]),
         # Kadri 26.11.2026 (nõrgad numbrid): märki ei panda sihiga ühele ribale. Hankija märge, hangete arv ja eelarve annavad
         # eri arvu ning sihi ühik on kontrollimata (hanked.html#innovatsioon).
         menuu("hanked", f'innovatsioonihangete siht {pr(INN_SIHT, 0)}% (2027); hankija märkega {pr(inn["innovatsioonimark_osakaal"])}% ({inn["aasta"]}), mõõtmisviis kontrollimata', "innovatsioon"),
         HL["seis"]["kuupaev"]),
    ]
    viimane = max(r[-1] for r in R)

    laud, tel = [], []
    for tid, nimi, ank, arv, sel, kulg, kulg_all, muutus, el, el_tel, (v_html, _), siht, kuup in R:
        nimi_l = menuu(tid, nimi)
        arv_l = menuu(tid, arv, ank).replace("<a ", '<a class="tv-arv" ', 1)
        laud.append(
            f'<tr><th scope="row">{nimi_l}</th>'
            f'<td class="tv-num">{arv_l}<small>{e(sel)}</small></td>'
            f'<td class="tv-kulg">{kulg}<small>{e(kulg_all)}</small></td>'
            f'<td class="tv-mu">{muutus}</td><td class="tv-el">{el}</td><td class="tv-va">{v_html}</td>'
            f'<td class="tv-si">{siht}</td><td class="tv-vr">{_varskus(kuup, viimane)}</td></tr>')
        tel.append(
            f'<details class="tv-r"><summary><span class="tv-t">{e(nimi)}</span>'
            f'<span class="tv-n"><b>{arv}</b><small>{e(sel)}</small></span><span class="tv-k">{kulg}</span>'
            + (f'<span class="tv-ko"><b>{e(el_tel[0])}</b><small>{e(el_tel[1])}</small></span></summary>' if el_tel[0] != "–" else '<span class="tv-ko"><small>–</small></span></summary>')
            + f'<dl><dt>Kulg</dt><dd>{e(kulg_all)}</dd><dt>Muutus</dt><dd>{muutus}</dd><dt>Väited</dt><dd>{v_html}</dd>'
            f'<dt>Siht ja reeglid</dt><dd>{siht}</dd><dt>Värskus</dt><dd>{_varskus(kuup, viimane)}</dd></dl>'
            f'<p class="tv-ava">{menuu(tid, "Ava teema " + nimi + " →")}</p></details>')

    sec = f"""
<section class="pn sp12 tv" id="teemad" aria-labelledby="h-teemad">
  <div class="pn-h"><h2 id="h-teemad"><span class="kys">Mis on iga teema seis?</span> <b>Viis teemat, igaüks ühel real</b></h2></div>
  <p class="ps">Teema nimi viib teema lehele. Iga rida on oma skaalal. <span class="tv-lg ee"></span> Eesti, <span class="tv-lg eu"></span> ELi keskmine, <span class="tv-lg siht"></span> siht. Koht ELis on uusima Eurostati aasta kohta.</p>
  <div class="tbl tv-laud"><table><caption class="peidus">Teemade seis</caption>
  <thead><tr><th scope="col">Teema</th><th scope="col">Praegu</th><th scope="col">Kulg</th><th scope="col">Muutus</th><th scope="col">Koht ELis</th><th scope="col">Väited</th><th scope="col">Siht ja reeglid</th><th scope="col">Värskus</th></tr></thead>
  <tbody>{"".join(laud)}</tbody></table></div>
  <div class="tv-tel"><div class="tv-pea" aria-hidden="true"><span>Teema</span><span>Praegu</span><span>Kulg</span><span>Koht</span></div>{"".join(tel)}</div>
  <p class="allikas">Värske = avaldatud kuni {VARSKE_PAEVI} päeva enne kõige uuemat ({kp(viimane)}). Iga numbri allikas on teema lehel numbri juures.</p>
</section>"""
    return sec, R


# ---------------------------------------------------------------- ajajoon

def ajajoon(voog, tulevad, tana, w=900, h=96, paevi_tagasi=60, paevi_ette=400):
    """Möödunud kanded vasakul, tulevad tähtajad paremal, täna vahel. voog: [(iso, liik, tekst, url)]; tulevad: [(iso, tekst, "el"|"ee")]."""
    t0 = tana - datetime.timedelta(days=paevi_tagasi)
    keskel = w * 0.42

    def X(dd):
        if dd <= tana:
            return 10 + (dd - t0).days / paevi_tagasi * (keskel - 10)
        return keskel + min(paevi_ette, (dd - tana).days) / paevi_ette * (w - keskel - 14)
    out = [f'<line class="tv-aax" x1="8" x2="{w - 8}" y1="56" y2="56"/>',
           f'<line class="tv-tana" x1="{keskel:.1f}" x2="{keskel:.1f}" y1="22" y2="84"/>',
           f'<text class="tv-tt" x="{keskel:.1f}" y="14" text-anchor="middle">täna {kp(tana.isoformat())}</text>',
           f'<text class="tv-at" x="10" y="88">{kp(t0.isoformat())}</text>']
    virn = {}
    for iso, liik, tekst, _ in voog:
        dd = datetime.date.fromisoformat(iso[:10])
        if dd < t0 or dd > tana:
            continue
        k = virn[round(X(dd) / 12)] = virn.get(round(X(dd) / 12), -1) + 1
        out.append(f'<circle class="tv-a{"n" if liik == "uus number" else "v"}" cx="{X(dd):.1f}" cy="{56 - min(k, 2) * 12}" r="5"><title>{kp(iso)}: {tekst}</title></circle>')
    viimane_x = 0
    for iso, tekst, k in tulevad:
        dd = datetime.date.fromisoformat(iso)
        x = X(dd)
        out.append(f'<rect class="tv-a{k}" x="{x - 4:.1f}" y="52" width="8" height="8" transform="rotate(45 {x:.1f} 56)"><title>{kp(iso)}: {e(tekst)}</title></rect>')
        if x - keskel > 44 and x - viimane_x > 70:
            out.append(f'<text class="tv-at" x="{min(x, w - 40):.1f}" y="80" text-anchor="middle">{kp(iso)}</text>')
            viimane_x = x
    return f'<svg class="tv-aeg" viewBox="0 0 {w} {h}" width="100%" role="img" aria-label="Möödunud kanded ja tulevad tähtajad; sama info on all loendis">{"".join(out)}</svg>'


def tulevad_tahtajad(A, tana):
    """ELi tehisaru määruse tähtajad (otsused) ja Eesti tähtajad (uudised, teema riik), tänasest edasi."""
    iso = tana.isoformat()
    el = [(o["kuupaev"] if len(o["kuupaev"]) == 10 else o["kuupaev"] + "-01", o["nimi"], "el") for o in A["otsused"]]
    ee = [(r["tahtaeg"], r["pealkiri"], "ee") for r in A.get("uudised", []) if r.get("teema") == "riik" and r.get("tahtaeg")]
    return sorted(x for x in el + ee if x[0] > iso)


def aja_jaotis(voog, tulevad, tana, vaated):
    """voog: [(iso, liik, silt, tekst html, url)] nagu avalehel (uuemad ees)."""
    d = lambda iso: datetime.date.fromisoformat(iso[:10])  # noqa: E731
    hiljuti = [r for r in voog if 0 <= (tana - d(r[0])).days <= VOO_PAEVI]
    jargmine = tulevad[0] if tulevad else None
    lyh = [(r[0], r[1], r[3], r[4]) for r in voog]
    li1 = "".join(f'<li><span class="tv-lg {"n" if r[1] == "uus number" else "v"}"></span><time datetime="{r[0][:10]}">{kp(r[0])}</time>'
                  f'<span>{f"<a href={chr(34)}{e(r[4])}{chr(34)}>{r[3]}</a>" if r[4] else r[3]}</span></li>' for r in hiljuti[:5])
    li2 = "".join(f'<li><span class="tv-lg t{k}"></span><time datetime="{iso}">{kp(iso)}</time><span>{e(t)}</span></li>' for iso, t, k in tulevad[:3])
    return f"""
<section class="pn sp12 tv" id="muutus" aria-labelledby="h-muutus">
  <div class="pn-h"><h2 id="h-muutus"><span class="kys">Mis muutus ja mis tuleb?</span> <b>{len(hiljuti)} {"kanne" if len(hiljuti) == 1 else "kannet"} {VOO_PAEVI} päevaga{f", järgmine tähtaeg {kp(jargmine[0])}" if jargmine else ""}</b></h2></div>
  <p class="ps"><span class="tv-lg n"></span> uus number · <span class="tv-lg v"></span> kontrollitud väide · <span class="tv-lg tel"></span> ELi tehisaru määruse tähtaeg · <span class="tv-lg tee"></span> Eesti tähtaeg</p>
  <div class="tv-aeg-lai">{ajajoon(lyh, tulevad, tana)}</div>
  <div class="tv-loendid"><div><h3>Mis muutus ({VOO_PAEVI} päeva)</h3><ul>{li1 or "<li>Viimase 30 päeva jooksul uusi kandeid pole.</li>"}</ul></div>
  <div><h3>Mis tuleb</h3><ul>{li2 or "<li>Tulevaid tähtaegu pole.</li>"}</ul></div></div>
  <p class="allikas">Kogu loend: {link(vaated, "kas-tosi", "Usaldus › Värskus", "muutused")}. Tähtajad: {link(vaated, "reeglid", "Reeglid ja otsused", "tahtajad")}. Uudised: {link(vaated, "uudised", "Uudised")}.</p>
</section>"""
