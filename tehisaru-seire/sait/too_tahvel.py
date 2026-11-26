"""Töö lehe töölaud (Kadri 17.11.2026 valis näidistest „A ja C koos“).

Leht algab tahvliga (kuus Eesti küsimust, iga rida üks pilk), siis tõendikaart (küsimus × koht, iga lahter näitab
uuringu liiki) ja hõive muutus ametite avatuse astme järgi. Praegused plokid on lehe lõpus kokkupandult.

Kadri 25.11.2026 (oluline enne valikulist): tahvli rida vastab sõnaga, number on selle kõrval ja märkus avaneb real.
Tahvli all on nähtaval töötus kuu kaupa, koondamised ja hõive avatuse astme järgi; tõendikaart on üksikasjade esimene rida.
"""
from andmekiht import EL, AndmeViga
from avaleht_tahvel import kulujoon, vahvel as vahvel100
from abi import a
from komponendid import allikarida, e, kp, pr
import teema_tahvel as tt

NB = " "
KUUD = ["jaanuar", "veebruar", "märts", "aprill", "mai", "juuni", "juuli", "august", "september", "oktoober", "november", "detsember"]
# Mida ettevõte tehisaru kohta ütles: s = nimetas põhjusena, m = mainis muul moel, t = ei maininud või eitas (sama mis koondamiste ribadel)
ROLL = {"otsene": "s", "osaline": "s", "kaudne": "m", "tulevikus": "m", "ei_pohjus": "t", "ei_mainita": "t"}


def _arvt(n):
    return f"{n:,.0f}".replace(",", NB)


def mt(x):
    return f'{"+" if x >= 0 else "−"}{pr(abs(x))}%'


def _koondatud(r):
    return r["arv_eestis"] if r.get("arv_eestis") is not None else r.get("arv_ulem")


class Andmed:
    """Tahvli, tõendikaardi ja astmete pildi ühised numbrid; iga number tuleb samast failist mis lehe plokis."""

    def __init__(self, A):
        from lehed_ulevaade import LUHI, UNE_UUENDATUD, _kv, _loe, tootus
        self.A, self.T, self.U = A, A["tooelu"], A["uuringud"]
        self.une_uuendatud = UNE_UUENDATUD
        TM = tootus()
        self.tm = TM
        self.kuu, self.t_ee = TM["EE"][-1]
        self.t_el = dict(TM[EL])[self.kuu]
        self.t_ee0 = dict(TM["EE"]).get(f"{int(self.kuu[:4]) - 1}{self.kuu[4:]}")
        # vabad ametikohad, Statistikaamet PAV011
        R = _loe("vabad-ametikohad.csv")
        arv = {(r["nimi"], r["periood"]): float(r["vaartus"]) for r in R if r["tabel"] == "PAV011" and r["naitaja"] == "Vabade ametikohtade arv"}
        KOKKU = "Kokku – kõik tegevusalad"
        self.vab = sorted(((p, v) for (n, p), v in arv.items() if n == KOKKU), key=lambda x: _kv(x[0]))
        self.v_kv, self.v_n = self.vab[-1]
        aa, _ = _kv(self.v_kv)
        v0 = arv.get((KOKKU, f'{aa - 1} {self.v_kv.split(" ", 1)[1]}'))
        if v0 is None:
            raise AndmeViga("vabad-ametikohad.csv: aasta varasema kvartali rida puudub")
        self.v_muut = (self.v_n - v0) / v0 * 100
        alad = sorted(((n, v) for (n, p), v in arv.items() if p == self.v_kv and n != KOKKU), key=lambda x: -x[1])
        self.v_enim = [LUHI.get(n, n).lower() for n, _ in alad[:2]]
        self.v_uuend = R[0]["uuendatud"]
        # koondamised (uudised)
        self.ko = A["koondamised"]
        self.kj = self.ko["juhtumid"]
        for r in self.kj:
            if r["roll"] not in ROLL:
                raise AndmeViga(f"koondamised_ee.json: tundmatu roll {r['roll']} ({r['id']})")
        self.k_osa = {"s": 0, "m": 0, "t": 0}
        for r in self.kj:
            self.k_osa[ROLL[r["roll"]]] += _koondatud(r) or 0
        self.k_kokku = sum(self.k_osa.values())
        self.k_otsene = sum(r["roll"] == "otsene" for r in self.kj)
        self.k_pohjusena = [r for r in self.kj if r["roll"] in ("otsene", "osaline")]
        # tehisaru- ja andmetööde kuulutused (CV.ee)
        ak = A["ai_kuulutused"]
        g = ak["ruhmad"]
        self.ak, self.ak_n = ak, ak["kuulutusi_kokku"]
        self.ak_amet = g["ai_amet"]["arv"] + g["andmeamet"]["arv"]
        self.ak_osk = g["ai_oskus"]["arv"]
        self.ak_harju = sum(m["arv"] for k in ("ai_amet", "andmeamet") for m in g[k]["maakonnad"] if m["nimi"] == "Harjumaa")
        # kokkupuude ja hõive muutus (ILO indeks, Eurostat lfsa_egai2d)
        K = A["kokkupuude"]
        self.K = K
        self.A0, self.A1 = 2022, max(K["aeg"][("EE", "T")])
        self.ee_av, self.ee_mu = self.mu("EE", "avatud"), self.mu("EE", "muud")
        self.el_av, self.el_mu = self.mu(EL, "avatud"), self.mu(EL, "muud")
        self.ee_k, self.el_k = self.mu("EE", "korge"), self.mu(EL, "korge")
        tu = self.T["tulevik"]["tootus_ee"]
        self.t2030 = next(r for r in tu["read"] if r["aasta"] == 2030)
        self.rm = self.U[tu["uuring"]]

    def mu(self, geo, osa):
        g = self.K["aeg_uhtlane"][(geo, "T")]
        return (g[self.A1][osa] / g[self.A0][osa] - 1) * 100


