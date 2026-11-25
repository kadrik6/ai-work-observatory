"""Ülevaade (avaleht) töölauana (Kadri valikud 5.11.2026, suundade leht 9EWSmGTPNJRapX5z9CoEc6).

Ülesehitus: pealkiri, kuus numbriplaati, ELi kaart koos järjestusega omaette real, siis töötuse prognoos ja
ettevõtete trend, siis „Mis muutus“, sihid ja hanked, lõpuks väidete tabel. Koondamised on ainult
Töö vaates (Kadri 5.11 22:22: soovitused 1–5 kehtivad).

Iga pealkirja number tuleb andmetest. Mallist väljas olevad osad kontrollitakse abi.kontrolli() abil.
"""
import collections
import csv
import html
import re
from pathlib import Path

import andmekiht as andmed
from abi import ARVSONAD, SEESTYTLEV, a, kontrolli, link, sonaga
from andmekiht import EL, AndmeViga
from komponendid import KUUD, aastatulbad, allikarida, e, kaart, kp, pr, riik, sihiriba
from lehed_usaldus import RASKUS, _raskus
from lehed_uudised import KASITSI, _vaja
from pealkiri import taida

SISU = Path(__file__).resolve().parent / "sisu"
IN, EB, DS = "inimeste-tehisaru-kasutus", "ettevotete-tehisaru-kasutus", "inimeste-digioskused"
EUROSTAT = "https://ec.europa.eu/eurostat/databrowser/view/{}/default/table"
UNE_URL = "https://ec.europa.eu/eurostat/databrowser/view/une_rt_m/default/table"
HANKED_URL = "https://riigihanked.riik.ee/"
OECD_KUUPAEV = "2026-11-03"  # OECD avaliku sektori innovatsiooni raport (sama kuupäev teematabelis)
VOO_PAEVI, VOO_RIDU = 14, 8


def voo_silt(kuupaev, liik, tana):
    """„Mis muutus“ rea silt. Oranž „uus“ ainult siis, kui number on avaldatud viimase VOO_PAEVI päeva jooksul
    (Kadri 10.11.2026: septembri ja oktoobri numbrid ei ole enam uued). Vanem number saab halli sildi „number“."""
    from datetime import date
    if liik != "uus number":
        return f'<span class="t">{e(liik)}</span>'
    if (tana - date.fromisoformat(kuupaev[:10])).days <= VOO_PAEVI:
        return '<span class="t uus">uus</span>'
    return '<span class="t">number</span>'
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


def tootuse_uuendatud():
    """Kuupäev, millal Eurostat töötuse kuurida viimati muutis (sait/lae_tootus.py kirjutab selle faili)."""
    kp_ = {r.get("uuendatud") or "" for r in _loe("eurostat-tootus-kuud.csv")}
    if len(kp_) != 1 or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", next(iter(kp_))):
        raise AndmeViga("sisu/eurostat-tootus-kuud.csv: veerus „uuendatud“ peab olema üks kuupäev")
    return kp_.pop()


UNE_UUENDATUD = tootuse_uuendatud()
REG_URL = "https://andmed.stat.ee/et/stat/sotsiaalelu__tooturg__tootud__luhiajastatistika/TT065"


def reg_tootud():
    """Registreeritud töötute arv kuu kaupa (Statistikaamet TT065; sait/lae_reg_tootud.py): ([(kuu, arv)], avaldatud).

    See on Töötukassas arvel olijate arv, mitte töötuse määr; määraga seda ei võrrelda ega liideta."""
    read = _loe("reg-tootud-kuud.csv")
    kuud = sorted((r["kuu"], int(r["arv"])) for r in read)
    kp_ = {r["uuendatud"] for r in read}
    if len(kuud) < 13 or len(kp_) != 1:
        raise AndmeViga("sisu/reg-tootud-kuud.csv: vaja vähemalt 13 kuud ja üks avaldamise kuupäev")
    return kuud, kp_.pop()


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


