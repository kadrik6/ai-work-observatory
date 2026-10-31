"""Lehe „Tehisaru ja töö“ generaator: ehitub repo failidest ja näitab parandatud kohti õigesti."""
import os
import subprocess
import sys
from pathlib import Path

LEHT = Path(__file__).resolve().parents[1] / "leht"


def ehita(tmp_path):
    env = dict(os.environ, TOOELU_TOO=str(tmp_path))
    subprocess.run([sys.executable, str(LEHT / "tee_leiud.py")], check=True, env=env, capture_output=True)
    return (tmp_path / "leht-mall.html").read_text(encoding="utf-8")


def test_leht_ehitub_ja_koik_kaardid_on_olemas(tmp_path):
    s = ehita(tmp_path)
    for kysimus in ("Kas tehisaru teeb töö kiiremaks?", "Kas töökohti kaob?", "Mida töökorralduse muutmine tähendab",
                    "Kuidas töökorralduse muutust paremini mõõta?", "Kas tehisaru on Eesti koondamiste põhjus?",
                    "Kui suur on töötus tulevikus?"):
        assert kysimus in s, kysimus


def test_eli_keskmine_on_umardatud_pool_yles(tmp_path):
    # Eurostati väärtus 19,95 näidatakse 20,0, nagu seire ja „Tehisaru 2027“ lehel.
    s = ehita(tmp_path)
    assert "EL keskmisest veidi eespool (20,0%)" in s
    assert "(19,9%)" not in s


def test_2026_tulp_on_eraldi_reana(tmp_path):
    s = ehita(tmp_path)
    assert "ts-col-uus" in s and "ei ole Eurostati reaga võrreldav" in s
    assert "kaks aastat varem iga seitsmes" not in s


def test_mallis_ja_eurostati_failis_pole_kandidaate():
    # Kandidaatide pealkirjad jäävad käivituse artefakti (Kadri otsus 30.10), mitte repo.
    for f in ("mall.html", "eurostat_isoc_eb_ai_2026-10-31.json"):
        assert "openalex.org/W" not in (LEHT / f).read_text(encoding="utf-8"), f