# ---------------------------------------------------------------- tahvli väikesed pildid

def kv_tulbad(read, w=150, h=42):
    """Kvartalite tulbad nullist, viimane fookusvärviga."""
    m = max(v for _, v in read)
    bw = (w - 4) / len(read)
    out = []
    for i, (p, v) in enumerate(read):
        hh = v / m * (h - 14)
        out.append(f'<rect class="{"tv-v" if i == len(read) - 1 else "tv-bg"}" x="{2 + i * bw:.1f}" y="{h - 12 - hh:.1f}" '
                   f'width="{bw - 3:.1f}" height="{hh:.1f}" rx="1.5"><title>{e(p)}: {_arvt(v)}</title></rect>')
    out.append(f'<text class="tt-t" x="2" y="{h - 1}">{read[0][0][:4]}</text><text class="tt-t" x="{w - 2}" y="{h - 1}" text-anchor="end">{read[-1][0][:4]}</text>')
    return (f'<svg class="tt-svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-label="Vabad ametikohad kvartalite kaupa: '
            + ", ".join(f"{p} {_arvt(v)}" for p, v in read) + f'">{"".join(out)}</svg>')


def jaotusriba(osad, silt, w=150):
    """Üks riba 0–100%, järjestikused osad [(klass s|m|t, %)]. Osad on sama terviku osad, mitte eri mõõdikud."""
    if sum(v for _, v in osad) > 100.5:
        raise AndmeViga(f"Jaotusriba „{silt}“: osade summa on üle 100%")
    x, out = 0.0, [f'<rect class="tv-bg" x="0" y="4" width="{w}" height="8" rx="2"/>']
    for k, v in osad:
        out.append(f'<rect class="tt-jr {k}" x="{x:.1f}" y="4" width="{v / 100 * w:.1f}" height="8"/>')
        x += v / 100 * w
    return f'<svg class="tv-osa" viewBox="0 0 {w} 16" width="{w}" height="16" role="img" aria-label="{e(silt)}">{"".join(out)}</svg>'


