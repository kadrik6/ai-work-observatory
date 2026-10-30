"""Seireraporti kuldfailitesti abiskript: ehitab raporti ajutises koopias külmutatud sisendist.

    python tests/kuld/ehita.py            näitab, millised lehed erinevad viitest
    python tests/kuld/ehita.py --uuenda   kirjutab viited.json uuesti (tee seda ainult teadlikult)

Sisend on kaustas tests/kuld/sisend/ (päris andmete koopia 27.10.2026 seisuga). Seepärast ei kuku
test läbi, kui seire laeb uued andmed, vaid ainult siis, kui raporti kood muutub.
"""

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

KULD = Path(__file__).resolve().parent
JUUR = KULD.parent.parent
SISEND = KULD / "sisend"
VIITED = KULD / "viited.json"
KUUPAEV = "2026-10-27"  # sisendi seis; lehtedel on kirjas „Uuendatud“ selle kuupäevaga
# Andmefailid ja fotod, mis koopias asendatakse külmutatud sisendiga. Kõik muu (kood, stiil) võetakse päris kaustast.
# Fotode asemel on sisendis sünteetilised testpildid: isiklikud fotod ei lähe repo ja test ei sõltu neist.
ANDMED = ["naitajad.json", "andmed", "allikad/*.csv", "kataloog/*.csv", "raportid/*.csv", "raportid/fotod"]
TEKST = {".html", ".css", ".csv", ".json", ".js", ".svg", ".md", ".txt"}
KAIVITA = """
import datetime as real, sys
sys.path[:0] = [".", "raportid"]
import koosta
class Paev(real.date):
    @classmethod
    def today(cls):
        return cls.fromisoformat(sys.argv[1])
class Moodul:
    date, datetime, timedelta = Paev, real.datetime, real.timedelta
koosta.dt = Moodul
koosta.main()
"""


def rasi(p):
    """SHA-256; tekstifailides enne ühtlustatakse reavahetused (Windows kirjutab \\r\\n), et test ei sõltuks arvutist."""
    sisu = p.read_bytes()
    if p.suffix.lower() in TEKST:
        sisu = sisu.replace(b"\r\n", b"\n")
    return hashlib.sha256(sisu).hexdigest()


def ehita(siht):
    """Kopeerib seire koodi kausta siht, paneb andmete asemele külmutatud sisendi ja ehitab raporti."""
    koopia = siht / "tehisaru-seire"
    shutil.copytree(JUUR, koopia, ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache", "tests", "html"))
    for muster in ANDMED:
        for p in koopia.glob(muster):
            shutil.rmtree(p) if p.is_dir() else p.unlink()
    shutil.copytree(SISEND, koopia, dirs_exist_ok=True)
    subprocess.run([sys.executable, "-I", "-c", KAIVITA, KUUPAEV], cwd=koopia, check=True, capture_output=True)
    valja = koopia / "raportid" / "html"
    return {p.relative_to(valja).as_posix(): rasi(p) for p in sorted(valja.rglob("*")) if p.is_file()}


def main():
    with tempfile.TemporaryDirectory() as tmp:
        uued = ehita(Path(tmp))
    vanad = json.loads(VIITED.read_text(encoding="utf-8")) if VIITED.exists() else {"failid": {}}
    erinevad = sorted(f for f in set(uued) | set(vanad["failid"]) if uued.get(f) != vanad["failid"].get(f))
    print("Erinevad viitest:", ", ".join(erinevad) or "mitte ükski")
    if "--uuenda" in sys.argv:
        VIITED.write_text(json.dumps({"kuupaev": KUUPAEV, "failid": uued}, indent=1) + "\n", encoding="utf-8")
        print(f"Kirjutatud {VIITED}")


if __name__ == "__main__":
    main()