# KPI-plaadid Kadri lukustatud valiku „ver1“ järgi (KPI-labor, 7.11.2026 21:46 „lukusta ver1“):
# kast, kaks rida (3 + 3), number 24 px, silt numbri kohal, lühike allikas, fookus Inimesed;
# iga plaadi kontekst on oma: muutus ja/või tekst ja/või võrdlusriba. Lugeja neid ei muuda.
KPI_VER1 = {  # avalehe kuus plaati läksid 14.11.2026 ära (avaleht on signaalitahvel, Kadri valis näidise C)
            # uuendus, laiendus ja genai läksid 17.11.2026 ära: Avaliku sektori lehel on tahvel
            # Alamlehtede päis (Kadri 8.11.2026: „ka teistel alamlehtedel, käsitsi üle vaadatud nagu ver1“).
            # Iga plaat sai oma konteksti: muutus, kui on võrreldav eelmine aasta; riba, kui on siht või võrdlus.
            # Inimeste plaadid in-* läksid 14.11.2026 ära: leht algab tahvliga (Kadri valis „A ja B koos“)
            # Ettevõtete plaadid ev-* läksid 14.11.2026 ära: leht algab tahvliga (Kadri valis „B koos C maatriksiga“)
            # Töö plaadid too-* läksid 17.11.2026 ära: leht algab tahvliga (Kadri valis „A ja C koos“)
            # Hangete plaadid hk-* läksid 19.11.2026 ära: leht algab tahvliga (Kadri valis „A ja C koos“)
            "us-muud": ("tekst", "riba"), "us-lahk": ("tekst",), "us-uudis": ("tekst",),
            "kl-allikad": ("tekst",), "kl-klassid": ("tekst",), "kl-uuringud": ("tekst",),
            "ma-jargmine": ("muutus", "tekst"), "ma-korge": ("muutus", "tekst"), "ma-osad": ("muutus", "riba"),
            "tk-ai": ("muutus", "tekst"), "tk-andmed": ("muutus", "tekst"), "tk-oskus": ("muutus", "tekst"),
            "ud-ee": ("muutus",), "ud-maailm": ("muutus",), "ud-suured": ("tekst",), "ud-kontroll": ("tekst",)}


def kpi_pais(*plaadid, tihe=False):
    """Alamlehe päise numbriplaadid samas kujus nagu avalik sektor (ver1).
    tihe: madalamad plaadid, kontekst ühel real (Kadri 11.11.2026 uudiste lehel: et uudised paistaks kiiremini)."""
    return (f'<aside class="vastus kpi-pais{" tihe" if tihe else ""}" aria-label="Peamised numbrid">'
            + "".join(plaadid) + "</aside>")


def kpi_riba(v, lopp, siht=None, vrd=None, vrd_nimi="EL", fookus=False, siht_tekst=None):
    """Võrdlusriba: tulp, oranž kriips = siht, tume kriips = võrdlus. Värv ei ole ainus tunnus: kriipsud on ka tekstis."""
    p = lambda x: f"{x / lopp * 100:.1f}%"  # noqa: E731
    o = (f'<span class="kriba{" f" if fookus else ""}" aria-hidden="true"><i style="width:{p(v)}"></i>'
         + (f'<b style="left:{p(siht)}"></b>' if siht is not None else "")
         + (f'<u style="left:{p(vrd)}"></u>' if vrd is not None else "") + "</span>")
    # Kadri 8.11.2026: vähem teksti — üks rida, märgi juures ainult sõna ja number
    lg = []
    if siht is not None:
        lg.append(f'<i class="lg s"></i>{e(siht_tekst or "siht " + pr(siht, 0) + "%")}')
    if vrd is not None:
        lg.append(f'<i class="lg v"></i>{e(vrd_nimi)} {pr(vrd, 0 if float(vrd).is_integer() else 1)}%')
    if lg:
        o += f'<span class="marg lgd">{" · ".join(lg)}</span>'
    return o


def kpi_plaat(pid, lbl, big, per, kontekst, src, fookus=False, href=""):
    """kontekst: {"muutus": (rasvane, hall), "tekst": html, "riba": html}; näidatakse ainult KPI_VER1 valitud osad."""
    nimi = f'<a href="{e(href)}">{e(lbl)}</a>' if href else e(lbl)
    osad = []
    for k in KPI_VER1[pid]:
        if k not in kontekst:
            raise AndmeViga(f"KPI-plaadil {pid} puudub kontekst „{k}“ (lukustatud valik ver1)")
        if k == "muutus":
            m, hall = kontekst[k]
            osad.append(f'<span class="muut">{m}</span>' + (f'<span class="marg">{hall}</span>' if hall else ""))
        else:
            osad.append(f'<span class="tekst">{kontekst[k]}</span>' if k == "tekst" else kontekst[k])
    return (f'<div class="plaat kp" data-kpi="{pid}"><span class="lbl">{nimi}</span>'
            f'<span class="big{" s" if fookus else ""}">{big}{f"<small>{per}</small>" if per else ""}</span>'
            f'<span class="ctx">{"".join(osad)}</span>'
            # Allikarida ainult siis, kui allikas on (Kadri 11.11.2026: „Seire uudistekogumine“ ei andnud infot)
            + (f'<span class="src">{src}{kopeeri_nupp(pid, lbl, big, per, src)}</span>' if src else "") + '</div>')


