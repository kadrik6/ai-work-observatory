"""Igapäevase seire käivituse logist lehe „Tehisaru ja töö“ andmed dash/*.json.

Kasutus: python3 seire_logist.py LOGIFAIL KAIVITUSE_URL
LOGIFAIL = GitHubi get_job_logs vastus (JSON väljaga logs_content), töö "kogu" workflow'st seire.yml.
Kirjutab töökausta (TOOELU_TOO või see kaust) dash/kandidaadid.json, allikad.json, eurostat.json, kaivitus.json.
Lisatud 5.11.2026 (Kadri: leht peab ise uuenema).
"""
import json
import os
import re
import sys
from email.utils import parsedate_to_datetime

B = os.environ.get("TOOELU_TOO", os.path.join(os.environ.get("UUENDUS_ANDMED", "/mnt/project-files"), "tooelu-leht-andmed")).rstrip("/") + "/"
NIMI = {"arxiv": "arXiv", "openalex": "OpenAlex", "err": "ERR uudised"}
RUHM = {"arxiv": "uuringud", "openalex": "uuringud", "err": "teated"}


def kp(s):
    if not s:
        return ""
    if re.match(r"\d{4}-\d{2}-\d{2}", s):
        return s[:10]
    try:
        return parsedate_to_datetime(s).date().isoformat()
    except Exception:
        return ""


def main(logifail, url):
    c = json.loads(open(logifail).read())["logs_content"]
    kirjed, olek = [], None
    for rida in c.split("\n"):
        if " KIRJE " in rida:
            kirjed.append(json.loads(rida.split(" KIRJE ", 1)[1]))
        elif " OLEK " in rida:
            olek = json.loads(rida.split(" OLEK ", 1)[1])
    if olek is None or not kirjed:
        sys.exit("Logist ei leitud OLEK või KIRJE ridu, andmeid ei muudetud.")

    kand, euro = [], []
    for k in kirjed:
        a = k["allikas"]
        if a == "eurostat":
            euro.append({"kood": k["voti"], "pealkiri": k["pealkiri"], "uuendatud": kp(k.get("uuendatud")),
                         "viimane_periood": k.get("viimane_periood", ""),
                         "url": f"https://ec.europa.eu/eurostat/databrowser/view/{k['voti']}/default/table"})
            continue
        paev = kp(k.get("avaldatud"))
        kand.append({"id": f"{a}:{k['voti']}", "allikas": NIMI.get(a, a), "liik": k.get("allika_liik", ""),
                     "pealkiri": k["pealkiri"], "url": k["url"], "avaldatud": paev,
                     "suund": k.get("suund", "") or "", "reegel": k.get("reegel", "") or "",
                     "kuupaev": paev, "versioon": k.get("versioon")})
    kand.sort(key=lambda x: x["kuupaev"], reverse=True)

    allikad = []
    for a, v in olek["allikad"].items():
        baas = a.split(":")[0]
        allikad.append({"allikas": a, "nimi": NIMI.get(a, "Eurostat " + a.split(":", 1)[1] if baas == "eurostat" else a),
                        "rühm": RUHM.get(baas, "statistika"), "olek": v.get("olek", ""), "kirjeid": v.get("kirjeid"),
                        "voos": v.get("voos"), "markus": v.get("markus", "")})
    kaivitus = [{"aeg": olek["aeg"], "alates": olek["alates"], "allikaid": olek["allikaid"], "toimis": olek["toimis"],
                 "kandidaate": len(kand), "uusi": olek["uusi"], "uusi_versioone": olek["uusi_versioone"],
                 "duplikaate": olek["duplikaate"], "kaivitus": url}]

    os.makedirs(B + "dash", exist_ok=True)
    for nimi, d in [("kandidaadid", kand), ("allikad", allikad), ("eurostat", euro), ("kaivitus", kaivitus)]:
        json.dump(d, open(B + f"dash/{nimi}.json", "w"), ensure_ascii=False, indent=0)
    print(f"kandidaate {len(kand)}, allikaid {len(allikad)} ({olek['toimis']} toimis), eurostat {len(euro)}, uusi {olek['uusi']}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
