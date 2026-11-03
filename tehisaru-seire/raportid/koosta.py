"""Koostab seire mitmelehelise HTML-raporti otse seire andmefailidest.

Loeb: ../naitajad.json, ../andmed/<id>.csv, ../andmed/<id>.meta.json, ../andmed/muutused.csv,
../kataloog/ (kategooriad, mõisted, mõõdikud, vaatlused; loeb seire/kataloog.py)
ja selle kausta käsitsi peetavad failid sundmused.csv, lahknevused.csv, riskid.csv.
Kirjutab: html/ (index.html, teemad.html, kuidas.html, üks leht iga näitaja kohta <id>.html, stiil.css).

Käivitamine kaustast tehisaru-seire:  python raportid/koosta.py
Numbreid käsitsi ei kirjutata: iga number tuleb andmefailist.
"""

import csv
import datetime as dt
import html
import json
import shutil
import sys
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

SIIN = Path(__file__).resolve().parent
JUUR = SIIN.parent
VALJA = SIIN / "html"
sys.path.insert(0, str(JUUR))

from seire import kataloog  # noqa: E402
from seire.usaldus import VASTUOLU_PIIR  # noqa: E402

sys.path.insert(0, str(SIIN))
import analuus  # noqa: E402  (analüütiku vaade, eraldi moodulis)
import pildid  # noqa: E402  (väikesed graafikud)

RIIGID = {
    "EE": "Eesti", "FI": "Soome", "SE": "Rootsi", "DK": "Taani", "NO": "Norra",
    "DE": "Saksamaa", "NL": "Holland", "EU27_2020": "EL27",
    "UK": "Ühendkuningriik", "US": "USA", "CA": "Kanada", "KR": "Lõuna-Korea", "JP": "Jaapan",
    "AT": "Austria", "BE": "Belgia", "BG": "Bulgaaria", "CY": "Küpros", "CZ": "Tšehhi", "EL": "Kreeka", "ES": "Hispaania",
    "FR": "Prantsusmaa", "HR": "Horvaatia", "HU": "Ungari", "IE": "Iirimaa", "IT": "Itaalia", "LT": "Leedu",
    "LU": "Luksemburg", "LV": "Läti", "MT": "Malta", "PL": "Poola", "PT": "Portugal", "RO": "Rumeenia",
    "SI": "Sloveenia", "SK": "Slovakkia",
}
FOOKUS = "EE"
# Uuringud tulevad suuna „Tehisaru ja töö“ failist. Kui faili pole (nt ainult seire kaust), jääb kast ära.
LEIUD = JUUR.parent / "tooelu-seire" / "leiud.json"
TOOELU_LEHT = "tehisaru-ja-too.html"  # ühise saidi teine osa, avaldatakse samas artefaktis
UURINGUID_KUNI = 3
# Avalike lausete kontroll (osa „Mida väidetakse“, 3.11.2026). Näitajaga seotud väited on raportid/riskid.csv-s,
# uuringute ja aruannete kohta käivad väited ühises kihis kataloog/vaited.csv.
VAITED = JUUR / "kataloog" / "vaited.csv"
VAITED_LEHT = "vaited.html"
# Hinnang -> (raskus, märgi klass, mida see tähendab). Raskus järjestab lehe: eespool laused, mis eksitavad.
HINNANGUD = {
    "Vale tõlgendus": (0, "risk", "Lause ütleb allikast midagi muud, kui allikas ütles."),
    "Nimetaja vale": (0, "risk", "Protsent on arvutatud teisest rühmast, kui lause ütleb."),
    "Sõnastus liialdab": (0, "risk", "Lause ütleb rohkem, kui allikas ütles, näiteks „kaob“, kui allikas ütles „puudutab“."),
    "Suurus ebakindel": (1, "warn", "Suund on tõenäoliselt õige, täpne suurus mitte."),
    "Täpsustus puudu": (1, "warn", "Number vastab allikale, aga lausest puudub, keda või mida see kirjeldab."),
    "Vastab allikale": (2, "ok", "Lause ütleb sama, mida allikas."),
}
# Osa „Mida otsustatakse“ (3.11.2026): seaduste tähtajad ühises kihis, sihid tulevad registrist naitajad.json.
OTSUSED = JUUR / "kataloog" / "otsused.csv"
OTSUSED_LEHT = "otsused.html"
KUU_NIM = ["jaanuar", "veebruar", "märts", "aprill", "mai", "juuni", "juuli", "august", "september", "oktoober",
           "november", "detsember"]
RASKUS = {0: ("Ütleb muud kui allikas", "risk"), 1: ("Vajab täpsustust", "warn"), 2: ("Vastab allikale", "ok")}
TOEND = {"tugev": "Tugev tõend", "keskmine": "Keskmine tõend", "nork": "Nõrk tõend", "prognoos": "Prognoos"}
MEETOD = {"katse": "juhuslik katse", "loomulik_katse": "loomulik katse", "registriandmed": "registri- või platvormiandmed",
          "kirjeldav": "kirjeldav analüüs", "kusitlus": "küsitlus", "hinnang": "hinnang ülesannete kohta",
          "mudel": "majandusmudel", "ekspertintervjuud": "ekspertintervjuud", "prognoos": "prognoos, mitte mõõtmine"}
VIIDE = "EU27_2020"
MARGENDID = {"b": "aegrea katkestus", "p": "esialgne", "e": "hinnang", "u": "ebausaldusväärne", "c": "konfidentsiaalne"}
# Kolm taset: ülevaade (vastus) -> näitaja leht (number ja usaldus) -> teemad ja metoodika.
# Näitajate lehed (<id>.html) avanevad ülevaate kaartidelt, navis on ainult üldlehed.
LEHED = [
    ("index.html", "Ülevaade"),
    ("kaart.html", "ELi kaart"),
    ("teemad.html", "Teemad ja allikad"),
    ("analuus.html", "Analüütiku vaade"),
    ("kuidas.html", "Kuidas see töötab"),
]
LIIGID = {"allikas": "Allikas", "seire": "Seire", "lahknevus": "Allikate vahe"}

e = html.escape


# ---------- abifunktsioonid ----------

def arv(x, kohti=1):
    """Eesti kujul arv: koma, poolikud ülespoole (19,95 -> 20,0)."""
    q = Decimal(1).scaleb(-kohti)
    return str(Decimal(str(x)).quantize(q, rounding=ROUND_HALF_UP)).replace(".", ",").replace("-", "−")


def kuupaev(s):
    if not s:
        return "–"
    d = dt.date.fromisoformat(s[:10])
    return f"{d.day:02d}.{d.month:02d}.{d.year}"


