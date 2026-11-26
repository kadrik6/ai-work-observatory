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


TOENDI_SILT = {"vahter2026": "tugev andmestik, nõrk tulemus"}


# Ettevõtted, mis ei kuulu saidile (koondamiste tabel, uudised, koondajad), koos põhjusega
VALJA_ETTEVOTTED = {
    "ekkm": "Kadri 8.11.2026 21:41: kunstimuuseumi koondamine sisepingete tõttu pole tehisaru ja töö teemaga piisavalt seotud",
}


def jata_valja(A):
    """Eemaldab VALJA_ETTEVOTTED kõigist ettevõttega seotud loenditest; repo ja projekti andmefailid jäävad samaks."""
    valja = lambda nimi: (nimi or "").strip().lower() in VALJA_ETTEVOTTED  # noqa: E731
    K = A.get("koondamised") or {}
    if K.get("juhtumid"):
        K["juhtumid"] = [j for j in K["juhtumid"] if not valja(j.get("ettevote"))]
    if A.get("uudised"):
        A["uudised"] = [r for r in A["uudised"] if not valja(r.get("ettevote"))]
    F = (A.get("koondajad") or {}).get("firmad")
    if F:
        for nimi in [n for n in F if valja(n)]:
            del F[nimi]


def lisa_uudiste_koondamised(A):
    """Igapäevaste uudiste Eesti koondamised, mida käsitsi kontrollitud nimekirjas veel pole, lähevad Töö vaatesse
    kandidaadina (Kadri 6.11.2026: Eesti Energia puudus, sest nimekiri uuenes ainult käsitsi). Ettevõte loetakse samaks
    nime järgi 45 päeva piires. Arvu võetakse ainult arvuväljast, mitte tekstist."""
    K = A.get("koondamised") or {}
    if not K or not A.get("uudised"):
        return
    import datetime as _dt
    olemas = [(j["ettevote"].lower(), _dt.date.fromisoformat(j["kuupaev"])) for j in K["juhtumid"]]
    for r in A["uudised"]:
        if r.get("piirkond") != "EE" or r.get("teema") != "koondamine" or not r.get("ettevote"):
            continue
        if r.get("ai_roll") not in K["rollid"]:
            raise AndmeViga(f"uudised.jsonl: koondamisel {r['ettevote']} on tundmatu ai_roll {r.get('ai_roll')!r}")
        kp_ = _dt.date.fromisoformat(r["kuupaev"])
        if any(n == r["ettevote"].lower() and abs((kp_ - k).days) <= 45 for n, k in olemas):
            continue
        arv = r.get("arv_eestis") if isinstance(r.get("arv_eestis"), int) else None
        K["juhtumid"].append({
            "id": "uudis-" + "".join(c if c.isalnum() else "-" for c in r["ettevote"].lower()) + "-" + r["kuupaev"],
            "kuupaev": r["kuupaev"], "ettevote": r["ettevote"], "sektor": r.get("sektor") or "sektor teadmata",
            "arv_eestis": arv, "arv_tekst": r.get("arv_tekst") or "", "roll": r["ai_roll"], "pohjus": r.get("pohjus", "")[:300],
            "pealkiri": r["pealkiri"], "url": r["url"], "allikas": r["allikas"], "kandidaat": True})
        olemas.append((r["ettevote"].lower(), kp_))
    K["juhtumid"].sort(key=lambda j: j["kuupaev"], reverse=True)


ARVU_AKEN_PAEVI = 180


