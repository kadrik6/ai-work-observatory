"""Millal allikas avalehe numbrite tabeleid viimati uuendas (Kadri 26.11.2026: „what exactly was updated by which
source … there were late updates as well, and they should be seen here at the latest“).

Avalehel olev „avaldatud“ on numbri esimese avaldamise päev. Allikas võib tabelit hiljem parandada või täiendada
(näiteks Statistikaamet IT1490: avaldati 16.09.2026, uuendati 21.10.2026). See skript loeb iga tabeli viimase
uuendamise aja otse allikast:
- Statistikaamet: tabelikausta loend (andmed.stat.ee API), väli „updated“;
- Eurostat: andmestiku JSON, väli „updated“.
Kirjutab sisu/tabelite-uuendused.csv. Kui mõne tabeli päring ebaõnnestub, jääb selle rida eelmise seisuga.
Kui midagi ei muutunud, jääb fail puutumata.
Käivita: python3 sait/lae_uuendused.py   (andmed.stat.ee ja ec.europa.eu on lubatud võrgus)
"""
import csv
import json
import re
import sys
import urllib.request
from pathlib import Path

FAIL = Path(__file__).resolve().parent / "sisu" / "tabelite-uuendused.csv"
VALJAD = ["allikas", "tabel", "uuendatud"]
SA_API = "https://andmed.stat.ee/api/v1/et/stat/"
ES_API = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/"
# Avalehe numbrite tabelid. Statistikaamet: tabel → kaust API-s.
STATISTIKAAMET = {
    "IT71": "majandus/infotehnoloogia/infotehnoloogia-leibkonnas",
    "IT1490": "majandus/infotehnoloogia/infotehnoloogia-ettevettes",
}
# Eurostat: andmestik → väike päring (ainult „updated“ on vaja, andmeid mitte).
EUROSTAT = {
    "une_rt_m": "geo=EE&lastTimePeriod=1",
    "une_rt_a": "geo=EE&lastTimePeriod=1",
    "isoc_ai_iaiu": "geo=EE&lastTimePeriod=1",
    "isoc_eb_ai": "geo=EE&lastTimePeriod=1",
    "isoc_sk_dskl_i21": "geo=EE&lastTimePeriod=1",
}
KP = re.compile(r"\d{4}-\d{2}-\d{2}")


def _json(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers={"Accept": "application/json"}), timeout=60) as v:
        return json.load(v)


def sa_kuupaev(loend, tabel):
    """Statistikaameti kausta loendist tabeli „updated“ kuupäev („2026-10-21“)."""
    for x in loend:
        if x.get("id", "").upper() == tabel.upper() + ".PX":
            kp = (x.get("updated") or "")[:10]
            if KP.fullmatch(kp):
                return kp
    raise ValueError(f"Statistikaamet {tabel}: tabelit või kuupäeva ei leitud")


def es_kuupaev(d, tabel):
    """Eurostati JSON-ist „updated“ kuupäev („2026-11-24T11:00:00+0100“ → „2026-11-24“)."""
    kp = (d.get("updated") or "")[:10]
    if not KP.fullmatch(kp):
        raise ValueError(f"Eurostat {tabel}: väli „updated“ puudub")
    return kp


def uus_seis(vanad, leitud):
    """vanad: CSV read; leitud: {(allikas, tabel): kuupäev}. Tagastab uued read või None, kui midagi ei muutunud.
    Rida, mida seekord ei leitud, jääb vana kuupäevaga."""
    seis = {(r["allikas"], r["tabel"]): r["uuendatud"] for r in vanad}
    uus = {**seis, **leitud}
    if uus == seis:
        return None
    return [{"allikas": a, "tabel": t, "uuendatud": k} for (a, t), k in sorted(uus.items())]


def main():
    leitud, vead = {}, []
    kaustad = {}
    for tabel, kaust in STATISTIKAAMET.items():
        try:
            if kaust not in kaustad:
                kaustad[kaust] = _json(SA_API + kaust)
            leitud[("Statistikaamet", tabel)] = sa_kuupaev(kaustad[kaust], tabel)
        except Exception as v:  # noqa: BLE001 – üks tabel ei peata teisi
            vead.append(f"{tabel}: {v}")
    for tabel, q in EUROSTAT.items():
        try:
            leitud[("Eurostat", tabel)] = es_kuupaev(_json(f"{ES_API}{tabel}?{q}"), tabel)
        except Exception as v:  # noqa: BLE001
            vead.append(f"{tabel}: {v}")
    vanad = []
    if FAIL.exists():
        with open(FAIL, encoding="utf-8") as f:
            vanad = list(csv.DictReader(f))
    uued = uus_seis(vanad, leitud)
    if uued is None:
        print("tabelite-uuendused.csv: muutust pole")
    else:
        with open(FAIL, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=VALJAD)
            w.writeheader()
            w.writerows(uued)
        print(f"tabelite-uuendused.csv: {len(uued)} tabelit")
    for v in vead:
        print("HOIATUS", v, file=sys.stderr)
    return 1 if vead and not leitud else 0


if __name__ == "__main__":
    sys.exit(main())
