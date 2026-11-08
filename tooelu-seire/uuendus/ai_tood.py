#!/usr/bin/env python3
"""AI- ja andmetööde kuulutused CV.ee-s (Kadri 8.11.2026: kes otsib AI ja andmetega seotud inimesi).

Sisend: TinyFish fetch_content tulemuse fail(id) CV.ee avaliku otsingu kohta
  https://www.cv.ee/api/v1/vacancy-search-service/search?limit=1000&offset=N&showHidden=true&sorting=LATEST
  (N = 0, 1000, 2000, ... kuni kõik kuulutused on käes; showHidden=true annab sama arvu mis veebiotsing).
Väljund: $UUDISED/ai_tookuulutused.json (vaikimisi /mnt/project-files/tooelu-uudised)

Kasutus: python3 ai_tood.py TULEMUSFAIL [TULEMUSFAIL ...]

Salvestatakse ainult kuulutuse pealkiri, tööandja (ettevõte), maakond, avaldamise kuupäev ja link.
Kuulutuse teksti ei salvestata; seda kasutatakse ainult selleks, et leida kuulutused, mis nõuavad
tehisaru oskust. Isikuandmeid ei koguta.
"""
import json
import re
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

import os

# Andmed on repost väljas (vt README): UUDISED, vaikimisi $UUENDUS_ANDMED/tooelu-uudised.
UUDISED = Path(os.environ.get("UUDISED", os.path.join(os.environ.get("UUENDUS_ANDMED", "/mnt/project-files"), "tooelu-uudised")))
VALJUND = UUDISED / "ai_tookuulutused.json"

MAAKOND = {67: "Harjumaa", 68: "Hiiumaa", 69: "Ida-Virumaa", 70: "Jõgevamaa", 71: "Järvamaa",
           72: "Läänemaa", 73: "Lääne-Virumaa", 74: "Põlvamaa", 75: "Pärnumaa", 76: "Raplamaa",
           77: "Saaremaa", 78: "Tartumaa", 79: "Valgamaa", 80: "Viljandimaa", 81: "Võrumaa"}

# Suurtähtedega lühendid (tõstutundlik), et eesti sõnad ei läheks segi.
AI_LYH = re.compile(r"(?<![A-Za-zÄÖÜÕäöüõ])(AI|ML|MLOps|LLMs?|GenAI|NLP|RAG)(?![A-Za-zÄÖÜÕäöüõ0-9])")
AI_SONA = re.compile(r"tehisintellekt|tehisaru|machine learning|masinõp|deep learning|süvaõp|computer vision|"
                     r"data scien|andmeteadla|prompt engineer|generative ai|generatiivse? tehis|ai engineer|"
                     r"chatgpt|copilot|large language model|keelemudel", re.I)
ANDME = re.compile(r"andme|\bdata\b|\bBI\b|business intelligence|power ?bi|analytics|\bDWH\b|statistik|"
                   r"database|andmebaas", re.I)
EI_ANDME = re.compile(r"data communication", re.I)
EI_AI = re.compile(r"\bML Capital")  # firmanimed, kus lühend pole tehisaru


def loe(failid):
    kuulutused = {}
    for f in failid:
        d = json.load(open(f, encoding="utf-8"))
        for r in d.get("results", []):
            t = re.sub(r"\\([_*\[\]()#+\-.!`>~|{}])", r"\1", r["text"])  # markdowni põgendused maha
            j = json.loads(t)
            for v in j.get("vacancies", []):
                kuulutused[v["id"]] = v
            kokku = j.get("total")
    return list(kuulutused.values()), kokku


def ruhm(v):
    pealkiri = EI_AI.sub(" ", v.get("positionTitle") or "")
    sisu = EI_AI.sub(" ", v.get("positionContent") or "")
    if AI_LYH.search(pealkiri) or AI_SONA.search(pealkiri):
        return "ai_amet"
    if ANDME.search(pealkiri) and not EI_ANDME.search(pealkiri):
        return "andmeamet"
    if AI_LYH.search(sisu) or AI_SONA.search(sisu):
        return "ai_oskus"
    return None


def katked(sisu):
    """Lõigud kuulutuse tekstist, kus tehisaru mainitakse (ainult liigituseks, ei salvestata)."""
    sisu = EI_AI.sub(" ", sisu)
    m = list(AI_LYH.finditer(sisu)) + list(AI_SONA.finditer(sisu))
    # Sõnapõhine aken (5 sõna enne, 2 pärast), et kirjavahemärk või reavahetus ei muudaks üldlause võtit.
    out = set()
    for x in m:
        enne = re.sub(r"\W+", " ", sisu[max(0, x.start() - 80):x.start()]).lower().split()[-5:]
        parast = re.sub(r"\W+", " ", sisu[x.end():x.end() + 40]).lower().split()[:2]
        out.add(" ".join(enne + [x.group(0).lower()] + parast))
    return out


