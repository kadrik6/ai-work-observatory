"""Eesti hõivatud ametite pearühma (ISCO-08, 1 number) järgi kvartali kaupa Eurostatist (Kadri 27.11.2026, leht
„Minu amet“: lugeja näeb oma ametirühma hõive muutust uusima kvartalini).

Kirjutab sisu/ee-hoive-pearyhm-kvartal.csv: Eurostat lfsq_eisn2 (Statistikaameti tööjõu-uuring), 15+, kõik
tegevusalad, tuhat inimest, 2021. aasta I kvartalist. Märgend tuleb Eurostatist (u = väike usaldusväärsus,
b = aegrea katkestus). Kui numbrid ei muutunud, jääb fail puutumata.
Käivita: python3 sait/lae_ee_kvartal.py   (ec.europa.eu on lubatud võrgus)
"""
import csv
import json
import sys
import urllib.request
from pathlib import Path

SISU = Path(__file__).resolve().parent / "sisu"
FAIL = SISU / "ee-hoive-pearyhm-kvartal.csv"
API = ("https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/lfsq_eisn2"
       "?format=JSON&geo=EE&sex=T&age=Y_GE15&nace_r2=TOTAL&unit=THS_PER&sinceTimePeriod=2021-Q1")
RYHMAD = [f"OC{i}" for i in range(1, 10)]
VALJAD = ["kvartal", "isco", "tuhat", "margend", "uuendatud"]


def read_vastusest(d):
    """JSON-stat vastusest read (kvartal, isco, tuhat, märgend). Puuduv pearühm või kvartal kukutab."""
    isco = d["dimension"]["isco08"]["category"]["index"]
    aeg = d["dimension"]["time"]["category"]["index"]
    n = len(aeg)
    if any(r not in isco for r in RYHMAD):
        raise ValueError("lfsq_eisn2: mõni ISCO pearühm puudub")
    out = []
    for k, i in sorted(aeg.items()):
        v = [(r, d["value"].get(str(isco[r] * n + i)), d.get("status", {}).get(str(isco[r] * n + i), "")) for r in RYHMAD]
        if any(x[1] is None for x in v):
            continue  # kvartal, kus mõni rühm on avaldamata, jääb välja
        out += [(k, r, x, m) for r, x, m in v]
    return out


def main():
    with urllib.request.urlopen(API, timeout=60) as v:
        d = json.load(v)
    read = read_vastusest(d)
    uuendatud = d.get("updated", "")[:10]
    if not uuendatud:
        sys.exit("lfsq_eisn2: vastuses puudub uuendamise kuupäev")
    vanad = []
    if FAIL.exists():
        with open(FAIL, encoding="utf-8") as f:
            vanad = list(csv.DictReader(f))
    if {(r["kvartal"], r["isco"], float(r["tuhat"]), r["margend"]) for r in vanad} == {(k, i, float(x), m) for k, i, x, m in read}:
        print(f"ametirühmad: muutust pole, uusim kvartal {read[-1][0]}")
        return
    with open(FAIL, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=VALJAD)
        w.writeheader()
        w.writerows({"kvartal": k, "isco": i, "tuhat": x, "margend": m, "uuendatud": uuendatud} for k, i, x, m in read)
    print(f"ametirühmad: {len(read)} rida, uusim kvartal {read[-1][0]}, uuendatud {uuendatud}")


if __name__ == "__main__":
    main()