# Esmakordsele lugejale (kolleeg, kes saab lingi): mis sait see on. Kadri 8.11.2026, enne kolleegidele näitamist.
# Lühike päis (Kadri 8.11.2026: pealkiri ja selle all olev tekst lühemaks, allikad ühe lingi taha)
TUTVUS = "Tehisaru kasutus ja mõju Eestis ja ELis: statistika, uuringud ja väidete kontroll, iga number allikaga."

KOOPIA_KES = {"ma-": "ELi tehisaru määrus"}


def fakt(lbl, big, per, src, kes="Eesti"):
    """Kopeeritav lause: kes, näitaja, number, periood ja allikas koos lingiga (sisuloogika 8.11.2026, idee 2)."""
    tekst = lambda h: re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", h))).strip()  # noqa: E731
    url = re.search(r'href="(https?://[^"]+)"', src or "")
    nimi = tekst(lbl)
    if kes and not any(s in nimi for s in ("Eesti", "USA", "Taani")):
        nimi = f"{kes}, {nimi[0].lower()}{nimi[1:]}"
    p = tekst(per).replace(" · ", ", ") if per else ""
    p = f" {p}" if p.startswith(("/", "punkti", "protsendipunkti")) else (f" ({p})" if p else "")
    return (f"{nimi}: {tekst(big)}{p}."
            + f" Allikas: {tekst(src)}" + (f", {html.unescape(url.group(1))}" if url else "") + ".")


def kopeeri_nupp(pid, lbl, big, per, src):
    """Nupp ainult siis, kui plaadil on välise allika link (seire enda loendeid ja kuulutuste arve ei tsiteerita)."""
    if not re.search(r'href="https?://', src or "") or pid.startswith("tk-"):
        return ""
    kes = next((v for k, v in KOOPIA_KES.items() if pid.startswith(k)), "Eesti")
    return (f'<button type="button" class="kopeeri" data-fakt="{e(fakt(lbl, big, per, src, kes))}" '
            f'data-silt="Kopeeri fakt koos allikaga" aria-label="Kopeeri fakt koos allikaga">{KOOPIA_IKOONID}</button>')


# Ikoon nupul, sõna ilmub hõljudes (Kadri 8.11.2026 20:18). Kaks ikooni: kopeeri ja linnuke pärast õnnestumist.
KOOPIA_IKOONID = (
    '<svg class="ik ik-kop" viewBox="0 0 16 16" width="15" height="15" aria-hidden="true" focusable="false">'
    '<rect x="5.5" y="5.5" width="8" height="8" rx="1.5" fill="none" stroke="currentColor" stroke-width="1.4"/>'
    '<path d="M10.5 3.5v-.5a1.5 1.5 0 0 0-1.5-1.5H4A1.5 1.5 0 0 0 2.5 3v5A1.5 1.5 0 0 0 4 9.5h.5" '
    'fill="none" stroke="currentColor" stroke-width="1.4"/></svg>'
    '<svg class="ik ik-ok" viewBox="0 0 16 16" width="15" height="15" aria-hidden="true" focusable="false">'
    '<path d="M3 8.5l3.2 3L13 4.5" fill="none" stroke="currentColor" stroke-width="1.8" '
    'stroke-linecap="round" stroke-linejoin="round"/></svg>')


