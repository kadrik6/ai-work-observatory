"""OECD valvur: kas OECD on avaldanud Eesti avaliku sektori innovatsiooni või tehisaru kohta uue väljaande
(Kadri 8.11.2026: OECD raporti uuendus automaatseks). Numbrite ülekandmine jääb käsitsi; valvur annab ainult teada.

Otsib Crossrefist OECD (DOI eesliide 10.1787) väljaandeid, mille pealkirjas on „Estonia“ ja mõni teemasõna ning
mis on avaldatud pärast viimast teadaolevat raportit. Kirjutab sait/sisu/oecd-valvur.json (ainult siis, kui leiud
muutuvad); saidi „Mis uueneb ise“ tabel näitab leitud väljaannet. Võrguviga ei muuda faili (eelmine seis jääb).

Käivitus: python3 sait/oecd_valvur.py   (GitHub Actions, sait-andmed.yml)
"""
import datetime as dt
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

SISU = Path(__file__).resolve().parent / "sisu"
TEADA = {"doi": "10.1787/c2c09a06-en", "kuupaev": "2026-11-03",
         "pealkiri": "Strengthening the Innovative Capacity of the Public Sector of Estonia"}
TEEMAD = ("innovat", "public sector", "public governance", "artificial intelligence", " ai ", "digital government")
API = "https://api.crossref.org/works"


def paring(alates):
    q = {"query.bibliographic": "Estonia public sector innovation artificial intelligence",
         "filter": f"prefix:10.1787,from-pub-date:{alates}", "rows": "40", "select": "DOI,title,published,type"}
    return API + "?" + urllib.parse.urlencode(q)


def _kp(it):
    osad = (it.get("published") or {}).get("date-parts", [[None]])[0]
    if not osad or osad[0] is None:
        return ""
    osad = list(osad) + [1, 1]
    return f"{osad[0]:04d}-{osad[1]:02d}-{osad[2]:02d}"


def vali(items, teada=TEADA):
    """Crossrefi kirjetest need, mis on uued ja puudutavad Eestit ning teemat."""
    uued = []
    for it in items:
        pealkiri = " ".join(it.get("title") or [])
        p = f" {pealkiri.lower()} "
        kp = _kp(it)
        if it.get("DOI", "").lower() == teada["doi"] or "estonia" not in p or not any(t in p for t in TEEMAD):
            continue
        if kp and kp <= teada["kuupaev"]:
            continue
        uued.append({"doi": it["DOI"], "pealkiri": pealkiri, "kuupaev": kp, "url": f"https://doi.org/{it['DOI']}"})
    return sorted(uued, key=lambda u: u["kuupaev"], reverse=True)


def kontrolli(laadi=None, tana=None):
    laadi = laadi or (lambda url: json.load(urllib.request.urlopen(
        urllib.request.Request(url, headers={"User-Agent": "tehisaru-seire/1.0 (GitHub Actions)"}), timeout=30)))
    d = laadi(paring(TEADA["kuupaev"]))
    return {"kontrollitud": tana or dt.date.today().isoformat(), "teada": TEADA,
            "uued": vali(d.get("message", {}).get("items", []))}


if __name__ == "__main__":
    try:
        tulemus = kontrolli()
    except Exception as viga:  # võrk või Crossref maas: eelmine seis jääb
        sys.exit(f"HOIATUS OECD valvur: {viga}")
    f = SISU / "oecd-valvur.json"
    vana = json.loads(f.read_text(encoding="utf-8")) if f.exists() else None
    # Fail muutub ainult siis, kui leiud muutuvad: muidu teeks igapäevane töö iga päev tühja commit'i.
    if vana is None or vana.get("uued") != tulemus["uued"] or vana.get("teada") != tulemus["teada"]:
        f.write_text(json.dumps(tulemus, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"OECD valvur: uusi väljaandeid {len(tulemus['uued'])}")
