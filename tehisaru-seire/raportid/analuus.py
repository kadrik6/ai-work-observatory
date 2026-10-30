"""Analüütiku vaade (analuus.html): üks tihe leht, kus Eestit võrreldakse kõigi võrreldavate
põhimõõdikute järgi Põhjamaade, Saksamaa, Hollandi ja ELi keskmisega.

Numbrid tulevad ainult kataloogist (seire/kataloog.py: kataloog/vaatlused-*.csv ja andmed/).
Tõlgendused on käsitsi kirjutatud, aga iga tõlgenduse juures on tingimus. Kui andmed muutuvad
nii, et tingimus enam ei kehti, märgib leht tõlgenduse ülevaatamist vajavaks ja koostaja hoiatab.

Kutsub välja koosta.py: analuusi_leht(k, D, K, tana), kus k on koosta moodul (abifunktsioonid).
"""

import csv
import io
import sys
from statistics import mean

import pildid

RIIGID7 = ["EE", "FI", "SE", "DK", "NO", "DE", "NL"]
POHJA = ["FI", "SE", "DK", "NO"]
EL = "EU27_2020"
FAIL = "analuus.html"
CSV_FAIL = "analuus-andmed.csv"

# Võrreldavad põhimõõdikud (kataloogi võrdlusalused), loogilises järjekorras.
# (mõõdik, teema, lühinimi, kogum ja ühik, komakohti, järelliide, väiksem on parem, pealkirja sõna)
PROFIIL = [
    ("eurostat-isoc-ai-iaiu", "Tehisaru kasutus", "Inimesed kasutavad generatiivset tehisaru", "% 16–74-aastastest, viimase 3 kuu jooksul", 1, "%", False, "inimeste kasutus"),
    ("eurostat-isoc-ai-iaiu-too", "Tehisaru kasutus", "Inimesed kasutavad seda tööl", "% 16–74-aastastest", 1, "%", False, "kasutus tööl"),
    ("eurostat-isoc-eb-ai", "Tehisaru kasutus", "Ettevõtted kasutavad tehisaru", "% vähemalt 10 hõivatuga ettevõtetest", 1, "%", False, "ettevõtted"),
    ("eurostat-isoc-ai-iaiuxr-oskus", "Oskused", "Ei kasuta tehisaru, sest ei oska", "% 16–74-aastastest, väiksem on parem", 1, "%", True, "oskuse puudus"),
    ("eurostat-isoc-sk-dskl-i21", "Oskused", "Vähemalt baastasemel digioskused", "% 16–74-aastastest", 1, "%", False, "digioskused"),
    ("eurostat-isoc-sks-itspt", "Tööturg ja haridus", "IKT-spetsialistid hõivatute seas", "% hõivatutest", 1, "%", False, "IKT-spetsialistid"),
    ("uis-ikt-lopetajad", "Tööturg ja haridus", "IKT eriala lõpetajad", "% kõrgkoolide lõpetajatest", 1, "%", False, "IKT lõpetajad"),
    ("eurostat-rd-e-gerdtot", "Teadus ja arendus", "Teadus- ja arendustegevuse kulu", "% SKPst", 2, "%", False, "T&A kulu"),
    ("uis-teadlased", "Teadus ja arendus", "Teadlased", "täistööajale taandatud, miljoni elaniku kohta", 0, "", False, "teadlased"),
]
# Ajaread väikeste mitmikutena (vähemalt kolm aastat andmeid).
AJAREAD = ["eurostat-isoc-eb-ai", "eurostat-isoc-sk-dskl-i21", "eurostat-isoc-sks-itspt",
           "uis-ikt-lopetajad", "eurostat-rd-e-gerdtot", "uis-teadlased"]
# Muutus kahe aasta vahel: (mõõdik, algusaasta). Lõpp on ühine viimane aasta.
MUUTUSED = [("eurostat-isoc-eb-ai", 2023), ("eurostat-isoc-sk-dskl-i21", 2021),
            ("eurostat-isoc-sks-itspt", 2019), ("eurostat-rd-e-gerdtot", 2015)]
# Riikide endi uuemad numbrid (avaldatud enne Eurostati).
RIIKLIKUD = [
    ("Inimesed kasutavad generatiivset tehisaru", ["sa-it71", "ssb-14365", "scb-tab6388", "tk-sutivi"], "eurostat-isoc-ai-iaiu"),
    ("Inimesed kasutavad seda tööl", ["sa-it71-too"], "eurostat-isoc-ai-iaiu-too"),
    ("Ettevõtted kasutavad tehisaru", ["sa-it1490", "dst-itav28", "ssb-ikt"], "eurostat-isoc-eb-ai"),
]
HINNANGUD = {
    "yle": ("Üle kõigi Põhjamaade", "focus"),
    "vahemik": ("Põhjamaade vahemikus", "ok"),
    "maas": ("Põhjamaadest maas, EList eespool", "risk"),
    "alla_el": ("ELi keskmisest maas", "risk"),
    "alla_pohja": ("Alla kõigi Põhjamaade", "risk"),
}
SILDID = {
    "fakt": ("Fakt", "ok", "ametlik statistika"),
    "arvutus": ("Arvutus", "", "seire arvutas ametlikest numbritest"),
    "tolgendus": ("Tõlgendus", "focus", "seire hinnang, mida andmed toetavad"),
    "hupotees": ("Hüpotees", "risk", "võimalik seletus, mida andmed ei tõesta"),
    "piirang": ("Piirang", "", "mida number ei näita või miks võrdlus on ebatäpne"),
    "soovitus": ("Soovitus", "focus", "seire hinnang, millele tähelepanu pöörata"),
}


# ---------- andmed ----------

def seeria(K, mid):
    s = {}
    for v in K["vaatlused"]:
        if v["moodik"] == mid:
            s.setdefault(v["riik"], {})[v["aasta"]] = v["vaartus"]
    return s


def tapsus(K, mid, riik, aasta):
    """Komakohtade arv, millega allikas numbri avaldas (59 jääb 59-ks)."""
    return next((v["tapsus"] for v in K["vaatlused"] if v["moodik"] == mid and v["riik"] == riik and v["aasta"] == aasta), 1)


def yhine_aasta(s):
    """Viimane aasta, kus on Eesti ja vähemalt viis teist võrdlusriiki."""
    aastad = sorted({a for g in RIIGID7 for a in s.get(g, {})}, reverse=True)
    for a in aastad:
        if a in s.get("EE", {}) and sum(1 for g in RIIGID7[1:] if a in s.get(g, {})) >= 5:
            return a
    return None


def parem(a, b, vp):
    return a < b if vp else a > b


def statistika(K, rida):
    mid, teema, nimi, uhik, kohti, suf, vp, sona = rida
    s = seeria(K, mid)
    a = yhine_aasta(s)
    if a is None:
        return None
    v = {g: s[g][a] for g in RIIGID7 + [EL] if a in s.get(g, {})}
    ee, el = v["EE"], v.get(EL)
    po = [v[g] for g in POHJA if g in v]
    pk = mean(po)
    jrk = sorted((g for g in RIIGID7 if g in v), key=lambda g: v[g] if vp else -v[g])
    if el is not None and parem(el, ee, vp):
        hinnang = "alla_el"
    elif all(parem(ee, p, vp) for p in po):
        hinnang = "yle"
    elif all(parem(p, ee, vp) for p in po):
        hinnang = "maas" if el is not None else "alla_pohja"
    else:
        hinnang = "vahemik"
    eel = max(s["EE"])
    return {
        "mid": mid, "teema": teema, "sona": sona, "nimi": nimi, "uhik": uhik, "kohti": kohti, "suf": suf, "vp": vp,
        "s": s, "a": a, "v": v, "ee": ee, "el": el, "pk": pk, "pmin": min(po), "pmax": max(po),
        "koht": jrk.index("EE") + 1, "n": len(jrk), "jrk": jrk, "hinnang": hinnang,
        "indeks": (pk / ee if vp else ee / pk) * 100,
        "uuem": (eel, s["EE"][eel]) if eel > a else None,
    }


