"""Registreeritud töötute arv kuu kaupa (Kadri 25.11.2026: töötuse määr on septembri oma, kas uuemat pole).

Statistikaameti tabel TT065 (Töötukassa andmed): kogu Eesti, mehed ja naised, kõik vanuserühmad. See on arvel
olevate töötute arv, mitte töötuse määr: määr (Eurostat une_rt_m) tuleb tööjõu-uuringust ja loeb ka
neid tööotsijaid, kes Töötukassas arvel ei ole. Neid kahte lehel ei võrrelda ega liideta.
Kirjutab sisu/reg-tootud-kuud.csv: viimased 25 kuud. Kui arvud ei muutunud, jääb fail puutumata.
Käivita: python3 sait/lae_reg_tootud.py   (andmed.stat.ee on lubatud võrgus)
"""
import csv
import json
import sys
import urllib.request
from pathlib import Path

API = "https://andmed.stat.ee/api/v1/et/stat/"
TABEL = "TT065"
FAIL = Path(__file__).resolve().parent / "sisu" / "reg-tootud-kuud.csv"
VALIK = {"Piirkond/Haldusüksus": "Kogu Eesti", "Sugu": "Mehed ja naised", "Vanuserühm": "Vanuserühmad kokku"}
KUID = 25
VALJAD = ["kuu", "arv", "tabel", "uuendatud"]


def _json(url, paring=None):
    keha = json.dumps(paring).encode() if paring else None
    req = urllib.request.Request(url, data=keha, headers={"Content-Type": "application/json"} if keha else {})
    with urllib.request.urlopen(req, timeout=60) as v:
        return json.load(v)


def paring(meta, aastaid=4):
    """Päring tabeli metaandmete järgi: valitud rühmad, kõik kuud (ilma kuude keskmiseta), viimased aastad."""
    muut = {v["code"]: v for v in meta["variables"]}
    q = [{"code": k, "selection": {"filter": "item", "values": [muut[k]["values"][muut[k]["valueTexts"].index(t)]]}}
         for k, t in VALIK.items()]
    kuud = [c for c in muut["Kuu"]["values"] if c.isdigit() and 1 <= int(c) <= 12 and c == str(int(c))]
    q.append({"code": "Kuu", "selection": {"filter": "item", "values": kuud}})
    q.append({"code": "Aasta", "selection": {"filter": "item", "values": muut["Aasta"]["values"][-aastaid:]}})
    return {"query": q, "response": {"format": "json-stat2"}}


def read_vastusest(d, kuid=KUID):
    """json-stat2 vastusest [(„2026-10“, arv)], vanemad ees; tühjad kuud jäävad välja."""
    dims, suurus = d["id"], d["size"]
    jrk = {k: sorted(d["dimension"][k]["category"]["index"], key=d["dimension"][k]["category"]["index"].get) for k in dims}
    read = []
    for i, v in enumerate(d["value"]):
        j, idx = i, {}
        for k, n in reversed(list(zip(dims, suurus))):
            idx[k] = jrk[k][j % n]
            j //= n
        if v is not None:
            read.append((f'{int(idx["Aasta"])}-{int(idx["Kuu"]):02d}', int(v)))
    read.sort()
    if len(read) < kuid:
        raise ValueError(f"{TABEL}: kuid on {len(read)}, vaja {kuid}")
    read = read[-kuid:]
    oodatud = [f"{a}-{k:02d}" for a in range(int(read[0][0][:4]), int(read[-1][0][:4]) + 1) for k in range(1, 13)]
    oodatud = [k for k in oodatud if read[0][0] <= k <= read[-1][0]]
    if [k for k, _ in read] != oodatud:
        raise ValueError(f"{TABEL}: kuude reas on auk")
    return read


def uus_seis(vanad, read, uuendatud):
    """Tagastab uued CSV read või None, kui arvud on samad mis failis."""
    if [(r["kuu"], int(r["arv"])) for r in vanad] == read:
        return None
    return [{"kuu": k, "arv": v, "tabel": TABEL, "uuendatud": uuendatud} for k, v in read]


def main():
    d = _json(API + TABEL + ".PX", paring(_json(API + TABEL + ".PX")))
    read = read_vastusest(d)
    # avaldamise kuupäev tuleb otsingust (json-stat2 „updated“ ei ole tabeli uuendamise aeg)
    avaldatud = next((x["published"][:10] for x in _json(API + "?query=" + TABEL) if x["id"].upper().startswith(TABEL + ".")), "")
    vanad = []
    if FAIL.exists():
        with open(FAIL, encoding="utf-8") as f:
            vanad = list(csv.DictReader(f))
    uued = uus_seis(vanad, read, avaldatud)
    if uued is None:
        print(f"registreeritud töötud: muutust pole, uusim kuu {read[-1][0]} ({read[-1][1]})")
        return
    if not avaldatud:
        sys.exit(f"{TABEL}: avaldamise kuupäeva ei leitud")
    with open(FAIL, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=VALJAD)
        w.writeheader()
        w.writerows(uued)
    print(f"registreeritud töötud: {len(uued)} rida, uusim kuu {read[-1][0]} ({read[-1][1]}), avaldatud {avaldatud}")


if __name__ == "__main__":
    main()