def hoive_tapid(D, w=150, h=44):
    """Hõive muutus kõige avatumates ametites (aste 3–4): Eesti täpp üleval, ELi ring all, nulljoon vahel."""
    lo, hi = -2, 6
    X = lambda v: 8 + (min(hi, max(lo, v)) - lo) / (hi - lo) * (w - 40)  # noqa: E731
    out = [f'<line class="tv-ax" x1="{X(0):.1f}" x2="{X(0):.1f}" y1="2" y2="{h - 2}"/>']
    for i, (nimi, v, f) in enumerate([("EE", D.ee_k, "f"), ("EL", D.el_k, "r")]):
        yy = 12 + i * 20
        out.append(f'<line class="tv-l{f}" x1="{X(0):.1f}" x2="{X(v):.1f}" y1="{yy}" y2="{yy}" stroke-width="2"/>'
                   + (f'<circle class="tv-pf" cx="{X(v):.1f}" cy="{yy}" r="3.5"/>' if f == "f" else f'<circle class="tt-ring" cx="{X(v):.1f}" cy="{yy}" r="3.5"/>')
                   + f'<text class="tt-t{" b" if f == "f" else ""}" x="{max(X(v), X(0)) + 8:.1f}" y="{yy + 4}">{nimi}</text>')
    return (f'<svg class="tt-svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-label="Hõive muutus {D.A0}–{D.A1} '
            f'kõige avatumates ametites: Eesti {mt(D.ee_k)}, EL {mt(D.el_k)}">{"".join(out)}</svg>')


# Sõnaga vastuse piirid (25.11.2026). Vastus arvutatakse andmetest; piir on kirjas siin, et seda saaks muuta ühes kohas.
PIIR_TOOTUS_PP = 0.3      # töötuse määra muutus aastaga, protsendipunkti
PIIR_VABAD_PR = 5         # vabade ametikohtade muutus aastaga, %
PIIR_HOIVE_PR = (0.5, 2)  # hõive muutus: alla esimese = sama palju, alla teise = veidi


def sona_tootus(D):
    if D.t_ee0 is None:
        raise AndmeViga("Tahvli vastus „Kas töötus kasvab?“ vajab aasta varasemat kuud")
    d = D.t_ee - D.t_ee0
    return "Jah" if d >= PIIR_TOOTUS_PP else ("Ei, väheneb" if d <= -PIIR_TOOTUS_PP else "Püsib samal tasemel")


def sona_vabad(D):
    return "Jah" if D.v_muut <= -PIIR_VABAD_PR else ("Ei, rohkem" if D.v_muut >= PIIR_VABAD_PR else "Umbes sama palju")


def sona_koondamised(D):
    """Vastus ütleb, mida ettevõtted ise teatasid; ettevõtte selgitus ei tõenda põhjust."""
    n = len(D.k_pohjusena)
    return "Ükski ettevõte ei öelnud nii" if n == 0 else ("Mõni ettevõte ütleb nii" if n * 2 < len(D.kj) else "Enamik ettevõtteid ütleb nii")


def sona_oskus(osa):
    return "Väga harva" if osa < 1 else ("Harva" if osa < 5 else ("Osas kuulutustes" if osa < 20 else "Sageli"))


def sona_hoive(v):
    vahe, palju = PIIR_HOIVE_PR
    if abs(v) < vahe:
        return "Sama palju"
    return ("Jah" if v <= -palju else "Veidi vähem") if v < 0 else "Ei, rohkem"