def uuenda_koondamiste_arvud(A):
    """Koondatute arv uueneb jätku-uudisest ise (Kadri 25.11.2026: Pipedrive'i ja Eesti Energia lõplikud arvud olid
    uudistes olemas, aga Töö vaade näitas esimest teadet). Sama ettevõtte hilisem Eesti koondamisuudis, mille arvuväljal
    on arv, mida selle juhtumi kohta varem pole nähtud, asendab juhtumi arvu. Varem nähtud arvu kordamine (näiteks
    arvamuslugu, mis nimetab esialgset arvu) midagi ei muuda. Esimene teade jääb alles väljale arv_varem, uue arvu
    allikas väljale arv_uuendus. Tehisaru roll ja juhtumi kuupäev ei muutu: need tulevad esimesest teatest."""
    K = A.get("koondamised") or {}
    if not K.get("juhtumid") or not A.get("uudised"):
        return
    import datetime as _dt
    paev = _dt.date.fromisoformat
    read = sorted((r for r in A["uudised"] if r.get("piirkond") == "EE" and r.get("teema") == "koondamine" and r.get("ettevote")
                   and isinstance(r.get("arv_eestis"), int) and not isinstance(r.get("arv_eestis"), bool)),
                  key=lambda r: (r["kuupaev"], r.get("lisatud") or r["kuupaev"]))
    for j in K["juhtumid"]:
        nimi, algus = j["ettevote"].lower(), paev(j["kuupaev"])
        jargmine = min((paev(x["kuupaev"]) for x in K["juhtumid"]
                        if x is not j and x["ettevote"].lower() == nimi and paev(x["kuupaev"]) > algus), default=None)
        nahtud, uus = {j.get("arv_eestis")}, None
        for r in read:
            kp_ = paev(r["kuupaev"])
            if r["ettevote"].lower() != nimi or kp_ < algus or (kp_ - algus).days > ARVU_AKEN_PAEVI or (jargmine and kp_ >= jargmine):
                continue
            if r["arv_eestis"] not in nahtud:
                nahtud.add(r["arv_eestis"])
                uus = r
        if uus is None:
            continue
        tekst = (uus.get("arv_tekst") or "").strip()
        if tekst.lower().startswith("jätkulugu:"):
            tekst = tekst[len("jätkulugu:"):].strip()
        j["arv_varem"] = {"arv_eestis": j.get("arv_eestis"), "arv_vahemalt": bool(j.get("arv_vahemalt")),
                          "arv_ulem": j.get("arv_ulem"), "arv_tekst": j.get("arv_tekst", "")}
        j["arv_uuendus"] = {"kuupaev": uus["kuupaev"], "url": uus["url"], "allikas": uus["allikas"], "pealkiri": uus["pealkiri"]}
        j["arv_eestis"], j["arv_tekst"] = uus["arv_eestis"], tekst
        j.pop("arv_vahemalt", None)
        j.pop("arv_ulem", None)


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
        # UNESCO UIS ja muud välisallikad; kataloog/lae_valis.py uuendab neid iga päev otse API-dest
        "valis_vaatlused": loe_csv(juur / "kataloog" / "vaatlused-valis.csv"),
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
        # Kadri otsus 6.11.2026 (sisuloogika teine hinnang): andmestik on tugev, tulemus nõrga olulisusega
        for uid, silt in TOENDI_SILT.items():
            if uid in A["uuringud"]:
                A["uuringud"][uid]["silt"] = silt
    koond_p = juur.parent / "tooelu-seire" / "koondamised_ee.json"
    A["koondamised"] = loe_json(koond_p) if koond_p.exists() else {}
    # Kadri loal projekti kaustast toodud avalik hetkeseis (sait/vota_kaasa.py); puuduv fail = vaade pole valmis
    uu = sisu / "uudised.jsonl"
    A["uudised"] = ([json.loads(r) for r in uu.read_text(encoding="utf-8").splitlines() if r.strip()]
                    if uu.exists() else None)
    for voti, nimi in [("uudiste_vaited", "uudiste-vaited.json"), ("uudiste_olek", "uudiste-olek.json"),
                       ("hanked_leht", "hanked-leht.json"), ("publikatsioonid", "publikatsioonid.json"),
                       ("koondajad", "koondajad.json"), ("toopakkumised", "toopakkumised.json"),
                       ("ai_kuulutused", "ai-tookuulutused.json"), ("ootel", "ootel.json"),
                       ("oecd_valvur", "oecd-valvur.json"), ("ettekanded", "ettekanded.json"),
                       ("ligipaas", "ligipaas.json"), ("ligipaas_kontekst", "ligipaas-kontekst.json"),
                       ("strateegiad", "strateegiad.json")]:
        A[voti] = loe_json(sisu / nimi) if (sisu / nimi).exists() else None
    lisa_kinnitatud_uuringud(A, sisu / "uuringud-lisa.json")
    jata_valja(A)
    lisa_uudiste_koondamised(A)
    uuenda_koondamiste_arvud(A)
    lisa_uudiste_vaited(A)
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


