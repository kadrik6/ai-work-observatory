"""Andmekiht: loeb repo andmefailid üheks objektiks ja kontrollib neid. Kukub valjult, mitte vaikselt.

Igal vaatlusel on võrreldavusklass kataloogi viiest klassist (kataloog/README.md):
alus, sama, osaliselt, erinev, kontrollimata. Klass tuleb kataloogi failist moodikud.csv, mitte siit.
Eurostati read on oma näitaja võrdlusalus („alus“). Riikide 2026. aasta numbrid saavad mõõdiku failist
sisu/moodikud-2026.csv; kui reale mõõdikut pole, ehitus peatub.
"""
import csv
import json
from pathlib import Path

SIIN = Path(__file__).resolve().parent
JUUR = SIIN.parent  # tehisaru-seire/

KLASSID = ("alus", "sama", "osaliselt", "erinev", "kontrollimata")
# Kataloogi järgi on „sama“ sama küsitlus ja määratlus kui võrdlusalus: need võib panna ühele teljele.
VORRELDAVAD = ("alus", "sama")
EL = "EU27_2020"


class AndmeViga(Exception):
    """Andmed on puudu või vastuolus. Ehitus peatub."""


def loe_csv(p):
    p = Path(p)
    if not p.exists():
        raise AndmeViga(f"Fail puudub: {p}")
    with open(p, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def loe_json(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def _vaatlus(naitaja, geo, aasta, vaartus, margend, moodik, klass, allikas, url, avaldatud, kogum=""):
    if klass not in KLASSID:
        raise AndmeViga(f"{naitaja} {geo} {aasta}: tundmatu võrreldavusklass {klass!r}")
    if not url:
        raise AndmeViga(f"{naitaja} {geo} {aasta}: numbril puudub allika link")
    return {"naitaja": naitaja, "geo": geo, "aasta": int(aasta), "vaartus": float(vaartus), "margend": margend,
            "moodik": moodik, "klass": klass, "allikas": allikas, "url": url, "avaldatud": avaldatud, "kogum": kogum}


def lae(juur=JUUR, sisu=SIIN / "sisu"):
    juur, sisu = Path(juur), Path(sisu)
    reg = loe_json(juur / "naitajad.json")
    naitajad = {n["id"]: n for n in reg["naitajad"]}
    moodikud = {r["id"]: r for r in loe_csv(juur / "kataloog" / "moodikud.csv")}
    alus = {r["naitaja"]: r for r in moodikud.values() if r["naitaja"] and r["vorreldavus"] == "alus"}
    meta = {p.name[:-len(".meta.json")]: loe_json(p) for p in (juur / "andmed").glob("*.meta.json")}

    vaatlused, nahtud = [], set()

    def lisa(v):
        voti = (v["naitaja"], v["geo"], v["aasta"], v["moodik"])
        if voti in nahtud:
            return
        nahtud.add(voti)
        vaatlused.append(v)

    # 1. Eurostati aegread ja ELi 27 riigi read: oma näitaja võrdlusalus
    for nid in naitajad:
        if nid not in alus:
            raise AndmeViga(f"Näitajal {nid} pole kataloogis võrdlusalust (moodikud.csv, vorreldavus=alus)")
        m = meta.get(nid)
        if m is None:
            raise AndmeViga(f"Näitajal {nid} puudub andmed/{nid}.meta.json")
        url = alus[nid]["url"] or m["url"]
        for r in loe_csv(juur / "andmed" / f"{nid}.csv"):
            if r["vaartus"]:
                lisa(_vaatlus(nid, r["geo"], r["time"], r["vaartus"], r.get("margend", ""), alus[nid]["id"], "alus",
                              naitajad[nid]["allikas"] + ", " + naitajad[nid]["andmestik"], url, m["allikas_uuendas"]))
    for r in loe_csv(juur / "andmed" / "el27.csv"):
        nid = r["naitaja"]
        if r["vaartus"] and nid in alus:
            lisa(_vaatlus(nid, r["geo"], r["time"], r["vaartus"], r["margend"], alus[nid]["id"], "alus",
                          naitajad[nid]["allikas"] + ", " + naitajad[nid]["andmestik"], alus[nid]["url"] or meta[nid]["url"],
                          meta[nid]["allikas_uuendas"]))

    # 2. Riikide uusimad numbrid (sageli 2026): mõõdik ja klass kataloogist
    kaart = {(r["naitaja"], r["riik"], r["aasta"]): r["moodik"] for r in loe_csv(sisu / "moodikud-2026.csv")}
    uued = loe_csv(juur / "allikad" / "numbrid-2026.csv")
    for r in uued:
        if not r["vaartus"]:
            continue  # number puudub (näiteks USA BTOS); seda ei näidata
        voti = (r["naitaja"], r["riik"], r["aasta"])
        if voti not in kaart:
            raise AndmeViga(f"numbrid-2026.csv rida {voti}: mõõdik puudub failis sisu/moodikud-2026.csv")
        mid = kaart[voti]
        if mid not in moodikud:
            raise AndmeViga(f"Mõõdik {mid} puudub kataloogis (moodikud.csv)")
        v = _vaatlus(r["naitaja"], r["riik"], r["aasta"], r["vaartus"], "", mid, moodikud[mid]["vorreldavus"],
                     r["allikas"], r["url"], r["avaldatud"], r["kogum"])
        v["miks"] = r["vorreldavus_eurostatiga"]
        lisa(v)

    A = {
        "el_riigid": reg["kaardi_riigid"],
        "naitajad": naitajad, "meta": meta, "moodikud": moodikud, "vaatlused": vaatlused,
        "lahknevused": loe_csv(juur / "raportid" / "lahknevused.csv"),
        "riskid": loe_csv(juur / "raportid" / "riskid.csv"),
        "vaited": koonda_vaited(loe_csv(juur / "raportid" / "riskid.csv"), loe_csv(juur / "kataloog" / "vaited.csv")),
        "uuringud": {},
        "leiud": {r["id"]: r for r in loe_csv(sisu / "leiud.csv")},
        "leiud_arvud": loe_csv(sisu / "leiud-arvud.csv"),
        "sihid": {r["id"]: r for r in loe_csv(sisu / "sihid.csv")},
        "kataloogi_vaatlused": loe_csv(juur / "kataloog" / "vaatlused-api.csv"),
        "allikad": loe_csv(juur / "allikad" / "allikad.csv"),
        "otsused": sorted(loe_csv(juur / "kataloog" / "otsused.csv"), key=lambda r: r["kuupaev"]),
        "sundmused": loe_csv(juur / "raportid" / "sundmused.csv"),
        "muutused": loe_csv(juur / "andmed" / "muutused.csv"),
        "avalik": {r["id"]: r for r in loe_csv(sisu / "avalik-sektor.csv")},
        "oecd_soovitused": loe_csv(sisu / "oecd-soovitused.csv"),
        "tooelu": {},
        "kokkupuude": arvuta_kokkupuude(sisu),
    }
    leiud_p = juur.parent / "tooelu-seire" / "leiud.json"
    if leiud_p.exists():
        A["tooelu"] = loe_json(leiud_p)
        A["uuringud"] = {u["id"]: u for u in A["tooelu"].get("uuringud", [])}
    for r in A["avalik"].values():
        if not r["vaartus"] or not r["koht"]:
            raise AndmeViga(f"sisu/avalik-sektor.csv rida {r['id']}: väärtus või koht raportis puudub")
    for lid in {r["leid"] for r in A["leiud_arvud"]}:
        if lid not in A["leiud"]:
            raise AndmeViga(f"sisu/leiud-arvud.csv viitab leiule {lid}, mida failis sisu/leiud.csv pole")
    for s in A["sihid"].values():
        if s["naitaja"] not in naitajad or not s["url"]:
            raise AndmeViga(f"Siht {s['id']}: tundmatu näitaja või puuduv allikas")
    kuup = [v["avaldatud"] for v in vaatlused if v["avaldatud"]]
    A["uuendatud"] = max(kuup)
    return A


ASTMED = ("4", "3", "2", "1", "minimaalne", "ei")
PA633_URL = "https://andmed.stat.ee/et/stat/majandus__palk-ja-toojeukulu__tootasu/PA633"
ILO_SKOORID_URL = "https://pgmyrek.github.io/2025_GenAI_scores_ISCO08/"


def arvuta_kokkupuude(sisu):
    """ILO 2025 generatiivse tehisaru kokkupuute astmed Eesti töötajate ametite järgi.
    Eesti: Statistikaamet PA633, 2022 oktoober, töötajad täistööajale taandatult, 4-kohaline amet.
    EL võrdlus: Eurostat lfsa_egai2d 2025, 2-kohaline amet; rühm jagatakse astmete vahel selle
    4-kohaliste ametite arvu järgi (kaalumata). See on ligikaudne ja eraldi arvutus."""
    sisu = Path(sisu)
    ilo = loe_csv(sisu / "ilo-kokkupuude-2025.csv")
    aste = {}
    for r in ilo:
        if r["isco4"] in aste:
            raise AndmeViga(f"ILO amet {r['isco4']} on kaks korda")
        if r["aste"] not in ASTMED:
            raise AndmeViga(f"ILO amet {r['isco4']}: tundmatu aste {r['aste']!r}")
        aste[r["isco4"]] = r["aste"]
    ee = loe_csv(sisu / "ee-tootajad-ametid-2022.csv")
    koodid = [r["kood"] for r in ee]
    if len(set(koodid)) != len(koodid):
        raise AndmeViga("ee-tootajad-ametid-2022.csv: ametikood on kaks korda")
    ryhm = {r["kood"]: int(r["tootajad_fte"]) for r in ee if len(r["kood"]) == 1}
    neli = [r for r in ee if len(r["kood"]) == 4]
    for g, kokku in ryhm.items():
        alla = sum(int(r["tootajad_fte"]) for r in neli if r["kood"][0] == g)
        if not 0.9 * kokku <= alla <= kokku:
            raise AndmeViga(f"PA633 rühm {g}: ametite summa {alla} ei sobi rühma kogusummaga {kokku}")
    kokku = sum(int(r["tootajad_fte"]) for r in neli)
    osa = {a: 0 for a in ASTMED}
    liigitamata, ametid = 0, []
    for r in neli:
        n = int(r["tootajad_fte"])
        a = aste.get(r["kood"])
        if a is None:
            liigitamata += n
            continue
        osa[a] += n
        if a in ("3", "4"):
            if not r["nimi_et"]:
                raise AndmeViga(f"Kõige avatumal ametil {r['kood']} puudub eestikeelne nimi")
            ametid.append({"kood": r["kood"], "nimi": r["nimi_et"], "fte": n, "aste": a})
    ametid.sort(key=lambda x: -x["fte"])
    pr_ = {a: n / kokku * 100 for a, n in osa.items()}
    # EL võrdlus samal ligikaudsel viisil
    from collections import Counter
    rühmad = {}
    for k, a in aste.items():
        rühmad.setdefault(k[:2], Counter())[a] += 1
    el = {}
    for r in loe_csv(sisu / "eurostat-hoive-ametid-2025.csv"):
        if r["isco"] == "TOTAL" or not r["tuhat"]:
            continue
        c = rühmad.get(r["isco"][2:4])
        if not c:
            continue  # kaitseväe ametid: ILO indeksis teise koodiga
        g = el.setdefault(r["geo"], {"kokku": 0.0, **{a: 0.0 for a in ASTMED}})
        v, m = float(r["tuhat"]), sum(c.values())
        g["kokku"] += v
        for a, k in c.items():
            g[a] += v * k / m
    el_pr = {geo: {"avatud": sum(g[a] for a in ("1", "2", "3", "4")) / g["kokku"] * 100,
                   "korge": (g["3"] + g["4"]) / g["kokku"] * 100} for geo, g in el.items()}
    return {
        "kokku": kokku, "osa": pr_, "liigitamata": liigitamata / kokku * 100,
        "avatud": sum(pr_[a] for a in ("1", "2", "3", "4")), "korge": pr_["3"] + pr_["4"],
        "ametid": ametid, "el": el_pr, "ilo_ameteid": len(aste),
        "ilo_avatud_ameteid": sum(1 for a in aste.values() if a in ("1", "2", "3", "4")),
    }


def koonda_vaited(riskid, vaited):
    """Üks väidete loend kahest failist: riskid.csv (liik=vaide) ja kataloog/vaited.csv."""
    tulem = []
    for r in riskid:
        if r["liik"] == "vaide":
            tulem.append({"id": f'{r["naitaja"]}-{len(tulem) + 1}', "vaide": r["pealkiri"], "kes": r["allikas"],
                          "kuupaev": r["kuupaev"], "url": r["url"], "hinnang": r["hinnang"], "selgitus": r["selgitus"],
                          "oige_lause": r.get("reegel") or r.get("mida_teha", ""), "naitaja": r["naitaja"], "kontrollitud": "",
                          "algallikas": "", "algallikas_utleb": "", "valjaanne": r["allikas"]})
    for r in vaited:
        tulem.append({"id": r["id"], "vaide": r["vaide"], "kes": r["kes"], "kuupaev": r["kuupaev"], "url": r["url"],
                      "hinnang": r["hinnang"], "selgitus": r["selgitus"], "oige_lause": r["oige_lause"],
                      "naitaja": "", "kontrollitud": r["kontrollitud"], "algallikas": r["algallikas"],
                      "algallika_url": r["algallika_url"], "algallikas_utleb": r["algallikas_utleb"],
                      # Väide kuulub väljaandele, mitte nimelisele töötajale (Kadri 3.11.2026)
                      "valjaanne": f'{r["kus"]}, {r["kes"].split(", ", 1)[1]}' if r["kus"] == "ERR" and ", " in r["kes"] else r["kes"]})
    return tulem


# ---------------------------------------------------------------- päringud

def vali(A, naitaja, geo=None, aasta=None, klass=None):
    return [v for v in A["vaatlused"] if v["naitaja"] == naitaja and (geo is None or v["geo"] == geo)
            and (aasta is None or v["aasta"] == aasta) and (klass is None or v["klass"] == klass)]


def leia(A, naitaja, geo, aasta):
    """Üks vaatlus. aasta: täisarv, 'uusim' (mis tahes klass) või 'uusim:alus' (ainult võrdlusalus)."""
    klass = None
    if isinstance(aasta, str) and aasta.startswith("uusim"):
        klass = aasta.split(":")[1] if ":" in aasta else None
        kand = vali(A, naitaja, geo, klass=klass)
        if not kand:
            raise AndmeViga(f"Vaatlus puudub: {naitaja} {geo} {aasta}")
        parim = max(v["aasta"] for v in kand)
        kand = [v for v in kand if v["aasta"] == parim]
    else:
        kand = vali(A, naitaja, geo, int(aasta))
    if not kand:
        raise AndmeViga(f"Vaatlus puudub: {naitaja} {geo} {aasta}")
    alusel = [v for v in kand if v["klass"] == "alus"]
    return (alusel or kand)[0]


def el27_aasta(A, naitaja, aasta):
    """ELi 27 riigi võrdlusaluse väärtused ühel aastal: {geo: vaatlus}."""
    el = {v["geo"]: v for v in vali(A, naitaja, aasta=aasta, klass="alus") if v["geo"] in A["el_riigid"]}
    if len(el) != len(A["el_riigid"]):
        puudu = sorted(set(A["el_riigid"]) - set(el))
        raise AndmeViga(f"{naitaja} {aasta}: ELi riikidest puuduvad {puudu}")
    return el


def koht(A, naitaja, geo, aasta):
    el = el27_aasta(A, naitaja, aasta)
    jarjest = sorted(el, key=lambda g: -el[g]["vaartus"])
    return jarjest.index(geo) + 1


def kataloogist(A, moodik, riik, aasta):
    """Kataloogi API-vaatlus (näiteks Statistikaameti tabel, mis ei ole aegrea osa). Kukub, kui puudub."""
    for r in A["kataloogi_vaatlused"]:
        if r["moodik"] == moodik and r["riik"] == riik and int(r["aasta"]) == int(aasta) and r["vaartus"]:
            return {**r, "vaartus": float(r["vaartus"]), "aasta": int(r["aasta"])}
    raise AndmeViga(f"Kataloogis pole vaatlust {moodik} {riik} {aasta}")