def read(D):
    TM, K = D.tm, D.K
    kuu = D.kuu
    ee_kuud = dict(TM["EE"])
    pohjus = D.k_pohjusena
    if not pohjus:
        k_lause = "Ükski ettevõte ei nimetanud tehisaru koondamise põhjusena"
    else:
        k_lause = (f'Tehisaru nimetas põhjusena {len(pohjus)} {"ettevõte" if len(pohjus) == 1 else "ettevõtet"} '
                   f'({", ".join(e(r["ettevote"]) for r in pohjus)}); otsese põhjusena {D.k_otsene if D.k_otsene else "mitte ükski"}')
    ak_osa = (D.ak_amet + D.ak_osk) / D.ak_n * 100
    return [
        dict(kys="Kas töötus kasvab?", ank="tootus-kuud", ava="Vaata töötuse graafikut", sona=sona_tootus(D), arv=f"{pr(D.t_ee)}%",
             all=f'{KUUD[int(kuu[5:]) - 1]} {kuu[:4]}, aasta varem {pr(D.t_ee0)}%',
             pilt=kulujoon([([(i, v) for i, (k, v) in enumerate(TM[EL]) if k in ee_kuud], "r"), ([(i, v) for i, (_, v) in enumerate(TM["EE"])], "f")],
                           5, 9, f"Töötus kuu kaupa: Eesti {pr(D.t_ee)}%, EL {pr(D.t_el)}%", w=150, h=40),
             mrk=f'ELis {pr(D.t_el)}% (pildil punktiirjoon). Kuunumber ei ütle, kas põhjus on tehisaru.',
             liik="mõõdetud", allikas="Eurostat une_rt_m", kuup=f"uuendatud {kp(D.une_uuendatud)}"),
        dict(kys="Kas tööandjad otsivad vähem?", ank="vabad-kohad", ava="Ava vabade ametikohtade andmed", sona=sona_vabad(D), arv=_arvt(D.v_n),
             all=f'vaba ametikohta, {D.v_kv.replace(" kvartal", " kv")}; {abs(D.v_muut):.0f}% {"vähem" if D.v_muut < 0 else "rohkem"} kui aasta varem',
             pilt=kv_tulbad(D.vab),
             mrk=f'Enim vabu kohti: {e(D.v_enim[0])} ja {e(D.v_enim[1])}.',
             liik="mõõdetud", allikas="Statistikaamet PAV011", kuup=kp(D.v_uuend)),
        dict(kys="Kas koondatakse tehisaru tõttu?", ank="koondamised", ava="Vaata koondamisi ettevõtte kaupa", sona=sona_koondamised(D),
             arv=f'{len(pohjus)} {"koondamine" if len(pohjus) == 1 else "koondamist"} {len(D.kj)}-st',
             all=f'{D.k_osa["s"]} töökohta umbes {D.k_kokku}-st',
             pilt=jaotusriba([(k, D.k_osa[k] / D.k_kokku * 100) for k in ("s", "m", "t")],
                             f'{D.k_kokku} töökohast {D.k_osa["s"]} puhul nimetati tehisaru põhjusena, {D.k_osa["m"]} puhul mainiti muul moel'),
             mrk=f"{k_lause}. Ettevõtte enda selgitus ei tõenda põhjust. Nimekiri pole täielik.",
             liik="uudised", allikas="Eesti uudised", kuup=f'viimane teade {kp(max(r["kuupaev"] for r in D.kj))}'),
        dict(kys="Kas tehisaruoskust otsitakse?", ank="ai-kuulutused", ava="Ava tehisaru- ja andmetööde kuulutused", sona=sona_oskus(ak_osa),
             arv=f"{pr(ak_osa)}%", all=f"{D.ak_amet + D.ak_osk} kuulutust {_arvt(D.ak_n)}-st",
             pilt=vahvel100(ak_osa, f"{D.ak_amet + D.ak_osk} kuulutust {D.ak_n}-st, {pr(ak_osa)}%"),
             mrk=(f"{D.ak_amet} on AI- või andmeametid, veel {D.ak_osk} muu ameti kuulutust mainib tehisaru. "
                  f"{pr(D.ak_harju / D.ak_amet * 100, 0)}% AI- ja andmetöödest on Harjumaal. Liigitus märksõnade järgi."),
             liik="arvutatud", allikas="CV.ee kuulutused", kuup=kp(D.ak["uuendatud"][:10])),
        dict(kys="Kui paljud on avatud ametites?", ank="kokkupuude", ava="Ava ametite avatuse andmed", sona=f'Umbes iga {round(100 / K["korge"])}. töötaja',
             arv=f'{pr(K["korge"], 0)}%', all="kõige avatumates ametites (aste 3–4), 2022",
             pilt=jaotusriba([("s", K["korge"]), ("m", K["avatud"] - K["korge"])], f'Aste 3–4 {pr(K["korge"], 0)}%, aste 1–2 {pr(K["avatud"] - K["korge"], 0)}%'),
             mrk=f'Kokku {pr(K["avatud"], 0)}% töötajatest on ametites, mille ülesandeid generatiivne tehisaru puudutab. Kokkupuude ei ole mõju.',
             liik="arvutatud", allikas="ILO indeks, Statistikaamet", kuup="2022"),
        dict(kys="Kas kõige avatumates ametites on tööd vähem?", ank="astmed", ava="Vaata hõivet avatuse astme järgi", sona=sona_hoive(D.ee_k),
             arv=mt(D.ee_k), all=f"hõive astmes 3–4, {D.A0}–{D.A1}; ELis {mt(D.el_k)}",
             pilt=hoive_tapid(D),
             mrk=(f'Kõigis avatud ametites kokku (aste 1–4) {mt(D.ee_av)}, teistes ametites {mt(D.ee_mu)}. '
                  'Kirjeldus, mitte põhjus; Eesti valim on väike.'),
             liik="arvutatud", allikas="Eurostat lfsa_egai2d", kuup="uuendatud 30.10.2026"),
    ]


