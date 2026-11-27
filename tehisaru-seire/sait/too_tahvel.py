"""Töö lehe töölaud (Kadri 17.11.2026 valis näidistest „A ja C koos“).

Leht algab tahvliga (kuus Eesti küsimust, iga rida üks pilk), siis tõendikaart (küsimus × koht, iga lahter näitab
uuringu liiki) ja hõive muutus ametite avatuse astme järgi. Praegused plokid on lehe lõpus kokkupandult.

Kadri 25.11.2026 (oluline enne valikulist): tahvli rida vastab sõnaga, number on selle kõrval ja märkus avaneb real.
Tahvli all on nähtaval töötus kuu kaupa, koondamised ja hõive avatuse astme järgi; tõendikaart on üksikasjade esimene rida.
"""
from andmekiht import EL, PA633_URL, AndmeViga, tooalane_hoivatutest, tooalane_kasutus
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
        self.ak_n, self.ak_osk = ak["kuulutusi_kokku"], ak["ruhmad"]["ai_oskus"]["arv"]
        # tööalane kasutus (Statistikaamet / Eurostat), sama kirje mis Inimeste lehel
        self.too = tooalane_kasutus(A)[1]
        # sama küsimus hõivatute seas: tahvli number (jagaja on töötajad, mitte kõik 16–74-aastased)
        self.too_h0, self.too_h = tooalane_hoivatutest(A)
        if self.too_h["aasta"] != self.too["aasta"]:
            raise AndmeViga("Tööalane kasutus: hõivatute ja kõigi 16–74-aastaste number on eri aastast")
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
# Hõive muutus avatuse astmete rühmas: alla selle piiri ei ütle tahvel ega pealkiri, et hõive kasvas või kahanes.
# Rühmas on Eestis umbes 100 000 hõivatut ja number tuleb tööjõu-uuringu valimist. Piir 5% on seire ettevaatlik hinnang
# valimivea suuruse kohta (26.11.2026); Statistikaameti usalduspiire selle rühma kohta pole kontrollitud.
# ELi kohta piiri ei rakendata: sama rühm on ELis üle 20 miljoni hõivatu.
PIIR_HOIVE_PR = 5


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
    # Sõna ei ütle „enamik“ ega „vähesed“: teated on uudistest kogutud, mitte kõigi koondamiste loend (Kadri 26.11.2026)
    return "Ükski ettevõte ei öelnud nii" if n == 0 else ("Üks ettevõte ütleb nii" if n == 1 else "Mõni ettevõte ütleb nii")


def selge_muutus(v):
    return abs(v) >= PIIR_HOIVE_PR


def sona_hoive(v):
    if not selge_muutus(v):
        return "Selget muutust ei ole"
    return "Jah" if v < 0 else "Ei, rohkem"


def teate_ruudud(kj, r=11):
    """Üks ruut teate kohta, vanemast uuemani; värv näitab, mida ettevõte tehisaru kohta ütles. Ei ole osakaal: teated on valik."""
    read = sorted(kj, key=lambda x: x["kuupaev"])
    out = "".join(f'<rect class="tt-jr {ROLL[x["roll"]]}" x="{i * (r + 3)}" y="1" width="{r}" height="{r}" rx="2"><title>{e(x["ettevote"])}, {kp(x["kuupaev"])}</title></rect>'
                  for i, x in enumerate(read))
    n = sum(ROLL[x["roll"]] == "s" for x in read)
    return (f'<svg class="tt-svg" viewBox="0 0 {len(read) * (r + 3)} {r + 2}" width="{len(read) * (r + 3)}" height="{r + 2}" role="img" '
            f'aria-label="Kogutud {len(read)} koondamisteadet ajajärjekorras; {n} puhul nimetas ettevõte tehisaru põhjusena">{out}</svg>')