def _p(x):
    return ("+" if x > 0 else "") + pr(x)


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
         lihtne=False, y_skaala=False):
    """Joondiagramm SVG-na. seeriad: [(nimi, [(x, y)], liik)], liik ∈ {"fookus", "ref", ""}. Otsasildid paremal.

    lihtne=True: ruudustikku ega y-telge pole, ainult jooned, lõppväärtused ja esimene ning viimane kuu (Kadri 5.11 22:49).
    Siis algab y vahemik andmete miinimumi lähedalt, sest telge ega tulpa, mille pikkust lugeda, pole.
    y_skaala=True (lihtne vaade): heledad abijooned iga täisprotsendi kohal koos väärtusega vasakul, et lugeja näeks,
    kui suur muutus on (disainikriitika 14.11.2026, soovitus 2)."""
    import math
    y0 = 0
    if lihtne:
        koik = [py for _, pts, _ in seeriad for _, py in pts]
        y0, y1 = max(0, math.floor(min(koik)) - 1), math.ceil(max(koik)) + 1
    X = lambda x: ml + (x - x0) / (x1 - x0) * (w - ml - mr)  # noqa: E731
    Y = lambda y: mt + (1 - (y - y0) / (y1 - y0)) * (h - mt - mb)  # noqa: E731
    osad = []
    y = 0
    if lihtne and y_skaala:
        yy = y0
        while yy <= y1 + 1e-9:
            osad.append(f'<line class="v" x1="{ml}" x2="{w - mr}" y1="{Y(yy):.1f}" y2="{Y(yy):.1f}"/>')
            osad.append(_svg_tekst(ml - 6, Y(yy) + 4, pr(yy, 0), "t", "end"))
            yy += 1 if y1 - y0 <= 6 else 2
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


def _esimene_lause(t):
    """Avalehe voos ainult esimene lause; kogu tekst on lehel Usaldus › Värskus (Kadri 7.11.2026: teksti on liiga palju)."""
    import re
    m = re.match(r"(.+?[.!?])\s+(?=[A-ZÕÄÖÜŠŽ])", t)
    return m.group(1) if m else t

