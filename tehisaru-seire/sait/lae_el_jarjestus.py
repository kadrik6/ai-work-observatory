"""ELi riikide aegread järjestuse muutuse graafikute jaoks (Kadri 7.11.2026: „see annab hea pildi muutusest ajas“).

Kirjutab sisu/el-jarjestus.csv: iga näitaja kõik ELi riigid ja kõik avaldatud aastad Eurostatist.
Käivita: python3 sait/lae_el_jarjestus.py   (ec.europa.eu on lubatud võrgus)
"""
import csv
import json
import sys
import urllib.request
from pathlib import Path

SIIN = Path(__file__).resolve().parent
SISU = SIIN / "sisu"
API = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/"
# nimi: (tabel, päring, kirjeldus)
NAITAJAD = {
    "ettevotete-tehisaru-kasutus": ("isoc_eb_ai", "size_emp=GE10&unit=PC_ENT&nace_r2=C10-S951_X_K&indic_is=E_AI_TANY",
                                    "Tehisaru kasutavad ettevõtted, % vähemalt 10 hõivatuga ettevõtetest"),
    # Kadri 9.11.2026: inimeste kasutuse järjestus ajas; Eurostat mõõtis seda esimest korda 2025
    "inimeste-tehisaru-kasutus": ("isoc_ai_iaiu", "indic_is=I_IUAI&unit=PC_IND&ind_type=IND_TOTAL",
                                  "Generatiivset tehisaru kasutanud inimesed, % 16–74-aastastest"),
    "tootuse-maar": ("une_rt_a", "age=Y15-74&unit=PC_ACT&sex=T&sinceTimePeriod=2015",
                     "Töötuse määr, % tööjõust, 15–74-aastased"),
}


def lae(tabel, paring):
    with urllib.request.urlopen(f"{API}{tabel}?format=JSON&{paring}", timeout=60) as v:
        d = json.load(v)
    geo = {i: g for g, i in d["dimension"]["geo"]["category"]["index"].items()}
    aeg = {i: a for a, i in d["dimension"]["time"]["category"]["index"].items()}
    n = len(aeg)
    read = [(geo[int(k) // n], int(aeg[int(k) % n]), v) for k, v in d["value"].items()]
    return read, d.get("updated", "")[:10]


def main():
    sys.path.insert(0, str(SIIN))
    import andmekiht
    el = set(andmekiht.lae()["el_riigid"])
    with open(SISU / "el-jarjestus.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["naitaja", "geo", "aasta", "vaartus", "tabel", "kirjeldus", "uuendatud"])
        for nimi, (tabel, paring, kirjeldus) in NAITAJAD.items():
            read, uuendatud = lae(tabel, paring)
            read = sorted(r for r in read if r[0] in el)
            if not read:
                sys.exit(f"{tabel}: Eurostat ei andnud ridu")
            for g, a, v in read:
                w.writerow([nimi, g, a, v, tabel, kirjeldus, uuendatud])
            print(nimi, len(read), "rida, uuendatud", uuendatud)


if __name__ == "__main__":
    main()