def firma_uldnouded(koik):
    """Tööandja ühine lause (sama lõik vähemalt 3 kuulutuses): see on firma üldnõue, mitte ameti nõue."""
    loend = {}
    for v in koik:
        if ruhm(v) != "ai_oskus":
            continue
        for k in katked(v.get("positionContent") or ""):
            loend.setdefault((v.get("employerName"), k), set()).add(v["id"])
    return {key: ids for key, ids in loend.items() if len(ids) >= 3}


def main(failid):
    koik, kokku = loe(failid)
    vana = json.load(open(VALJUND, encoding="utf-8")) if VALJUND.exists() else {}
    nahtud = set(vana.get("nahtud_id", []))
    tana = datetime.now(timezone(timedelta(hours=2))).date()
    nadal = (tana - timedelta(days=7)).isoformat()

    uld = firma_uldnouded(koik)
    uld_id = {}
    for (firma, k), ids in uld.items():
        for i in ids:
            uld_id.setdefault(i, set()).add(k)
    read = []
    for v in koik:
        g = ruhm(v)
        if not g:
            continue
        if g == "ai_oskus" and uld_id.get(v["id"]) == katked(v.get("positionContent") or ""):
            g = "ai_firma_noue"
        avaldatud = (v.get("publishDate") or "")[:10]
        uus = (v["id"] not in nahtud) if nahtud else (avaldatud >= nadal)
        read.append({
            "id": v["id"], "ruhm": g, "pealkiri": (v.get("positionTitle") or "").strip(),
            "tooandja": (v.get("employerName") or "").strip(),
            "maakond": MAAKOND.get(v.get("countyId"), "välismaa" if v.get("countryId") not in (1, None) else "Eesti (täpsustamata)"),
            "kaugtoo": v.get("remoteWorkType"), "avaldatud": avaldatud,
            "url": f"https://www.cv.ee/et/vacancy/{v['id']}", "uus": uus,
        })
    read.sort(key=lambda r: (r["ruhm"], r["avaldatud"]), reverse=True)

    def koond(g):
        rr = [r for r in read if r["ruhm"] == g]
        return {
            "arv": len(rr), "uusi": sum(r["uus"] for r in rr),
            "tooandjad": [{"nimi": n, "arv": a} for n, a in Counter(r["tooandja"] for r in rr).most_common(15)],
            "maakonnad": [{"nimi": n, "arv": a} for n, a in Counter(r["maakond"] for r in rr).most_common()],
        }

    ajalugu = [a for a in vana.get("ajalugu", []) if a["kuupaev"] != tana.isoformat()]
    ajalugu.append({"kuupaev": tana.isoformat(), "kuulutusi_kokku": len(koik),
                    "ai_amet": sum(r["ruhm"] == "ai_amet" for r in read),
                    "andmeamet": sum(r["ruhm"] == "andmeamet" for r in read),
                    "ai_oskus": sum(r["ruhm"] == "ai_oskus" for r in read),
                    "ai_firma_noue": sum(r["ruhm"] == "ai_firma_noue" for r in read)})
    out = {
        "kirjeldus": "Tehisaru- ja andmetööde kuulutused CV.ee-s. Kolm rühma: ai_amet = pealkirjas on tehisaru "
                     "(AI, ML, LLM, tehisintellekt, masinõpe, andmeteadlane jne); andmeamet = pealkirjas on andmed, "
                     "data, BI, analytics, statistik või andmebaas; ai_oskus = muu amet, mille kuulutuse tekst mainib "
                     "tehisaru või tehisaru tööriistu; ai_firma_noue = muu amet, kus tehisaru on ainult tööandja ühises "
                     "lauses (sama lõik vähemalt kolmes selle firma kuulutuses, nt firma üldnõue). Rühmad ei kattu. Märksõnapõhine liigitus, mitte käsitsi kontrollitud.",
        "allikas": "CV.ee avalik otsing (https://www.cv.ee/et/search), kõik kuulutused",
        "uuendatud": datetime.now(timezone(timedelta(hours=2))).isoformat(timespec="minutes"),
        "kuulutusi_kokku": len(koik), "portaali_kokku": kokku,
        "uus_tahendab": "kuulutus, mida eelmisel kontrollil polnud" if nahtud else "avaldatud viimase 7 päeva jooksul (esimene kontroll)",
        "ruhmad": {g: koond(g) for g in ("ai_amet", "andmeamet", "ai_oskus", "ai_firma_noue")},
        "kuulutused": read,
        "ajalugu": ajalugu,
        "nahtud_id": sorted(nahtud | {r["id"] for r in read}),
        "piirangud": "Ainult üks portaal (CV.ee); CV Keskuse otsing ei andnud automaatsel lugemisel tulemusi ja "
                     "Töötukassa robots.txt keelab otsingulehed. Sama ametikoht võib olla mitmes portaalis. "
                     "Pealkiri 'analüütik' ilma andmesõnata ei lähe andmeametite alla (äri-, finants- ja turbeanalüütikud).",
    }
    VALJUND.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(len(koik), kokku, {g: out["ruhmad"][g]["arv"] for g in out["ruhmad"]})


if __name__ == "__main__":
    main(sys.argv[1:])