def avaleht(A, vaade, vaated):
    """Avaleht on signaalitahvel (Kadri 14.11.2026 valis näidise C): teemade tabel ja ajajoon.
    Varasemad plokid (KPI-plaadid, ELi kaart, töötuse prognoos, ettevõtete trend, sihid, hanked, väited) on teemalehtedel."""
    from datetime import date
    from avaleht_tahvel import aja_jaotis, tahvel, tulevad_tahtajad
    ein, eeb = andmed.leia(A, IN, "EE", "uusim"), andmed.leia(A, EB, "EE", "uusim")
    ein25 = andmed.leia(A, IN, "EE", "uusim:alus")
    if ein25["aasta"] != ein["aasta"] - 1 or ein["klass"] not in andmed.VORRELDAVAD:
        raise AndmeViga("Inimeste muutus eeldab kahte järjestikust võrreldavat aastat")
    ds = andmed.leia(A, DS, "EE", "uusim:alus")
    T = tootus()
    kuu, t_ee = T["EE"][-1]
    t_el = dict(T[EL]).get(kuu)
    if t_el is None:
        raise AndmeViga(f"ELi töötus puudub kuul {kuu}")
    t_aasta_eest = dict(T["EE"]).get(f"{int(kuu[:4]) - 1}{kuu[4:]}")
    if t_aasta_eest is None:
        raise AndmeViga(f"Töötuse muutus vajab kuud {int(kuu[:4]) - 1}{kuu[4:]}")
    if andmed.leia(A, IN, "EE", "uusim:alus")["aasta"] != andmed.leia(A, EB, "EE", "uusim:alus")["aasta"]:
        raise AndmeViga("Avalehe h1 annab ELi kohtadele ühe aasta, aga inimeste ja ettevõtete ELi aastad erinevad")
    # Sama allikas ja periood nagu hangete lehel (sisuloogika 8.11.2026)
    HL = _vaja(A, "hanked_leht", "hanked-leht.json")
    H = [{"aasta": r["aasta"], "ai_ja_andmed": r["ai_andmed"], "osa": r["ai_andmed_osakaal"]} for r in HL["aastad"]]
    h_seis = HL.get("seis", {}).get("kuupaev", "")
    h_uus = {**H[-1], "periood": f"kuni {kp(h_seis)}" if h_seis[:4] == str(H[-1]["aasta"]) and h_seis[5:] != "12-31" else str(H[-1]["aasta"])}
    V = A["vaited"]
    menuu = lambda vid, t, ank="": link(vaated, vid, t, ank)  # noqa: E731

    # Töö rea koht ELis: töötuse järjestus (sama mis Töö lehel)
    m = re.search(r"ELis (\d+)\. kõrgeim \((\d{4})\)", re.sub(r"<[^>]+>", "", tootus_el()))
    t_koht = (f"ELis {m.group(1)}. kõrgeim töötus ({m.group(2)})", (f"{m.group(1)}.", "kõrgeim töötus")) if m else ("–", ("–", ""))
    sec_tahvel, _ = tahvel(A, vaated, {"ein": ein, "ein25": ein25, "eeb": eeb, "ds": ds, "T": T, "kuu": kuu, "t_ee": t_ee, "t_el": t_el,
                                       "t_aasta_eest": t_aasta_eest, "h_uus": h_uus, "une_uuendatud": UNE_UUENDATUD,
                                       "oecd_kuupaev": OECD_KUUPAEV}, vaite_teema, t_koht)

    voog = []
    for s in A["sundmused"]:
        if s["liik"] == "allikas":
            voog.append((s["kuupaev"], "uus number", "uus", e(_esimene_lause(s["tekst"])), s["url"]))
    for v in V:
        if v["kuupaev"]:
            lyh = v["vaide"] if len(v["vaide"]) <= 70 else v["vaide"][:67].rsplit(" ", 1)[0] + "…"
            voog.append((v["kuupaev"], "väide", "", f'{e(v["valjaanne"])}: „{e(lyh)}“ ({e(RASKUS[_raskus(v)][0].lower())})', ""))
    voog.append((UNE_UUENDATUD, "uus number", "uus", f"Eesti töötus {kuu_seesytlev(kuu)} {pr(t_ee)}% (Eurostat)", UNE_URL))
    voog.append((ein["avaldatud"], "uus number", "uus", f"Inimeste tehisaru kasutus {pr(ein['vaartus'])}% (Statistikaamet)", ein["url"]))
    voog.append((eeb["avaldatud"], "uus number", "uus", f"Ettevõtete tehisaru kasutus {pr(eeb['vaartus'])}% (Statistikaamet)", eeb["url"]))
    voog = sorted(sorted(set(voog), key=lambda r: (r[1], r[3])), key=lambda r: r[0], reverse=True)  # kindel järjekord
    tana = date.today()
    sec_aeg = aja_jaotis(voog, tulevad_tahtajad(A, tana), tana, vaated)

    pea = f"""
<div class="pea-t pea-rahu pilt">
  <h1>{taida(vaade["h1"], A)}</h1>
  <div class="alla">
    <p class="tutvus">{TUTVUS} {menuu("saidist", "Mis see sait on?")}</p>
    <details class="allikad-l"><summary>Allikad ja kuupäevad</summary><div>
      <p>Andmed: Statistikaamet {kp(ein["avaldatud"])} ja {kp(eeb["avaldatud"])}, Eurostat {kp(UNE_UUENDATUD)}.</p>
      <p>ELi järjestus on {ein25["aasta"]}. aasta kohta (Eurostat). Iga number on allikaga, allikas on teema lehel numbri juures.</p>
      <p>{menuu("kuidas", "Kuidas numbreid lugeda")}</p>
    </div></details>
  </div>
</div>"""
    return pea + '<div class="g12">' + sec_tahvel + "</div>" + '<div class="g12">' + sec_aeg + "</div>"


# ---------------------------------------------------------------- Töö vaate Eesti rida

ROLL_NIMI = {"otsene": "otsene põhjus", "osaline": "üks põhjus", "kaudne": "kaudne", "tulevikus": "võib tulevikus",
             "ei_pohjus": "pole põhjus", "ei_mainita": "ei mainita"}


def koondamise_arv(r):
    """Koondatute arv Eestis tekstina: täpne, „vähemalt“, „kuni“ või „arv pole teada“."""
    if r.get("arv_eestis") is not None:
        return ("vähemalt " if r.get("arv_vahemalt") else "") + str(r["arv_eestis"])
    return f'kuni {r["arv_ulem"]}' if r.get("arv_ulem") else "arv pole teada"