def loe_csv(p):
    if not p.exists():
        return []
    with open(p, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def loe_json(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def arv_r(r):
    """Riikliku numbri esitus allika täpsusega (59 jääb 59-ks, mitte 59,0)."""
    kohti = len(r["vaartus"].split(".")[1]) if "." in r["vaartus"] else 0
    return arv(r["v"], kohti)


def riik(kood):
    return RIIGID.get(kood, kood)


# ---------- andmete laadimine ----------

def lae():
    reg = loe_json(JUUR / "naitajad.json")
    naitajad = []
    for n in reg["naitajad"]:
        nid = n["id"]
        meta_p = JUUR / "andmed" / f"{nid}.meta.json"
        andmed_p = JUUR / "andmed" / f"{nid}.csv"
        if not meta_p.exists() or not andmed_p.exists():
            print(f"Hoiatus: {nid} andmeid pole veel laaditud, jätan vahele.", file=sys.stderr)
            continue
        meta = loe_json(meta_p)
        read = loe_csv(andmed_p)
        seeria = {}
        for r in read:
            if r["vaartus"] == "":
                continue
            seeria.setdefault(r["geo"], {})[int(r["time"])] = (float(r["vaartus"]), r.get("margend", ""))
        aastad = sorted({a for s in seeria.values() for a in s})
        viimane = aastad[-1]
        uuem = meta.get("uuem_allikas")
        if uuem is None and "uuem_allikas" not in meta:
            # Varulahendus, kuni seire ise lippu ei kirjuta: riiklik number uuema aasta kohta.
            kandidaadid = [t for t in n.get("teised_allikad", [])
                           if t["riik"] == FOOKUS and t["aasta"] > viimane and t["usaldus"] == "ametlik statistika"]
            uuem = max(kandidaadid, key=lambda t: t["aasta"]) if kandidaadid else None
        riiklikud = [r for r in loe_csv(SIIN / "riiklikud.csv") if r["naitaja"] == nid]
        for r in riiklikud:
            r["v"] = float(r["vaartus"]) if r["vaartus"] else None
            # Käsitsi kantud number peab klappima seire enda laaditud numbriga.
            if uuem and r["riik"] == uuem["riik"] and int(r["aasta"]) == uuem["aasta"] and r["v"] != uuem["vaartus"]:
                print(f"Hoiatus: riiklikud.csv {r['riik']} {r['aasta']} = {r['v']}, seire laadis {uuem['vaartus']}.", file=sys.stderr)
        naitajad.append({"n": n, "meta": meta, "seeria": seeria, "aastad": aastad, "viimane": viimane, "uuem": uuem,
                         "riiklikud": riiklikud})
    L = lae_leiud()
    return {
        "riigid": reg["riigid"],
        "naitajad": naitajad,
        "muutused": loe_csv(JUUR / "andmed" / "muutused.csv"),
        "sundmused": sorted(loe_csv(SIIN / "sundmused.csv"), key=lambda r: r["kuupaev"], reverse=True),
        "lahknevused": loe_csv(SIIN / "lahknevused.csv"),
        "riskid": loe_csv(SIIN / "riskid.csv"),
        "el27": loe_csv(JUUR / "andmed" / "el27.csv"),
        "sarnased": loe_csv(SIIN / "sarnased.csv"),
        "lugejad": loe_csv(SIIN / "lugejad.csv"),
        "uuringud": lae_uuringud(L),
        "leiud": {u["id"]: u for u in (L or {}).get("uuringud", [])},
        "vaited": lae_vaited(loe_csv(SIIN / "riskid.csv")),
    }


def lae_leiud():
    """Suuna „Tehisaru ja töö“ leiud.json või None, kui faili pole või see ei ole loetav."""
    if not LEIUD.exists():
        return None
    try:
        L = loe_json(LEIUD)
        if not all(isinstance(u, dict) and "id" in u for u in L["uuringud"]):
            raise ValueError("uuringul puudub id")
        return L
    except (ValueError, KeyError, TypeError) as viga:
        # Teise osa vigane fail ei tohi peatada ametliku statistika lehti: kast jääb lihtsalt ära.
        print(f"Hoiatus: {LEIUD} ei ole loetav ({viga}), uuringuid ei näidata.", file=sys.stderr)
        return None


def lae_vaited(riskid):
    """Kõik kontrollitud avalikud laused ühes loendis: enne eksitavad, siis uuemad."""
    tulem, mitu = [], {}
    for r in (x for x in riskid if x["liik"] == "vaide"):
        mitu[r["naitaja"]] = mitu.get(r["naitaja"], 0) + 1  # id on näitaja piires järjekorranumber
        tulem.append({"id": f'{r["naitaja"]}-{mitu[r["naitaja"]]}', "vaide": r["pealkiri"], "kes": r["allikas"], "kus": "",
                      "kuupaev": r["kuupaev"], "url": r["url"], "algallikas": "", "algallika_url": "",
                      "algallikas_utleb": "", "hinnang": r["hinnang"], "selgitus": r["selgitus"], "oige_lause": "",
                      "mida_teha": r["mida_teha"], "naitaja": r["naitaja"], "uuringud": []})
    if VAITED.exists():
        for r in loe_csv(VAITED):
            tulem.append({**r, "mida_teha": "", "naitaja": "", "uuringud": r["uuringud"].split()})
    for v in tulem:
        if v["hinnang"] not in HINNANGUD:
            print(f"Hoiatus: väite {v['id']} hinnang „{v['hinnang']}“ pole lubatud loendis.", file=sys.stderr)
    tulem.sort(key=lambda v: v["kuupaev"], reverse=True)
    tulem.sort(key=lambda v: HINNANGUD.get(v["hinnang"], (1,))[0])
    return tulem


def lae_uuringud(L=False):
    """Küsimuse id -> uuringud (leiud.json kirje + veerg seos), faili kataloog/uuringud.csv järjekorras.
    L on juba laaditud leiud.json (või None); vaikimisi laaditakse see siin."""
    seosed = JUUR / "kataloog" / "uuringud.csv"
    if L is False:
        L = lae_leiud()
    if L is None or not seosed.exists():
        return {}
    U = {u["id"]: u for u in L["uuringud"]}
    tugevus = {m: k for k, ms in L.get("kindlus", {}).items() for m in ms}
    tulem = {}
    for r in loe_csv(seosed):
        u = U.get(r["uuring"])
        if u is None:
            print(f"Hoiatus: uuringud.csv viitab uuringule {r['uuring']}, mida leiud.json-is pole.", file=sys.stderr)
            continue
        tulem.setdefault(r["kusimus"], []).append({**u, "seos": r["seos"], "toend": tugevus.get(u["meetod"], "")})
    return tulem


def andmeprobleemid(x):
    """Kontrollide hoiatused (v.a uuema numbri märge, mida näidatakse eraldi) ja ebatavalised langused."""
    tulem = []
    for p in x["meta"].get("probleemid", []):
        if p["tekst"].startswith("Uuem number"):
            continue
        kood, _, rest = p["tekst"].partition(" ")
        tekst = f"{riik(kood)} {rest}" if kood in RIIGID else p["tekst"]
        tulem.append({**p, "tekst": tekst})
    for geo, s in x["seeria"].items():
        aastad = sorted(s)
        for a, b in zip(aastad, aastad[1:]):
            v0, v1 = s[a][0], s[b][0]
            if v0 - v1 >= 3 and not s[b][1]:
                tulem.append({"tase": "kontrollimata", "tekst": (
                    f"{riik(geo)} {b}: väärtus langes {arv(v0)}%-lt {arv(v1)}%-le, "
                    "aga Eurostat ei märgi aegrea katkestust. Põhjus on kontrollimata.")})
    return tulem


def vaiksem_parem(x):
    """Näitajad, kus väiksem number on parem (näiteks „ei kasuta, sest ei oska“)."""
    return x["n"].get("suund") == "vaiksem_parem"


def jarjestus(x, aasta):
    """Eesti koht võrdlusriikide seas. Koht 1 on parim: suurim või, kui väiksem on parem, väikseim."""
    riigid = [(g, s[aasta][0]) for g, s in x["seeria"].items() if aasta in s and g != VIIDE]
    riigid.sort(key=lambda t: t[1] if vaiksem_parem(x) else -t[1])
    koht = [g for g, _ in riigid].index(FOOKUS) + 1
    return koht, len(riigid)


def koha_tekst(x, koht, kokku):
    return f"{koht}. kohal {kokku}-st" + (" (väiksem on parem)" if vaiksem_parem(x) else "")


def eesti_eespool(x):
    """Kas Eesti on viimasel aastal ELi keskmisest paremal pool (None, kui ELi keskmist pole)."""
    a = x["viimane"]
    el = x["seeria"].get(VIIDE, {}).get(a, (None,))[0]
    if el is None:
        return None
    ee = x["seeria"][FOOKUS][a][0]
    return ee < el if vaiksem_parem(x) else ee > el


def leid(x):
    """Ühe lause leid näitaja kohta, arvutatud andmetest."""
    a = x["viimane"]
    ee = x["seeria"][FOOKUS][a][0]
    el = x["seeria"].get(VIIDE, {}).get(a, (None,))[0]
    koht, kokku = jarjestus(x, a)
    osa = []
    if el is not None:
        osa.append("ELi keskmisest rohkem" if ee > el else "ELi keskmisest vähem")
    rohkem, vahem = ("vähem", "rohkem") if vaiksem_parem(x) else ("rohkem", "vähem")
    if koht == kokku:
        # „kuid“ ainult siis, kui ELi võrdlus ütleb vastupidist (ELi keskmisest rohkem, kuid ...).
        sidesona = "ja" if el is not None and (ee < el) != vaiksem_parem(x) else "kuid"
        osa.append(f"{sidesona} kõigist võrdlusriikidest {vahem}")
    elif koht == 1:
        osa.append(f"ja kõigist võrdlusriikidest {rohkem}")
    else:
        osa.append(f"võrdlusriikide seas {koha_tekst(x, koht, kokku)}")
    return ee, ", ".join(osa)


# ---------- lehe raam ----------

IKOON_PAIKE = ('<svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true" fill="none" stroke="currentColor" '
               'stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4'
               'M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>')
IKOON_KUU = ('<svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true" fill="none" stroke="currentColor" '
             'stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5z"/></svg>')


# Ühise saidi kaks osa (Kadri otsus 3.11.2026). Sama riba on lehel „Tehisaru ja töö“ (tooelu-seire/leht/mall.html).
KOHAL = ' aria-current="page"'
OSAD = [("mootmine", "index.html", "Mida mõõdetakse", "ametlik statistika"),
        ("uuringud", TOOELU_LEHT, "Mida uuritakse", "uuringud ja raportid"),
        ("vaited", VAITED_LEHT, "Mida väidetakse", "avalike lausete kontroll"),
        ("otsused", OTSUSED_LEHT, "Mida otsustatakse", "seadused ja sihid")]


def osade_riba(praegu):
    """Riba lehe kohal, mis vahetab saidi osa. Ilma teise osata (leiud.json puudub) riba pole."""
    if not LEIUD.exists():
        return ""
    lingid = "".join(
        f'<a href="{f}" title="{e(selg)}"{KOHAL if k == praegu else ""}><b>{e(nimi)}</b> <span>{e(selg)}</span></a>'
        for k, f, nimi, selg in OSAD)
    return f'<nav class="osad" aria-label="Saidi osad"><div class="wrap">{lingid}</div></nav>'


def leht(fail, pealkiri, sisu, uuendatud, ylal="", osa="mootmine"):
    praegune = ' aria-current="page"'
    nav = "".join(
        f'<li><a href="{f}"{praegune if f == fail else ""}>{e(nimi)}</a></li>'
        for f, nimi in LEHED)
    pea = (
        f"<title>{e(pealkiri)}</title>\n"
        '<meta name="claude:viewport-fit-sides" content="cover">\n'
        '<link rel="preconnect" href="https://fonts.googleapis.com">\n'
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
        '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&family=Space+Grotesk:wght@700&display=swap">\n'
        '<link rel="stylesheet" href="stiil.css">\n'
        # Värvirežiimi valik jääb meelde selle vaataja brauseris; vaikimisi järgib see süsteemi.
        "<script>(function(){var t='light';try{if(localStorage.getItem('seire-teema')==='dark')t='dark';}catch(e){}"
        "document.documentElement.setAttribute('data-theme',t);})();</script>\n"
    )
    keha = (
        '<a class="skip" href="#sisu">Liigu sisu juurde</a>'
        + osade_riba(osa)
        + '<header class="top"><div class="wrap">'
        '<a class="mark" href="index.html">Tehisaru seire</a>'
        f'<nav aria-label="Raporti lehed"><ul class="nav">{nav}</ul></nav>'
        f'<div class="top-tools"><span class="updated">Uuendatud {kuupaev(uuendatud)}</span>'
        '<div class="theme-seg" role="group" aria-label="Värvirežiim">'
        f'<button type="button" data-t="light" aria-label="Hele režiim" title="Hele">{IKOON_PAIKE}</button>'
        f'<button type="button" data-t="dark" aria-label="Tume režiim" title="Tume">{IKOON_KUU}</button>'
        "</div></div></div></header>\n"
        # Avalehe fotopäis koos pealkirjaga on samuti põhisisu osa.
        + f'<main id="sisu">{ylal}<div class="wrap">{sisu}</div></main>\n'
        '<footer><div class="wrap">'
        f"<p>Koostatud {kuupaev(uuendatud)}. Allikad: Eurostat (taaskasutus viitega lubatud), Statistikaamet, OECD ja "
        "riikide statistikaametid. Kust iga number tuleb ja mis on käsitsi kantud: "
        '<a href="kuidas.html#allikad">Kuidas see töötab</a>.</p>'
        "</div></footer>\n"
        "<script>(function(){var r=document.documentElement,bb=document.querySelectorAll('.theme-seg button');"
        "function show(){var c=r.getAttribute('data-theme')==='dark'?'dark':'light';"
        "bb.forEach(function(b){b.setAttribute('aria-pressed',String(b.dataset.t===c));});}"
        "bb.forEach(function(b){b.addEventListener('click',function(){var t=b.dataset.t;r.setAttribute('data-theme',t);"
        "try{localStorage.setItem('seire-teema',t);}catch(e){}show();});});"
        "show();})();</script>\n"
    )
    if fail == "index.html":
        # Avalehe ümbritseb artefakti raam, alamlehed on täisdokumendid.
        return pea + keha
    return ('<!doctype html>\n<html lang="et">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
            f"{pea}</head>\n<body>\n{keha}</body>\n</html>\n")


# Avalehe päis foto peal (valitud 27.10.2026: kõrge 2,4:1, pehme foto, tekst all vasakul nurgaudu peal).
# Ainult avalehel; andmelehtedel fotot pole. Telefonis läheb tekst foto alla.
def avafoto(h1, lead, tana):
    return (
        '<div class="wrap hero-photo"><div class="hero-stack">'
        '<img src="fotod/pano-siluett-lai-1200.jpg" '
        'srcset="fotod/pano-siluett-lai-1200.jpg 1200w, fotod/pano-siluett-lai.jpg 2400w" '
        'sizes="(max-width: 1040px) 100vw, 1008px" width="2400" height="1000" '
        'alt="Tallinna siluett üle mere, esiplaanil ujuvad luiged. Hall foto.">'
        '<div class="hero-scrim" aria-hidden="true"></div>'
        f'<div class="hero-text"><h1>{h1}</h1><p class="lead">{lead}</p></div>'
        '</div><div class="photo-meta">'
        '<span class="photo-credit">Foto: Kadri · Tallinn, aprill 2024</span>'
        "</div></div>\n"
    )


def pais(eyebrow, h1, lead=None):
    s = f'<div><p class="eyebrow">{e(eyebrow)}</p><h1>{h1}</h1>'
    if lead:
        s += f'<p class="lead">{lead}</p>'
    return s + "</div>"


def sektsioon(pealkiri, sisu, eyebrow=None, ank=None):
    idattr = f' id="{ank}"' if ank else ""
    eb = f'<p class="eyebrow">{e(eyebrow)}</p>' if eyebrow else ""
    return f'<section{idattr}><div class="section-head">{eb}<h2>{pealkiri}</h2></div>{sisu}</section>'


# ---------- graafikud ----------

def siht(x):
    """Näitaja esimene ametlik siht (või None). Siht on registris naitajad.json väljal "sihid"."""
    s = x["n"].get("sihid") or []
    return s[0] if s else None


def siht_silt(s):
    kelle = "Eesti" if s["riik"] == FOOKUS else "EL kokku" if s["riik"] == VIIDE else riik(s["riik"])
    return f'Siht{" " + str(s["aasta"]) if s.get("aasta") else ""} ({kelle})'


def arv_s(v):
    """Sihi number: täisarv ilma komakohata (75%, mitte 75,0%)."""
    return arv(v, 0) if float(v) == int(v) else arv(v)


def tulbad(x, aasta):
    s = sorted(((g, v[aasta][0], v[aasta][1]) for g, v in x["seeria"].items() if aasta in v), key=lambda t: -t[1])
    sh = siht(x)
    if sh:
        s = sorted(s + [("siht", sh["vaartus"], "")], key=lambda t: -t[1])
    tipp = max(v for _, v, _ in s)
    read = []
    for g, v, m in s:
        if g == "siht":
            read.append(
                f'<li class="is-target"><span class="lab">{e(siht_silt(sh))}</span>'
                f'<span class="track"><span class="bar" style="width:{v / tipp * 100:.1f}%"></span></span>'
                f'<span class="val">{arv_s(v)}%</span></li>')
            continue
        klass = "is-focus" if g == FOOKUS else "is-ref" if g == VIIDE else ""
        lab = riik(g) + (" (ELi keskmine)" if g == VIIDE else "")
        mrk = f' <span class="small">({e(m)})</span>' if m else ""
        read.append(
            f'<li class="{klass}"><span class="lab">{e(lab)}</span>'
            f'<span class="track"><span class="bar" style="width:{v / tipp * 100:.1f}%"></span></span>'
            f'<span class="val">{arv(v)}%{mrk}</span></li>')
    return f'<ul class="bars" role="list">{"".join(read)}</ul>'


def jooned(x):
    aastad = x["aastad"]
    W, H = 640, 330
    ml, mr, mt, mb = 36, 128, 14, 30
    a0, a1 = aastad[0], aastad[-1]
    tipp = max(v for s in x["seeria"].values() for v, _ in s.values())
    sh = siht(x)
    if sh:
        tipp = max(tipp, sh["vaartus"])
    # Samm 10 nagu varem; väikeste väärtuste (nt T&A kulu % SKPst) puhul 1 või 0,5.
    samm = 10 if tipp > 10 else 1 if tipp > 3 else 0.5
    ymax = -(-tipp // samm) * samm
    if samm >= 1:
        ymax = int(ymax)

    def X(a):
        return ml + (a - a0) / (a1 - a0) * (W - ml - mr)

    def Y(v):
        return mt + (1 - v / ymax) * (H - mt - mb)

    osad = []
    for i in range(int(round(ymax / samm)) + 1):
        t = i * samm if samm < 1 else int(i * samm)
        osad.append(f'<line class="gridline" x1="{ml}" x2="{W - mr}" y1="{Y(t):.1f}" y2="{Y(t):.1f}"/>')
        osad.append(f'<text x="{ml - 8}" y="{Y(t) + 5:.1f}" text-anchor="end">{arv(t) if samm < 1 else t}</text>')
    if sh:
        osad.append(f'<line class="target" x1="{ml}" x2="{W - mr}" y1="{Y(sh["vaartus"]):.1f}" y2="{Y(sh["vaartus"]):.1f}"/>')
        osad.append(f'<text class="target-lab" x="{ml + 6}" y="{Y(sh["vaartus"]) - 7:.1f}">'
                    f'{e(siht_silt(sh))}: {arv_s(sh["vaartus"])}%</text>')
    iga = 1 if a1 - a0 <= 8 else 2 if a1 - a0 <= 16 else 5
    for a in range(a0, a1 + 1):
        if (a1 - a) % iga == 0:
            osad.append(f'<text x="{X(a):.1f}" y="{H - 8}" text-anchor="middle">{a}</text>')

    jrk = sorted(x["seeria"], key=lambda g: (g == FOOKUS, g == VIIDE))  # fookus joonistatakse viimasena
    sildid = []
    for g in jrk:
        s = x["seeria"][g]
        klass = "focus" if g == FOOKUS else "ref" if g == VIIDE else ""
        aa = sorted(s)
        for p, q in zip(aa, aa[1:]):
            gap = " gap" if q - p > 1 else ""
            osad.append(f'<path class="ln {klass}{gap}" d="M{X(p):.1f},{Y(s[p][0]):.1f} L{X(q):.1f},{Y(s[q][0]):.1f}"/>')
        if klass:
            r = 4.5 if klass == "focus" else 3.5
            osad.append(f'<circle class="dot {klass}" cx="{X(aa[-1]):.1f}" cy="{Y(s[aa[-1]][0]):.1f}" r="{r}"/>')
        tekst = riik(g) + (f" {arv(s[aa[-1]][0])}%" if klass else "")
        sildid.append([Y(s[aa[-1]][0]), tekst, klass])
    # Lõpusildid ei tohi kattuda: lükka vähemalt 17 px lahku.
    sildid.sort(key=lambda t: t[0])
    for i in range(1, len(sildid)):
        sildid[i][0] = max(sildid[i][0], sildid[i - 1][0] + 17)
    for y, tekst, klass in sildid:
        k = f' class="lab-{klass}"' if klass else ""
        osad.append(f'<text x="{W - mr + 10}" y="{y + 5:.1f}"{k}>{e(tekst)}</text>')
    return (f'<div class="scroll"><svg viewBox="0 0 {W} {max(H, sildid[-1][0] + 12):.0f}" role="img" '
            f'aria-label="{e(x["n"]["nimi"])} riigiti {a0}–{a1}. Andmed on lehe lõpus tabelis.">'
            f'{"".join(osad)}</svg></div>')


def punktirida(read, viide):
    vaartused = [r["v"] for r in read]
    lo = float(Decimal(str(min(vaartused) - 0.5)).quantize(Decimal("1"), rounding="ROUND_FLOOR"))
    hi = float(Decimal(str(max(vaartused) + 0.5)).quantize(Decimal("1"), rounding="ROUND_CEILING"))

    def P(v):
        return (v - lo) / (hi - lo) * 100

    rid = []
    for r in read:
        klass = "is-focus" if r.get("fookus") else ""
        pt = "pt hollow" if r.get("teisene") else "pt"
        rid.append(
            f'<li class="{klass}"><span class="who">{r["nimi"]}<small>{e(r["usaldus"])}</small></span>'
            f'<span class="line"><span class="ref-mark" style="left:{P(viide):.1f}%"></span>'
            f'<span class="{pt}" style="left:{P(r["v"]):.1f}%"></span></span>'
            f'<span class="v">{arv(r["v"])}%</span></li>')
    samm = 0.5 if (hi - lo) / 0.5 <= 8 else 1.0
    sammud = [lo + i * samm for i in range(int(round((hi - lo) / samm)) + 1)]
    skaala = "".join(f"<span>{arv(s)}</span>" for s in sammud)
    return (f'<ul class="strip" role="list">{"".join(rid)}</ul>'
            f'<div class="strip-scale" aria-hidden="true"><span></span><div>{skaala}</div><span></span></div>')


def andmetabel(x):
    aastad = x["aastad"]
    pea = "".join(f'<th class="r" scope="col">{a}</th>' for a in aastad)
    read = []
    for g in [g for g in RIIGID if g in x["seeria"]]:
        s = x["seeria"][g]
        lahtrid = "".join(
            f'<td class="r">{arv(s[a][0]) + (f" ({e(s[a][1])})" if s[a][1] else "") if a in s else "–"}</td>'
            for a in aastad)
        read.append(f'<tr class="{"is-focus" if g == FOOKUS else ""}"><th scope="row">{riik(g)}</th>{lahtrid}</tr>')
    mm = lipud(x, aastad)
    selg = ("Sulgudes Eurostati märgend: " + ", ".join(f"({m}) {LIPUD.get(m, 'märgend')}" for m in mm) + ".") if mm else ""
    return (f'<div class="table-wrap"><table><caption>{e(kogum(x["n"]))}. {selg}</caption>'
            f'<thead><tr><th scope="col">Riik</th>{pea}</tr></thead><tbody>{"".join(read)}</tbody></table></div>')




# ---------- kataloogi abi ----------

KLASSI_SILT = {"alus": "focus", "sama": "ok", "osaliselt": "", "erinev": "risk", "kontrollimata": "risk"}
OLEKU_SILT = {"seires": "focus", "andmed": "ok", "kavandatud": "", "allikas_leidmata": "risk"}
OLEKU_JARJEKORD = ["seires", "andmed", "kavandatud", "allikas_leidmata"]

# Kuidas numbrit lauses õigesti öelda: mida tehti ja kelle kohta. Puuduva näitaja korral kasutatakse ühikut.
SONASTUS = {
    "ettevotete-tehisaru-kasutus": ("kasutas tehisaru", "Eesti vähemalt 10 töötajaga ettevõtetest"),
    "inimeste-tehisaru-kasutus": ("kasutas viimase 3 kuu jooksul generatiivse tehisaru tööriistu", "Eesti 16–74-aastastest"),
    "tooalane-tehisaru-kasutus": ("kasutas viimase 3 kuu jooksul generatiivse tehisaru tööriistu tööalaselt", "Eesti 16–74-aastastest"),
    "tehisaru-oskuse-puudus": ("jättis generatiivse tehisaru kasutamata, sest ei osanud seda kasutada,", "Eesti 16–74-aastastest"),
    "inimeste-digioskused": ("olid vähemalt baastasemel digioskused", "Eesti 16–74-aastastest"),
    "ettevotete-digiintensiivsus": ("olid vähemalt baastasemel digiintensiivsusega", "Eesti 10–249 hõivatuga ettevõtetest"),
    "ta-kulud": ("kulutati teadus- ja arendustegevusele", "Eesti SKPst"),
}
# Kui tavaline lausemall („Eurostati järgi {tegu} {aasta}. aastal {v}% {kelle}“) on kohmakas, terve lause siit.
LAUSED = {
    "inimeste-digioskused": "Eurostati järgi olid {a}. aastal vähemalt baastasemel digioskused {v}%-l Eesti 16–74-aastastest",
    "ettevotete-digiintensiivsus": ("Eurostati järgi oli {a}. aastal vähemalt baastasemel digiintensiivsusega "
                                    "{v}% Eesti 10–249 hõivatuga ettevõtetest"),
    "ta-kulud": "Eurostati järgi kulutati Eestis {a}. aastal teadus- ja arendustegevusele {v}% SKPst",
}


# Eurostati märgendid. Joonise all selgitatakse ainult neid, mis joonisel on.
LIPUD = {"b": "aegrea katkestus", "p": "esialgne", "e": "hinnanguline", "u": "väike usaldusväärsus", "d": "määratlus erineb"}
# Kõik viis näitajat on küsitlused: number on vastajate endi vastus, mitte mõõdetud kasutus (selgitus lehel Kuidas see töötab).
ANDMELIIK = '<a href="kuidas.html#allikad">küsitlus</a>, vastajate endi vastused'


def lipud(x, aastad):
    """{märgend: ["Holland 2025", ...]} kõigi riikide ja antud aastate kohta."""
    leitud = {}
    for g, v in x["seeria"].items():
        for a in aastad:
            for m in (v[a][1] or "") if a in v else "":
                leitud.setdefault(m, []).append(f"{riik(g)} {a}")
    return leitud


def lipud_lause(x, aastad):
    return " ".join(f"({m}) {LIPUD.get(m, 'Eurostati märgend')}: {', '.join(kus)}." for m, kus in lipud(x, aastad).items())


def kogum(n):
    """Ühik koos sellega, kelle kohta number on, näiteks „% vähemalt 10 töötajaga ettevõtetest“."""
    kelle = SONASTUS.get(n["id"], ("", ""))[1].removeprefix("Eesti ")
    return f"% {kelle}" if kelle else n["uhik"]


def arv_k(v):
    """Kataloogi vaatlus allika täpsusega, aga mitte üle kahe komakoha."""
    return arv(v["vaartus"], min(v["tapsus"], 2))


def linkita(tekst, url):
    return f'<a href="{e(url)}">{e(tekst)}</a>' if url else e(tekst)


def klassi_tag(klass):
    return f'<span class="tag {KLASSI_SILT[klass]}">{e(kataloog.VORREDAVUS[klass])}</span>'


def vorreldavuse_legend():
    read = "".join(f"<dt>{klassi_tag(k)}</dt><dd>{e(t)}</dd>" for k, t in kataloog.VORREDAVUS_SELGITUS.items())
    return f'<dl class="legend">{read}</dl>'


def org(K, moodik):
    a = K["allikad"].get(moodik["allikas"])
    return a["organisatsioon"] if a else moodik["nimi"].split(",")[0]


def fail_naitajale(x):
    return f'{x["n"]["id"]}.html'


def avatav(pealkiri, sisu, klass="more", avatud=False, ank=None):
    idattr = f' id="{ank}"' if ank else ""
    return (f'<details class="{klass}"{idattr}{" open" if avatud else ""}><summary>{pealkiri}</summary>'
            f'<div class="more-body">{sisu}</div></details>')


def kirje(sil, klass, pealk, selg, teha=None, r=None):
    t = f'<p class="todo"><b>Mida teha:</b> {e(teha)}</p>' if teha else ""
    kes = ""
    if r and r.get("allikas"):
        silt = "Ütles" if r["liik"] == "vaide" else "Alus"
        nimi = linkita(r["allikas"], r.get("url"))
        kes = f'<p class="small">{silt}: {nimi}{", " + kuupaev(r["kuupaev"]) if r.get("kuupaev") else ""}</p>'
    return (f'<li><div class="row"><h4>{e(pealk)}</h4><span class="tag {klass}">{e(sil)}</span></div>'
            f'{kes}<p>{e(selg)}</p>{t}</li>')


# ---------- ühe näitaja kokkuvõte ----------

def kontekst(x, D, K):
    """Kõik, mida ülevaade ja näitaja leht ühe näitaja kohta vajavad, ühest kohast."""
    nid = x["n"]["id"]
    m = next((m for m in K["moodikud"].values() if m["naitaja"] == nid), None)
    c = {"moodik": m, "moiste": None, "ala": None, "teema": None, "V": None, "uuemad": [], "ee_uus": None, "ee_uus_lahk": []}
    if m:
        c["moiste"] = K["moisted"][m["moiste"]]
        c["ala"] = K["kategooriad"][c["moiste"]["kategooria"]]
        c["teema"] = K["kategooriad"][c["ala"]["ulem"]]
        V = kataloog.vordle(K, m["moiste"])
        c["V"] = V
        for r, d in V["riigid"].items():
            if d["uuem"]:
                u = {"riik": r, "v": d["uuem"], "alus": d["alus"], "m": K["moodikud"][d["uuem"]["moodik"]]}
                c["uuemad"].append(u)
                if r == FOOKUS:
                    c["ee_uus"] = u
        c["uuemad"].sort(key=lambda u: -u["v"]["vaartus"])
        if c["ee_uus"]:
            # Kui sama allika varasem aasta erineb võrdlusalusest, ei saa selle uuemat numbrit pealkirjaks panna.
            c["ee_uus_lahk"] = [p for p in V["paarid"] if p["moodik"] == c["ee_uus"]["m"]["id"]
                                and p["riik"] == FOOKUS and p["staatus"] == "lahknevus"]
    c["reeglid"] = [r for r in D["riskid"] if r["naitaja"] == nid and r.get("reegel")]
    c["vaited"] = [r for r in D["riskid"] if r["naitaja"] == nid and r["liik"] == "vaide"]
    c["piirangud"] = [r for r in D["riskid"] if r["naitaja"] == nid and r["liik"] == "piirang"]
    c["hupoteesid"] = [r for r in D["riskid"] if r["naitaja"] == nid and r["liik"] == "hupotees"]
    c["kontrollid"] = kontrollid(x, D, K, c)
    return c


def ee_allikad_tabel(K, V):
    """Eesti number kõigi allikate järgi, üks rida allika kohta."""
    mood = {x["id"]: x for x in V["moodikud"]}
    ee_mood = [x for x in V["moodikud"] if any(r == FOOKUS for r, _ in V["vaatlused"][x["id"]])]
    if not ee_mood:
        return ""
    aastad = sorted({a for x in ee_mood for r, a in V["vaatlused"][x["id"]] if r == FOOKUS})
    paar = {(p["moodik"], p["riik"], p["aasta"]): p for p in V["paarid"]}
    read = []
    for x in ee_mood:
        lahtrid = []
        for a in aastad:
            v = V["vaatlused"][x["id"]].get((FOOKUS, a))
            if v is None:
                lahtrid.append('<td class="r">–</td>')
                continue
            p = paar.get((x["id"], FOOKUS, a))
            if p and p["klass"] == "sama" and p["staatus"] != "kooskolas":
                lahtrid.append(f'<td class="r is-lahk">{arv_k(v)}<br><span class="small">{kataloog.STAATUSED[p["staatus"]]}</span></td>')
            else:
                lahtrid.append(f'<td class="r">{arv_k(v)}</td>')
        read.append(
            f'<tr><th scope="row">{e(x["nimi"])}<br><span class="small">{e(x["populatsioon"])}</span></th>'
            f'<td>{klassi_tag(x["vorreldavus"])}</td>{"".join(lahtrid)}</tr>')
    pea = "".join(f'<th class="r" scope="col">{a}</th>' for a in aastad)
    return (
        f'<h4>Eesti kõigi allikate järgi</h4><p class="small">{e(mood[V["alus_id"]]["uhik"])}. Esimene rida on võrdlusalus. '
        "Esiletõstetud lahter: sama mõõdikuga allikas erineb võrdlusalusest rohkem, kui ümardamine seletab.</p>"
        '<div class="table-wrap"><table><thead><tr><th scope="col">Allikas</th><th scope="col">Võrreldavus</th>'
        f'{pea}</tr></thead><tbody>{"".join(read)}</tbody></table></div>')


def kontrollide_loend(V):
    """Iga mõõdiku võrdlus võrdlusalusega."""
    kontrollid = []
    for x in V["moodikud"]:
        pp = [p for p in V["paarid"] if p["moodik"] == x["id"]]
        if not pp:
            continue
        loend = {s: sum(1 for p in pp if p["staatus"] == s) for s in kataloog.STAATUSED}
        kokku = ", ".join(f"{kataloog.STAATUSED[s]} {n}" for s, n in loend.items() if n)
        erand = [p for p in pp if p["staatus"] != "kooskolas"]
        det = "".join(
            f'<li>{riik(p["riik"])} {p["aasta"]}: {arv(p["teine"], 2)} vs võrdlusalus {arv(p["alus"], 2)}, '
            f'vahe {arv(p["vahe"], 2)} protsendipunkti ({kataloog.STAATUSED[p["staatus"]]})</li>' for p in erand)
        if x["vorreldavus"] == "sama":
            selg = "Peab klappima võrdlusalusega." + (" Kõik klapivad." if not erand else " Erinevused:")
        else:
            selg = "Erinevus on oodatav: " + (x["erinevused"] or "erinev kogum või klassifikaator.")
        kontrollid.append(
            f'<li><div class="row"><h4>{e(x["nimi"])}</h4>{klassi_tag(x["vorreldavus"])}</div>'
            f'<p>{len(pp)} võrdlust: {kokku}.</p><p class="small">{e(selg)}</p>'
            + (f'<ul class="small">{det}</ul>' if det and x["vorreldavus"] == "sama" else "")
            + "</li>")
    return f'<ul class="items">{"".join(kontrollid)}</ul>' if kontrollid else ""


def muud_kusitlused(K, V):
    """Teised küsitlused eraldi tabelis, mitte võrdlusalusega samas reas."""
    mood = {x["id"]: x for x in V["moodikud"]}
    muud = sorted((v for d in V["riigid"].values() for v in d["muud"]),
                  key=lambda v: (kataloog.JARJEKORD.index(mood[v["moodik"]]["vorreldavus"]), v["moodik"], v["riik"]))
    if not muud:
        return ""
    mr, nahtud = [], set()
    for v in muud:
        x = mood[v["moodik"]]
        # Pikk selgitus ainult mõõdiku esimesel real, järgmistel viide sellele.
        miks = (f'{e(x["populatsioon"])}; {e(x["periood"])}. {e(x["erinevused"])}' if x["id"] not in nahtud
                else "Sama mis eespool.")
        nahtud.add(x["id"])
        mr.append(f'<tr><td>{linkita(x["nimi"], v["url"] or x["url"])}<br>{klassi_tag(x["vorreldavus"])}</td>'
                  f'<td>{riik(v["riik"])}</td><td>{v["aasta"]}</td><td class="r">{arv_k(v)}</td>'
                  f'<td class="small">{miks}</td></tr>')
    return ('<p class="small">Need riigid mõõdavad teise küsitlusega (teine periood, ettevõtete suurus või küsimus). '
            "Neid ei järjestata koos Eurostati numbritega.</p>"
            '<div class="table-wrap"><table><thead><tr><th scope="col">Allikas</th><th scope="col">Riik</th>'
            '<th scope="col">Aasta</th><th class="r" scope="col">Väärtus</th><th scope="col">Miks ei saa võrrelda</th>'
            f'</tr></thead><tbody>{"".join(mr)}</tbody></table></div>')


def vahe_joonis(x, D):
    """Eesti numbri lahknevus ametlike allikate vahel punktireana koos seletusega."""
    n, meta = x["n"], x["meta"]
    olekud = {(l["naitaja"], int(l["aasta"])): l for l in D["lahknevused"]}
    osad = []
    for a in sorted({v["aasta"] for v in meta.get("vordlus", []) if v.get("vastuolu")}):
        vrd = [v for v in meta["vordlus"] if v["aasta"] == a and v["riik"] == FOOKUS and v.get("vaartus") is not None]
        if a not in x["seeria"].get(FOOKUS, {}):
            continue
        pohi = x["seeria"][FOOKUS][a][0]
        vmin = min((v for v in vrd if v.get("vastuolu")), key=lambda v: abs(v["vahe"]))
        ol = olekud.get((n["id"], a), {})
        read = [{"nimi": f"Eurostat <code>{e(n['andmestik'])}</code>", "usaldus": "võrdlusalus", "v": pohi, "fookus": True}]
        for v in vrd:
            read.append({"nimi": f'<a href="{e(v["url"])}">{e(v["allikas"])}</a>', "usaldus": v["usaldus"],
                         "v": v["vaartus"], "teisene": v["usaldus"] != "ametlik statistika"})
        osad.append(
            f'<h4>Eesti {a}: Eurostat {arv(pohi)}%, Statistikaamet {arv(vmin["vaartus"])}%, vahe {arv(abs(vmin["vahe"]))} punkti</h4>'
            '<p class="small">Katkendjoon on Eurostati väärtus, tühi ring on teisene allikas (uudis).</p>'
            f'{punktirida(read, pohi)}'
            '<div class="note">'
            f'<p><b>Põhjus: {e(ol.get("staatus", "kinnitamata"))}.</b> {e(n.get("vastuolu_selgitus", ""))}</p>'
            + (f'<p><b>Järgmine samm.</b> {e(ol["jargmine_samm"])}</p>' if ol.get("jargmine_samm") else "")
            + "</div>")
    return "".join(osad)


def kontrollid(x, D, K, c):
    """Viis usaldusküsimust. Igaühel silt, üks lause ja avatav detail."""
    n, meta = x["n"], x["meta"]
    V = c["V"]
    tulem = []

    # 1. Värskus
    st = meta["varskus"]["staatus"]
    lause = (f'Eurostat uuendas andmeid {kuupaev(meta["allikas_uuendas"])}. '
             f'Järgmine uuendus on oodata {kuupaev(meta["varskus"]["jargmine_oodatav"])}.')
    if c["ee_uus"]:
        u = c["ee_uus"]
        lause += f' {org(K, u["m"])} on {u["v"]["aasta"]}. aasta numbri juba avaldanud.'
    tulem.append({"id": "varskus", "nimi": "Kui värske see on", "luhi": "Värskus", "silt": st,
                  "klass": "ok" if st == "ajakohane" else "risk", "lause": lause, "detail": varskuse_detail(x, K, c)})

    # 2. Allikate kooskõla. Kriitilised lahtrid (Eesti ja EL viimane aasta) eraldi, koopiaid kinnituseks ei loeta.
    kl = kataloog.klappimine(V["paarid"]) if V else {"koik": {"kokku": 0}, "kriitilised": {"kokku": 0}, "koopiaid": 0}
    koik, kriit = kl["koik"], kl["kriitilised"]
    olekud = {(l["naitaja"], int(l["aasta"])): l for l in D["lahknevused"]}
    koopiad = (f' {kl["koopiaid"]} korral kordab allikas lihtsalt võrdlusaluse numbrit (näiteks OECD võtab ELi riikide '
               "numbri Eurostatist), neid kinnituseks ei loeta.") if kl["koopiaid"] else ""
    if not koik["kokku"]:
        silt, klass = "kontrollimata", ""
        lause = "Teist sõltumatut sama mõõdikuga allikat pole, nii et numbrit ei saa veel teise allikaga kontrollida." + koopiad
    else:
        lahk, vaike = koik["lahknevused"], koik["vaikesed"]
        if kriit["lahknevused"]:
            silt, klass = "kriitiline vahe", "risk"
        else:
            silt, klass = (f"{len(lahk)} vahe", "risk") if lahk else ("väike vahe", "") if vaike else ("klapivad", "ok")
        lause = (f'Kõige olulisemates lahtrites (Eesti ja ELi viimane aasta) klapib {numbrit(kriit["klapib"])} {kriit["kokku"]}-st. '
                 if kriit["kokku"] else "")
        lause += (f'Kõigist sõltumatutest võrdlustest klapib ümardamise täpsusega {numbrit(koik["klapib"])} {koik["kokku"]}-st.'
                  + koopiad)
        for p in lahk:
            ol = olekud.get((n["id"], p["aasta"]), {})
            lause += (f' {riik(p["riik"])} {p["aasta"]}: Eurostat {arv(p["alus"], 1)}%, {K["moodikud"][p["moodik"]]["nimi"]} '
                      f'{arv(p["teine"], 1)}%, põhjus on {ol.get("staatus", "selgitamata")}.')
        if vaike:
            lause += f" Väike vahe {len(vaike)} korral."
    detail = vahe_joonis(x, D)
    for h in c["hupoteesid"]:
        detail += f'<ul class="items">{kirje("Hüpotees", "", h["pealkiri"], h["selgitus"], h["mida_teha"], h)}</ul>'
    if V:
        detail += ee_allikad_tabel(K, V) + "<h4>Iga allikas võrdlusaluse suhtes</h4>" + kontrollide_loend(V)
    tulem.append({"id": "kooskola", "nimi": "Kas allikad klapivad", "luhi": "Allikad", "silt": silt, "klass": klass,
                  "lause": lause, "detail": detail})

    # 3. Meetodi muutused
    margid = [kirje("Piirang", "", r["pealkiri"], r["selgitus"], r["mida_teha"], r) for r in c["piirangud"]]
    if c["ee_uus"] and c["ee_uus"]["m"]["vorreldavus"] == "osaliselt":
        u = c["ee_uus"]
        margid.append(kirje("Võrreldavus", "", f'{u["m"]["nimi"]}: {u["v"]["aasta"]}', u["m"]["erinevused"]))
    for p in andmeprobleemid(x):
        sil = "Kontrollimata" if p["tase"] == "kontrollimata" else "Eurostati märge"
        margid.append(kirje(sil, "risk" if p["tase"] == "kontrollimata" else "", "Aegrida", p["tekst"]))
    esimene = (c["piirangud"][0]["pealkiri"] + ".") if c["piirangud"] else "Teadaolevaid meetodimuutusi pole."
    tulem.append({"id": "meetod", "nimi": "Kas mõõtmisviis on muutunud", "luhi": "Meetod",
                  "silt": f"{len(margid)} märget" if margid else "muutusi pole", "klass": "risk" if c["piirangud"] else "",
                  "lause": esimene + (f" Kokku {len(margid)} märget aegrea kohta." if len(margid) > 1 else ""),
                  "detail": f'<ul class="items">{"".join(margid)}</ul>' if margid else ""})

    # 4. Mida number ei ütle
    pp = n.get("piirangud", [])
    tulem.append({"id": "piirangud", "nimi": "Mida number ei ütle", "luhi": "Piirangud",
                  "silt": f"{len(pp)} piirangut", "klass": "", "lause": pp[0] if pp else "Piiranguid pole kirja pandud.",
                  "detail": f'<ul class="plain">{"".join(f"<li>{e(p)}</li>" for p in pp)}</ul>' if pp else ""})

    # 5. Avalikud väited
    vv = c["vaited"]
    if vv:
        lause = f"Seire kontrollis {len(vv)} avalikku väidet: " + "; ".join(
            f'{r["allikas"].split(",")[0]} ({r["hinnang"].lower() or "täpsusta"})' for r in vv) + "."
        detail = '<ul class="items">' + "".join(
            kirje(r["hinnang"] or "Täpsusta", "risk", r["pealkiri"], r["selgitus"], r["mida_teha"], r) for r in vv) + "</ul>"
    else:
        lause, detail = "Avalikke väiteid selle numbri kohta pole veel kontrollitud.", ""
    tulem.append({"id": "vaited", "nimi": "Kas seda on avalikult õigesti öeldud", "luhi": "Väited",
                  "silt": f"{len(vv)} täpsustada" if vv else "kontrollimata", "klass": "risk" if vv else "",
                  "lause": lause, "detail": detail})
    return tulem


def varskuse_detail(x, K, c):
    meta = x["meta"]
    u = dt.date.fromisoformat(meta["allikas_uuendas"])
    k = dt.date.fromisoformat(meta["kontrollitud"])
    j = dt.date.fromisoformat(meta["varskus"]["jargmine_oodatav"])
    vanus, tsykkel = (k - u).days, (j - u).days
    riba = (
        '<div class="age">'
        f'<p>Eurostati andmed olid kontrollimise päeval ({kuupaev(meta["kontrollitud"])}) {vanus} päeva vanad. '
        f'Uuenduste vahe on umbes {tsykkel} päeva.</p>'
        f'<div class="age-track" role="img" aria-label="{vanus} päeva {tsykkel}-st">'
        f'<div class="age-fill" style="width:{min(vanus / tsykkel, 1) * 100:.1f}%"></div></div>'
        f'<div class="age-legend"><span>Uuendatud {kuupaev(meta["allikas_uuendas"])}</span>'
        f'<span>Järgmine {kuupaev(meta["varskus"]["jargmine_oodatav"])}</span></div></div>')
    read = [f'<tr><td>Eurostat <code>{e(x["n"]["andmestik"])}</code></td><td>{x["viimane"]}</td>'
            f'<td>{kuupaev(meta["allikas_uuendas"])}</td><td>{staatuse_silt(meta["varskus"]["staatus"])}</td></tr>']
    for uu in c["uuemad"]:
        v = uu["v"]
        read.append(f'<tr><td>{linkita(uu["m"]["nimi"], v["url"] or uu["m"]["url"])}</td><td>{v["aasta"]}</td>'
                    f'<td>{kuupaev(v["avaldatud"]) if v["avaldatud"] else "–"}</td><td><span class="tag focus">uuem number</span></td></tr>')
    for r in x["riiklikud"]:
        if r["v"] is None:
            read.append(f'<tr><td>{linkita(r["allikas"], r["url"])}</td><td>–</td><td>–</td>'
                        f'<td><span class="tag">{e(r["aasta"])} avaldamata</span></td></tr>')
    tabel = ('<div class="table-wrap"><table><thead><tr><th scope="col">Allikas</th><th scope="col">Viimane aasta</th>'
             f'<th scope="col">Avaldatud</th><th scope="col">Olek</th></tr></thead><tbody>{"".join(read)}</tbody></table></div>')
    return riba + tabel


def staatuse_silt(st):
    return f'<span class="tag {"ok" if st == "ajakohane" else "risk"}">{e(st)}</span>'


def oige_lause(x, K, c):
    a, s, n = x["viimane"], x["seeria"], x["n"]
    tegu, kelle = SONASTUS.get(n["id"], ("", ""))
    ee = s[FOOKUS][a][0]
    el = s.get(VIIDE, {}).get(a, (None,))[0]
    if n["id"] in LAUSED:
        lause = LAUSED[n["id"]].format(a=a, v=arv(ee))
    elif tegu:
        lause = f"Eurostati järgi {tegu} {a}. aastal {arv(ee)}% {kelle}"
    else:
        lause = f"{n['nimi']}: Eestis {arv(ee)}% ({a}, Eurostat)"
    lause += f" (ELi keskmine {arv(el)}%)." if el is not None else "."
    if c["ee_uus"]:
        u = c["ee_uus"]
        lause += f' {org(K, u["m"])} annab {u["v"]["aasta"]}. aasta kohta {arv_k(u["v"])}%.'
        if c["ee_uus_lahk"]:
            p = c["ee_uus_lahk"][0]
            lause += (f' {org(K, u["m"])} arvutab seda aga teisiti: {p["aasta"]}. aasta kohta andis ta {arv(p["teine"], 1)}%, '
                      f'Eurostat {arv(p["alus"], 1)}%. Võrdle selle allika numbreid ainult omavahel.')
        elif u["m"]["vorreldavus"] != "sama":
            lause += " Need kaks numbrit pole täpselt võrreldavad, nii et kasvu nende vahel ei saa täpselt arvutada."
    return lause


def kaart(x, c, K):
    """Ülevaate tabloo rida: näitaja, Eesti uusim number, koht võrdlusriikide seas, usaldus ja üks reegel."""
    n, a, s = x["n"], x["viimane"], x["seeria"]
    ee, _ = leid(x)
    el = s.get(VIIDE, {}).get(a, (None,))[0]
    koht, kokku = jarjestus(x, a)
    _, kelle = SONASTUS.get(n["id"], ("", n["uhik"]))
    if c["ee_uus"] and not c["ee_uus_lahk"]:
        u = c["ee_uus"]
        suur, millal = arv_k(u["v"]), f'{u["v"]["aasta"]}, {org(K, u["m"])}'
    else:
        suur, millal = arv(ee), f"{a}, Eurostat"
    vrd = (f"ELiga võrreldav {a}. aasta number: Eesti {arv(ee)}%, ELi keskmine {arv(el)}%. "
           f"Võrdlusriikide seas {koha_tekst(x, koht, kokku)}.") if el is not None else ""
    # Pilt enne teksti: Eesti punkt võrdlusriikide seas, kriips = ELi keskmine. Lause jääb ekraanilugejale.
    punktid = [(riik(g), v[a][0], f"{arv(v[a][0])}%", g == FOOKUS) for g, v in s.items() if a in v and g != VIIDE]
    asukoht = (f'<div class="tb-loc"><p class="ind-loc-cap">Eurostat {a}: Eesti {arv(ee)}%, {koht}. koht {kokku}-st'
               + (" (väiksem on parem)" if vaiksem_parem(x) else "")
               + (f'<span class="nw"><i class="k-eu"></i> EL {arv(el)}%</span>' if el is not None else "") + "</p>"
               + pildid.asukoht(punktid, el=(el, f"{arv(el)}%") if el is not None else None, title=True)
               + f'<p class="sr-only">{e(vrd)}</p></div>')
    usaldus = "".join(f'<li class="tr {k["klass"]}"><i aria-hidden="true"></i>{e(k["luhi"])}: {e(k["silt"])}</li>'
                      for k in c["kontrollid"] if k["id"] in ("varskus", "kooskola", "vaited"))
    eyebrow = c["ala"]["nimi"] if c["ala"] else "Näitaja"
    leht_ = fail_naitajale(x)
    reegel = (f'<p class="tb-rule"><b>Pea meeles:</b> {e(c["reeglid"][0]["reegel"])} '
              f'<a href="{leht_}#usaldus">Miks</a></p>') if c["reeglid"] else ""
    return (
        '<li class="tb-row">'
        f'<a class="tb-name" href="{leht_}"><span class="eyebrow">{e(eyebrow)}</span>'
        f'<b>{e(n["nimi"])}</b><small>{e(kelle)}</small></a>'
        f'<p class="tb-big"><span>{suur}%</span><small>{e(millal)}</small></p>'
        f'{asukoht}<ul class="tb-trust" aria-label="Kas numbrit võib usaldada">{usaldus}</ul>{reegel}</li>')


# ---------- lehed ----------

def kusimuse_naitaja(K, mid):
    """Küsimuse seire näitaja id võrdlusaluse mõõdiku kaudu (sama reegel nagu lehel „Tehisaru ja töö“), või ""."""
    return K["moodikud"].get(K["moisted"][mid]["vordlusalus"], {}).get("naitaja", "")


# Avalehe plokk „Kust vastus tuleb“: rühm ütleb, kui kaugel on ametlik number; uuringute arv on iga küsimuse juures.
NUMBRI_OLEK = [
    ("seires", "Seire näitaja", "Number, usaldus ja uuringud on näitaja lehel."),
    ("andmed", "Numbrid kataloogis", "Numbrid on teemade lehel, eraldi näitajat veel pole."),
    ("kavandatud", "Allikas teada, andmed laadimata", "Ametlik allikas on leitud, aga seire ei lae seda veel."),
    ("allikas_leidmata", "Ametlikku allikat pole leitud", "Võrreldavat ametlikku numbrit pole veel leitud."),
]


def kusimuste_kaart(D, K):
    """Iga kataloogi küsimus täpselt ühes rühmas võrdlusaluse oleku järgi, juures seotud uuringute arv."""
    lehed = {x["n"]["id"]: fail_naitajale(x) for x in D["naitajad"]}
    ryhmad = {k: [] for k, _, _ in NUMBRI_OLEK}
    for mid, mo in K["moisted"].items():
        nid = kusimuse_naitaja(K, mid)
        olek = "seires" if nid in lehed else K["moodikud"].get(mo["vordlusalus"], {}).get("olek", "allikas_leidmata")
        olek = olek if olek in ryhmad else "allikas_leidmata"
        n_uur = len(D["uuringud"].get(mid, []))
        if nid in lehed:
            nimi = f'<a href="{lehed[nid]}">{e(mo["nimi"])}</a>'
            uur = f' · <a class="n" href="{lehed[nid]}#uuringud">{n_uur} uuring{"ut" if n_uur > 1 else ""}</a>' if n_uur else ""
        else:
            nimi = f'<a href="teemad.html#{e(mid)}">{e(mo["nimi"])}</a>'
            uur = f' · <a class="n" href="{TOOELU_LEHT}">{n_uur} uuring{"ut" if n_uur > 1 else ""}</a>' if n_uur else ""
        ryhmad[olek].append(f'<li data-kusimus="{e(mid)}">{nimi}{uur}</li>')
    plokk = "".join(
        f'<div class="qgroup qgroup-{k}"><h3>{e(pealk)} <span class="n">{len(ryhmad[k])}</span></h3><p class="small">{e(selg)}</p>'
        f'<ul class="plain">{"".join(ryhmad[k])}</ul></div>'
        for k, pealk, selg in NUMBRI_OLEK if ryhmad[k])
    return (f'<div class="qgroups">{plokk}</div>'
            '<p class="small">Rühm näitab, kui kaugel on ametlik number. Uuringute arv näitab, mitu uuringut on küsimusega '
            'seotud: need on üksikud tulemused oma valimi ja meetodiga, mitte ametlik statistika, ja neid ei panda numbriga '
            'samale joonisele.</p>')

def avaleht(D, K, tana):
    NN = D["naitajad"]
    kk = kataloog.kokkuvote(K)
    eespool = [x for x in NN if eesti_eespool(x)]
    vrdl = [x for x in NN if eesti_eespool(x) is not None]
    # Pealkiri sama sõnumiga kui analüütiku vaade: Põhjamaade võrdlus on teravam kui ELi keskmine.
    P = {S["mid"]: S for S in (analuus.statistika(K, r) for r in analuus.PROFIIL) if S}
    hea = [S for S in P.values() if S["hinnang"] in ("yle", "vahemik")]
    iu, eb = P.get("eurostat-isoc-ai-iaiu"), P.get("eurostat-isoc-eb-ai")
    if iu and eb and iu["hinnang"] in ("yle", "vahemik") and eb["hinnang"] not in ("yle", "vahemik"):
        h1 = 'Inimesed on Põhjamaade tasemel, <span class="hl">ettevõtted maas</span>'
    elif vrdl:
        h1 = f'Eesti on ELi keskmisest eespool <span class="hl">{len(eespool)} näitajas {len(vrdl)}-st</span>'
    else:
        h1 = "Tehisaru kasutus ja oskused Eestis ja võrdlusriikides"
    lead = "Eesti tehisaru kasutus ja oskused ametliku statistika järgi"
    if vrdl:
        lead += (f". ELi keskmisest eespool kõigis {len(vrdl)} näitajas." if len(eespool) == len(vrdl)
                 else f". ELi keskmisest eespool {len(eespool)} näitajas {len(vrdl)}-st.")
    else:
        lead += "."

    pais_rida = ('<li class="tb-head" aria-hidden="true"><span>Näitaja</span><span>Eesti uusim</span>'
                 '<span>Koht 7 riigi seas</span><span>Kas võib usaldada</span></li>')
    tabloo = (f'<ul class="tabloo">{pais_rida}{"".join(kaart(x, x["k"], K) for x in NN)}</ul>'
              '<p class="small">Punktireal on Eesti suurem lilla punkt, teised riigid hallid ja püstkriips ELi keskmine. '
              'Iga näitaja kõik reeglid, allikad ja ajalugu on tema lehel.</p>')

    uudised = [s for s in D["sundmused"] if s["liik"] in ("allikas", "lahknevus")][:3]
    uut = "".join(
        f'<li><span class="when">{kuupaev(s["kuupaev"])}</span><div class="body"><p>{e(s["tekst"])}</p>'
        + (f'<a class="small" href="{e(s["url"])}">Allikas</a>' if s.get("url") else "") + "</div></li>"
        for s in uudised)
    edasi = [
        ("kaart.html", "ELi kaart", "Kõik 27 ELi riiki kaardil. Kus Eesti paikneb iga näitaja järgi."),
        ("analuus.html", "Analüütiku vaade", f"{len(hea)} näitajat {len(P)}-st Põhjamaade tasemel. Tugevad ja nõrgad küljed, kas vahe väheneb."),
        ("teemad.html", "Teemad ja allikad", f'{kk["moisteid"]} küsimust {kk["teemasid"]} teemas, andmed {kk["moisteid_andmetega"]} kohta. Kust iga number tuleb.'),
        ("kuidas.html", "Kuidas see töötab", "Mida märgid tähendavad, seire enda nõrkused ja muudatuste logi."),
    ]
    if D["uuringud"]:
        edasi.insert(0, (TOOELU_LEHT, "Mida uuritakse", "Mida uuringud leiavad tehisaru mõjust tööle ja kui kindlad need leiud on."))
    if D["vaited"]:
        nv = len(D["vaited"])
        edasi.insert(1 if D["uuringud"] else 0,
                     (VAITED_LEHT, "Mida väidetakse",
                      f'{nv} {"avalik lause" if nv == 1 else "avalikku lauset"}, kontrollitud algallika vastu.'))
    edasi.insert(sum(1 for f, _, _ in edasi if f in (TOOELU_LEHT, VAITED_LEHT)),
                 (OTSUSED_LEHT, "Mida otsustatakse", "Tehisaru määruse tähtajad ja ametlikud sihid ühel ajajoonel."))
    edasi_html = '<ul class="edasi">' + "".join(
        f'<li><a href="{f}"><b>{e(t)} <span aria-hidden="true">→</span></b><span>{e(d)}</span></a></li>' for f, t, d in edasi) + "</ul>"
    sisu = (
        sektsioon(f"{len(NN)} näitajat ühe pilguga", tabloo, "Eesti uusimad numbrid", "tabloo")
        + (sektsioon("Kust vastus tuleb", kusimuste_kaart(D, K), "Mõõdikud ja uuringud", "kusimused") if D["uuringud"] else "")
        + sektsioon("Mis on andmetes uut", f'<ul class="list">{uut}</ul><p><a href="kuidas.html#logi">Kogu muudatuste logi</a></p>', "Uuendused")
        + sektsioon("Kuhu edasi", edasi_html, "Süvitsi"))
    return leht("index.html", "Tehisaru seire", sisu, tana, avafoto(h1, lead, tana))


def uuemad_plokk(x, c):
    uu = c["uuemad"]
    if not uu:
        return ""
    n = x["n"]
    kogu = uu
    # Joonisele ainult sama ühikuga numbrid (näiteks % isikutest). Teise nimetajaga numbrid on ainult tabelis.
    alus_uhik = c["moodik"]["uhik"] if c["moodik"] else None
    uu = [u for u in kogu if alus_uhik is None or u["m"]["uhik"] == alus_uhik]
    teine_nimetaja = [u for u in kogu if u not in uu]
    if not uu:
        uu = kogu
        teine_nimetaja = []
    aastad = sorted({u["v"]["aasta"] for u in uu})
    aasta = aastad[-1]
    tipp = max(u["v"]["vaartus"] for u in uu)
    tulbad_html = "".join(
        f'<li class="{"is-focus" if u["riik"] == FOOKUS else ""}"><span class="lab">{riik(u["riik"])}</span>'
        f'<span class="track"><span class="bar" style="width:{u["v"]["vaartus"] / tipp * 100:.1f}%"></span></span>'
        f'<span class="val">{arv_k(u["v"])}%</span></li>' for u in uu)
    avaldamata = [riik(r["riik"]) for r in x["riiklikud"] if r["v"] is None]
    kontroll = max(u["v"]["kontrollitud"] for u in uu)
    if len(uu) == 1:
        pealk = f'{riik(uu[0]["riik"])} on {uu[0]["v"]["aasta"]}. aasta numbri juba avaldanud'
    elif len(aastad) == 1:
        pealk = f'{len(uu)} riiki on {aasta}. aasta numbri juba avaldanud'
    else:
        pealk = f'{len(uu)} riigil on uuem number kui Eurostatis'
    read = "".join(
        f'<tr class="{"is-focus" if u["riik"] == FOOKUS else ""}"><th scope="row">{riik(u["riik"])}</th>'
        f'<td class="r">{arv_k(u["v"])}% ({u["v"]["aasta"]})</td>'
        f'<td class="r">{arv_k(u["alus"]) + "% (" + str(u["alus"]["aasta"]) + ")" if u["alus"] else "–"}</td>'
        f'<td>{linkita(u["m"]["nimi"], u["v"]["url"] or u["m"]["url"])}'
        f'<br><span class="small">{"avaldatud " + kuupaev(u["v"]["avaldatud"]) if u["v"]["avaldatud"] else ""}</span></td>'
        f'<td>{klassi_tag(u["m"]["vorreldavus"])}<br><span class="small">{e(u["m"]["populatsioon"])}. {e(u["m"]["erinevused"])}</span></td></tr>'
        for u in kogu)
    tabel = ('<div class="table-wrap"><table><thead><tr><th scope="col">Riik</th><th class="r" scope="col">Uuem (riiklik)</th>'
             '<th class="r" scope="col">Eurostat</th><th scope="col">Allikas</th><th scope="col">Võrreldavus</th></tr></thead>'
             f'<tbody>{read}</tbody></table></div>')
    osaliselt = [u for u in uu if u["m"]["vorreldavus"] == "osaliselt"]
    lahk = [u for u in uu if u["riik"] == FOOKUS and c["ee_uus_lahk"]]
    markus = ""
    if osaliselt or lahk:
        miks = " ".join(f'{riik(u["riik"])}: {u["m"]["erinevused"]}' for u in osaliselt + lahk if u not in teine_nimetaja)
        markus = ('<div class="note"><p><b>Miks neid ei panda Eurostati numbritega samale joonisele?</b> '
                  f"{e(miks)} Kasvu arvutamiseks oota Eurostati {aasta}. aasta väärtusi.</p></div>")
    joonis = (
        '<div class="card"><div class="chart">'
        f'<h3 class="chart-title">{pealk}</h3>'
        f'<p class="chart-sub">{e(n["uhik"])}, riikide statistikaametid. Eurostatis neid veel pole.</p>'
        f'<ul class="bars" role="list">{tulbad_html}</ul>'
        + (f'<p class="source">{e(", ".join(avaldamata))} pole {aasta}. aasta numbrit veel avaldanud. ' if avaldamata else '<p class="source">')
        + (f'{e(", ".join(riik(u["riik"]) for u in teine_nimetaja))} number on arvutatud teisest nimetajast '
           "ja on ainult tabelis „Allikad ja võrreldavus“. " if teine_nimetaja else "")
        + f"Kontrollitud {kuupaev(kontroll)}.</p></div></div>")
    return sektsioon("Uuemad numbrid riikide statistikaametitelt",
                     joonis + markus + avatav("Allikad ja võrreldavus", tabel), "Uuem kui Eurostat", "uuemad")


def ajas_plokk(x, c, K):
    n, s, a = x["n"], x["seeria"], x["viimane"]
    eel = [t for t in s.get(FOOKUS, {}) if t < a]
    if eel:
        eel = max(eel)
        kasv_ee = s[FOOKUS][a][0] - s[FOOKUS][eel][0]
        pealk = f"Eesti {'kasv' if kasv_ee > 0 else 'muutus'} {eel}–{a} oli {arv(kasv_ee)} protsendipunkti"
        if eel in s.get(VIIDE, {}) and a in s.get(VIIDE, {}):
            pealk += f", ELi keskmisel {arv(s[VIIDE][a][0] - s[VIIDE][eel][0])}"
        sisu = (
            '<div class="card"><div class="chart">'
            f'<h3 class="chart-title">{pealk}</h3>'
            f'<p class="chart-sub">{e(kogum(n))}, {x["aastad"][0]}–{a}, Eurostat · {ANDMELIIK}</p>{jooned(x)}'
            '<p class="source">Katkendjoon: vahepealse aasta kohta väärtust pole. '
            f'{e(lipud_lause(x, x["aastad"]))} Enne kasvu tõlgendamist vaata, '
            'kas mõõtmisviis on muutunud (<a href="#usaldus">usaldus</a>).</p></div></div>')
        return sektsioon("Muutus ajas", sisu, "Aegrida", "ajas")
    tekst = f"Eurostat küsis seda esimest korda {a}. aastal, nii et Eurostati aegrida veel pole."
    u = c["ee_uus"]
    if u and u["m"]["vorreldavus"] == "sama" and c["V"]:
        vv = c["V"]["vaatlused"][u["m"]["id"]]
        ee = sorted((t, v) for (r, t), v in vv.items() if r == FOOKUS)
        if len(ee) >= 2:
            (t0, v0), (t1, v1) = ee[-2], ee[-1]
            muutus = v1["vaartus"] - v0["vaartus"]
            tekst += (f' {u["m"]["nimi"]} küsib sama küsimust: Eestis {t0}. aastal '
                      f'{arv_k(v0)}%, {t1}. aastal {arv_k(v1)}%, {"kasv" if muutus >= 0 else "langus"} '
                      f'{arv(abs(muutus))} protsendipunkti.')
            if c["ee_uus_lahk"]:
                tekst += (f' {org(K, u["m"])} arvutab seda teisiti kui Eurostat, nii et muutust saab lugeda ainult '
                          'selle allika enda numbrite vahel.')
    return sektsioon("Muutus ajas", f'<div class="note"><p>{e(tekst)}</p></div>', "Aegrida", "ajas")


def numbrit(n):
    return f"{n} number" if n == 1 else f"{n} numbrit"


def kriitilise_hoiatus(x, D, K, c):
    """Hoiatus lehe esimeses vaates, kui allikad lähevad lahku kriitilises lahtris (Eesti või EL viimane aasta)."""
    if not c["V"]:
        return ""
    olekud = {(l["naitaja"], int(l["aasta"])): l for l in D["lahknevused"]}
    osad = []
    for p in kataloog.klappimine(c["V"]["paarid"])["kriitilised"]["lahknevused"]:
        ol = olekud.get((x["n"]["id"], p["aasta"]), {})
        osad.append(f'{riik(p["riik"])} {p["aasta"]}: Eurostat {arv(p["alus"], 1)}%, '
                    f'{e(K["moodikud"][p["moodik"]]["nimi"])} {arv(p["teine"], 1)}%. '
                    f'Põhjus on {e(ol.get("staatus", "selgitamata"))}.')
    if not osad:
        return ""
    return ('<div class="note"><p><b>Allikad annavad kõige olulisema numbri kohta eri vastuse.</b> '
            + " ".join(osad) + ' <a href="#usaldus-kooskola">Vaata põhjendust</a></p></div>')


def uuringute_kast(D, c):
    """Kast „Mida uuringud ütlevad“: üksikud uuringud sama küsimuse kohta, eraldi ametlikust numbrist."""
    if not c["moiste"]:
        return ""
    U = D["uuringud"].get(c["moiste"]["id"], [])[:UURINGUID_KUNI]
    if not U:
        return ""
    read = []
    for u in U:
        tunnus = " · ".join(x for x in [
            e(u["kus"]), e(MEETOD.get(u["meetod"], u["meetod"])),
            "retsenseeritud" if u.get("retsenseeritud") else "retsenseerimata"] if x)
        read.append(
            '<li class="study">'
            f'<p class="study-link">{e(u["seos"])}</p>'
            f'<p class="small"><b>{e(u["autorid"])} {e(str(u["aasta"]))}</b> · {tunnus}'
            + (f' <span class="tag">{e(TOEND[u["toend"]])}</span>' if u["toend"] in TOEND else "") + "</p>"
            + avatav("Mida uuring leidis", f'<p>{e(u["leid"])}</p><p class="small">{linkita(u["pealkiri"], u.get("url"))}</p>')
            + "</li>")
    sisu = ('<p class="small">Need on üksikud uuringud, mitte ametlik statistika. Nende numbreid ei saa ülal oleva '
            'numbriga otse võrrelda, sest kogum, aeg ja meetod on teised.</p>'
            f'<ul class="plain studies">{"".join(read)}</ul>'
            f'<p class="small"><a href="{TOOELU_LEHT}">Kõik uuringud lehel „Tehisaru ja töö“</a></p>')
    return sektsioon("Mida uuringud ütlevad", sisu, "Uuringud", "uuringud")


def naitaja_leht(x, D, K, tana):
    n, meta, a, s, c = x["n"], x["meta"], x["viimane"], x["seeria"], x["k"]
    ee, tekst = leid(x)
    el = s.get(VIIDE, {}).get(a, (None,))[0]
    koht, kokku = jarjestus(x, a)
    teekond = '<nav class="crumbs" aria-label="Asukoht"><a href="index.html">Ülevaade</a>'
    if c["teema"]:
        teekond += (f'<span aria-hidden="true">›</span><a href="teemad.html#teema-{e(c["teema"]["kood"])}">{e(c["teema"]["nimi"])}</a>'
                    f'<span aria-hidden="true">›</span><span>{e(c["ala"]["nimi"])}</span>')
    teekond += "</nav>"
    h1 = f'{e(n["nimi"])}: Eestis <span class="hl">{arv(ee)}%</span>, {e(tekst)}'
    faktid = [f'<div><dt>Eesti {a}</dt><dd class="hl">{arv(ee)}%<small>Eurostat, ELiga võrreldav</small></dd></div>']
    if el is not None:
        faktid.append(f'<div><dt>ELi keskmine {a}</dt><dd>{arv(el)}%<small>Eurostat</small></dd></div>')
    sh = siht(x)
    if sh:
        faktid.append(f'<div><dt>{e(siht_silt(sh))}</dt><dd>{arv_s(sh["vaartus"])}%'
                      f'<small>{e(sh["allikas"].split(",")[0])}</small></dd></div>')
    faktid.append(f'<div><dt>Koht võrdlusriikide seas</dt><dd>{koht}.<small>{kokku} riigist'
                  f'{", väiksem on parem" if vaiksem_parem(x) else ""}</small></dd></div>')
    if c["ee_uus"]:
        u = c["ee_uus"]
        faktid.append(f'<div><dt>Eesti {u["v"]["aasta"]}</dt><dd>{arv_k(u["v"])}%<small>{e(org(K, u["m"]))}, '
                      f'{"arvutab teisiti, vt usaldus" if c["ee_uus_lahk"] else "sama mõõdik" if u["m"]["vorreldavus"] == "sama" else "pole päris võrreldav"}'
                      '</small></dd></div>')
    reeglid = "".join(f"<li>{e(r['reegel'])}</li>" for r in c["reeglid"])
    kriitiline = kriitilise_hoiatus(x, D, K, c)
    oige = ('<div class="note"><p><b>Nii on õige öelda</b></p>'
            f'<p class="quote">{e(oige_lause(x, K, c))}</p>'
            + (f'<ul class="plain">{reeglid}</ul>' if reeglid else "") + "</div>")

    riigid = (
        '<div class="card"><div class="chart">'
        f'<h3 class="chart-title">Eesti on {kokku} võrdlusriigi seas {koht}. kohal'
        + (" (väiksem on parem)" if vaiksem_parem(x) else "")
        + (f", ELi keskmine on {arv(el)}%" if el is not None else "") + "</h3>"
        f'<p class="chart-sub">{e(kogum(n))}, {a} · {ANDMELIIK}</p>{tulbad(x, a)}'
        f'<p class="source">Allikas: Eurostat, andmestik <code>{e(n["andmestik"])}</code>, uuendatud {kuupaev(meta["allikas_uuendas"])}. '
        f"Riike võrreldakse Eurostati numbritega, sest need on kõigi riikide kohta sama meetodiga. {e(lipud_lause(x, [a]))}</p>"
        + (f'<p class="source">Katkendjoonega tulp on siht: {linkita(sh["allikas"], sh.get("url"))}. {e(sh.get("markus", ""))}</p>'
           if sh else "")
        + (f'<p class="source"><a href="kaart.html#{e(n["id"])}">Vaata kõiki 27 ELi riiki kaardil</a></p>'
           if any(r["naitaja"] == n["id"] for r in D["el27"]) else "")
        + "</div></div>")

    read = "".join(
        f'<details class="check" id="usaldus-{k["id"]}"><summary><span class="check-name">{e(k["nimi"])}</span>'
        f'<span class="tag {k["klass"]}">{e(k["silt"])}</span><span class="check-text">{e(k["lause"])}</span></summary>'
        f'<div class="more-body">{k["detail"] or "<p class=small>Rohkem detaile pole.</p>"}</div></details>'
        for k in c["kontrollid"])
    usaldus = sektsioon("Kas numbrit võib usaldada", f'<p class="small">Ava rida, et näha põhjendust ja allikaid.</p><div class="checks">{read}</div>',
                        "Usaldus", "usaldus")

    definitsioon = (
        '<div class="prose">'
        f'<p><b>Küsimus.</b> {e(n["kusimus"])}</p>'
        f'<p><b>Mõõdik Eurostatis.</b> {e(meta["naitaja_nimi"])}</p>'
        f'<p class="small">Päring: <a href="{e(meta["url"])}">{e(meta["url"])}</a></p>'
        f'<p class="small">Filtrid kontrollitud: {"jah, " + kuupaev(n.get("filtrid_kontrollitud_kuupaev")) if n.get("filtrid_kontrollitud") else "ei"}. '
        f'Uuendussagedus: {n["uuendussagedus_kuudes"]} kuud.</p></div>')
    muud = muud_kusitlused(K, c["V"]) if c["V"] else ""
    lisad = (avatav("Kõik Eurostati väärtused", andmetabel(x))
             + (avatav("Teised riigid teiste küsitlustega", muud) if muud else "")
             + avatav("Määratlus ja päring", definitsioon))
    sisu = (teekond + pais(f'Näitaja · {c["ala"]["nimi"] if c["ala"] else ""}', h1, e(n["mida_see_tahendab"]))
            + f'<dl class="facts">{"".join(faktid)}</dl>' + kriitiline + oige
            + sektsioon("Võrdlus riikidega", riigid, "Riigid", "riigid")
            + uuemad_plokk(x, c) + ajas_plokk(x, c, K) + usaldus + uuringute_kast(D, c)
            + sektsioon("Andmed ja määratlus", lisad, "Detailid", "detailid"))
    return leht(fail_naitajale(x), f'{n["nimi"]} · Tehisaru seire', sisu, tana)


# ---------- ELi kaart ----------

KAARDI_KLASSE = 5


def kaardi_klassid(vaartused):
    """Võrdsed vahemikud väikseimast suurimani, ümardatud ilusateks piirideks."""
    lo, hi = min(vaartused), max(vaartused)
    samm = (hi - lo) / KAARDI_KLASSE or 1
    kohti = 0 if samm >= 2 else 1 if samm >= 0.2 else 2
    piirid = [round(lo + i * samm, kohti) for i in range(KAARDI_KLASSE + 1)]
    piirid[0], piirid[-1] = min(piirid[0], lo), max(piirid[-1], hi)
    return piirid, kohti


def klass(v, piirid):
    for i in range(KAARDI_KLASSE):
        if v <= piirid[i + 1]:
            return i
    return KAARDI_KLASSE - 1


def euroopa_kaart(x, read, kuju):
    """Üks näitaja ELi kaardil. read: [(riik, väärtus, märgend)] ühe aasta kohta."""
    n = x["n"]
    vv = {g: (v, m) for g, v, m, _ in read}
    piirid, kohti = kaardi_klassid([v for v, _ in vv.values()])
    # Kujud on lehel üks kord (<defs>), iga kaart viitab neile <use> kaudu. Nii jääb leht väikeseks.
    osad = [f'<use href="#t-{g}" class="bg"/>' for g in sorted(kuju["taust"])]
    ee_tee = ""
    for g in sorted(kuju["el"]):
        if g in vv:
            v, m = vv[g]
            silt = f'{riik(g)}: {arv(v)}%' + (f" ({m})" if m else "")
            tee = f'<use href="#k-{g}" class="c{klass(v, piirid)}{" ee" if g == FOOKUS else ""}"><title>{e(silt)}</title></use>'
        else:
            tee = f'<use href="#k-{g}" class="na"><title>{e(riik(g))}: andmeid pole</title></use>'
        if g == FOOKUS:
            ee_tee = tee  # Eesti joonistatakse viimasena, et piirjoon jääks peale
        else:
            osad.append(tee)
    osad.append(ee_tee)
    jrk = sorted(vv.items(), key=lambda t: t[1][0] if vaiksem_parem(x) else -t[1][0])
    tipp = max(v for v, _ in vv.values())
    koht = [g for g, _ in jrk].index(FOOKUS) + 1 if FOOKUS in vv else None
    aasta = read[0][3] if read else ""
    pealk = (f"Eesti on ELi {len(vv)} riigi seas {koht}. kohal" + (" (väiksem on parem)" if vaiksem_parem(x) else "")
             + f": {arv(vv[FOOKUS][0])}%") if koht else n["nimi"]
    legend = "".join(
        f'<li><i class="c{i}"></i>{arv(piirid[i], kohti)}–{arv(piirid[i + 1], kohti)}%</li>' for i in range(KAARDI_KLASSE))
    tulbad_html = "".join(
        f'<li class="{"is-focus" if g == FOOKUS else ""}"><span class="lab">{e(riik(g))}</span>'
        f'<span class="track"><span class="bar" style="width:{v / tipp * 100:.1f}%"></span></span>'
        f'<span class="val">{arv(v)}%{f" ({e(m)})" if m else ""}</span></li>' for g, (v, m) in jrk)
    mm = sorted({c for _, m in vv.values() for c in m})
    return (
        f'<figure class="card map-fig" id="{e(n["id"])}" data-k="{e(n["id"])}"><div class="chart">'
        f'<h3 class="chart-title">{pealk}</h3>'
        f'<p class="chart-sub">{e(n["nimi"])} · {e(kogum(n))}, {aasta} · Eurostat</p>'
        f'<svg class="eumap" viewBox="{kuju["viewBox"]}" role="img" aria-label="{e(n["nimi"])} ELi riikides {aasta}. '
        f'Kõik väärtused on kaardi all loendis.">{"".join(osad)}</svg>'
        f'<ul class="map-legend" aria-label="Värvide tähendus">{legend}<li><i class="na"></i>andmeid pole</li></ul>'
        f'<p class="source">Mida tumedam, seda suurem number. Eesti on tumeda piirjoonega. '
        + ("Selles näitajas on väiksem number parem. " if vaiksem_parem(x) else "")
        + (" ".join(f"({m}) {LIPUD.get(m, 'Eurostati märgend')}." for m in mm) + " " if mm else "")
        + f'<a href="{fail_naitajale(x)}">Näitaja leht ja usaldus</a></p>'
        + avatav(f"Kõik {len(vv)} riiki järjekorras", f'<ul class="bars" role="list">{tulbad_html}</ul>')
        + "</div></figure>")


def euroopa_leht(D, tana):
    kuju_p = SIIN / "euroopa.json"
    kuju = loe_json(kuju_p) if kuju_p.exists() else None
    rida = {}
    for r in D["el27"]:
        rida.setdefault(r["naitaja"], []).append((r["geo"], float(r["vaartus"]), r["margend"], r["time"]))
    NN = [x for x in D["naitajad"] if x["n"]["id"] in rida]
    if not kuju or not NN:
        sisu = (pais("ELi kaart", "Kaardi andmeid pole veel laaditud")
                + '<div class="note"><p>Käivita <code>python run.py</code>, siis tekib fail <code>andmed/el27.csv</code>.</p></div>')
        return leht("kaart.html", "ELi kaart · Tehisaru seire", sisu, tana)
    nupud = "".join(
        f'<button type="button" data-k="{e(x["n"]["id"])}" aria-pressed="{"true" if i == 0 else "false"}">{e(x["n"]["nimi"])}</button>'
        for i, x in enumerate(NN))
    kaardid = "".join(euroopa_kaart(x, rida[x["n"]["id"]], kuju) for x in NN)
    kujud = ('<svg class="map-defs" width="0" height="0" aria-hidden="true" focusable="false"><defs>'
             + "".join(f'<path id="k-{g}" d="{d}"/>' for g, d in sorted(kuju["el"].items()))
             + "".join(f'<path id="t-{g}" d="{d}"/>' for g, d in sorted(kuju["taust"].items()))
             + "</defs></svg>")
    skript = (
        "<script>(function(){var bb=document.querySelectorAll('.map-pick button'),ff=document.querySelectorAll('.map-fig');"
        "function vali(k){var ok=false;ff.forEach(function(f){var s=f.dataset.k===k;f.hidden=!s;ok=ok||s;});"
        "if(!ok){return vali(ff[0].dataset.k);}bb.forEach(function(b){b.setAttribute('aria-pressed',String(b.dataset.k===k));});}"
        "bb.forEach(function(b){b.addEventListener('click',function(){vali(b.dataset.k);"
        "try{history.replaceState(null,'','#'+b.dataset.k);}catch(e){}});});"
        "vali((location.hash||'').slice(1)||ff[0].dataset.k);})();</script>")
    sisu = (pais("ELi kaart", "Kus Eesti ELi riikide seas paikneb",
                 "Kaardil on kõik 27 ELi riiki Eurostati viimase aasta numbriga. Vali näitaja.")
            + f'<div class="map-pick" role="group" aria-label="Näitaja">{nupud}</div>'
            + kujud + kaardid
            + f'<p class="small">Riigipiirid: {e(kuju["allikas"])}. Ülemeremaad pole kaardil. '
              "Kaardi värvid jagavad riigid viide võrdsesse vahemikku väikseimast suurimani.</p>"
            + skript)
    return leht("kaart.html", "ELi kaart · Tehisaru seire", sisu, tana)


# ---------- kalender, mõisted, lugejad ----------

def kalender(D, tana):
    """Millal tuleb iga näitaja uus number: viimane uuendus ja järgmine oodatav (arvutatud uuendussagedusest)."""
    t0 = dt.date.fromisoformat(tana)
    read = []
    for x in D["naitajad"]:
        v = x["meta"].get("varskus", {})
        if not v.get("jargmine_oodatav"):
            continue
        read.append((x, dt.date.fromisoformat(x["meta"]["allikas_uuendas"]), dt.date.fromisoformat(v["jargmine_oodatav"])))
    if not read:
        return ""
    read.sort(key=lambda r: r[2])
    a0 = dt.date(min(min(r[1] for r in read).year, t0.year), 1, 1)
    a1 = dt.date(max(r[2] for r in read).year + 1, 1, 1)
    W, ml, mr, rida, mt = 680, 300, 16, 30, 26
    H = mt + rida * len(read) + 8

    def X(d):
        return ml + (d - a0).days / (a1 - a0).days * (W - ml - mr)

    osad = []
    for aasta in range(a0.year, a1.year + 1):
        x_ = X(dt.date(aasta, 1, 1))
        osad.append(f'<line class="gridline" x1="{x_:.1f}" x2="{x_:.1f}" y1="{mt - 6}" y2="{H - 4}"/>')
        if aasta < a1.year:
            osad.append(f'<text x="{X(dt.date(aasta, 7, 1)):.1f}" y="14" text-anchor="middle">{aasta}</text>')
    osad.append(f'<line class="today" x1="{X(t0):.1f}" x2="{X(t0):.1f}" y1="{mt - 8}" y2="{H - 4}"/>')
    osad.append(f'<text class="today-lab" x="{X(t0) + 4:.1f}" y="{mt - 10}">täna</text>')
    for i, (x, eel, jargm) in enumerate(read):
        y = mt + i * rida + rida / 2
        nimi = x["n"]["nimi"] if len(x["n"]["nimi"]) <= 36 else x["n"]["nimi"][:35] + "…"
        osad.append(f'<text x="{ml - 10}" y="{y + 4:.1f}" text-anchor="end">{e(nimi)}</text>')
        osad.append(f'<line class="ln" x1="{X(eel):.1f}" x2="{X(jargm):.1f}" y1="{y:.1f}" y2="{y:.1f}"/>')
        osad.append(f'<circle class="dot hollow" cx="{X(eel):.1f}" cy="{y:.1f}" r="4"><title>Viimati uuendatud {kuupaev(eel.isoformat())}</title></circle>')
        osad.append(f'<circle class="dot focus" cx="{X(jargm):.1f}" cy="{y:.1f}" r="5"><title>Järgmine oodatav {kuupaev(jargm.isoformat())}</title></circle>')
    tulevased = [r for r in read if r[2] >= t0]
    if tulevased:
        x, _, j = tulevased[0]
        pealk = f"Järgmine uus number tuleb eeldatavasti {KUUD[j.month - 1]} {j.year}: {x['n']['nimi'].lower()}"
    else:
        pealk = "Kõigi näitajate oodatav uuendus on möödas"
    tabel = "".join(
        f'<tr><th scope="row"><a href="{fail_naitajale(x)}">{e(x["n"]["nimi"])}</a></th><td>{e(x["n"]["andmestik"])}</td>'
        f'<td class="r">{kuupaev(eel.isoformat())}</td><td class="r">{kuupaev(j.isoformat())}</td>'
        f'<td class="r">{x["n"]["uuendussagedus_kuudes"]} kuud</td></tr>' for x, eel, j in read)
    return (
        '<div class="card"><div class="chart">'
        f'<h3 class="chart-title">{e(pealk)}</h3>'
        '<p class="chart-sub">Õõnes ring: Eurostat uuendas viimati. Täidetud ring: järgmine oodatav uuendus.</p>'
        f'<div class="scroll"><svg class="cal" viewBox="0 0 {W} {H}" role="img" aria-label="Näitajate uuendamise kalender. '
        f'Kuupäevad on all tabelis.">{"".join(osad)}</svg></div>'
        '<p class="source">Oodatav kuupäev on arvutatud: viimane uuendus pluss näitaja tavaline uuendussagedus. '
        "Eurostat võib avaldada varem või hiljem. Statistikaamet avaldab Eesti numbri sageli mõni kuu enne Eurostati.</p>"
        + avatav("Kuupäevad tabelina", '<div class="table-wrap"><table><thead><tr><th scope="col">Näitaja</th>'
                 '<th scope="col">Andmestik</th><th class="r" scope="col">Viimati uuendatud</th>'
                 '<th class="r" scope="col">Järgmine oodatav</th><th class="r" scope="col">Sagedus</th></tr></thead>'
                 f'<tbody>{tabel}</tbody></table></div>')
        + "</div></div>")


KUUD = ["jaanuaris", "veebruaris", "märtsis", "aprillis", "mais", "juunis", "juulis", "augustis", "septembris",
        "oktoobris", "novembris", "detsembris"]


def vaite_kirje(v, D):
    raskus, klass, _ = HINNANGUD.get(v["hinnang"], (1, "", ""))
    kes = linkita(v["kes"], v.get("url"))
    kus = f', {e(v["kus"])}' if v.get("kus") else ""
    aeg = f', {kuupaev(v["kuupaev"])}' if v.get("kuupaev") else ""
    if v["naitaja"]:
        alus = f'<p class="small"><b>Ametlik number:</b> {naitaja_link(D, v["naitaja"])}</p>'
    else:
        alus = (f'<p class="claim-src"><b>Allikas ütleb:</b> {e(v["algallikas_utleb"])}</p>'
                f'<p class="small">{linkita(v["algallikas"], v.get("algallika_url"))}</p>')
    if v["oige_lause"]:
        teha = f'<p class="todo"><b>Täpsem oleks:</b> {e(v["oige_lause"])}</p>'
    elif v["mida_teha"]:
        teha = f'<p class="todo"><b>Mida teha:</b> {e(v["mida_teha"])}</p>'
    else:
        teha = ""
    uu = [D["leiud"][u] for u in v["uuringud"] if u in D["leiud"]]
    lisa = ""
    if uu:
        lisa = ('<p class="small">Sama teema uuringud: '
                + ", ".join(f'{e(u.get("autorid", u["id"]).split(",")[0])} {e(str(u.get("aasta", "")))}' for u in uu)
                + f'. <a href="{TOOELU_LEHT}">Vaata lehel „Tehisaru ja töö“</a></p>')
    return (f'<li class="claim" data-hinnang="{e(v["hinnang"])}"><div class="row"><blockquote>{e(v["vaide"])}</blockquote>'
            f'<span class="tag {klass}">{e(v["hinnang"])}</span></div>'
            f'<p class="small">Ütles: {kes}{kus}{aeg}</p>{alus}{teha}'
            + avatav("Miks see hinnang", f'<p>{e(v["selgitus"])}</p>{lisa}') + "</li>")


def vaidete_riba(V):
    """Üks tulp kuni kolme osaga: mitu lauset ütleb muud kui allikas, vajab täpsustust või vastab allikale."""
    loend = {k: 0 for k in RASKUS}
    for v in V:
        loend[HINNANGUD.get(v["hinnang"], (1,))[0]] += 1
    osad = "".join(
        f'<span class="vb-seg vb-{RASKUS[k][1]}" style="flex-grow:{n}"><b>{n}</b> {e(RASKUS[k][0].lower())}</span>'
        for k, n in loend.items() if n)
    if not V:
        return "", loend
    return f'<div class="vbar" role="img" aria-label="{e(vaidete_lause(V, loend))}">{osad}</div>', loend


def vaidete_lause(V, loend):
    if not V:
        return "Kontrollitud lauseid veel pole."
    osad = [f"{n} {RASKUS[k][0].lower()}" for k, n in loend.items() if n]
    jada = osad[0] if len(osad) == 1 else ", ".join(osad[:-1]) + " ja " + osad[-1]
    return f"{len(V)} kontrollitud lausest {jada}."


def vaited_leht(D, tana):
    V = D["vaited"]
    riba, loend = vaidete_riba(V)
    kokku = (f'<div class="vsum">{riba}<p>{e(vaidete_lause(V, loend))}</p></div>')
    legend = "".join(
        f'<tr><th scope="row"><span class="tag {k}">{e(h)}</span></th><td>{e(t)}</td></tr>'
        for h, (_, k, t) in HINNANGUD.items())
    kuidas = ('<ol class="steps"><li>Leiame lause algallika: raporti, tabeli või uuringu, millele lause toetub.</li>'
              '<li>Võrdleme sõnastust: kas allikas ütles sama, kas see oli mõõtmine, ootus või hinnang.</li>'
              '<li>Kontrollime, kelle kohta number on: kõik ettevõtted või suurettevõtted, Eesti või maailm, inimesed või oskused.</li>'
              '<li>Kirjutame lause, mis ütleb sama numbriga täpselt seda, mida allikas ütles.</li></ol>'
              '<p class="small">Hinnang on lause kohta, mitte inimese kohta. Uudise pealkirja teeb sageli toimetus, '
              'mitte artikli autor. Kontrollime ainult avalikke lauseid ja ainult algallika järgi.</p>'
              f'<div class="table-wrap"><table><thead><tr><th scope="col">Hinnang</th><th scope="col">Mida see tähendab</th></tr>'
              f'</thead><tbody>{legend}</tbody></table></div>')
    sisu = (pais("Mida väidetakse", "Kas avalik lause vastab allikale?",
                 "Avalikud laused tehisaru, töö ja oskuste kohta, kontrollitud algallika vastu.")
            + kokku
            + sektsioon("Kontrollitud laused",
                        f'<ul class="items claims">{"".join(vaite_kirje(v, D) for v in V)}</ul>' if V
                        else '<p>Siia tulevad avalikud laused, kui need on algallika vastu kontrollitud.</p>',
                        "Laused", "laused")
            + sektsioon("Kuidas me kontrollime", kuidas, "Meetod", "meetod"))
    return leht(VAITED_LEHT, "Mida väidetakse · Tehisaru seire", sisu, tana, osa="vaited")


def vaike_algus(t):
    """Esitäht väikeseks lause keskel, aga lühend (VKEde, IKT) jääb nii, nagu on."""
    return t if t[1:2].isupper() else t[:1].lower() + t[1:]


def lae_otsused(D):
    """Seaduste tähtajad failist otsused.csv ja näitajate sihid registrist, ajalises järjekorras.
    Aastata siht (nt T&A 3%) läheb loendi lõppu."""
    tulem = [{**r, "naitaja": ""} for r in loe_csv(OTSUSED)]
    for x in D["naitajad"]:
        n = x["n"]
        for sh in n.get("sihid") or []:
            uhik = n.get("uhik", "")
            arvu = f'{arv_s(sh["vaartus"])}{uhik}' if uhik.startswith("%") else f'{arv_s(sh["vaartus"])} {uhik}'.strip()
            kelle = "Eesti" if sh["riik"] == FOOKUS else "EL kokku" if sh["riik"] == VIIDE else riik(sh["riik"])
            tulem.append({
                "id": f'siht-{n["id"]}-{sh["riik"]}', "kuupaev": str(sh["aasta"]) if sh.get("aasta") else "",
                "tapsus": "aasta" if sh.get("aasta") else "",
                "tase": "Eesti" if sh["riik"] == FOOKUS else "EL" if sh["riik"] == VIIDE else riik(sh["riik"]),
                "liik": "siht", "nimi": f'Siht: {vaike_algus(n["nimi"])} {arvu}',
                "mida_tahendab": sh.get("markus", ""), "kelle_jaoks": kelle, "allikas": sh["allikas"],
                "url": sh.get("url", ""), "kontrollitud": sh.get("kontrollitud", ""), "naitaja": n["id"]})
    tulem.sort(key=lambda o: (o["kuupaev"] == "", o["kuupaev"]))
    return tulem


def otsuse_aeg(o):
    """Kuupäev nii täpselt, kui allikas selle annab."""
    k = o["kuupaev"]
    if not k:
        return "aastata"
    if o["tapsus"] == "aasta" or len(k) == 4:
        return f"aastaks {k[:4]}" if o["liik"] == "siht" else k[:4]
    if o["tapsus"] == "kuu" or len(k) == 7:
        return f"{KUU_NIM[int(k[5:7]) - 1]} {k[:4]}"
    return kuupaev(k)


def otsus_kehtib(o, tana):
    """Kas tähtaeg on käes. Kuu täpsusega tähtaeg on käes alles selle kuu algusest.
    Siht ei hakka „kehtima“: selle tähtaeg on möödas, kui sihi aasta on läbi."""
    k = o["kuupaev"]
    if not k:
        return False
    if o["liik"] == "siht" or len(k) == 4:
        return int(k[:4]) < int(tana[:4])
    return (k + "-01")[:10] <= tana if len(k) == 7 else k[:10] <= tana


def murdaasta(k):
    """Kuupäev aastaarvuna joonise jaoks (2026-08-02 -> 2026,58)."""
    if len(k) == 4:
        return int(k) + 0.5  # siht on aasta kohta; punkt aasta keskel, et seda ei loetaks järgmise aasta omaks
    d = dt.date.fromisoformat((k + "-15")[:10] if len(k) == 7 else k[:10])
    return d.year + (d.timetuple().tm_yday - 1) / 366


def otsuste_joon(OO, tana):
    """Ajajoon: iga tähtaeg punktina, sihid rõngana, tänane päev joonena. Sildid on loendis, mitte joonisel."""
    oo = [o for o in OO if o["kuupaev"]]
    if not oo:
        return ""
    a0 = int(min(o["kuupaev"][:4] for o in oo))
    a1 = max(int(max(o["kuupaev"][:4] for o in oo)), int(tana[:4])) + 1
    W, X0, X1 = 1000, 24, 976
    x = lambda t: X0 + (t - a0) / (a1 - a0) * (X1 - X0)
    tikid = "".join(
        f'<line class="tick" x1="{x(a):.1f}" x2="{x(a):.1f}" y1="56" y2="64"/>'
        f'<text class="yr" x="{x(a):.1f}" y="84" text-anchor="middle">{a}</text>' for a in range(a0, a1 + 1))
    read, punktid = [], []  # iga rea viimase punkti x; punkt läheb madalaimasse ritta, kus see ei kattu
    for o in oo:
        xx = x(murdaasta(o["kuupaev"]))
        rida = next((i for i, v in enumerate(read) if xx - v >= 14), len(read))
        if rida == len(read):
            read.append(xx)
        read[rida] = xx
        y = 44 - min(rida, 2) * 14  # üle kolme rea ei lähe; iga punkti nimi on selle title-sildis
        klass = "dot hollow" if o["liik"] == "siht" else "dot law" if otsus_kehtib(o, tana) else "dot law-next"
        punktid.append(f'<circle class="{klass}" cx="{xx:.1f}" cy="{y}" r="6"><title>{e(otsuse_aeg(o))}: {e(o["nimi"])}</title></circle>')
    tx = x(murdaasta(tana))
    tana_j = (f'<line class="today" x1="{tx:.1f}" x2="{tx:.1f}" y1="4" y2="64"/>'
              f'<text class="today-lab" x="{tx + 6:.1f}" y="14">täna</text>')
    silt = otsuste_loendus([o for o in oo if otsus_kehtib(o, tana)], [o for o in oo if not otsus_kehtib(o, tana)])
    return (f'<svg class="otsjoon" viewBox="0 0 {W} 92" role="img" aria-label="Ajajoon {a0}–{a1}. {e(silt)}.">'
            f'<line class="axis" x1="{X0}" x2="{X1}" y1="60" y2="60"/>{tikid}{tana_j}{"".join(punktid)}</svg>'
            '<p class="small legend"><span class="key law"></span> seaduse tähtaeg, mis on käes '
            '<span class="key law-next"></span> tulev tähtaeg <span class="key hollow"></span> siht</p>')


def otsuse_kirje(o, D, moodas=False):
    link = linkita(o["allikas"], o.get("url"))
    num = (f' · <a href="{fail_naitajale(x)}">Näitaja leht</a>'
           if o["naitaja"] and (x := next((x for x in D["naitajad"] if x["n"]["id"] == o["naitaja"]), None)) else "")
    silt = "Siht" if o["liik"] == "siht" else "Seadus"
    if o["liik"] == "siht" and moodas:
        silt = "Siht, tähtaeg möödas"
    return (f'<li class="decision"><span class="when">{e(otsuse_aeg(o))}</span><div class="body">'
            f'<div class="row"><h4>{e(o["nimi"])}</h4><span class="tag">{e(o["tase"])} · {silt}</span></div>'
            f'<p>{e(o["mida_tahendab"])}</p>'
            f'<p class="small">Kelle jaoks: {e(o["kelle_jaoks"])} · Allikas: {link}{num}</p></div></li>')


def mitu(n, ainsus, mitmus):
    return f"{n} {ainsus if n == 1 else mitmus}"


def otsuste_loendus(kaes, ees):
    """Seaduste tähtajad ja sihid eraldi, sest siht ei hakka kehtima nagu seadus."""
    def osa(L):
        t = sum(1 for o in L if o["liik"] != "siht")
        h = len(L) - t
        return " ja ".join(x for x in [mitu(t, "seaduse tähtaeg", "seaduse tähtaega") if t else "",
                                       mitu(h, "siht", "sihti") if h else ""] if x)
    osad = [f"{nimi} {osa(L)}" for nimi, L in (("käes või möödas", kaes), ("ees", ees)) if L]
    lause = "; ".join(osad) or "otsuseid pole"
    return lause[:1].upper() + lause[1:]


def otsused_leht(D, tana):
    OO = lae_otsused(D)
    kaes = [o for o in OO if otsus_kehtib(o, tana)]
    ees = [o for o in OO if not otsus_kehtib(o, tana)]
    jarg = next((o for o in ees if o["liik"] != "siht" and o["kuupaev"]), None)
    lause = (otsuste_loendus(kaes, ees) + "."
             + (f' Järgmine: {otsuse_aeg(jarg)}, {vaike_algus(jarg["nimi"])}.' if jarg else ""))
    kokku = f'<div class="vsum">{otsuste_joon(OO, tana)}<p>{e(lause)}</p></div>' if OO else ""
    loend = lambda L, m=False: f'<ol class="list decisions">{"".join(otsuse_kirje(o, D, m) for o in L)}</ol>'
    sisu = (pais("Mida otsustatakse", "Mis on otsustatud ja millal see kehtima hakkab?",
                 "Seadused ja ametlikud sihid, mis puudutavad tehisaru, tööd ja oskusi. Igal real on ametlik allikas.")
            + kokku
            + (sektsioon("Tulekul", loend(ees), "Ees", "ees") if ees else "")
            + (sektsioon("Juba käes", loend(list(reversed(kaes)), True), "Käes", "kaes")
               if kaes else "")
            + sektsioon("Mida see leht ei näita",
                        '<ul class="plain"><li>Siin on ainult vastu võetud otsused ja nende ametlikud kuupäevad, mitte ettepanekud ega lubadused.</li>'
                        '<li>Siht ja praegune number on eri lehtedel: sihti mõõdetakse sageli teise allikaga kui ELi võrdlust, '
                        'nii et neid ei panda siin kõrvuti. Kui sihti mõõdetakse teise numbriga, on see sihi juures kirjas.</li>'
                        '<li>Seaduse tähtaeg näitab, millal kohustus hakkab kehtima, mitte seda, kas seda täidetakse.</li></ul>',
                        "Piirid", "piirid"))
    return leht(OTSUSED_LEHT, "Mida otsustatakse · Tehisaru seire", sisu, tana, osa="otsused")


def naitaja_link(D, nid):
    x = next((x for x in D["naitajad"] if x["n"]["id"] == nid), None)
    return f'<a href="{fail_naitajale(x)}">{e(x["n"]["nimi"])}</a>' if x else e(nid)


def sarnased_tabel(D):
    if not D["sarnased"]:
        return ""
    read = "".join(
        f'<tr><th scope="row">{e(r["moiste"])}</th><td>{e(r["mida_mootab"])}</td><td>{e(r["kelle_kohta"])}</td>'
        f'<td>{e(r["ara_aja_segi"])}</td><td>{naitaja_link(D, r["naitaja"])}</td></tr>' for r in D["sarnased"])
    return ('<p>Need mõisted kõlavad sarnaselt, aga mõõdavad eri asja. Kui kaks numbrit tunduvad vastuolus, '
            'on põhjus sageli siin.</p><div class="table-wrap"><table><thead><tr><th scope="col">Mõiste</th>'
            '<th scope="col">Mida mõõdab</th><th scope="col">Kelle kohta</th><th scope="col">Ära aja segi</th>'
            f'<th scope="col">Näitaja</th></tr></thead><tbody>{read}</tbody></table></div>')


def lugejate_tabel(D):
    if not D["lugejad"]:
        return ""
    read = "".join(
        f'<tr><th scope="row">{e(r["lugeja"])}</th><td>{e(r["kusimus"])}</td>'
        f'<td>{", ".join(naitaja_link(D, nid.strip()) for nid in r["naitajad"].split(";"))}</td>'
        f'<td>{e(r["ettevaatust"])}</td></tr>' for r in D["lugejad"])
    return ('<p>Sama number vastab eri lugejale eri küsimusele. Tabel näitab, kust alustada ja millele tähelepanu pöörata.</p>'
            '<div class="table-wrap"><table><thead><tr><th scope="col">Lugeja</th><th scope="col">Küsimus</th>'
            '<th scope="col">Vaata</th><th scope="col">Pea meeles</th></tr></thead>'
            f'<tbody>{read}</tbody></table></div>')


def teemade_leht(D, K, tana):
    kk = kataloog.kokkuvote(K)
    vrd = set(kataloog.vorreldavad_moisted(K))
    kat = K["kategooriad"]
    lehed = {x["k"]["moiste"]["id"]: x for x in D["naitajad"] if x["k"]["moiste"]}
    andmetega = {K["moodikud"][v["moodik"]]["moiste"] for v in K["vaatlused"]}
    h1 = (f'{kk["moisteid"]} küsimust {kk["teemasid"]} teemas. Andmed on praegu '
          f'<span class="hl">{kk["moisteid_andmetega"]}</span> küsimuse kohta')
    lead = ("Iga teema all on küsimused, millele seire tahab vastata, ja allikad, mis neile vastavad. "
            "Ava teema, et näha küsimusi, ja küsimuse allikad, et näha, keda iga allikas loendab ja kas seda saab võrrelda.")
    kaart_ = pildid.kattuvus(pildid.kataloogi_teemad(K), {o: kataloog.OLEKUD[o] for o in OLEKU_JARJEKORD})
    osad = [pais("Teemad ja allikad", h1, lead),
            sektsioon("Iga ruut on üks küsimus: värviline ruut tähendab, et andmed on olemas", kaart_, "Kaart", "kaart")
            + '<p class="small">Klõpsa ruudul, et avada küsimus ja selle allikad.</p>']
    for kood, teema in kat.items():
        if teema["ulem"]:
            continue
        alad = [(ak, ala) for ak, ala in kat.items() if ala["ulem"] == kood]
        moisted = [m for m in K["moisted"].values() if any(m["kategooria"] == ak for ak, _ in alad)]
        n_andm = sum(1 for m in moisted if m["id"] in andmetega)
        plokid = [f'<p>{e(teema["kirjeldus"])}</p>']
        tuhjad = []
        for akood, ala in alad:
            mm = [m for m in moisted if m["kategooria"] == akood]
            if not mm:
                tuhjad.append(ala["nimi"])
                continue
            kirjed = []
            for m in mm:
                mood = sorted((x for x in K["moodikud"].values() if x["moiste"] == m["id"]),
                              key=lambda x: (kataloog.JARJEKORD.index(x["vorreldavus"]), x["id"]))
                olek = min((x["olek"] for x in mood), key=OLEKU_JARJEKORD.index) if mood else "allikas_leidmata"
                read = "".join(
                    f'<tr><td>{linkita(x["nimi"], x["url"])}'
                    + (f'<br><span class="small"><code>{e(x["andmestik"])}</code></span>' if x["andmestik"] else "")
                    + f'</td><td class="small">{e(x["populatsioon"]) or "–"}</td><td class="small">{e(x["periood"]) or "–"}</td>'
                    f'<td>{klassi_tag(x["vorreldavus"])}</td>'
                    f'<td><span class="tag {OLEKU_SILT[x["olek"]]}">{e(kataloog.OLEKUD[x["olek"]])}</span></td></tr>'
                    for x in mood)
                tabel = ('<div class="table-wrap"><table><thead><tr><th scope="col">Allikas</th>'
                         '<th scope="col">Keda loendab</th><th scope="col">Periood</th><th scope="col">Võrreldavus</th>'
                         f'<th scope="col">Olek</th></tr></thead><tbody>{read}</tbody></table></div>')
                if m["markus"]:
                    tabel = f'<p class="small">{e(m["markus"])}</p>' + tabel
                if m["id"] in vrd and m["id"] not in lehed:
                    V = kataloog.vordle(K, m["id"])
                    tabel += ee_allikad_tabel(K, V)
                x = lehed.get(m["id"])
                pealk = f'<a href="{fail_naitajale(x)}">{e(m["nimi"])}</a>' if x else e(m["nimi"])
                vaata = f'<p><a href="{fail_naitajale(x)}">Vaata näitajat <span aria-hidden="true">→</span></a></p>' if x else ""
                kirjed.append(
                    f'<li id="{e(m["id"])}"><div class="row"><h4>{pealk}</h4>'
                    f'<span class="tag {OLEKU_SILT[olek]}">{e(kataloog.OLEKUD[olek])}</span></div>'
                    f'<p>{e(m["kusimus"])}</p>{vaata}'
                    + avatav(f"{len(mood)} allikat", tabel) + "</li>")
            plokid.append(f'<h3>{e(ala["nimi"])}</h3><ul class="items">{"".join(kirjed)}</ul>')
        if tuhjad:
            plokid.append(f'<p class="small">Küsimusi pole veel lisatud: {e(", ".join(tuhjad))}.</p>')
        kokku = f'{len(moisted)} küsimust · {n_andm} andmetega' if moisted else "küsimusi pole veel"
        osad.append(
            f'<details class="theme" id="teema-{kood}"{" open" if n_andm else ""}>'
            f'<summary><span class="theme-name">{e(teema["nimi"])}</span><span class="theme-count">{kokku}</span></summary>'
            f'<div class="more-body">{"".join(plokid)}</div></details>')
    # Ruudu link avab suletud teema, kus küsimus asub.
    osad.append("<script>document.addEventListener('click',function(ev){var a=ev.target.closest&&ev.target.closest('a.tile');"
                "if(!a)return;var t=document.getElementById(decodeURIComponent(a.hash.slice(1)));"
                "for(var d=t&&t.parentElement;d;d=d.parentElement){if(d.tagName==='DETAILS')d.open=true;}});</script>")
    return leht("teemad.html", "Teemad ja allikad · Tehisaru seire", "".join(osad), tana)


def kuidas_leht(D, K, tana):
    allikad = (
        '<div class="prose">'
        "<p><b>Võrdlusalus on Eurostat.</b> Eurostat kogub ELi riikidest sama küsitluse sama meetodiga, nii et ainult tema "
        "numbritega saab riike järjestada. Seire laeb need otse Eurostati andmeliidesest.</p>"
        "<p><b>Riikide statistikaametid annavad uue numbri varem.</b> Näiteks Statistikaamet avaldab Eesti numbri umbes kolm kuud "
        "enne Eurostati. Need on samast küsitlusest, aga vahel uue klassifikaatoriga, nii et neid näidatakse eraldi.</p>"
        "<p><b>ELi-väliste riikide numbrid on teistest küsitlustest.</b> Ühendkuningriik, USA ja Kanada küsivad teist küsimust "
        "või teise perioodi kohta. Neid näidatakse eraldi ja ei järjestata koos Eurostati numbritega.</p>"
        "<p><b>Kõik näitajad on küsitlused.</b> Ettevõtted ja inimesed vastavad ise, mida nad kasutavad või oskavad. "
        "Number näitab nende vastust, mitte mõõdetud kasutust, ja sellel on valimiviga. Väike vahe kahe riigi või aasta "
        "vahel ei pruugi olla päris vahe.</p>"
        "<p><b>Numbreid käsitsi ei kirjutata.</b> Iga number tuleb andmefailist. Käsitsi on kantud ainult sündmuste logi, "
        "väidete hinnangud ja teiste riikide uuemad numbrid, igaüks viitega allikale.</p></div>")
    varskus = (
        '<dl class="legend">'
        f'<dt>{staatuse_silt("ajakohane")}</dt><dd>Allikas on uuendanud viimase oodatava tsükli jooksul.</dd>'
        '<dt><span class="tag risk">aegumas</span></dt><dd>Oodatav uuendus on lähedal või hilineb veidi.</dd>'
        '<dt><span class="tag risk">aegunud</span></dt><dd>Oodatav uuendus on ammu möödas. Number ei pruugi kirjeldada praegust olukorda.</dd>'
        "</dl>")
    kooskola = (
        '<dl class="legend">'
        '<dt><span class="tag ok">klapivad</span></dt><dd>Kahe sama mõõdikuga allika vahe mahub ümardamise sisse.</dd>'
        f'<dt><span class="tag">väike vahe</span></dt><dd>Vahe on suurem kui ümardamine, aga alla {arv(VASTUOLU_PIIR)} protsendipunkti üle selle.</dd>'
        f'<dt><span class="tag risk">vahe</span></dt><dd>Vahe on vähemalt {arv(VASTUOLU_PIIR)} protsendipunkti üle ümardamise. Seda tuleb uurida.</dd>'
        "</dl>")
    margid = (f"<h3>Värskus</h3>{varskus}<h3>Kas allikad klapivad</h3>{kooskola}"
              f"<h3>Kas allikaid saab võrrelda</h3>{vorreldavuse_legend()}")

    seire = [r for r in D["riskid"] if r["liik"] == "risk"]
    s_html = "".join(kirje("Seire risk", "risk", r["pealkiri"], r["selgitus"], r["mida_teha"]) for r in seire)

    if D["muutused"]:
        mr = "".join(
            f'<tr><td>{kuupaev(m["kuupaev"])}</td><td>{e(m["naitaja"])}</td><td>{riik(m["geo"])}</td><td>{e(m["aasta"])}</td>'
            f'<td class="r">{arv(float(m["vana"])) if m["vana"] else "–"}</td><td class="r">{arv(float(m["uus"]))}</td></tr>'
            for m in D["muutused"])
        andm = ('<div class="table-wrap"><table><thead><tr><th scope="col">Kuupäev</th><th scope="col">Näitaja</th>'
                '<th scope="col">Riik</th><th scope="col">Aasta</th><th class="r" scope="col">Vana</th><th class="r" scope="col">Uus</th>'
                f'</tr></thead><tbody>{mr}</tbody></table></div>')
    else:
        andm = ('<p class="small">Andmemuutusi pole veel registreeritud. Seire võrdleb iga käivituse numbreid eelmisega; '
                "muutused ilmuvad siia näiteks siis, kui allikas parandab varasema aasta väärtust.</p>")
    def sund_li(s):
        return (
            f'<li><span class="when">{kuupaev(s["kuupaev"])}</span><div class="body">'
            f'<span><span class="tag">{e(LIIGID.get(s["liik"], s["liik"]))}</span></span><p>{e(s["tekst"])}</p>'
            + (f'<a class="small" href="{e(s["url"])}">Allikas</a>' if s.get("url") else "")
            + "</div></li>")
    LOGI_N = 6
    vanemad = D["sundmused"][LOGI_N:]
    logi = (f'<ul class="list">{"".join(sund_li(s) for s in D["sundmused"][:LOGI_N])}</ul>'
            + (avatav(f"Vanemad sündmused ({len(vanemad)})", f'<ul class="list">{"".join(sund_li(s) for s in vanemad)}</ul>') if vanemad else "")
            + avatav("Andmemuutused (automaatne logi)", andm))

    kk = kataloog.kooskola(K, JUUR)
    kr = "".join(
        f'<tr><td><code>{e(r["fail"])}</code></td><td class="small">{e(r["kirje"])}</td>'
        f'<td class="r">{arv(r["teine"], kataloog.tapsus(str(r["teine"])))}</td>'
        f'<td class="r">{arv(r["kataloog"], 2) if r["kataloog"] is not None else "–"}</td>'
        f'<td><span class="tag {"ok" if r["staatus"] == "klapib" else "risk"}">{e(r["staatus"])}</span></td></tr>'
        for r in kk)
    erinevad = sum(1 for r in kk if r["staatus"] != "klapib")
    failid = ('<p class="small">Sama number võib olla mitmes failis. Seire kontrollib igal koostamisel, et need pole lahku läinud.</p>'
              '<div class="table-wrap"><table><thead><tr><th scope="col">Fail</th><th scope="col">Kirje</th>'
              '<th class="r" scope="col">Failis</th><th class="r" scope="col">Kataloogis</th><th scope="col">Olek</th></tr></thead>'
              f'<tbody>{kr}</tbody></table></div>')

    sisu = (pais("Kuidas see töötab", "Kust numbrid tulevad, mida märgid tähendavad ja mis on muutunud",
                 "Selle lehe abil saab kontrollida, kuidas seire numbreid kogub ja hindab. Numbrid ise on näitajate lehtedel.")
            + sektsioon("Kust numbrid tulevad", allikad, "Allikad", "allikad")
            + (sektsioon("Millal tuleb uus number", kal, "Kalender", "kalender") if (kal := kalender(D, tana)) else "")
            + (sektsioon("Sarnased mõisted, mis mõõdavad eri asja", sar, "Mõisted", "moisted") if (sar := sarnased_tabel(D)) else "")
            + (sektsioon("Kellele mis number vastab", lug, "Lugejad", "lugejad") if (lug := lugejate_tabel(D)) else "")
            + sektsioon("Mida märgid tähendavad", margid, "Märgid", "margid")
            + sektsioon("Seire enda nõrkused", f'<ul class="items">{s_html}</ul>', "Ausalt", "seire")
            + sektsioon("Muudatuste logi", logi, "Logi", "logi")
            + sektsioon(f"Failide kooskõla: {len(kk) - erinevad} numbrit {len(kk)}-st klapivad",
                        avatav("Näita kontrolli", failid), "Kontroll", "kooskola"))
    return leht("kuidas.html", "Kuidas see töötab · Tehisaru seire", sisu, tana)


def main():
    tana = dt.date.today().isoformat()
    D = lae()
    if not D["naitajad"]:
        sys.exit("Ühegi näitaja andmeid pole. Käivita enne python run.py")
    K = kataloog.lae(JUUR)
    for viga in kataloog.kontrolli(K):
        print(f"Hoiatus (kataloog): {viga}", file=sys.stderr)
    for x in D["naitajad"]:
        x["k"] = kontekst(x, D, K)
    if VALJA.exists():
        shutil.rmtree(VALJA)  # vanad lehed ei tohi jääda maha
    VALJA.mkdir()
    lehed = {"index.html": avaleht(D, K, tana), "kaart.html": euroopa_leht(D, tana), "teemad.html": teemade_leht(D, K, tana),
             "kuidas.html": kuidas_leht(D, K, tana)}
    for x in D["naitajad"]:
        lehed[fail_naitajale(x)] = naitaja_leht(x, D, K, tana)
    # Osade riba viitab neile igalt lehelt, nii et need ehitatakse ka siis, kui väiteid või otsuseid pole.
    lehed[VAITED_LEHT] = vaited_leht(D, tana)
    lehed[OTSUSED_LEHT] = otsused_leht(D, tana)
    lehed.update(analuus.analuusi_leht(sys.modules[__name__], D, K, tana))
    for nimi, sisu in lehed.items():
        (VALJA / nimi).write_text(sisu, encoding="utf-8")
    shutil.copyfile(SIIN / "stiil.css", VALJA / "stiil.css")
    if (SIIN / "fotod").is_dir():  # fotosid repos pole; avaldamisel lisatakse need kohapeal
        shutil.copytree(SIIN / "fotod", VALJA / "fotod")
    print(f"Valmis: {len(lehed)} lehte kaustas {VALJA}")


if __name__ == "__main__":
    main()