def read(D):
    TM, K = D.tm, D.K
    kuu = D.kuu
    ee_kuud = dict(TM["EE"])
    pohjus = D.k_pohjusena
    if not pohjus:
        k_lause = "Ükski ettevõte ei nimetanud tehisaru koondamise põhjusena"
    else:
        k_lause = (f'{len(pohjus)} {"ettevõte" if len(pohjus) == 1 else "ettevõtet"} '
                   f'({", ".join(e(r["ettevote"]) for r in pohjus)}) nimetas põhjusena tehisaru, otsese põhjusena {D.k_otsene if D.k_otsene else "mitte ükski"}')
    too, th, th0 = D.too, D.too_h, D.too_h0
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
             # Kadri 26.11.2026: uudistest kogutud teated ei ole kõigi koondamiste loend, seepärast arv ilma jagajata
             arv=f'{len(pohjus)} {"ettevõte" if len(pohjus) == 1 else "ettevõtet"}',
             all=f'nimetas tehisaru põhjusena; kokku {D.k_osa["s"]} töökohta',
             pilt=teate_ruudud(D.kj),
             mrk=(f"{k_lause}. Ettevõtte enda selgitus ei tõenda põhjust. Kogutud on {len(D.kj)} teadet uudistest; "
                  "see ei ole kõigi koondamiste loend, seepärast osakaalu ei arvutata."),
             liik="uudised", allikas="Eesti uudised", kuup=f'viimane teade {kp(max(r["kuupaev"] for r in D.kj))}'),
        # Kadri 26.11.2026 („Jah, vaheta“): kuulutuste arv ei näita, kas tehisaru tööl kasutatakse (jagaja on kõik kuulutused,
        # tööandja kirjutab oskust kuulutusse harva). Küsitlus mõõdab kasutamist otse; kuulutused jäävad üksikasjadesse.
        # Jagaja on hõivatud (Kadri 26.11.2026: jagaja peab sobima küsimusega); kõigi 16–74-aastaste number jääb märkusesse.
        dict(kys="Kui paljud töötajad kasutavad tehisaru tööl?", ank="tool", leht="inimesed.html", ava="Ava tööalane kasutus lehel Inimesed",
             sona=tt.sona_osa(th["vaartus"]), arv=f'{pr(th["vaartus"])}%',
             all=f'{th["aasta"]}, hõivatutest' + (f'; aasta varem {pr(th0["vaartus"])}%' if th0 else ""),
             pilt=vahvel100(th["vaartus"], f'{pr(th["vaartus"])}% hõivatutest kasutab tehisaru tööl'),
             mrk=(f'Kõigist 16–74-aastastest (ka töötud, õpilased ja pensionärid) {pr(too["vaartus"])}%; ELiga võrreldakse seda arvu. '
                  f'Töökuulutustest kasutamist ei näe: tehisaru mainib {D.ak_osk} muu ameti kuulutust {_arvt(D.ak_n)}-st '
                  '(<a href="#ai-kuulutused">CV.ee kuulutused</a>, märksõnade järgi).'),
             liik="mõõdetud", allikas="Statistikaamet " + too["allikas"].split("tabel ")[-1],
             kuup=kp(too["avaldatud"]) if too.get("avaldatud") else str(too["aasta"])),
        dict(kys="Kui paljud on avatud ametites?", ank="kokkupuude", ava="Ava ametite avatuse andmed", sona=f'Umbes iga {round(100 / K["korge"])}. töötaja',
             arv=f'{pr(K["korge"], 0)}%', all="kõige avatumates ametites (aste 3–4), 2022",
             pilt=jaotusriba([("s", K["korge"]), ("m", K["avatud"] - K["korge"])], f'Aste 3–4 {pr(K["korge"], 0)}%, aste 1–2 {pr(K["avatud"] - K["korge"], 0)}%'),
             mrk=f'Kokku {pr(K["avatud"], 0)}% töötajatest on ametites, mille ülesandeid generatiivne tehisaru puudutab. Kokkupuude ei ole mõju.',
             liik="arvutatud", allikas="ILO indeks, Statistikaamet", kuup="2022"),
        dict(kys="Kas kõige avatumates ametites on tööd vähem?", ank="astmed", ava="Vaata hõivet avatuse astme järgi", sona=sona_hoive(D.ee_k),
             arv=mt(D.ee_k), all=f"hõive astmes 3–4, {D.A0}–{D.A1}; ELis {mt(D.el_k)}",
             pilt=hoive_tapid(D),
             mrk=(f'Alla {PIIR_HOIVE_PR}% muutust Eesti kohta ei tõlgendata: number tuleb tööjõu-uuringu valimist ja nii väike vahe '
                  f'võib olla valimiviga (seire hinnang, Statistikaameti usalduspiire pole kontrollitud). '
                  f'Kõigis avatud ametites kokku (aste 1–4) {mt(D.ee_av)}, teistes ametites {mt(D.ee_mu)}. Kirjeldus, mitte põhjus.'),
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
         [lahter("uudised", "ükski ettevõte ei ütle nii" if yks == 0 else "üks ettevõte ütleb nii" if yks == 1 else f"{yks} ettevõtet ütleb nii", f"Eesti uudised, {len(D.kj)} teadet"), lahter(),
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


AS_LO, AS_HI, AS_SAMM = -4, 10, 2  # hõive muutuse telg, %


def _as_x(v):
    return (min(AS_HI, max(AS_LO, v)) - AS_LO) / (AS_HI - AS_LO) * 100


def _naide(nimi):
    """Ametinimi loetelus: väike algustäht, lühend (IKT) jääb suureks."""
    return nimi if nimi[1:2].isupper() else nimi[0].lower() + nimi[1:]


def _astmed_joonis(D):
    """Iga aste on rida: nimi ja kolm suurimat ametit Eestis, hõivatute arv ning hõive muutus (Eesti ja EL).
    HTML, mitte SVG: ametinimed murduvad ise ja tekst jääb telefonis loetava suurusega (Kadri 26.11.2026)."""
    g1 = D.K["aeg_uhtlane"][("EE", "T")][D.A1]
    maxn = max(g1[k] for k, _ in ASTE)
    read = []
    for k, nimi in ASTE:
        ve, vl = D.mu("EE", k), D.mu(EL, k)
        xe, xl = _as_x(ve), _as_x(vl)
        naited = " · ".join(e(_naide(x["nimi"])) for x in D.K["naited"][k])
        read.append(
            f'<li class="as-r{" f" if k in ("4", "3") else ""}">'
            f'<div class="as-n"><b>{e(nimi)}</b><small>{naited}</small></div>'
            f'<div class="as-h" aria-hidden="true"><i style="--w:{g1[k] / maxn:.3f}"></i><span>{pr(g1[k], 0)}</span></div>'
            f'<div class="as-m" aria-hidden="true"><i class="as-0" style="left:{_as_x(0):.2f}%"></i>'
            f'<i class="as-v" style="left:{min(xe, xl):.2f}%;width:{abs(xe - xl):.2f}%"></i>'
            f'<i class="as-el" style="left:{xl:.2f}%" title="EL: {mt(vl)}"></i><i class="as-ee" style="left:{xe:.2f}%" title="Eesti: {mt(ve)}"></i>'
            f'<b style="left:{xe:.2f}%">{mt(ve)}</b></div>'
            f'<span class="peidus">Hõivatuid Eestis {pr(g1[k], 0)} tuhat. Hõive muutus {D.A0}–{D.A1}: Eesti {mt(ve)}, EL {mt(vl)}.</span></li>')
    telg = "".join(f'<span style="left:{_as_x(v):.2f}%">{"+" if v > 0 else "−" if v < 0 else ""}{abs(v)}%</span>' for v in range(AS_LO, AS_HI + 1, AS_SAMM))
    return (f'<div class="as-pea" aria-hidden="true"><span>Aste ja kolm suurimat ametit Eestis</span><span>Hõivatuid Eestis {D.A1}, tuh</span>'
            f'<span>Hõive muutus {D.A0}–{D.A1} <span class="as-leg"><i class="as-ee"></i>Eesti <i class="as-el"></i>EL</span></span></div>'
            f'<ul class="as-l" style="--as-n:{(AS_HI - AS_LO) // AS_SAMM}">{"".join(read)}</ul>'
            f'<div class="as-telg" aria-hidden="true"><div class="as-tl">{telg}</div></div>')


def sec_astmed(D):
    ilo = D.U["ilo2025"]
    # Pealkiri ütleb Eesti kohta suuna ainult siis, kui muutus on üle valimivea piiri (PIIR_HOIVE_PR); ELi kohta alati.
    if D.el_k <= 0:
        raise AndmeViga("Astmete pealkiri ütleb, et ELis kõige avatumates ametites hõive kasvas; andmed seda enam ei näita")
    if selge_muutus(D.ee_k):
        ee_lause = f'<b>Eestis hõive {"vähenes" if D.ee_k < 0 else "kasvas"} {pr(abs(D.ee_k))}%</b>'
    else:
        ee_lause = f'<b>Eestis selget muutust ei ole</b> ({mt(D.ee_k)})'
    g1 = D.K["aeg_uhtlane"][("EE", "T")][D.A1]
    from lehed_ulevaade import EUROSTAT
    return f"""
<section class="jaotis" id="astmed" aria-labelledby="h-astmed">
  <header>
    <h2 id="h-astmed"><span class="kys">Kas kõige avatumates ametites (aste 3–4) on tööd vähem?</span> {ee_lause}, ELis kasvas hõive {pr(D.el_k)}%</h2>
    <p class="alam">Aste näitab, kui suurt osa ameti ülesannetest generatiivne tehisaru puudutab (ILO hinnang).</p>
  </header>
  <figure class="as-fig">{_astmed_joonis(D)}</figure>
  {allikarida([("Eurostat, lfsa_egai2d", EUROSTAT.format("lfsa_egai2d"), "uuendatud 30.10.2026"), (f"ILO {ilo['aasta']}, kokkupuute indeks", ilo["url"], ""),
               ("Statistikaamet, PA633", PA633_URL, "ametite töötajate arv, oktoober 2022")])}
  <p class="allikas">See on kirjeldus, mitte põhjus: Eesti majandus oli 2023–2024 langusel ja see mõjutas harusid eri moodi. Eesti arvud tulevad tööjõu-uuringu valimist ja rühmad on väikesed (astmes 4 umbes {pr(g1["4"], 0)} tuhat hõivatut), seepärast võib alla {PIIR_HOIVE_PR}% muutus olla valimiviga. Piir on seire hinnang; Statistikaameti usalduspiire pole kontrollitud.</p>
</section>"""
