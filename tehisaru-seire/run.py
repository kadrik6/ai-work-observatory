"""Seire käivitamine.

    python run.py                    laadib kõik näitajad ja koostab kaardid
    python run.py --uuri isoc_eb_ai  näitab andmestiku mõõtmeid ja koode
    python run.py --uuri-sa majandus/infotehnoloogia/infotehnoloogia-ettevettes/IT1490
                                     näitab Statistikaameti tabeli muutujaid ja koode

Tulemused:
    andmed/<id>.csv         andmed tabelina
    andmed/<id>.meta.json   metaandmed: allikas, värskus, kontrollid
    andmed/muutused.csv     iga muutunud väärtus koos kuupäevaga
    kaardid/<id>.md         numbrikaart
    kaardid/<id>.svg        graafik
    kaardid/README.md       avaleht kõigi näitajatega
"""

import argparse
import csv
import json
import sys
from datetime import date
from pathlib import Path

from seire import eurostat, kaart, kontrollid, statistikaamet, usaldus

JUUR = Path(__file__).parent
ANDMED = JUUR / "andmed"
KAARDID = JUUR / "kaardid"
MUUTUSED = ANDMED / "muutused.csv"
VALJAD = ["geo", "time", "vaartus", "margend"]


def loe_seadistus():
    with open(JUUR / "naitajad.json", encoding="utf-8") as f:
        return json.load(f)


def loe_eelmised(fail):
    """Eelmise käivituse väärtused, et näha, mis muutus."""
    if not fail.exists():
        return {}
    with open(fail, encoding="utf-8") as f:
        return {(r["geo"], r["time"]): r["vaartus"] for r in csv.DictReader(f)}


def leia_muutused(naitaja_id, read, eelmised, tana):
    muutused = []
    for r in read:
        vana = eelmised.get((r["geo"], r["time"]))
        uus = "" if r["vaartus"] is None else str(r["vaartus"])
        if eelmised and vana != uus:
            muutused.append({"kuupaev": tana, "naitaja": naitaja_id, "geo": r["geo"], "aasta": r["time"], "vana": vana or "uus rida", "uus": uus})
    return muutused


def salvesta_muutused(muutused):
    uus_fail = not MUUTUSED.exists()
    with open(MUUTUSED, "a", encoding="utf-8", newline="") as f:
        kirjutaja = csv.DictWriter(f, fieldnames=["kuupaev", "naitaja", "geo", "aasta", "vana", "uus"])
        if uus_fail:
            kirjutaja.writeheader()
        kirjutaja.writerows(muutused)


def loe_muutused(naitaja_id):
    if not MUUTUSED.exists():
        return []
    with open(MUUTUSED, encoding="utf-8") as f:
        return [m for m in csv.DictReader(f) if m["naitaja"] == naitaja_id]