def too_eesti(A):
    """Töö vaate andmed: (Eesti töötus kuu kaupa, Eesti koondamised, kus küsiti tehisaru rolli).

    Kadri 11.11.2026: koondamised olid liiga suure fookuse all (esimese saki 3/4). Töötus on nüüd esimene sakk üksi,
    koondamised on oma sakis koos tabeliga „Keda koondajad otsivad“."""
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
                  0, n, 10, 2, w=720, h=220, ml=30, mr=64, x_margid=sorted(set(margid)), lihtne=True, y_skaala=True,
                  x_silt=lambda i: T["EE"][int(i)][0][5:] + "." + T["EE"][int(i)][0][:4], silt="Töötuse määr kuu kaupa")
    aasta_tagasi = dict(T["EE"]).get(f"{int(kuu[:4]) - 1}{kuu[4:]}")
    muutus = "" if aasta_tagasi is None else (
        f"Aasta varem {pr(aasta_tagasi)}%, muutus {'+' if t_ee >= aasta_tagasi else '−'}{pr(abs(t_ee - aasta_tagasi))} protsendipunkti. ")
    sec_t = f"""
<section class="pn sp12" id="tootus-kuud" aria-labelledby="h-tootus-kuud">
  <div class="pn-h"><h2 id="h-tootus-kuud">Eesti töötus oli {kuu_seesytlev(kuu)} {kuu[:4]} <b>{pr(t_ee)}%</b>, ELis {pr(t_el)}%</h2></div>
  <p class="ps">Töötuse määr, %, sesoonselt tasandatud, {k0[5:]}.{k0[:4]}–{kuu[5:]}.{kuu[:4]}. {muutus}Kuunumber ei ütle, kas põhjus on tehisaru.</p>
  {joonis}
  {allikarida([("Eurostat une_rt_m", UNE_URL, f"uuendatud {kp(UNE_UUENDATUD)}")])}
</section>"""
    # Registreeritud töötud (Kadri 25.11.2026: määr on septembri oma, uuem kuu on olemas ainult selle arvu kohta)
    RT, r_avaldatud = reg_tootud()
    r_kuu, r_n = RT[-1]
    r_n0 = dict(RT).get(f"{int(r_kuu[:4]) - 1}{r_kuu[4:]}")
    if r_n0 is None:
        raise AndmeViga(f"Registreeritud töötute muutus vajab kuud {int(r_kuu[:4]) - 1}{r_kuu[4:]}")
    r_muut = (r_n - r_n0) / r_n0 * 100
    rn = len(RT) - 1
    r_margid = sorted({i for i, (k, _) in enumerate(RT) if k[5:7] == "01"} | {0, rn})
    r_joonis = joon([("Eesti", [(i, v / 1000) for i, (_, v) in enumerate(RT)], "fookus")],
                    0, rn, 50, 10, w=720, h=200, ml=30, mr=64, x_margid=r_margid, lihtne=True, y_skaala=True,
                    x_silt=lambda i: RT[int(i)][0][5:] + "." + RT[int(i)][0][:4], silt="Registreeritud töötute arv kuu kaupa, tuhandetes")
    r_arv = lambda x: f"{x:,}".replace(",", NBSP)  # noqa: E731
    sec_t += f"""
<section class="pn sp12" id="reg-tootud" aria-labelledby="h-reg-tootud">
  <div class="pn-h"><h2 id="h-reg-tootud">Töötukassas oli {kuu_seesytlev(r_kuu)} {r_kuu[:4]} arvel <b>{r_arv(r_n)}</b> töötut</h2></div>
  <p class="ps">Registreeritud töötute arv, tuhandetes, {RT[0][0][5:]}.{RT[0][0][:4]}–{r_kuu[5:]}.{r_kuu[:4]}. Aasta varem {r_arv(r_n0)}, muutus {'+' if r_muut >= 0 else '−'}{pr(abs(r_muut), 0)}%. See ei ole töötuse määr: määr tuleb küsitlusest ja loeb ka tööotsijaid, kes Töötukassas arvel ei ole. Neid kahte numbrit ei võrrelda.</p>
  {r_joonis}
  {allikarida([("Statistikaamet TT065", REG_URL, f"avaldatud {kp(r_avaldatud)}")])}
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
            "ei_pohjus": ("t", "tehisaru polnud põhjus"),
            "ei_mainita": ("t", "tehisaru polnud põhjus")}  # ei_pohjus: ettevõte eitas (Kadri 8.11.2026)
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
    legend = "".join(f'<span><i class="kr-t {k}"></i>{e(t)}</span>' for k, t in [("s", "nimetas tehisaru põhjusena"), ("m", "mainis tehisaru muul moel"), ("t", "tehisaru ei mainitud või eitati")])
    sec_v = f"""