def tahvel(D):
    """Kadri 25.11.2026: tahvli ees ei ole lugemisjuhist ega all loendurite rida; jääb üks hoiatus, mis muudab lugemist."""
    return tt.vastustahvel("tahvel", "Mida näitavad Eesti andmed?", "Ükski rida ei näita, kas muutuse põhjus on tehisaru.", read(D))


# ---------------------------------------------------------------- tõendikaart (näidis A)

# lahtri märk: p = võrdleb rühmi (võib näidata põhjust), k = kirjeldab, h = hinnang või prognoos
LIIGID = {"katse": ("p", "katse"), "loomulik_katse": ("p", "loomulik katse"), "registriandmed": ("p", "registriandmed"),
          "kirjeldav": ("k", "kirjeldav"), "kusitlus": ("k", "küsitlus"), "statistika": ("k", "statistika"), "uudised": ("k", "uudised"),
          "hinnang": ("h", "hinnang"), "prognoos": ("h", "prognoos")}
KOHAD = ["Eesti", "Euroopa", "USA", "Mujal"]


def lahter(liik=None, tulemus="", allikas="", url=""):
    if not liik:
        return ("0", '<td class="tk-0"><span class="tk-m" aria-hidden="true"></span><span class="tk-r">uuringut pole</span></td>')
    k, nimi = LIIGID[liik]
    src = a(url, allikas) if url else e(allikas)
    return (k, f'<td class="tk-{k}"><span class="tk-m" aria-hidden="true"></span><span class="tk-l">{e(nimi)}</span>'
               f'<b class="tk-r">{tulemus}</b><small>{src}</small></td>')


def _uu(U, uid, eesliide=""):
    """Uuringu lahter: liik uuringu meetodist, allikas „Autor jt aasta“ koos lingiga."""
    u = U[uid]
    au = u["autorid"].split(" (")[0]
    nimi = au.split(",")[0].split(" ja ")[0] + (" jt" if "," in au or " jt" in au or " ja " in au else "")
    return dict(liik=u["meetod"], allikas=f"{eesliide}{nimi} {u['aasta']}", url=u["url"])