NAITEID = 3  # mitu ametit näidatakse astme juures näitena


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
    liigitamata, ametid, astmes = 0, [], {a: [] for a in ASTMED}
    for r in neli:
        n = int(r["tootajad_fte"])
        a = aste.get(r["kood"])
        if a is None:
            liigitamata += n
            continue
        osa[a] += n
        if not r["nimi_et"]:
            raise AndmeViga(f"Ametil {r['kood']} puudub eestikeelne nimi (Statistikaamet PA633)")
        astmes[a].append({"kood": r["kood"], "nimi": r["nimi_et"], "fte": n, "aste": a})
        if a in ("3", "4"):
            ametid.append(astmes[a][-1])
    ametid.sort(key=lambda x: -x["fte"])
    # Näited iga astme kohta (Kadri 26.11.2026: aste üksi ei ütle midagi): kolm suurima töötajate arvuga ametit.
    # Jääkrühm „mujal liigitamata“ ei ole näide, sest see ei nimeta ametit.
    naited = {}
    for a, l in astmes.items():
        sobib = sorted((x for x in l if "mujal liigitamata" not in x["nimi"]), key=lambda x: (-x["fte"], x["kood"]))
        if len(sobib) < NAITEID:
            raise AndmeViga(f"Astmes {a} on alla {NAITEID} nimega ameti; näiteid ei saa näidata")
        naited[a] = sobib[:NAITEID]
    pr_ = {a: n / kokku * 100 for a, n in osa.items()}
    # EL võrdlus samal ligikaudsel viisil
    from collections import Counter
    rühmad = {}
    for k, a in aste.items():
        rühmad.setdefault(k[:2], Counter())[a] += 1

    def jaota(read):
        """read: [(isco 'OCxx', tuhat)] → hõive astmete kaupa (tuhat). Avaldamata lahtrid jäävad välja."""
        g = {"kokku": 0.0, **{a: 0.0 for a in ASTMED}}
        for isco, v in read:
            c = rühmad.get(isco[2:4])
            if not c or v is None:
                continue  # kaitseväe ametid on ILO indeksis teise koodiga
            m = sum(c.values())
            g["kokku"] += v
            for a, k in c.items():
                g[a] += v * k / m
        g["avatud"] = sum(g[a] for a in ("1", "2", "3", "4"))
        g["korge"] = g["3"] + g["4"]
        g["muud"] = g["kokku"] - g["avatud"]
        return g

    el = {}
    for r in loe_csv(sisu / "eurostat-hoive-ametid-2025.csv"):
        if r["isco"] != "TOTAL":
            el.setdefault(r["geo"], []).append((r["isco"], float(r["tuhat"]) if r["tuhat"] else None))
    el_pr = {}
    for geo, read in el.items():
        g = jaota(read)
        el_pr[geo] = {"avatud": g["avatud"] / g["kokku"] * 100, "korge": g["korge"] / g["kokku"] * 100}
    # Aegrida 2021–2025 (tööjõu-uuringu uus metoodika algab 2021): kas avatud ametite hõive muutub teisiti
    aeg_read = loe_csv(sisu / "eurostat-hoive-ametid-2021-2025.csv")
    aastad = [k for k in aeg_read[0] if k.isdigit()]
    aeg = {}
    for geo, sugu in {(r["geo"], r["sugu"]) for r in aeg_read}:
        osa_ = [r for r in aeg_read if r["geo"] == geo and r["sugu"] == sugu and r["isco"] != "TOTAL"]
        aeg[(geo, sugu)] = {int(y): jaota([(r["isco"], float(r[y]) if r[y] else None) for r in osa_]) for y in aastad}
    # Muutus 2022 → uusim ainult lahtritest, mis on avaldatud mõlemal aastal (Kadri otsus 6.11.2026):
    # avaldamata lahtrid jäävad aastati erinevalt välja ja muudaksid muidu summat
    y0, y1 = 2022, max(int(y) for y in aastad)
    aeg_uhtlane = {}
    for geo, sugu in {(r["geo"], r["sugu"]) for r in aeg_read}:
        osa_ = [r for r in aeg_read if r["geo"] == geo and r["sugu"] == sugu and r["isco"] != "TOTAL"
                and r[str(y0)] and r[str(y1)]]
        aeg_uhtlane[(geo, sugu)] = {y: jaota([(r["isco"], float(r[str(y)])) for r in osa_]) for y in (y0, y1)}
    return {
        "kokku": kokku, "osa": pr_, "liigitamata": liigitamata / kokku * 100,
        "avatud": sum(pr_[a] for a in ("1", "2", "3", "4")), "korge": pr_["3"] + pr_["4"],
        "ametid": ametid, "naited": naited, "el": el_pr, "aeg": aeg, "aeg_uhtlane": aeg_uhtlane, "ilo_ameteid": len(aste),
        "ilo_avatud_ameteid": sum(1 for a in aste.values() if a in ("1", "2", "3", "4")),
    }