# ---------- vormistus ----------

def f(k, S, x, kohti=None, suf=True):
    """Number mõõdiku täpsusega; tuhanded tühikuga (4 800)."""
    kohti = S["kohti"] if kohti is None else kohti
    t = k.arv(x, kohti)
    if kohti == 0 and abs(x) >= 1000:
        t = f"{int(round(x)):,}".replace(",", " ")
    return t + (S["suf"] if suf else "")


def pp(k, x, kohti=1):
    """Muutus märgiga: +18,2 või −0,1."""
    return ("+" if x > 0 else "") + k.arv(x, kohti)


def loetelu(sonad):
    return " ja ".join([", ".join(sonad[:-1]), sonad[-1]]) if len(sonad) > 1 else "".join(sonad)


def silt(liik):
    nimi, klass, _ = SILDID[liik]
    return f'<span class="tag {klass}">{nimi}</span>'


def viide(k, K, mid):
    m = K["moodikud"][mid]
    nimi = f'{k.org(K, m)} {m["andmestik"]}'.strip()
    return k.linkita(nimi, m["url"])


def allikad(k, K, mids, lisa=""):
    osad = list(dict.fromkeys(viide(k, K, m) for m in mids)) + ([lisa] if lisa else [])
    return f'<p class="small an-src">Allikad: {"; ".join(osad)}.</p>'


def tip(vaartus, sild):
    return f' data-tip="{vaartus}|{sild}"'


# ---------- graafikud ----------

