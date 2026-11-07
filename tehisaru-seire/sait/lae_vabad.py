"""Statistikaameti vabad ametikohad (Kadri 7.11.2026: „mida palgatakse kõige rohkem, millistes valdkondades ja kus“).

Kirjutab sisu/vabad-ametikohad.csv: viimased 8 kvartalit
  PAV011 tegevusala järgi: vabade ametikohtade arv ja määr, tööle võetute arv;
  PAV014 maakonna järgi: vabade ametikohtade määr ja osatähtsus.
Kirjutab sisu/vabad-jarjestus.csv: PAV011 vabade ametikohtade arv tegevusala järgi viimase kvartali kohta
  (nt II kvartal) iga aasta kohta AASTAID aastat tagasi. Sama kvartal igal aastal, et hooaeg järjestust ei muudaks
  (Kadri 7.11.2026: järjestuse muutus aastate kaupa).
Käivita: python3 sait/lae_vabad.py   (andmed.stat.ee on lubatud võrgus)
"""
import csv
import json
import sys
import urllib.request
from pathlib import Path

API = "https://andmed.stat.ee/api/v1/et/stat/"
SISU = Path(__file__).resolve().parent / "sisu"
TABELID = {
    "PAV011": ("Tegevusala", ["Vabade ametikohtade arv", "Vabade ametikohtade määr, %", "Tööle võetud töötajate arv"]),
    "PAV014": ("Maakond", ["Vabade ametikohtade määr, %", "Vabade ametikohtade osatähtsus, %"]),
}
KVARTALEID = 8
AASTAID = 10


def _json(url, paring=None):
    keha = json.dumps(paring).encode() if paring else None
    req = urllib.request.Request(url, data=keha, headers={"Content-Type": "application/json"} if keha else {})
    with urllib.request.urlopen(req, timeout=60) as v:
        return json.load(v)


def lae(tabel, naitajad=None, sama_kvartal=False):
    ruhm, koik_naitajad = TABELID[tabel]
    naitajad = naitajad or koik_naitajad
    meta = _json(API + tabel)
    muut = {v["code"]: v for v in meta["variables"]}
    nv = muut["Näitaja"]
    per = muut["Vaatlusperiood"]
    kood = {t: c for c, t in zip(nv["values"], nv["valueTexts"])}
    perioodid = per["values"][-KVARTALEID:]
    if sama_kvartal:
        kv = per["valueTexts"][-1].split(" ", 1)[1]  # nt „II kvartal“
        perioodid = [c for c, t in zip(per["values"], per["valueTexts"]) if t.endswith(" " + kv)][-AASTAID:]
    paring = {"query": [
        {"code": "Näitaja", "selection": {"filter": "item", "values": [kood[n] for n in naitajad]}},
        {"code": ruhm, "selection": {"filter": "all", "values": ["*"]}},
        {"code": "Vaatlusperiood", "selection": {"filter": "item", "values": perioodid}},
    ], "response": {"format": "json-stat2"}}
    d = _json(API + tabel, paring)
    dims = d["id"]
    sild = {k: d["dimension"][k]["category"]["label"] for k in dims}
    jrk = {k: sorted(d["dimension"][k]["category"]["index"], key=d["dimension"][k]["category"]["index"].get) for k in dims}
    suurus = d["size"]
    read = []
    for i, v in enumerate(d["value"]):
        j, idx = i, {}
        for k, n in reversed(list(zip(dims, suurus))):
            idx[k] = jrk[k][j % n]
            j //= n
        if v is None:
            continue
        read.append({"tabel": tabel, "ruhm": ruhm, "nimi": sild[ruhm][idx[ruhm]], "periood": sild["Vaatlusperiood"][idx["Vaatlusperiood"]],
                     "naitaja": sild["Näitaja"][idx["Näitaja"]], "vaartus": v})
    # avaldamise kuupäev tuleb otsingust (json-stat2 „updated“ on tühi väärtus 9999-12-31)
    otsing = _json(API + "?query=" + tabel)
    avaldatud = next((x["published"][:10] for x in otsing if x["id"].startswith(tabel + ".")), "")
    return read, avaldatud


def main():
    koik = []
    uuendatud = ""
    for t in TABELID:
        r, u = lae(t)
        koik += r
        uuendatud = max(uuendatud, u)
    if not koik:
        sys.exit("Statistikaamet ei andnud ridu")
    with open(SISU / "vabad-ametikohad.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, ["tabel", "ruhm", "nimi", "periood", "naitaja", "vaartus", "uuendatud"])
        w.writeheader()
        for r in koik:
            w.writerow({**r, "uuendatud": uuendatud})
    print(f"{len(koik)} rida, uuendatud {uuendatud}")
    jrj, u = lae("PAV011", ["Vabade ametikohtade arv"], sama_kvartal=True)
    with open(SISU / "vabad-jarjestus.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, ["tabel", "ruhm", "nimi", "periood", "naitaja", "vaartus", "uuendatud"])
        w.writeheader()
        for r in jrj:
            w.writerow({**r, "uuendatud": u})
    print(f"järjestus: {len(jrj)} rida")


if __name__ == "__main__":
    main()
