"""Eesti ja ELi töötuse määr kuu kaupa Eurostatist (Kadri 25.11.2026: töötuse number peab uuenema ise).

Kirjutab sisu/eurostat-tootus-kuud.csv: viimased 25 kuud (uusim kuu, sama kuu aasta varem ja aasta enne seda),
sesoonselt tasandatud, 15–74-aastased, % tööjõust. Uusim kuu on viimane, mille kohta on olemas nii Eesti kui ka
ELi number. Kui Eesti ja ELi numbrid ei muutunud, jääb fail puutumata; veerg „uuendatud“ on seega Eurostati
andmestiku uuendamise kuupäev sel päeval, kui lehe numbrid viimati muutusid.
Käivita: python3 sait/lae_tootus.py   (ec.europa.eu on lubatud võrgus)
"""
import csv
import json
import sys
import urllib.request
from pathlib import Path

SISU = Path(__file__).resolve().parent / "sisu"
FAIL = SISU / "eurostat-tootus-kuud.csv"
API = ("https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/une_rt_m"
       "?format=JSON&s_adj=SA&age=TOTAL&sex=T&unit=PC_ACT&geo=EE&geo=EU27_2020&lastTimePeriod=40")
GEOD = ("EU27_2020", "EE")
KUID = 25
VALJAD = ["geo", "kuu", "protsent", "margend", "uuendatud"]


def read_vastusest(d, kuid=KUID):
    """Eurostati JSON-stat vastusest read (geo, kuu, protsent, märgend) viimase `kuid` kuu kohta."""
    geo = d["dimension"]["geo"]["category"]["index"]
    aeg = d["dimension"]["time"]["category"]["index"]
    n = len(aeg)
    margid = d.get("status", {})
    v = {g: {k: (d["value"].get(str(geo[g] * n + i)), margid.get(str(geo[g] * n + i), "")) for k, i in aeg.items()}
         for g in GEOD if g in geo}
    if set(v) != set(GEOD):
        raise ValueError("une_rt_m: Eesti või ELi rida puudub")
    koos = sorted(k for k in aeg if all(v[g][k][0] is not None for g in GEOD))
    if len(koos) < kuid:
        raise ValueError(f"une_rt_m: ühiseid kuid on {len(koos)}, vaja {kuid}")
    kuud = koos[-kuid:]
    return [(g, k, v[g][k][0], v[g][k][1]) for g in GEOD for k in kuud]


def uus_seis(vanad, read, uuendatud):
    """Tagastab uued CSV read või None, kui Eesti ja ELi numbrid on samad mis failis."""
    enne = {(r["geo"], r["kuu"]): (float(r["protsent"]), r.get("margend", "")) for r in vanad}
    nyyd = {(g, k): (float(p), m) for g, k, p, m in read}
    if enne == nyyd:
        return None
    return [{"geo": g, "kuu": k, "protsent": p, "margend": m, "uuendatud": uuendatud} for g, k, p, m in read]


def main():
    with urllib.request.urlopen(API, timeout=60) as v:
        d = json.load(v)
    read = read_vastusest(d)
    with open(FAIL, encoding="utf-8") as f:
        vanad = list(csv.DictReader(f))
    uued = uus_seis(vanad, read, d.get("updated", "")[:10])
    viimane = read[-1]
    if uued is None:
        print(f"töötus: muutust pole, uusim kuu {viimane[1]} (Eesti {viimane[2]}%)")
        return
    if not uued[0]["uuendatud"]:
        sys.exit("une_rt_m: vastuses puudub uuendamise kuupäev")
    with open(FAIL, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=VALJAD)
        w.writeheader()
        w.writerows(uued)
    print(f"töötus: {len(uued)} rida, uusim kuu {viimane[1]} (Eesti {viimane[2]}%), uuendatud {uued[0]['uuendatud']}")


if __name__ == "__main__":
    main()