def indeksi_joonis(k, P):
    """Eesti näitaja Põhjamaade keskmise suhtes (= 100). Üle 100 on alati parem."""
    korgus = max(abs(S["indeks"] - 100) for S in P)
    ulat = max(20, -(-korgus // 20) * 20)
    lo, hi = 100 - ulat, 100 + ulat

    def X(v):
        return (min(max(v, lo), hi) - lo) / (hi - lo) * 100

    read = []
    for S in sorted(P, key=lambda S: -S["indeks"]):
        i = S["indeks"]
        x0, x1 = sorted((X(100), X(i)))
        # Värv tuleb hinnangust, et see klapiks kokkuvõttega: lilla = Põhjamaade tasemel, oranž = maas.
        klass = "up" if S["hinnang"] in ("yle", "vahemik") else "down"
        read.append(
            f'<li><span class="lab">{S["nimi"]}<small>{S["a"]}</small></span>'
            f'<span class="idx-track"{tip(k.arv(i, 0), S["nimi"] + ", Põhjamaade keskmine = 100")}>'
            f'<span class="idx-bar {klass}" style="left:{x0:.1f}%;width:{x1 - x0:.1f}%"></span></span>'
            f'<span class="val">{k.arv(i, 0)}</span></li>')
    skaala = "".join(f"<span>{t}</span>" for t in (int(lo), int((lo + 100) / 2), 100, int((hi + 100) / 2), int(hi)))
    return (f'<ul class="idx" role="list">{"".join(read)}</ul>'
            f'<div class="idx-scale" aria-hidden="true"><span></span><div>{skaala}</div><span></span></div>')


def profiili_joonis(k, P):
    """Iga rida: kõigi riikide väärtused oma skaalal, hall vöö = Põhjamaade vahemik, kriips = EL27."""
    read = []
    teema = None
    for S in P:
        if S["teema"] != teema:
            teema = S["teema"]
            read.append(f'<li class="prof-theme">{teema}</li>')
        v = S["v"]
        lo, hi = min(v.values()), max(v.values())
        pad = (hi - lo) * 0.06 or 1

        def X(x):
            return (x - lo + pad) / (hi - lo + 2 * pad) * 100

        osad = [f'<span class="band" style="left:{X(S["pmin"]):.1f}%;width:{X(S["pmax"]) - X(S["pmin"]):.1f}%"></span>']
        if S["el"] is not None:
            osad.append(f'<span class="eu" style="left:{X(S["el"]):.1f}%"{tip(f(k, S, S["el"]), "EL27 " + str(S["a"]))}></span>')
        for g in sorted(v, key=lambda g: g == "EE"):
            if g == EL:
                continue
            kl = "pt ee" if g == "EE" else "pt"
            osad.append(f'<span class="{kl}" style="left:{X(v[g]):.1f}%"{tip(f(k, S, v[g]), k.riik(g) + " " + str(S["a"]))}></span>')
        nimi, klass = HINNANGUD[S["hinnang"]]
        lingi = S.get("leht")
        pealk = f'<a href="{lingi}">{S["nimi"]}</a>' if lingi else S["nimi"]
        uuem = (f'<small class="hl">Eesti {S["uuem"][0]}: {f(k, S, S["uuem"][1])}</small>' if S["uuem"] else "")
        read.append(
            f'<li class="prof-row"><span class="who">{pealk}<small>{S["uhik"]}, {S["a"]}</small></span>'
            f'<span class="prof-line">{"".join(osad)}</span>'
            f'<span class="v"><b>{f(k, S, S["ee"])}</b><small>{S["koht"]}./{S["n"]}</small>{uuem}</span>'
            f'<span class="verdict"><span class="tag {klass}">{nimi}</span></span></li>')
    legend = ('<div class="an-legend" aria-hidden="true"><span><i class="k-ee"></i>Eesti</span>'
              '<span><i class="k-pt"></i>teised võrdlusriigid</span><span><i class="k-band"></i>Põhjamaade vahemik</span>'
              '<span><i class="k-eu"></i>ELi keskmine</span></div>')
    return legend + f'<ul class="prof" role="list">{"".join(read)}</ul>'


def minijoon(k, S):
    s = S["s"]
    riigid = [g for g in RIIGID7 + [EL] if g in s]
    aastad = sorted({a for g in riigid for a in s[g]})
    W, H = 340, 190
    ml, mr, mt, mb = 50, 86, 12, 24
    a0, a1 = aastad[0], aastad[-1]
    tipp = max(v for g in riigid for v in s[g].values())
    samm = [1, 2, 2.5, 5]
    mag = 10 ** (len(str(int(tipp))) - 1) if tipp >= 1 else 0.1
    st = next(m * mag for m in samm + [10] if tipp / (m * mag) <= 4)
    ymax = -(-tipp // st) * st

    def X(a):
        return ml + (a - a0) / ((a1 - a0) or 1) * (W - ml - mr)

    def Y(v):
        return mt + (1 - v / ymax) * (H - mt - mb)

    osad = []
    t = 0
    while t <= ymax + 1e-9:
        osad.append(f'<line class="gridline" x1="{ml}" x2="{W - mr}" y1="{Y(t):.1f}" y2="{Y(t):.1f}"/>')
        tk = f(k, S, t, 0 if float(st).is_integer() else (1 if float(st * 10).is_integer() else 2), suf=False)
        osad.append(f'<text x="{ml - 6}" y="{Y(t) + 4:.1f}" text-anchor="end">{tk}</text>')
        t += st
    for a in (a0, a1):
        osad.append(f'<text x="{X(a):.1f}" y="{H - 6}" text-anchor="middle">{a}</text>')
    sildid = []
    # Katkendjoon ainult siis, kui aasta on päriselt puudu (mitte iga kahe aasta tagant tehtava küsitluse vahe).
    tavasamm = min((q - p for g in riigid for p, q in zip(sorted(s[g]), sorted(s[g])[1:])), default=1)
    for g in sorted(riigid, key=lambda g: (g == "EE", g == EL)):
        aa = sorted(s[g])
        kl = "focus" if g == "EE" else "ref" if g == EL else ""
        for p, q in zip(aa, aa[1:]):
            gap = " gap" if q - p > tavasamm else ""
            osad.append(f'<path class="ln {kl}{gap}" d="M{X(p):.1f},{Y(s[g][p]):.1f} L{X(q):.1f},{Y(s[g][q]):.1f}"/>')
        if kl:
            osad.append(f'<circle class="dot {kl}" cx="{X(aa[-1]):.1f}" cy="{Y(s[g][aa[-1]]):.1f}" r="{4 if kl == "focus" else 3}"/>')
            nm = "Eesti" if g == "EE" else "EL27"
            sildid.append([Y(s[g][aa[-1]]), f"{nm} {f(k, S, s[g][aa[-1]], suf=False)}", kl])
        for a in aa:
            osad.append(f'<circle class="hit" cx="{X(a):.1f}" cy="{Y(s[g][a]):.1f}" r="7"'
                        f'{tip(f(k, S, s[g][a]), f"{k.riik(g)} {a}")}/>')
    sildid.sort(key=lambda t: t[0])
    for i in range(1, len(sildid)):
        sildid[i][0] = max(sildid[i][0], sildid[i - 1][0] + 15)
    for y, tekst, kl in sildid:
        osad.append(f'<text class="lab-{kl}" x="{W - mr + 7}" y="{y + 4:.1f}">{tekst}</text>')
    return (f'<figure class="mini"><figcaption><b>{S["nimi"]}</b><span class="small">{S["uhik"]}</span></figcaption>'
            f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="{S["nimi"]} {a0}–{a1}, Eesti, ELi keskmine ja võrdlusriigid. '
            f'Väärtused on lehe lõpus tabelis.">{"".join(osad)}</svg></figure>')


def hantlid(k, K, mid, a0):
    S = next(x for x in PROFIIL_S if x["mid"] == mid)
    s, a1 = S["s"], S["a"]
    read = [(g, s[g][a0], s[g][a1]) for g in RIIGID7 + [EL] if a0 in s.get(g, {}) and a1 in s.get(g, {})]
    read.sort(key=lambda t: t[2] - t[1], reverse=not S["vp"])
    vals = [v for _, x, y in read for v in (x, y)]
    lo, hi = min(vals), max(vals)
    pad = (hi - lo) * 0.05

    def X(x):
        return (x - lo + pad) / (hi - lo + 2 * pad) * 100

    rid = []
    for g, x, y in read:
        kl = "is-focus" if g == "EE" else "is-ref" if g == EL else ""
        l, r = sorted((X(x), X(y)))
        nm = "EL27" if g == EL else k.riik(g)
        rid.append(
            f'<li class="{kl}"><span class="lab">{nm}</span><span class="db-track">'
            f'<span class="db-line" style="left:{l:.1f}%;width:{r - l:.1f}%"></span>'
            f'<span class="db-a"{tip(f(k, S, x), f"{nm} {a0}")} style="left:{X(x):.1f}%"></span>'
            f'<span class="db-b"{tip(f(k, S, y), f"{nm} {a1}")} style="left:{X(y):.1f}%"></span></span>'
            f'<span class="val">{pp(k, y - x, S["kohti"])}</span></li>')
    yhik = "punkti" if S["suf"] == "%" else ""
    return (f'<figure class="dumb"><figcaption><b>{S["nimi"]}</b><span class="small">{a0} → {a1}, muutus {yhik}'
            f' ({S["uhik"]})</span></figcaption>'
            f'<ul role="list">{"".join(rid)}</ul>'
            f'<div class="db-scale" aria-hidden="true"><span></span><div><span>{f(k, S, lo)}</span><span>{f(k, S, hi)}</span></div><span></span></div>'
            '</figure>')


# ---------- tõlgendused ----------



def kaart(k, K, liik, pealkiri, kehtib, plokid, mids, lisa="", pilt="", lihtne=""):
    """Üks tõlgenduskaart: pealkiri, graafik ja üks lihtne lause on kohe näha,
    põhjendus tekstina (fakt, arvutus, tõlgendus, piirang) avaneb klõpsuga.
    Kui tingimus ei kehti, märgitakse kaart ülevaatamiseks."""
    hoiatus = ""
    if not kehtib:
        print(f"Hoiatus (analüüs): tõlgendus „{pealkiri}“ ei pruugi enam kehtida, andmed on muutunud.", file=sys.stderr)
        hoiatus = ('<p class="an-stale">Andmed on pärast selle teksti kirjutamist muutunud ja tingimus, millel see '
                   'tõlgendus põhineb, enam ei kehti. Numbrid on uued, aga tekst vajab ülevaatamist.</p>')
    sisu = "".join(f'<div class="an-claim">{silt(s)}<p>{t}</p></div>' for s, t in plokid if t)
    pilt = f'<div class="an-vis">{pilt}</div>' if pilt else ""
    lihtne = f'<p class="an-plain">{lihtne}</p>' if lihtne else ""
    return (f'<article class="an-card {liik}">'
            f'<h3>{pealkiri}</h3>{hoiatus}{pilt}{lihtne}'
            f'<details class="an-more"><summary>Loe põhjendus tekstina</summary><div class="an-more-body">{sisu}</div></details>'
            f'{allikad(k, K, mids, lisa)}</article>')


def vaartus(K, mid, riik, aasta):
    s = seeria(K, mid)
    return s.get(riik, {}).get(aasta)


def mprof(k, S, sild=None):
    """Kompaktne profiilirida kaardile: kõik riigid, Põhjamaade vöö, ELi kriips, Eesti väärtus."""
    punktid = [(k.riik(g), v, f(k, S, v), g == "EE") for g, v in S["v"].items() if g != EL]
    el = (S["el"], f(k, S, S["el"])) if S["el"] is not None else None
    rida = pildid.asukoht(punktid, el=el, vahemik=(S["pmin"], S["pmax"]), sildid=False)
    return (f'<div class="mprof"><span class="lab">{sild or S["nimi"]}<small>{S["a"]}</small></span>{rida}'
            f'<span class="v">{f(k, S, S["ee"])}<small>{S["koht"]}./{S["n"]}</small></span></div>')


MPROF_LEGEND = ('<div class="an-legend" aria-hidden="true"><span><i class="k-ee"></i>Eesti</span>'
                '<span><i class="k-pt"></i>teised</span><span><i class="k-band"></i>Põhjamaad</span>'
                '<span><i class="k-eu"></i>EL</span></div>')


def riigitulbad(k, S, ref_el=True, sild=None):
    read = sorted(((k.riik(g), v, f(k, S, v), "ee" if g == "EE" else "") for g, v in S["v"].items() if g != EL),
                  key=lambda t: t[1], reverse=not S["vp"])
    ref = (S["el"], f"ELi keskmine {f(k, S, S['el'])}") if ref_el and S["el"] is not None else None
    pais = f'<p class="an-vis-title">{sild or S["nimi"]}, {S["a"]}</p>'
    return pais + pildid.tulbad(read, ref=ref)


def tolgendused(k, D, K, P):
    S = {x["mid"]: x for x in P}
    iu, it, eb = S["eurostat-isoc-ai-iaiu"], S["eurostat-isoc-ai-iaiu-too"], S["eurostat-isoc-eb-ai"]
    osk, dig, ikt = S["eurostat-isoc-ai-iaiuxr-oskus"], S["eurostat-isoc-sk-dskl-i21"], S["eurostat-isoc-sks-itspt"]
    lop, ta, tead = S["uis-ikt-lopetajad"], S["eurostat-rd-e-gerdtot"], S["uis-teadlased"]
    kuusalt = next((r for r in D["riskid"] if "ddn-20251211" in r.get("url", "")), None)
    kys_lisa = k.linkita("Eurostati uudis 11.12.2025 küsimustiku muutusest", kuusalt["url"]) if kuusalt else ""
    tugev, nork, fookus = [], [], []

    def kk(x, kohti=1):
        return k.arv(x, kohti)

    # 1. Inimeste kasutus
    ee26, ee25 = vaartus(K, "sa-it71", "EE", 2026), vaartus(K, "sa-it71", "EE", 2025)
    no26, no25 = vaartus(K, "ssb-14365", "NO", 2026), vaartus(K, "ssb-14365", "NO", 2025)
    se26, se25 = vaartus(K, "scb-tab6388", "SE", 2026), vaartus(K, "scb-tab6388", "SE", 2025)
    kasv = [("Eesti", ee26 - ee25), ("Norra", no26 - no25), ("Rootsi", se26 - se25)] if None not in (ee26, ee25, no26, no25, se26, se25) else []
    kasvu_lause, suurim_kasv = "", None
    if kasv:
        suurim_kasv = max(kasv, key=lambda t: t[1])[0]
        kasvu_lause = (f" 2025→2026 kasvas see riikide endi tabelite järgi Eestis {kk(kasv[0][1])}, Norras "
                       f"{kk(kasv[1][1], 0)} ja Rootsis {kk(kasv[2][1], 0)} punkti: kasv oli suurim riigis {suurim_kasv}.")
    pilt = MPROF_LEGEND + mprof(k, iu, "Kasutab generatiivset tehisaru") + mprof(k, it, "Kasutab seda tööl")
    if kasv:
        pilt += ('<p class="an-vis-title">Riikide endi numbrid 2025 → 2026</p>'
                 + pildid.hantlid([("Eesti", ee25, ee26, "+" + kk(ee26 - ee25), "ee", f"{kk(ee25)}%", f"{kk(ee26)}%"),
                                   ("Norra", no25, no26, "+" + kk(no26 - no25, 0), "", f"{kk(no25, 0)}%", f"{kk(no26, 0)}%"),
                                   ("Rootsi", se25, se26, "+" + kk(se26 - se25, 0), "", f"{kk(se25, 0)}%", f"{kk(se26, 0)}%")],
                                  "2025", "2026"))
    tugev.append(kaart(k, K, "tugev", "Inimeste tehisaru kasutus on Põhjamaade tasemel",
        iu["hinnang"] in ("vahemik", "yle") and it["hinnang"] in ("vahemik", "yle"),
        [("fakt", f"{iu['a']}. aastal kasutas generatiivset tehisaru {f(k, iu, iu['ee'])} Eesti 16–74-aastastest "
                  f"(ELis {f(k, iu, iu['el'])}, Põhjamaades {f(k, iu, iu['pmin'], suf=False)}–{f(k, iu, iu['pmax'])}). "
                  f"Tööalaselt kasutas seda {f(k, it, it['ee'])} (ELis {f(k, it, it['el'])}). Eesti on vastavalt "
                  f"{iu['koht']}. ja {it['koht']}. kohal {iu['n']}-st."
                  + (f" Riikide endi 2026. aasta numbrid: Eesti {kk(ee26)}%, Norra {kk(no26, 0)}%, Rootsi {kk(se26, 0)}%." if kasv else "")),
         ("arvutus", "Eesti on mõlemal näitajal Põhjamaade vahemikus ja ELi keskmisest üle 10 punkti eespool." + kasvu_lause
          if iu["ee"] - iu["el"] > 10 and it["ee"] - it["el"] > 5 else "Eesti on mõlemal näitajal Põhjamaade vahemikus." + kasvu_lause),
         ("tolgendus", "Elanike poolel ei ole Eesti tehisaru kasutuses maas. Kui Eesti jääb kuskil maha, siis mitte selles, "
                       "kas inimesed tööriistu proovivad."),
         ("piirang", "Näitaja ütleb, kas inimene kasutas tööriista viimase 3 kuu jooksul, mitte kui sageli, milleks ega kui oskuslikult. "
                     "2026. aasta numbrid on riikide endi avaldused enne Eurostati. Rootsi number on täisarvuni ümardatud ja selle veapiir on ±2 punkti.")],
        ["eurostat-isoc-ai-iaiu", "eurostat-isoc-ai-iaiu-too", "sa-it71", "ssb-14365", "scb-tab6388"],
        pilt=pilt,
        lihtne=(f"Eesti punkt on Põhjamaade hallil alal ja ELi kriipsust kaugel paremal."
                + (f" 2026. aastal kasvas kasutus Eestis kõige rohkem." if suurim_kasv == "Eesti" else ""))))

    # 2. IKT lõpetajad ja spetsialistid
    teine = lop["jrk"][1] if lop["koht"] == 1 else lop["jrk"][0]
    tugev.append(kaart(k, K, "tugev", "IKT eriala lõpetajaid on suhteliselt kõige rohkem",
        lop["koht"] == 1 and ikt["hinnang"] in ("vahemik", "yle"),
        [("fakt", f"{lop['a']}. aastal lõpetas IKT eriala {f(k, lop, lop['ee'])} Eesti kõrgkoolide lõpetajatest, järgmisena "
                  f"{k.riik(teine)} {f(k, lop, lop['v'][teine])}."
                  + (f" Eesti {lop['uuem'][0]}. aasta number on {f(k, lop, lop['uuem'][1])}." if lop["uuem"] else "")
                  + f" IKT-spetsialiste oli {ikt['a']}. aastal {f(k, ikt, ikt['ee'])} hõivatutest (ELis {f(k, ikt, ikt['el'])}), "
                  f"Eesti on {ikt['koht']}. kohal {ikt['n']}-st."),
         ("arvutus", f"IKT-spetsialistide osakaal muutus Eestis {ikt['a'] - 1}→{ikt['a']} "
                     f"{pp(k, ikt['ee'] - ikt['s']['EE'].get(ikt['a'] - 1, ikt['ee']))} punkti."),
         ("tolgendus", "Eesti haridus suunab IKT-sse suurema osa lõpetajatest kui võrdlusriigid ja IKT-spetsialiste on hõivatute seas "
                       "ELi keskmisest tunduvalt rohkem. Tehnilise tööjõu pakkumine on suhteline tugevus."),
         ("piirang", "Osakaal ei ütle lõpetajate arvu ega oskuste taset. Väikese lõpetajate koguarvu tõttu kõigub osakaal aastati. "
                     "UNESCO andmetes pole seires ELi keskmist. Üheaastane muutus tööjõu-uuringus võib olla valimi kõikumine.")],
        ["uis-ikt-lopetajad", "eurostat-isoc-sks-itspt"],
        pilt=riigitulbad(k, lop, sild="IKT lõpetajad, % kõrgkoolide lõpetajatest") + MPROF_LEGEND + mprof(k, ikt, "IKT-spetsialistid hõivatute seas"),
        lihtne=f"Eesti tulp on kõige pikem: iga {round(100 / lop['ee'])}. kõrgkooli lõpetaja on IKT erialalt."))

    # 3. Oskuse puudus (nõrk tõend)
    sa72 = vaartus(K, "sa-it72-oskus", "EE", osk["a"])
    read = [("Eesti, Eurostat", osk["ee"], f(k, osk, osk["ee"]), "ee")]
    if sa72 is not None:
        read.append(("Eesti, Statistikaamet", sa72, f"{kk(sa72)}%", "risk"))
    read.append(("ELi keskmine", osk["el"], f(k, osk, osk["el"]), "eu"))
    tugev.append(kaart(k, K, "tugev", "Oskuse puudus ei paista olevat peamine takistus, aga tõend on nõrk",
        osk["hinnang"] in ("vahemik", "yle"),
        [("fakt", f"Eurostati järgi ütles {osk['a']}. aastal {f(k, osk, osk['ee'])} Eesti elanikest, et nad ei kasutanud "
                  f"generatiivset tehisaru, sest ei osanud (ELis {f(k, osk, osk['el'])}, Põhjamaades "
                  f"{f(k, osk, osk['pmin'], suf=False)}–{f(k, osk, osk['pmax'])})."),
         ("piirang", "Statistikaameti tabel IT72 annab Eesti kohta "
                     + (f"{kk(sa72)}%" if sa72 is not None else "teise numbri")
                     + " (lahknevus C6, põhjus selgitamata). Eurostat paneb iga mittekasutaja ühe põhjuse alla, Statistikaamet "
                       "võib lubada mitut. Kuni see on selgitamata, ei saa sellele järeldusele toetuda."),
         ("tolgendus", "Kui Eurostati number peab paika, ei ole oskuste puudus Eestis suurem probleem kui Põhjamaades.")],
        ["eurostat-isoc-ai-iaiuxr-oskus", "sa-it72-oskus"],
        pilt=f'<p class="an-vis-title">„Ei kasuta, sest ei oska“, % 16–74-aastastest, {osk["a"]}</p>' + pildid.tulbad(read),
        lihtne=("Eurostati järgi on Eestis neid vähem kui ELis keskmiselt. Statistikaamet annab samale küsimusele "
                f"{kk(sa72 / osk['ee'], 0)} korda suurema numbri, nii et see järeldus on ebakindel." if sa72 else
                "Eurostati järgi on Eestis neid vähem kui ELis keskmiselt.")))

    # 4. Ettevõtted
    g = {a: eb["s"]["EE"][a] - mean(eb["s"][c][a] for c in POHJA) for a in sorted(eb["s"]["EE"])}
    r = {a: eb["s"]["EE"][a] / mean(eb["s"][c][a] for c in POHJA) * 100 for a in g}
    a0 = 2023 if 2023 in g else min(g)
    a1 = eb["a"]
    d_ee = eb["s"]["EE"][a1] - eb["s"]["EE"][a0]
    d_pk = mean(eb["s"][c][a1] - eb["s"][c][a0] for c in POHJA)
    it149 = vaartus(K, "sa-it149", "EE", a1)
    r26 = {m: vaartus(K, m, c, 2026) for m, c in (("sa-it1490", "EE"), ("dst-itav28", "DK"), ("ssb-ikt", "NO"))}
    aa = [a for a in sorted(g) if a >= a0]
    pk = {a: mean(eb["s"][c][a] for c in POHJA) for a in aa}
    pilt = (pildid.jooned(
        [("Eesti", {a: eb["s"]["EE"][a] for a in aa}, "focus"), ("Põhjamaad", pk, "ref")],
        lambda v, kohti=1: k.arv(v, kohti),
        vahemik={a: (min(eb["s"][c][a] for c in POHJA), max(eb["s"][c][a] for c in POHJA)) for a in aa},
        markused=[(a0, eb["s"]["EE"][a0], pk[a0], f"{kk(g[a0])} p"), (a1, eb["s"]["EE"][a1], pk[a1], f"{kk(g[a1])} p")],
        kirjeldus=f"Eesti ja Põhjamaade keskmine {a0}–{a1}: vahe {kk(g[a0])} ja {kk(g[a1])} punkti")
        + '<div class="an-legend" aria-hidden="true"><span><i class="k-ln-ee"></i>Eesti</span>'
          '<span><i class="k-ln-eu"></i>Põhjamaade keskmine</span><span><i class="k-band"></i>Põhjamaade vahemik</span></div>'
        + pildid.numbrid([("Vahe protsendipunktides", f"{kk(g[a0])}", f"{kk(g[a1])}", f"{a0} → {a1}: vahe kasvas"),
                          ("Eesti Põhjamaade keskmisest", f"{kk(r[a0], 0)}%", f"{kk(r[a1], 0)}%", f"{a0} → {a1}: suhe paranes")]))
    nork.append(kaart(k, K, "nork", "Ettevõtete tehisaru kasutus jääb Põhjamaadest maha ja vahe protsendipunktides kasvab",
        eb["hinnang"] in ("maas", "alla_el") and g[a1] < g[a0],
        [("fakt", f"{a1}. aastal kasutas tehisaru {f(k, eb, eb['ee'])} Eesti vähemalt 10 hõivatuga ettevõtetest, ELis "
                  f"{f(k, eb, eb['el'])}, Põhjamaades {f(k, eb, eb['pmin'], suf=False)}–{f(k, eb, eb['pmax'])}. Eesti on "
                  f"{eb['koht']}. kohal {eb['n']}-st."),
         ("arvutus", f"{a0}→{a1} kasvas Eesti {kk(d_ee)} punkti, Põhjamaade keskmine {kk(d_pk)} punkti. Vahe "
                     f"Põhjamaade keskmisega oli {a0} {kk(g[a0])} ja {a1} {kk(g[a1])} punkti. Suhtena on Eesti tase "
                     f"{kk(r[a0], 0)}%-lt {kk(r[a1], 0)}%-le Põhjamaade keskmisest."),
         ("tolgendus", "Mõlemad väited on õiged: suhtena jõuab Eesti järele, protsendipunktides jääb maha. „Eesti jõuab järele“ "
                       "on õige ainult siis, kui öelda, et see käib suhte kohta. Kõigist seire näitajatest on siin Eesti vahe "
                       "Põhjamaadega tehisaru kasutuses suurim."),
         ("piirang", "2025. aastal lisandus küsimustikku piltide, video ja heli genereerimine, mis tõstab kõigi riikide numbreid. "
                     + (f"Statistikaameti tabel IT149 annab {a1} kohta {kk(it149)}% (lahknevus C5). " if it149 else "")
                     + ("Riikide 2026. aasta numbrid (Eesti {}%, Taani {}%, Norra {}%) on uute tegevusalade klassifikaatoritega, "
                        "nii et neid ei järjestata ega arvutata nendest kasvu.".format(
                            *(kk(r26[m], 1 if m == "sa-it1490" else 0) for m in r26)) if None not in r26.values() else ""))],
        ["eurostat-isoc-eb-ai", "sa-it149", "sa-it1490", "dst-itav28", "ssb-ikt"], kys_lisa,
        pilt=pilt,
        lihtne=(f"Eesti joon tõuseb järsult, aga Põhjamaade joon veel järsemalt, nii et vahe läks laiemaks. "
                f"Suhtena läheneb Eesti Põhjamaadele, punktides kaugeneb.")))

    # 6. Digioskused
    s = dig["s"]
    a_eel = max(a for a in s["EE"] if a < dig["a"])
    muut = {c: s[c][dig["a"]] - s[c][a_eel] for c in RIIGID7 + [EL] if a_eel in s.get(c, {}) and dig["a"] in s.get(c, {})}
    suurim = max((c for c in muut if c != EL), key=lambda c: muut[c])
    aa = sorted(s["EE"])
    pilt = (pildid.jooned(
        [("Eesti", {a: s["EE"][a] for a in aa}, "focus"), ("EL27", {a: s[EL][a] for a in aa if a in s[EL]}, "ref")],
        lambda v, kohti=1: k.arv(v, kohti),
        vahemik={a: (min(s[c][a] for c in POHJA), max(s[c][a] for c in POHJA)) for a in aa},
        sihid=[(80, "siht 2030"), (70, "siht 2025")], ymax=100,
        kirjeldus=f"Digioskused {aa[0]}–{aa[-1]}: Eesti, EL ja Põhjamaade vahemik, ELi sihid 70% ja 80%")
        + '<div class="an-legend" aria-hidden="true"><span><i class="k-ln-ee"></i>Eesti</span>'
          '<span><i class="k-ln-eu"></i>ELi keskmine</span><span><i class="k-band"></i>Põhjamaade vahemik</span>'
          '<span><i class="k-target"></i>ELi siht</span></div>')
    nork.append(kaart(k, K, "nork", "Digioskused on Põhjamaadest madalamad ega kasvanud viimasel perioodil",
        dig["hinnang"] in ("maas", "alla_el") and abs(muut["EE"]) < 1,
        [("fakt", f"Vähemalt baastasemel digioskused olid {dig['a']}. aastal {f(k, dig, dig['ee'])} Eesti 16–74-aastastest "
                  f"(ELis {f(k, dig, dig['el'])}, Põhjamaades {f(k, dig, dig['pmin'], suf=False)}–{f(k, dig, dig['pmax'])}). "
                  "ELi digikümnendi siht on 80% aastaks 2030."),
         ("arvutus", f"{a_eel}→{dig['a']} muutus: Eesti {pp(k, muut['EE'])}, EL {pp(k, muut[EL])}, suurim {k.riik(suurim)} "
                     f"{pp(k, muut[suurim])} punkti. Eesti vahe 2030. aasta sihiga on {kk(80 - dig['ee'])} punkti."),
         ("tolgendus", f"Eesti on ELi keskmisest {kk(dig['ee'] - dig['el'])} punkti eespool"
                       + (f" ja vahe ELiga on vähenenud ({a_eel}. aastal {kk(s['EE'][a_eel] - s[EL][a_eel])} punkti)"
                          if s["EE"][a_eel] - s[EL][a_eel] > dig["ee"] - dig["el"] else "")
                       + f". Põhjamaadest jääb Eesti maha {kk(dig['pmin'] - dig['ee'])}–{kk(dig['pmax'] - dig['ee'])} punktiga. "
                       "Kõrge tehisaru kasutus ja keskpärane digioskuste tase käivad Eestis koos."),
         ("piirang", "Näitaja põhineb sellel, mida inimesed ütlevad end teinud olevat (viis valdkonda), mitte oskuste testil. "
                     "Tehisaru oskust see otse ei mõõda. Testipõhist võrdlust (OECD PIAAC) seire veel ei kasuta.")],
        ["eurostat-isoc-sk-dskl-i21"],
        pilt=pilt,
        lihtne=(f"Eesti joon on {a_eel}–{dig['a']} lame, ELi joon tõuseb ja jõuab Eestile järele. "
                f"Põhjamaade hall ala ja 2030. aasta siht on Eestist kõrgemal.")))

    # 7. Teadus ja arendus
    s = ta["s"]["EE"]
    t0 = min(s)
    pilt = ('<div class="an-vis-two"><div>' + riigitulbad(k, ta, sild="T&A kulu, % SKPst") + "</div><div>"
            + riigitulbad(k, tead, sild="Teadlasi miljoni elaniku kohta") + "</div></div>")
    nork.append(kaart(k, K, "nork", "Teadus- ja arendustegevuse baas on väike",
        ta["hinnang"] == "alla_el" and tead["koht"] == tead["n"],
        [("fakt", f"T&A kulu oli {ta['a']}. aastal {f(k, ta, ta['ee'])} Eesti SKPst, ELis {f(k, ta, ta['el'])}. "
                  f"Teadlasi oli {tead['a']}. aastal Eestis {f(k, tead, tead['ee'])} miljoni elaniku kohta, teistes "
                  f"võrdlusriikides {f(k, tead, min(v for c, v in tead['v'].items() if c not in ('EE', EL)))}–"
                  f"{f(k, tead, max(v for c, v in tead['v'].items() if c not in ('EE', EL)))}."),
         ("arvutus", f"Eesti T&A kulu kasvas {t0} {f(k, ta, s[t0])} → {ta['a']} {f(k, ta, s[ta['a']])} SKPst. "
                     f"Eesti on teadlaste arvult {tead['koht']}. kohal {tead['n']}-st."),
         ("tolgendus", "Need on pikaajalised struktuursed näitajad, mitte tehisaru näitajad. Need piiravad, kui palju tehisaru "
                       "uurimis- ja arendustööd Eestis saab teha, ning seletavad osaliselt, miks Eesti on tugevam kasutaja kui arendaja "
                       "(viimane on hüpotees)."),
         ("piirang", "T&A kulu protsent sõltub ka SKP suurusest. UNESCO teadlaste andmetes pole seires ELi keskmist. "
                     "Seires pole veel tehisaru investeeringute ega tehisaru teadustöö ametlikku näitajat.")],
        ["eurostat-rd-e-gerdtot", "uis-teadlased"],
        pilt=pilt,
        lihtne=(f"Eesti T&A kulu jääb alla ELi joone ja teadlaste tulp on kõige lühem: umbes "
                f"{kk(tead['ee'] / mean(v for c, v in tead['v'].items() if c not in ('EE', EL)) * 100, 0)}% teiste riikide keskmisest.")))

    # Fookus
    vahe_iu = iu["ee"] - iu["pk"]
    vahed = [("Inimesed", iu["ee"] - iu["pk"]), ("Tööl", it["ee"] - it["pk"]), ("Ettevõtted", eb["ee"] - eb["pk"])]
    fookus.append(kaart(k, K, "fookus", "Suurim vahe on ettevõtetes, mitte inimestes",
        g[a1] < vahe_iu,
        [("arvutus", f"Vahe Põhjamaade keskmisega {a1}: ettevõtted {kk(g[a1])} punkti, inimesed {kk(vahe_iu)} punkti."),
         ("hupotees", "Kui inimesed kasutavad tehisaru Põhjamaade tasemel, aga ettevõtted mitte, võib takistus olla ettevõtete "
                      "poolel (investeeringud, juhtimine, protsessid), mitte inimeste valmisolekus. Seire andmed seda ei tõesta."),
         ("piirang", "Kaks eri küsitlust ja eri kogumit: ettevõtted on vähemalt 10 hõivatuga ettevõtted, inimesed 16–74-aastased."),
         ("soovitus", "Kui küsimus on, kus Eesti tehisaru kasutuses Põhjamaadest maha jääb, siis vaata ettevõtteid. "
                      "Järgmine samm seires on tegevusalade ja ettevõtte suuruse jaotus (isoc_eb_ain2), et näha, millistes "
                      "harudes vahe tekib.")],
        ["eurostat-isoc-eb-ai", "eurostat-isoc-ai-iaiu"],
        pilt=(f'<p class="an-vis-title">Eesti vahe Põhjamaade keskmisega, protsendipunkti, {a1}</p>'
              + pildid.lahknev([(n, v, pp(k, v)) for n, v in vahed])),
        lihtne="Oranž tulp ettevõtete juures on teistest mitu korda pikem. Sealt tasub vahe põhjust otsida."))
    fookus.append(kaart(k, K, "fookus", "Ütle täpselt, millises mõttes Eesti on tehisaru kasutuses „Põhjamaade tasemel“",
        iu["hinnang"] in ("vahemik", "yle") and eb["hinnang"] in ("maas", "alla_el"),
        [("soovitus", "Õige: „Eesti inimesed kasutavad generatiivset tehisaru Põhjamaade tasemel, ettevõtted jäävad "
                      "Põhjamaadest maha, kuigi on ELi keskmisest eespool.“ Vale: „Eesti on tehisaru kasutuses Põhjamaade tasemel.“"),
         ("piirang", "Tehisaru kasutus ei ole sama mis tehisaru oskus, arendus ega mõju tootlikkusele. Neid seire ei mõõda.")],
        ["eurostat-isoc-ai-iaiu", "eurostat-isoc-eb-ai"],
        pilt=pildid.oige_vale("„Eesti inimesed kasutavad tehisaru Põhjamaade tasemel, ettevõtted jäävad maha.“",
                              "„Eesti on tehisaru kasutuses Põhjamaade tasemel.“"),
        lihtne="Ütle alati, kas räägid inimestest või ettevõtetest."))
    lungad = [m for m in K["moisted"].values()
              if not any(v["moodik"] == m["vordlusalus"] for v in K["vaatlused"])]
    teemad = pildid.kataloogi_teemad(K)
    fookus.append(kaart(k, K, "fookus", f"{len(lungad)} küsimusele pole veel võrreldavaid andmeid",
        True,
        [("fakt", "Andmeteta küsimused: " + ", ".join(m["nimi"].lower() if i else m["nimi"] for i, m in enumerate(lungad)) + "."),
         ("soovitus", "Enne järelduste tegemist tööturu ja investeeringute kohta tuleb need andmed leida. Kaks lahknevust "
                      "(C5 ja C6) ootavad Statistikaameti vastust.")],
        [], k.linkita("seire kataloog", "teemad.html"),
        pilt=pildid.kattuvus(teemad, OLEKU_NIMED, link="teemad.html", kompaktne=True),
        lihtne="Iga ruut on üks küsimus. Lilla ja hall ruut tähendab, et andmed on olemas; valge või oranžiga ääristatud ruut, et pole."))
    return tugev, nork, fookus


OLEKU_NIMED = {"seires": "seire laeb automaatselt", "andmed": "andmed kataloogis",
               "kavandatud": "andmestik teada, laadimata", "allikas_leidmata": "allikas leidmata"}


# ---------- leht ----------

PROFIIL_S = []


def andmete_csv(K, P):
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["moodik", "nimi", "uhik", "riik", "aasta", "vaartus", "allikas", "andmestik", "url", "vorreldavus"])
    for S in P:
        m = K["moodikud"][S["mid"]]
        for g in RIIGID7 + [EL]:
            for a in sorted(S["s"].get(g, {})):
                w.writerow([S["mid"], S["nimi"], S["uhik"], g, a, S["s"][g][a], m["allikas"], m["andmestik"], m["url"], m["vorreldavus"]])
    return buf.getvalue()


def koondtabel(k, K, P):
    pea = "".join(f'<th class="r" scope="col">{"EL27" if g == EL else k.riik(g)}</th>' for g in RIIGID7 + [EL])
    read = []
    for S in P:
        lahtrid = "".join(
            f'<td class="r{" is-ee" if g == "EE" else ""}">{f(k, S, S["v"][g], suf=False) if g in S["v"] else "–"}</td>'
            for g in RIIGID7 + [EL])
        read.append(f'<tr><th scope="row">{S["nimi"]}<br><span class="small">{S["uhik"]}</span></th><td>{S["a"]}</td>{lahtrid}'
                    f'<td class="r">{f(k, S, S["pk"], suf=False)}</td><td class="small">{viide(k, K, S["mid"])}</td></tr>')
    return ('<div class="table-wrap"><table class="an-table"><caption>Iga mõõdiku viimane aasta, mille kohta on andmed Eestil ja '
            'vähemalt viiel teisel võrdlusriigil. Põhjamaade keskmine on Soome, Rootsi, Taani ja Norra kaalumata keskmine (seire arvutus).</caption>'
            f'<thead><tr><th scope="col">Mõõdik</th><th scope="col">Aasta</th>{pea}<th class="r" scope="col">Põhja&shy;maad</th>'
            f'<th scope="col">Allikas</th></tr></thead><tbody>{"".join(read)}</tbody></table></div>')


def riiklike_tabel(k, K):
    read = []
    for nimi, mids, alus in RIIKLIKUD:
        for mid in mids:
            m = K["moodikud"].get(mid)
            if not m:
                continue
            s = seeria(K, mid)
            for g, aa in s.items():
                a1 = max(aa)
                a0 = a1 - 1
                v1 = aa[a1]
                kohti = min(tapsus(K, mid, g, a1), 1)
                muutus = "–"
                if a0 in aa and m["vorreldavus"] == "sama":
                    muutus = pp(k, v1 - aa[a0], kohti)
                elif a0 in aa and mid == "dst-itav28":
                    muutus = pp(k, v1 - aa[a0], 0)
                eus = seeria(K, alus).get(g, {})
                eua = max(eus) if eus else None
                read.append(
                    f'<tr class="{"is-focus" if g == "EE" else ""}"><td>{nimi}</td><th scope="row">{k.riik(g)}</th><td>{a1}</td>'
                    f'<td class="r">{k.arv(v1, kohti)}%</td><td class="r">{muutus}</td>'
                    f'<td class="r">{k.arv(eus[eua], 1) + f"% ({eua})" if eua else "–"}</td>'
                    f'<td>{k.klassi_tag(m["vorreldavus"])}</td><td class="small">{viide(k, K, mid)}</td></tr>')
    return ('<div class="table-wrap"><table><caption>Muutus on arvutatud ainult siis, kui sama tabel annab mõlemad aastad sama '
            'määratlusega. Eesti ja Norra ettevõtete 2026. aasta number on uue tegevusalade klassifikaatoriga, nii et kasvu ei arvutata. '
            'Taani tabel on arvutanud ka varasemad aastad uue klassifikaatori järgi ümber.</caption>'
            '<thead><tr><th scope="col">Näitaja</th><th scope="col">Riik</th><th scope="col">Aasta</th><th class="r" scope="col">Väärtus</th>'
            '<th class="r" scope="col">Muutus aastaga, punkti</th><th class="r" scope="col">Eurostati viimane number</th>'
            '<th scope="col">Võrreldavus Eurostatiga</th><th scope="col">Allikas</th></tr></thead>'
            f'<tbody>{"".join(read)}</tbody></table></div>')


def piirangud(k, D, K):
    nimed = {x["n"]["id"]: x["n"]["nimi"] for x in D["naitajad"]}
    lahk = "".join(
        f'<li><b>{k.e(r["kood"])}</b> ({k.e(nimed.get(r["naitaja"], r["naitaja"]).lower())}, {k.e(r["aasta"])}): '
        f'{k.e(r["staatus"])}. {k.e(r["jargmine_samm"])}</li>'
        for r in D["lahknevused"])
    p = [
        "Põhjamaade keskmine on Soome, Rootsi, Taani ja Norra lihtne keskmine, mitte rahvaarvuga kaalutud. See on seire arvutus, mitte ametlik näitaja.",
        "Hinnang „Põhjamaade vahemikus“ tähendab, et Eesti number on Põhjamaade väikseima ja suurima väärtuse vahel. "
        "Norra on mitmel näitajal teistest kaugel (näiteks T&A kulu), mis teeb vahemiku laiaks.",
        "OECD numbrid ELi riikide kohta tulevad Eurostatist, nii et need ei ole sõltumatu kinnitus. Seepärast kasutab see leht ainult võrdlusaluseid.",
        "Ettevõtete 2021. aasta väärtusi ei kasutata kasvu arvutamiseks: Taani number langes 2021→2023 ligi 9 punkti ja seire ei ole põhjust kontrollinud.",
        "UNESCO andmetes ei ole kõigil riikidel sama viimast aastat. Leht võrdleb ühist aastat ja näitab Eesti uuemat numbrit eraldi.",
        "Riikide endi 2026. aasta numbrid ei ole Eurostati võrdlusaluses. Neid näidatakse eraldi tabelis ja järjestatakse ainult siis, kui määratlus on sama.",
    ]
    return (f'<h3>Avatud lahknevused</h3><ul class="plain">{lahk}</ul>'
            + k.avatav(f"{len(p)} metoodilist piirangut", f'<ul class="plain">{"".join(f"<li>{t}</li>" for t in p)}</ul>'))


def analuusi_leht(k, D, K, tana):
    """Tagastab {failinimi: sisu}: analüüsileht ja selle andmed CSV-na."""
    P = [S for S in (statistika(K, r) for r in PROFIIL) if S]
    PROFIIL_S[:] = P
    for S in P:
        n = K["moodikud"][S["mid"]].get("naitaja")
        if n and any(x["n"]["id"] == n for x in D["naitajad"]):
            S["leht"] = f"{n}.html"
    tugev, nork, fookus = tolgendused(k, D, K, P)
    hea = [S for S in P if S["hinnang"] in ("yle", "vahemik")]
    halb = [S for S in P if S["hinnang"] in ("maas", "alla_el", "alla_pohja")]

    hyppe = '<nav class="an-jump" aria-label="Lehe osad">' + "".join(
        f'<a href="#{a}">{t}</a>' for a, t in (("tolgendus", "Tugev ja nõrk"), ("muutus", "Kas vahe väheneb"),
                                              ("profiil", "Kõik riigid"), ("fookus", "Millele keskenduda"),
                                              ("andmed", "Andmed ja piirangud"))) + "</nav>"
    ava = (
        '<div class="an-hero">'
        '<div class="an-hero-head"><div><p class="eyebrow">Analüütiku vaade</p><h1>Eesti Põhjamaade kõrval</h1>'
        f'<p class="an-hero-sub">Maas on {loetelu([S["sona"] for S in halb])}.</p></div>'
        '<div class="an-score" aria-label="Kokkuvõte">'
        f'<p class="up"><b>{len(hea)}</b><span>näitajat Põhjamaade tasemel</span></p>'
        f'<p class="down"><b>{len(halb)}</b><span>näitajat Põhjamaadest maas</span></p></div></div>'
        '<p class="small">Tulp näitab Eestit Põhjamaade keskmise (100) suhtes; üle 100 on Eestile parem. '
        '<span class="k-up">Lilla</span>: Põhjamaade vahemikus või üle, <span class="k-down">oranž</span>: maas. '
        'Vahemikus olla võib ka alla keskmise.</p>'
        + indeksi_joonis(k, P) + hyppe + "</div>")

    sisu = (
        ava
        + k.sektsioon("Tugevad ja nõrgad küljed",
                      '<div class="an-duo">'
                      f'<div><h3 class="an-col up">Tugev ({len(tugev)})</h3>' + "".join(tugev) + "</div>"
                      f'<div><h3 class="an-col down">Nõrk ({len(nork)})</h3>' + "".join(nork) + "</div></div>",
                      "Mida andmed ütlevad", "tolgendus")
        + k.sektsioon("Kas vahe väheneb?",
                      '<div class="an-legend" aria-hidden="true"><span><i class="k-db-a"></i>algusaasta</span>'
                      '<span><i class="k-db-b"></i>viimane aasta</span></div>'
                      '<div class="an-grid two">' + "".join(hantlid(k, K, m, a0) for m, a0 in MUUTUSED if any(S["mid"] == m for S in P)) + "</div>"
                      + k.avatav("Näita kõiki aegridu (6 graafikut)",
                                 '<div class="an-legend" aria-hidden="true"><span><i class="k-ln-ee"></i>Eesti</span>'
                                 '<span><i class="k-ln-eu"></i>ELi keskmine</span><span><i class="k-ln"></i>teised võrdlusriigid</span>'
                                 '<span><i class="k-ln-gap"></i>aasta andmed puuduvad</span></div>'
                                 '<div class="an-grid">' + "".join(minijoon(k, next(S for S in P if S["mid"] == m)) for m in AJAREAD if any(S["mid"] == m for S in P)) + "</div>"
                                 '<p class="small">Telg algab nullist. Ettevõtete aegreas lisandus 2025. aastal küsimustikku uus tehnoloogia, '
                                 'nii et 2024→2025 tõus on osaliselt küsimustiku muutus.</p>'),
                      "Muutus", "muutus")
        + k.sektsioon("Kõik riigid igal näitajal",
                      '<p class="small">Iga rida on oma skaalal. Vii hiir punktile, et näha riiki ja väärtust.</p>'
                      + profiili_joonis(k, P), "Profiil", "profiil")
        + k.sektsioon("Millele keskenduda", '<div class="an-cards">' + "".join(fookus) + "</div>", "Soovitus", "fookus")
        + k.sektsioon("Andmed ja piirangud",
                      piirangud(k, D, K)
                      + k.avatav("Riikide endi uuemad numbrid (2026)",
                                 '<p class="small">Statistikaametid avaldavad oma numbri enne Eurostati. Osa neist on uue '
                                 'klassifikaatoriga või teise kogumiga.</p>' + riiklike_tabel(k, K))
                      + k.avatav("Kõik numbrid tabelina", koondtabel(k, K, P))
                      + f'<p class="small"><a href="{CSV_FAIL}" download>Laadi alla kõik selle lehe aegread (CSV)</a>. '
                        'Veerud: mõõdik, riik, aasta, väärtus, allikas, andmestik, URL ja võrreldavusklass.</p>', "Andmed", "andmed")
        + TIP_JS
    )
    return {FAIL: k.leht(FAIL, "Analüütiku vaade · Tehisaru seire", sisu, tana), CSV_FAIL: andmete_csv(K, P)}


# Kohtspikker: väärtus ees, silt järel; tekst lisatakse textContent'iga.
TIP_JS = """<div class="tip" id="tip" hidden></div>
<script>
(function () {
  var t = document.getElementById('tip');
  function pos(x, y) {
    var r = t.getBoundingClientRect(), L = x + 14, T = y + 14;
    if (L + r.width > innerWidth - 8) L = x - r.width - 14;
    if (T + r.height > innerHeight - 8) T = y - r.height - 14;
    t.style.left = Math.max(8, L) + 'px'; t.style.top = Math.max(8, T) + 'px';
  }
  function show(el, x, y) {
    var p = el.getAttribute('data-tip').split('|');
    t.textContent = '';
    var b = document.createElement('strong'); b.textContent = p[0]; t.appendChild(b);
    if (p[1]) { var s = document.createElement('span'); s.textContent = p[1]; t.appendChild(s); }
    t.hidden = false; pos(x, y);
  }
  document.addEventListener('pointerover', function (ev) {
    var el = ev.target.closest && ev.target.closest('[data-tip]'); if (el) show(el, ev.clientX, ev.clientY);
  });
  document.addEventListener('pointermove', function (ev) {
    if (!t.hidden && ev.target.closest && ev.target.closest('[data-tip]')) pos(ev.clientX, ev.clientY);
  });
  document.addEventListener('pointerout', function (ev) {
    if (ev.target.closest && ev.target.closest('[data-tip]')) t.hidden = true;
  });
})();
</script>"""