def lisa_kinnitatud_uuringud(A, p):
    """Igapäevase ülevaatuse uuringud, mille Kadri on kinnitanud (sait/ootel.py), lähevad uuringute kogusse.
    Repo tooelu-seire/leiud.json võidab, kui id on mõlemas. Tundmatu meetod = ehitus kukub."""
    if not p.exists() or not A.get("tooelu"):
        return
    meetodid = {m for mm in A["tooelu"].get("kindlus", {}).values() for m in mm}
    for u in loe_json(p):
        if u["id"] in A["uuringud"]:
            continue
        if u.get("meetod") not in meetodid:
            raise AndmeViga(f"sisu/uuringud-lisa.json uuring {u['id']}: meetodil {u.get('meetod')!r} pole tõendi tugevust")
        A["uuringud"][u["id"]] = dict(u, lisa=True)


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


UUDISE_HINNANG = {"vale": "Vale", "osaliselt": "Osaliselt tõsi", "tõsi": "Vastab allikale", "õige": "Vastab allikale"}


def lisa_uudiste_vaited(A):
    """Üks väidete loend, üks skaala (5.11 sisuloogika, Kadri kinnitas 6.11.2026): uudistes kontrollitud väited
    (sisu/uudiste-vaited.json) lähevad samasse loendisse kui kataloog/vaited.csv. Tundmatu hinnang = ehitus kukub."""
    for r in A.get("uudiste_vaited") or []:
        if r["hinnang"] not in UUDISE_HINNANG:
            raise AndmeViga(f"Uudise väitel {r['id']} on tundmatu hinnang {r['hinnang']!r}")
        t = [x for x in r.get("toendid", []) if x.get("url")]
        A["vaited"].append({
            "id": "uudis-" + r["id"], "vaide": r["vaide"], "kes": r["kes"], "kuupaev": r["kuupaev"],
            "url": r.get("kes_url", ""), "hinnang": UUDISE_HINNANG[r["hinnang"]],
            "selgitus": r["kokkuvote"] + " " + " ".join(f'{x["nimi"]}: {x["naitab"]}.' for x in r.get("toendid", [])),
            "oige_lause": "", "naitaja": "", "kontrollitud": r["kuupaev"],
            "algallikas": t[0]["nimi"] if t else "", "algallika_url": t[0]["url"] if t else "",
            "algallikas_utleb": t[0]["naitab"] if t else "", "valjaanne": r["kes"], "uudisest": True})


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


TOOALANE = "tooalane-tehisaru-kasutus"


def tooalane_kasutus(A):
    """Eesti tööalane tehisaru kasutus: (Eurostati alusaasta kirje, uusim võrreldav kirje).
    Statistikaameti uuem number on registris eraldi näitaja nime all (numbrid-2026.csv). Sama arvutus Inimeste ja Töö lehel."""
    alus = leia(A, TOOALANE, "EE", "uusim:alus")
    uued = [v for v in vali(A, TOOALANE + "-uus", "EE") + vali(A, "inimeste-tehisaru-kasutus-too", "EE")
            if v["klass"] in VORRELDAVAD and v["aasta"] > alus["aasta"]]
    return alus, (max(uued, key=lambda v: v["aasta"]) if uued else alus)


HOIVATUD = "sa-it71-too-hoivatud"


def tooalane_hoivatutest(A):
    """Tööalane tehisaru kasutus hõivatute seas (Statistikaamet IT71, rühm „Hõivatud“): (aasta varasem kirje või None, uusim kirje).
    Küsimus „kui paljud kasutavad tööl“ vajab jagajaks töötajaid; kõigi 16–74-aastaste arvus on ka töötud, õpilased ja
    pensionärid (Kadri 26.11.2026: jagaja peab sobima küsimusega). Mõõdik on kataloogis klassis „osaliselt“: Eurostati
    võrdlusalusega (kõik isikud) seda ei võrrelda, ELi võrdlus jääb kõigi isikute alusele."""
    aastad = sorted(int(r["aasta"]) for r in A["kataloogi_vaatlused"] if r["moodik"] == HOIVATUD and r["riik"] == "EE" and r["vaartus"])
    if not aastad:
        raise AndmeViga(f"Kataloogis pole mõõdiku {HOIVATUD} vaatlusi (kataloog/vaatlused-api.csv)")
    uus = kataloogist(A, HOIVATUD, "EE", aastad[-1])
    return (kataloogist(A, HOIVATUD, "EE", aastad[-1] - 1) if aastad[-1] - 1 in aastad else None), uus


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
