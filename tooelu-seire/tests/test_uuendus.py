"""Igapäevase uuenduse kood (tooelu-seire/uuendus): logist andmete kokkupanek ja osa „Mis toimub“ plokid ilma võrguta."""

import base64
import gzip
import importlib
import json
import os
import subprocess
import sys
from pathlib import Path

UUENDUS = Path(__file__).resolve().parents[1] / "uuendus"


def test_hanked_logist_paneb_tykid_kokku(tmp_path):
    leht = {"aastad": [{"aasta": 2026, "ai_andmed": 3, "ai_marksonaga": 2}], "loend": [{"id": "x", "ai": True}]}
    b64 = base64.b64encode(gzip.compress(json.dumps(leht).encode())).decode()
    pool = len(b64) // 2
    log = tmp_path / "log.txt"
    # Tükid tulevad logis vales järjekorras ja muu teksti vahel.
    log.write_text(json.dumps({"logs_content": f"x\nLEHT 1 2 {b64[pool:]}\nmuu rida\nLEHT 0 2 {b64[:pool]}\n"}))
    env = dict(os.environ, SEIRE_UUENDUS=str(tmp_path / "andmed"))
    r = subprocess.run([sys.executable, str(UUENDUS / "hanked_logist.py"), str(log), "123"], env=env, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert json.loads((tmp_path / "andmed" / "hanked" / "leht.json").read_text()) == leht
    assert json.loads((tmp_path / "andmed" / "hanked" / "seis.json").read_text())["run"] == "123"


def test_hanked_logist_puuduv_tykk_on_viga(tmp_path):
    log = tmp_path / "log.txt"
    log.write_text("LEHT 0 2 QUJD\n")
    env = dict(os.environ, SEIRE_UUENDUS=str(tmp_path))
    r = subprocess.run([sys.executable, str(UUENDUS / "hanked_logist.py"), str(log), "1"], env=env, capture_output=True, text=True)
    assert r.returncode != 0 and "puuduvad" in (r.stderr + r.stdout)


def _lisalehed(tmp_path, monkeypatch):
    monkeypatch.setenv("UUDISED", str(tmp_path / "uudised"))
    monkeypatch.setenv("SEIRE_UUENDUS", str(tmp_path / "seire"))
    monkeypatch.syspath_prepend(str(UUENDUS))
    sys.modules.pop("lisalehed", None)
    return importlib.import_module("lisalehed")


def test_koondajate_plokk_loeb_kuulutused_ja_jatab_kontrollimata_valja(tmp_path, monkeypatch):
    m = _lisalehed(tmp_path, monkeypatch)
    (tmp_path / "uudised").mkdir()
    (tmp_path / "uudised" / "koondajad.json").write_text(json.dumps({
        "ametiliigid": ["IT ja andmed", "müük ja klienditeenindus", "muu"],
        "firmad": {
            "A": {"sektor": "pank", "firma_liik": "x", "omand": "välisomanikuga", "kaotatud": ["IT ja andmed"],
                  "kaotatud_tekst": "IT", "kaotatud_allikas": "https://a",
                  "otsib": {"kontrollitud": "2026-11-05", "ametid": [{"nimi": "Müügijuht", "liik": "müük ja klienditeenindus"}],
                            "tekst": "1 kuulutus.", "url": "https://a/jobs"}},
            "B": {"sektor": "kultuur", "firma_liik": "y", "omand": "kultuuriasutus", "kaotatud": ["muu"],
                  "kaotatud_tekst": "3", "kaotatud_allikas": "https://b",
                  "otsib": {"kontrollitud": None, "ametid": [], "tekst": "Ei kontrollitud.", "url": None}}}}))
    koond = [{"ettevote": "A"}, {"ettevote": "B"}, {"ettevote": "C"}]
    h = m.koondajate_plokk(koond)
    assert "otsivad praegu kokku 1 inimest, 0 firmat ei otsi kedagi" in h
    assert "Taustaandmeid pole veel: C" in h
    assert "Müügijuht" in h


def test_hangete_plokk_jaotab_tehisaru_ja_andmed(tmp_path, monkeypatch):
    m = _lisalehed(tmp_path, monkeypatch)
    hk = tmp_path / "seire" / "hanked"
    hk.mkdir(parents=True)
    aastad = [{"aasta": a, "ai_andmed": n, "ai_marksonaga": ai, "ai_andmed_osakaal": 0.5}
              for a, n, ai in ((2024, 10, 2), (2025, 12, 4), (2026, 9, 5))]
    loend = [{"id": "1", "a": 2026, "kp": "2026-10-01", "t": "Tehisaru", "h": "Amet", "ai": True, "v": 1000},
             {"id": "2", "a": 2026, "kp": "2026-09-01", "t": "Andmeladu", "h": "Amet", "ai": False}]
    (hk / "leht.json").write_text(json.dumps({"aastad": aastad, "loend": loend, "hankijad_top": [["Amet", 2]],
                                              "hindamine": {}}))
    (hk / "seis.json").write_text(json.dumps({"run": "1", "kuupaev": "2026-11-05"}))
    h = m.hangete_plokk()
    # 2026: tehisaru 5, andmed 9 - 5 = 4; varem oli andmeid alati rohkem.
    assert "esimest korda rohkem kui andmehankeid: 5 ja 4" in h
    assert 'data-loend="hanked-ai"' in h and 'data-loend="hanked-andmed"' in h
