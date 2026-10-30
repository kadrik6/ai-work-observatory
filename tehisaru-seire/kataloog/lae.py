"""Laeb kataloogi võrdlusvaatlused Statistikaameti ja Eurostati API-st faili vaatlused-api.csv.

Käivitamine kaustast tehisaru-seire:  python kataloog/lae.py
Fail kirjutatakse iga kord üle. Käsitsi kantud ja ühekordselt laaditud numbrid on failis
vaatlused-muud.csv, seda skript ei puuduta. Eurostati põhinäitaja numbrid loeb võrdlus
otse seire andmetest (andmed/<näitaja>.csv), neid siia ei laadita.
"""

import csv
import datetime as dt
import sys
from pathlib import Path

JUUR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(JUUR))

from seire import eurostat, statistikaamet  # noqa: E402

VALJA = JUUR / "kataloog" / "vaatlused-api.csv"
VALJAD = ["moodik", "riik", "aasta", "vaartus", "avaldatud", "kontrollitud", "kuidas", "url", "markus"]
RIIGID = ["EE", "FI", "SE", "DK", "NO", "DE", "NL", "EU27_2020"]

SA_ETTEVOTTED = {"Näitaja": ["E_AI_TANY"], "Tegevusala": ["TOTAL"], "Tööga hõivatud isikute arv": ["TOTAL"]}
STATISTIKAAMET = [
    # (mõõdik, tabel, valikud, märkus)
    ("sa-it149", "majandus/infotehnoloogia/infotehnoloogia-ettevettes/IT149", SA_ETTEVOTTED, ""),
    ("sa-it1490", "majandus/infotehnoloogia/infotehnoloogia-ettevettes/IT1490", SA_ETTEVOTTED,
     "Esimest korda avaldatud uudises 16.09.2026 (34%)."),
    ("sa-it71", "majandus/infotehnoloogia/infotehnoloogia-leibkonnas/IT71",
     {"Näitaja": ["PC_IND"], "Isikute rühm": ["IND_TOTAL"], "Tehisintellekti kasutamise eesmärk": ["II_IUAI"]}, ""),
    ("sa-it71-internetikasutajad", "majandus/infotehnoloogia/infotehnoloogia-leibkonnas/IT71",
     {"Näitaja": ["PC_I_USER"], "Isikute rühm": ["IND_TOTAL"], "Tehisintellekti kasutamise eesmärk": ["II_IUAI"]}, ""),
    ("sa-it71-too", "majandus/infotehnoloogia/infotehnoloogia-leibkonnas/IT71",
     {"Näitaja": ["PC_IND"], "Isikute rühm": ["IND_TOTAL"], "Tehisintellekti kasutamise eesmärk": ["II_IUAIWP"]}, ""),
    ("sa-it72-oskus", "majandus/infotehnoloogia/infotehnoloogia-leibkonnas/IT72",
     {"Näitaja": ["PC_IND"], "Isikute rühm": ["IND_TOTAL"], "Tehisintellekti mittekasutamise põhjus": ["II_IUAIR_2"]},
     "Põhjused liituvad üle 100% mittekasutajatest: üks inimene võib olla mitmes reas."),
]
EUROSTAT = [
    # (mõõdik, andmestik, filtrid)
    # Seire põhinäitajaid (mõõdikud, millel on veerg naitaja) siia ei lisata, need loetakse andmed/ kaustast.
    ("eurostat-isoc-ai-iaiuxr-oskus-mittekasutajad", "isoc_ai_iaiuxr",
     {"freq": "A", "indic_is": "I_IUAIX_NUUSE", "unit": "PC_IND_IUAIX", "ind_type": "IND_TOTAL"}),
]
# Teadaolevad esmaavaldamise kuupäevad (tabeli uuenduskuupäev ei ole avaldamise kuupäev).
AVALDATUD = {("sa-it1490", "2026"): "2026-09-16"}


def main():
    tana = dt.date.today().isoformat()
    read = []
    for moodik, tabel, valikud, markus in STATISTIKAAMET:
        vastus = statistikaamet.lae(tabel, valikud)
        for aasta, v in sorted(statistikaamet.aastate_vaartused(vastus, "Vaatlusperiood").items()):
            read.append({"moodik": moodik, "riik": "EE", "aasta": aasta, "vaartus": f"{v:.1f}",
                         "avaldatud": AVALDATUD.get((moodik, aasta), ""), "kontrollitud": tana,
                         "kuidas": "Statistikaameti API", "url": statistikaamet.veebi_url(tabel), "markus": markus})
    for moodik, andmestik, filtrid in EUROSTAT:
        vastus = eurostat.lae(andmestik, filtrid, RIIGID)
        for r in sorted(eurostat.json_stat_ridadeks(vastus), key=lambda r: (r["geo"], r["time"])):
            if r["vaartus"] is None:
                continue
            read.append({"moodik": moodik, "riik": r["geo"], "aasta": r["time"], "vaartus": f'{r["vaartus"]:.2f}',
                         "avaldatud": vastus["updated"][:10], "kontrollitud": tana, "kuidas": "Eurostati API",
                         "url": eurostat.koosta_url(andmestik, filtrid, RIIGID),
                         "markus": f'Eurostati märgend {r["margend"]}' if r["margend"] else ""})
    with open(VALJA, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=VALJAD)
        w.writeheader()
        w.writerows(read)
    print(f"Valmis: {len(read)} vaatlust failis {VALJA}")


if __name__ == "__main__":
    main()