<div class="kk-vis" id="koondamised-visuaal">
  <h3 class="kk-h3" id="h-koondamised-v">{piir.capitalize()}{kokku} koondatud töökohast <b>{pohjus} töökoha</b> puhul nimetati üheks põhjuseks tehisaru</h3>
  <p class="ps">Teatatud töökohad ettevõtte kaupa. Ainult koondamised, mille puhul uudis küsis tehisaru kohta; nimekiri pole täielik (viimane teade {kp(juhtumid[0]["kuupaev"])}).</p>
  <div class="kr-ribad" role="list" aria-label="Koondatavad töökohad ettevõtte kaupa">{ribad}</div>
  <p class="kr-leg">{legend}</p>
  <p class="allikas">Allikas: uudised, lingid tabelis <a href="#palkamine">Keda koondajad otsivad</a>. Ettevõtte enda selgitus ei tõenda põhjust. Katkendäärega tulp on teatatud ülempiir{"; + tähendab, et lõplik arv pole veel teada" if alam else ""}.</p>
  {bonney_rida}
</div>"""
    # Kaardid võeti maha; arv, põhjus ja link on tabelis „Keda koondajad otsivad“ (Kadri MKUS-i kommentaar 7.11.2026 08:48)
    sec_kv = f"""
<section class="pn sp12" id="koondamised" aria-labelledby="h-koondamised">
  {k_pea}
  {sec_v}
</section>"""
    return f'<div class="g12">{sec_t}</div>', f'<div class="g12">{sec_kv}</div>'


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


def el_jarjestus(naitaja, fookus="EE", kahanevalt=True, koht_praegu=None, aasta_praegu=None, lai=(720, 130, 140), min_aastaid=1):
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
    if len(aastad) < min_aastaid:  # järjestuse muutus vajab vähemalt kahte aastat
        return None
    koht = {g: {} for g in v}
    for a in aastad:
        for i, g in enumerate(sorted((g for g in v if a in v[g]), key=lambda g: -v[g][a] if kahanevalt else v[g][a]), 1):
            koht[g][a] = i
    if koht_praegu is not None and koht[fookus].get(aasta_praegu) != koht_praegu:
        raise AndmeViga(f"el-jarjestus.csv: {naitaja} {fookus} {aasta_praegu} koht {koht[fookus].get(aasta_praegu)}, "
                        f"registris {koht_praegu}; käivita python3 sait/lae_el_jarjestus.py")
    jarjest = sorted(koht, key=lambda g: koht[g].get(aastad[-1], 99))
    nimed = {g: riik(g) for g in jarjest}
    g = jarjestuse_muutus({nimed[x]: koht[x] for x in jarjest}, aastad, nimed[fookus], None, piirid=(10,),  # Kadri 8.11.2026: ainult Top 10 ja kõik
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


# ---------------------------------------------------------------- Avalehe teematabel (näidis C, Kadri 8.11.2026)

# Väited, millel pole näitajat, kuuluvad teemasse id järgi (käsitsi, ülevaatus 8.11.2026).
VAITE_TEEMA = {"ettevotete-tehisaru-kasutus": "ettevotted", "tehisaru-oskuse-puudus": "inimesed",
               "inimeste-tehisaru-kasutus": "inimesed", "tooalane-tehisaru-kasutus": "inimesed",
               "inimeste-digioskused": "inimesed",
               "pwc-2026-tootlikkus-40": "ettevotted", "err-2026-oskused-39": "too", "err-2026-vahendamine-40": "too",
               "worthynews-2024-imf-40": "too", "247wallst-2025-goldman-300m": "too",
               "uudis-ai-oskajad-votavad-tookohad": "too", "uudis-challenger-okt-153074": "too",
               "uudis-ai-noorte-esimene-too": "too"}
LAHK_TEEMA = {"ettevotete-tehisaru-kasutus": "ettevotted", "tehisaru-oskuse-puudus": "inimesed"}
VARSKE_PAEVI = 92


def vaite_teema(v):
    t = VAITE_TEEMA.get(v["naitaja"]) or VAITE_TEEMA.get(v["id"])
    if not t:
        raise AndmeViga(f"Väitel {v['id']} pole avalehe tabelis teemat: lisa see VAITE_TEEMA-sse")
    return t