def sec_toendid(D):
    T, U = D.T, D.U
    can = next(r for r in T["tookohad"] if r["uuring"] == "canaries2026")
    vabak = [r for r in T["tookohad"] if r["uuring"] in ("demirci2025", "teutloff2025")]
    ch = T["tulevik"]["koondamise_pohjused"]
    ai_t = next(r for r in ch["read"] if r["nimi"] == "Tehisaru")["teateid"]
    kz = T["kiirus"]
    kmax, kmin = max(r["kiiremini"] for r in kz), min(r["kiiremini"] for r in kz)
    ced = U["cedefop2026"]
    if "4%" not in ced["leid"]:
        raise AndmeViga("Tõendikaart: Cedefopi leius pole enam hõive kasvu 4%")
    ilo_m = next(r["protsent"] for r in T["avatus"]["riigid"] if r["nimi"] == "Maailm")
    bryn = U["brynjolfsson2023"]
    if "14%" not in bryn["leid"]:
        raise AndmeViga("Tõendikaart: Brynjolfsson 2023 leius pole enam 14%")
    vahter = U["vahter2026"]
    L = lambda d, tulemus: lahter(d["liik"], tulemus, d["allikas"], d["url"])  # noqa: E731
    yks = len(D.k_pohjusena)
    # (küsimus, ankur, kas töökohtade küsimus, [Eesti, Euroopa, USA, Mujal])
    R = [
        ("Kas tööd kaob kogu tööturul?", "maailm", True,
         [lahter("statistika", f"töötus {pr(D.t_ee)}%", "Eurostat"), L(_uu(U, "humlum2025", "Taani · "), "muutust pole"),
          L(_uu(U, "yale2025"), "muutust pole"), lahter()]),
        ("Kas avatud ametites on tööd vähem?", "hoive", True,
         [lahter("statistika", f"{mt(D.ee_av)} vs {mt(D.ee_mu)}", f"Eurostat, {D.A0}–{D.A1}"),
          lahter("statistika", f"{mt(D.el_av)} vs {mt(D.el_mu)}", "Eurostat, EL"),
          L(_uu(U, "canaries2026"), f'noored {e(can["muutus"])}'), lahter()]),
        ("Kas vabakutselistel on tööd vähem?", "maailm", True,
         [lahter(), lahter(), lahter(),
          lahter("registriandmed", " ja ".join(e(r["muutus"]) for r in vabak), f"platvormid, {max(U[r['uuring']]['aasta'] for r in vabak)}")]),
        ("Kas koondamise põhjus on tehisaru?", "koondamised", True,
         [lahter("uudised", f'{"üks" if yks == 1 else yks} juhtum {len(D.kj)}-st', "Eesti uudised"), lahter(),
          L(_uu(U, "challenger2026"), f"{pr(ai_t / ch['kokku'] * 100, 0)}% teadetest"), lahter()]),
        ("Kas töö läheb kiiremaks?", "ulesanded", True,
         [lahter(), lahter(), L(_uu(U, "brynjolfsson2023"), "klienditoes +14%"),
          lahter("katse", f"{'+' if kmin >= 0 else '−'}{pr(abs(kmin), 0)}% … +{pr(kmax, 0)}%", f"{len(kz)} katset")]),
        ("Kas tootlikkus kasvab?", "eesti", False,
         [L(_uu(U, "vahter2026"), "ilma töökorralduse muutuseta ei"), lahter(), lahter(), lahter()]),
        ("Kui suur osa tööst on avatud?", "kokkupuude", True,
         [lahter("hinnang", f'{pr(D.K["avatud"], 0)}% töötajatest', "ILO indeks, Statistikaamet"),
          lahter("hinnang", f'{pr(D.K["el"][EL]["avatud"], 0)}% (EL)', "ILO indeks, Eurostat"), lahter(),
          L(_uu(U, "ilo2025"), f"{ilo_m}% maailmas")]),
        ("Mis saab töötusest edasi?", "tulevik", True,
         [lahter("prognoos", f'{pr(D.t2030["protsent"])}% aastal 2030', "Rahandusministeerium", D.rm["url"]),
          lahter("prognoos", "hõive +4% 2035", f'Cedefop {ced["aasta"]}', ced["url"]), lahter(), lahter()]),
    ]
    if "registriandmed" not in vahter["meetod"]:
        raise AndmeViga("Tõendikaart: vahter2026 meetod pole enam registriandmed")
    ee_too = [r[3][0][0] for r in R if r[2]]
    if "p" in ee_too:
        raise AndmeViga("Tõendikaardi pealkiri ütleb, et Eesti kohta pole töökohtade küsimustes rühmi võrdlevat uuringut; nüüd on")
    ee_p = sum(1 for r in R if r[3][0][0] == "p")
    ridu = "".join(f'<tr><th scope="row"><a href="#{ank}">{e(k)}</a></th>{"".join(c for _, c in cc)}</tr>' for k, ank, _, cc in R)
    return f"""
<section class="jaotis tk" id="toendid" aria-labelledby="h-toendid">
  <header>
    <h2 id="h-toendid"><span class="kys">Kus on tõendeid?</span> <b>Eesti kohta on töökohtade küsimustes ainult statistika ja hinnangud</b> ¦ põhjust näitavad uuringud on Taanist, USAst ja platvormidelt</h2>
    <p class="alam">Iga lahter on parim uuring, mille seire selle küsimuse ja koha kohta leidis. Täis ruut: uuring võrdleb rühmi ja võib näidata põhjust. Poolik ruut: kirjeldab, mis juhtus, aga põhjust ei näita. Ring: hinnang või prognoos. Eesti veerus on {ee_p} täis {"ruut" if ee_p == 1 else "ruutu"}, see on tootlikkuse kohta.</p>
  </header>
  <div class="tbl tk-laud"><table><caption class="peidus">Tõendid küsimuse ja koha järgi</caption>
    <thead><tr><th scope="col">Küsimus</th><th scope="col">Eesti</th><th scope="col">Euroopa</th><th scope="col">USA</th><th scope="col">Mujal: platvormid, katsed, maailm</th></tr></thead>
    <tbody>{ridu}</tbody></table></div>
  <p class="tk-leg"><span><i class="tk-m p"></i>võrdleb rühmi</span><span><i class="tk-m k"></i>kirjeldab</span><span><i class="tk-m h"></i>hinnang või prognoos</span><span><i class="tk-m z"></i>uuringut pole</span></p>
  <p class="allikas">Eri lahtrite numbreid ei võrrelda: igal uuringul on oma rühm, periood ja mõõt. Rida viib ploki juurde, kus on kõik allikad.</p>
</section>"""