def tootle(naitaja, riigid, andmed, tana, riiklik=None, riikliku_viga=None):
    """Üks näitaja algusest lõpuni: andmed → kontroll → usaldus → kaart.

    riiklik: Statistikaameti tabelist automaatselt laaditud kirje (või None).
    riikliku_viga: tekst, kui Statistikaameti laadimine ebaõnnestus.
    """
    read = [{k: r[k] for k in VALJAD} for r in eurostat.json_stat_ridadeks(andmed)]
    read.sort(key=lambda r: (r["geo"], r["time"]))

    probleemid = kontrollid.kontrolli(read, riigid, protsent=naitaja["uhik"].startswith("%"))
    uuendatud = date.fromisoformat(andmed.get("updated", tana)[:10])
    varskus = usaldus.varskus(uuendatud, naitaja["uuendussagedus_kuudes"], date.fromisoformat(tana))
    teised = naitaja.get("teised_allikad", []) + ([riiklik] if riiklik else [])
    vordlus = usaldus.vordle_allikaid(read, teised)
    uuem = usaldus.uuem_allikas(read, teised)
    if riikliku_viga:
        probleemid.append({"tase": "hoiatus", "tekst": riikliku_viga})
    if uuem:
        probleemid.append({
            "tase": "hoiatus",
            "tekst": f"Uuem number on juba olemas: {uuem['allikas']} annab Eesti {uuem['aasta']}. aasta väärtuseks {kaart.protsent(uuem['vaartus'])}. Põhiallikas seda veel ei näita.",
        })

    moodete_nimed = {n: dict(v) for n, v in eurostat.moodete_kirjeldus(andmed).items()}
    meta = {
        "naitaja": naitaja["id"],
        "andmestiku_nimi": andmed.get("label", ""),
        "naitaja_nimi": "; ".join(moodete_nimed.get(n, {}).get(k, k) for n, k in naitaja["filtrid"].items()),
        "url": eurostat.koosta_url(naitaja["andmestik"], naitaja["filtrid"], riigid),
        "allikas_uuendas": uuendatud.isoformat(),
        "kontrollitud": tana,
        "varskus": varskus,
        "filtrid_kontrollitud": naitaja.get("filtrid_kontrollitud", False),
        "probleemid": probleemid,
        "vordlus": vordlus,
        "uuem_allikas": uuem,
    }

    csv_fail = ANDMED / f"{naitaja['id']}.csv"
    muutused = leia_muutused(naitaja["id"], read, loe_eelmised(csv_fail), tana)
    salvesta_muutused(muutused)

    with open(csv_fail, "w", encoding="utf-8", newline="") as f:
        kirjutaja = csv.DictWriter(f, fieldnames=VALJAD)
        kirjutaja.writeheader()
        kirjutaja.writerows(read)
    with open(ANDMED / f"{naitaja['id']}.meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    (KAARDID / f"{naitaja['id']}.svg").write_text(kaart.graafik_svg(read, naitaja["uhik"]), encoding="utf-8")
    (KAARDID / f"{naitaja['id']}.md").write_text(
        kaart.koosta_kaart(naitaja, read, meta, probleemid, vordlus, loe_muutused(naitaja["id"])), encoding="utf-8"
    )

    aasta, viimased = kaart.viimase_aasta_read(read)
    eesti = next((r["vaartus"] for r in viimased if r["geo"] == kaart.EESTI), None)
    return {
        "id": naitaja["id"],
        "nimi": naitaja["nimi"],
        "eesti": eesti,
        "aasta": aasta,
        "staatus": varskus["staatus"],
        "vastuolu": any(v["vastuolu"] for v in vordlus),
        "uuem_allikas": uuem is not None,
        "vigu": sum(p["tase"] == "viga" for p in probleemid),
        "hoiatusi": sum(p["tase"] == "hoiatus" for p in probleemid),
    }


def uuri(andmestik):
    """Prindib andmestiku mõõtmed ja koodid, et saaksid filtrid õigesti valida."""
    andmed = eurostat.lae(andmestik, filtrid={"geo": "EE"})
    print(f"{andmestik}: {andmed.get('label', '')}\nUuendatud: {andmed.get('updated', '?')}\n")
    for nimi, koodid in eurostat.moodete_kirjeldus(andmed).items():
        print(f"{nimi}:")
        for kood, silt in koodid:
            print(f"    {kood:<20} {silt}")


def uuri_sa(tabel):
    """Prindib Statistikaameti tabeli muutujad ja koodid, et saaksid päringu õigesti koostada."""
    meta = statistikaamet.metaandmed(tabel)
    print(f"{tabel}: {meta.get('title', '')}\n")
    for muutuja in meta.get("variables", []):
        print(f"{muutuja['code']} ({muutuja.get('text', '')}):")
        for kood, silt in zip(muutuja.get("values", []), muutuja.get("valueTexts", [])):
            print(f"    {kood:<20} {silt}")


def lae_riiklik(naitaja):
    """Laadib Statistikaameti numbri, kui näitajal on see seadistatud. Viga ei peata seiret."""
    seadistus = naitaja.get("riiklik_allikas")
    if not seadistus:
        return None, None
    try:
        andmed = statistikaamet.lae(seadistus["tabel"], seadistus["valikud"])
        return statistikaamet.riiklik_allikas(seadistus, andmed), None
    except Exception as viga:  # võrk, muutunud tabel või vale päring
        return None, f"Statistikaameti tabelit {seadistus['tabel']} ei õnnestunud laadida: {viga}"


def main():
    parser = argparse.ArgumentParser(description="Tehisaru ja andmete seire")
    parser.add_argument("--uuri", metavar="ANDMESTIK", help="näita andmestiku mõõtmeid ja koode")
    parser.add_argument("--uuri-sa", metavar="TABEL", help="näita Statistikaameti tabeli muutujaid ja koode")
    args = parser.parse_args()

    if args.uuri:
        uuri(args.uuri)
        return 0
    if args.uuri_sa:
        uuri_sa(args.uuri_sa)
        return 0

    ANDMED.mkdir(exist_ok=True)
    KAARDID.mkdir(exist_ok=True)
    seadistus = loe_seadistus()
    tana = date.today().isoformat()
    kokkuvotted = []
    for naitaja in seadistus["naitajad"]:
        print(f"Laadin: {naitaja['nimi']} ({naitaja['andmestik']})")
        andmed = eurostat.lae(naitaja["andmestik"], naitaja["filtrid"], seadistus["riigid"])
        riiklik, riikliku_viga = lae_riiklik(naitaja)
        kokkuvote = tootle(naitaja, seadistus["riigid"], andmed, tana, riiklik, riikliku_viga)
        print(f"    Eesti {kokkuvote['aasta']}: {kokkuvote['eesti']} · staatus {kokkuvote['staatus']} · vigu {kokkuvote['vigu']} · hoiatusi {kokkuvote['hoiatusi']}")
        kokkuvotted.append(kokkuvote)

    (KAARDID / "README.md").write_text(kaart.koosta_avaleht(kokkuvotted), encoding="utf-8")
    print("\nValmis. Ava kaardid/README.md")
    return 1 if any(k["vigu"] for k in kokkuvotted) else 0


if __name__ == "__main__":
    sys.exit(main())
