"""Võtab projekti kaustast saidi jaoks avaliku hetkeseisu: uudised, uudiste väited, hanked ja publikatsioonid.

Neid andmeid uuendavad igapäevased tööd väljaspool repot (uudiste kogumine, hangete Actionsi käik, OpenAlexi
analüüs). Sait ehitab ainult repo failidest. Repo reegli järgi kopeeritakse siia midagi väljastpoolt ainult Kadri loal.
Kopeeritakse ainult avalik sisu: pealkiri, link, kuupäev ja oma sõnadega lühikokkuvõte (mitte artikli tekst),
riigihangete registri avalikud väljad (kirjeldus lühendatud) ja publikatsioonide metaandmed.

Käivitus: python3 sait/vota_kaasa.py PROJEKTI_KAUST   (või keskkonnamuutuja PROJEKTI_KAUST)
Uudistest jäetakse välja, kes ütles (väide kuulub väljaandele, mitte inimesele).
"""
import json
import os
import re
import shutil
import sys
from pathlib import Path

SISU = Path(__file__).resolve().parent / "sisu"
KIRJELDUS_MAX = 300  # hanke kirjelduse pikkus; täistekst jääb registrisse


def _loe(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def _kirjuta(nimi, andmed):
    (SISU / nimi).write_text(json.dumps(andmed, ensure_ascii=False, indent=0) + "\n", encoding="utf-8")


def ilma_nimedeta(kes):
    """„ERR News 3.11.2026 (Sinisalu, Hiiemaa, Töötukassa)“ → „ERR News 3.11.2026“. Sulud, kus on number
    (nt „sarnaselt ERR News 3.11“), jäävad alles."""
    return re.sub(r"\s*\([^()\d]*\)", "", kes).strip()


def vota(proj):
    proj = Path(proj)
    uu = proj / "tooelu-uudised"
    read = [json.loads(r) for r in (uu / "uudised.jsonl").read_text(encoding="utf-8").splitlines() if r.strip()]
    for r in read:
        r.pop("kes_utles", None)
    (SISU / "uudised.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in read), encoding="utf-8")
    vaited = _loe(uu / "vaited.json")
    for r in vaited:  # väide kuulub väljaandele: sulgudes nimed (ilma kuupäevata) jäävad välja
        r["kes"] = ilma_nimedeta(r.get("kes", ""))
    (SISU / "uudiste-vaited.json").write_text(json.dumps(vaited, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    shutil.copyfile(uu / "olek.json", SISU / "uudiste-olek.json")
    shutil.copyfile(uu / "koondajad.json", SISU / "koondajad.json")  # keda koondajad ise tööle otsivad

    h = _loe(proj / "seire-uuendus" / "hanked" / "leht.json")
    for r in h["loend"]:
        if r.get("k") and len(r["k"]) > KIRJELDUS_MAX:
            r["k"] = r["k"][:KIRJELDUS_MAX].rstrip() + "…"
    h.get("hindamine", {}).pop("margenda_jargmiseks", None)
    h["seis"] = _loe(proj / "seire-uuendus" / "hanked" / "seis.json")
    _kirjuta("hanked-leht.json", h)

    an = proj / "tooelu-leht-andmed" / "analyys"
    meta = _loe(an / "osad.json")["meta"]
    _kirjuta("publikatsioonid.json", {
        "meta": {"aeg": meta["aeg"], "paring": meta["paring"], "teemad": meta["teemad"]},
        "aastad": _loe(an / "a_aastad.json"),
        "teemad": _loe(an / "a_teemad.json"),
        "tood": _loe(an / "a_tood.json"),
        "eesti_allikad": _loe(an / "a_eesti_allikad.json"),
        # Eesti tööde põhinumbrid, kontrollitud allika lehelt (Kadri MKUS-i kommentaar 7.11.2026 08:53)
        "eesti_kpi": _loe(an / "a_eesti_kpi.json") if (an / "a_eesti_kpi.json").exists() else None,
    })


if __name__ == "__main__":
    kaust = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("PROJEKTI_KAUST")
    if not kaust:
        sys.exit("Anna projekti kaust: python3 sait/vota_kaasa.py KAUST")
    vota(kaust)
    print("sisu/ uuendatud")