# ---------------------------------------------------------------- hõive avatuse astme järgi (näidis C)

ASTE = [("4", "Aste 4, kõige avatum"), ("3", "Aste 3"), ("2", "Aste 2"), ("1", "Aste 1"), ("minimaalne", "Minimaalne"), ("ei", "Ei puutu kokku")]


def _astmed_svg(D, w, h, kitsas):
    g1 = D.K["aeg_uhtlane"][("EE", "T")][D.A1]
    lo, hi = -4, 10
    ml, bw = 190, 120
    xl = 118 if kitsas else ml + bw + 30
    X = lambda v: xl + (min(hi, max(lo, v)) - lo) / (hi - lo) * (w - xl - (24 if kitsas else 60))  # noqa: E731
    maxn = max(g1[k] for k, _ in ASTE)
    o = ([] if kitsas else [f'<text class="tt-t" x="{ml}" y="14">Eesti, tuh hõivatut {D.A1}</text>'])
    o.append(f'<text class="tt-t" x="{X(0):.1f}" y="14" text-anchor="middle">Hõive muutus {D.A0}–{D.A1}</text>')
    for v in range(lo, hi + 1, 4 if kitsas else 2):
        o.append(f'<line class="tv-ax" x1="{X(v):.1f}" x2="{X(v):.1f}" y1="24" y2="{h - 22}" opacity="{1 if v == 0 else .4}"/>'
                 f'<text class="tt-t" x="{X(v):.1f}" y="{h - 6}" text-anchor="middle">{"+" if v > 0 else ""}{v}%</text>')
    for i, (k, nimi) in enumerate(ASTE):
        yy = 46 + i * 40
        f = k in ("4", "3")
        o.append(f'<text class="tt-t tt-as{" b" if f else ""}" x="0" y="{yy + 4}">{e(nimi.split(",")[0] if kitsas else nimi)}</text>')
        if not kitsas:
            o.append(f'<rect class="{"tv-v" if f else "tv-bg"}" x="{ml}" y="{yy - 6}" width="{g1[k] / maxn * bw:.1f}" height="12" rx="2"/>'
                     f'<text class="tt-t" x="{ml + g1[k] / maxn * bw + 4:.1f}" y="{yy + 4}">{pr(g1[k], 0)}</text>')
        ve, vl = D.mu("EE", k), D.mu(EL, k)
        o.append(f'<line class="tv-lr" x1="{X(ve):.1f}" x2="{X(vl):.1f}" y1="{yy}" y2="{yy}" stroke-width="2"/>'
                 f'<circle class="tt-elp" cx="{X(vl):.1f}" cy="{yy}" r="5"><title>EL, {e(nimi)}: {mt(vl)}</title></circle>'
                 f'<circle class="tv-pf" cx="{X(ve):.1f}" cy="{yy}" r="6"><title>Eesti, {e(nimi)}: {mt(ve)}</title></circle>')
        vas = ve < vl
        o.append(f'<text class="tt-t b f" x="{X(ve) + (-10 if vas else 10):.1f}" y="{yy - 9}" text-anchor="{"end" if vas else "start"}">{mt(ve)}</text>')
    y3 = 46 + 40
    o.append(f'<text class="tt-t" x="{X(D.mu(EL, "3")) + 9:.1f}" y="{y3 + 4}">EL</text>')
    return (f'<svg class="tt-svg" viewBox="0 0 {w} {h}" width="100%" role="img" aria-label="Hõive muutus {D.A0}–{D.A1} avatuse astme järgi: '
            + "; ".join(f"{n}: Eesti {mt(D.mu('EE', k))}, EL {mt(D.mu(EL, k))}" for k, n in ASTE) + f'">{"".join(o)}</svg>')


def sec_astmed(D):
    ilo = D.U["ilo2025"]
    if not D.ee_k < 0 < D.el_k:
        raise AndmeViga("Astmete pealkiri ütleb, et kõige avatumates ametites Eesti hõive vähenes ja ELi oma kasvas; andmed seda enam ei näita")
    if not all(D.mu("EE", k) > 0 for k in ("2", "1", "minimaalne", "ei")):
        raise AndmeViga("Astmete pealkiri ütleb, et vähem avatud ametites kasvas Eesti hõive; andmed seda enam ei näita")
    from lehed_ulevaade import EUROSTAT
    return f"""
<section class="jaotis" id="astmed" aria-labelledby="h-astmed">
  <header>
    <h2 id="h-astmed"><span class="kys">Kas kõige avatumates ametites on tööd vähem?</span> Kõige avatumates ametites (aste 3–4) <b>vähenes Eesti hõive {pr(abs(D.ee_k))}%, ELis kasvas {pr(D.el_k)}%</b> ¦ vähem avatud ametites kasvas hõive ka Eestis</h2>
    <p class="alam">Iga rida on ILO avatuse aste. Sinine täpp on Eesti, hall ring EL, {D.A0}–{D.A1}. Tulp näitab, kui palju inimesi selles astmes Eestis töötab. Valim on väike: astmes 4 on muutus alla tuhande inimese.</p>
  </header>
  <figure class="tt-scfig"><div class="tt-sc-lai">{_astmed_svg(D, 720, 300, False)}</div><div class="tt-sc-kitsas" aria-hidden="true">{_astmed_svg(D, 360, 300, True)}</div></figure>
  {allikarida([("Eurostat, lfsa_egai2d", EUROSTAT.format("lfsa_egai2d"), "uuendatud 30.10.2026"), (f"ILO {ilo['aasta']}, kokkupuute indeks", ilo["url"], "")])}
  <p class="allikas">See on kirjeldus, mitte põhjus: Eesti majandus oli 2023–2024 langusel ja see mõjutas harusid eri moodi.</p>
</section>"""
