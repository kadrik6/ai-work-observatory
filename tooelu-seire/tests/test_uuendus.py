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
    assert "otsivad praegu 1 inimest" in h
    assert "0 firmat 1-st ei otsi praegu kedagi." in h
    # A otsib müüjat, aga koondab IT-d: teised ametid. Eesti arv puudub mõlemal.
    assert "A otsib teisi ameteid kui need, mida koondab." in h
    assert "Eesti koondatavate arv pole teada: A, B." in h
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


def _tulemus(tmp_path, kuulutused, total):
    """TinyFish fetch_content tulemus: JSON markdowni põgendustega tekstina."""
    t = json.dumps({"total": total, "vacancies": kuulutused}).replace("_", "\\_")
    f = tmp_path / "tulemus.json"
    f.write_text(json.dumps({"results": [{"text": t}]}))
    return f


def test_ai_tood_liigitab_ja_eraldab_firma_uldlause(tmp_path):
    uld = "Perks may differ depending on your location and role{} At Bolt, using AI daily is a baseline expectation."
    k = [{"id": 1, "positionTitle": "Senior AI Engineer", "employerName": "X", "countyId": 67, "publishDate": "2026-11-07T10:00"},
         {"id": 2, "positionTitle": "Andmeinsener", "employerName": "Y", "countyId": 78, "publishDate": "2026-11-01"},
         {"id": 3, "positionTitle": "Data communication specialist", "employerName": "Y"},
         {"id": 4, "positionTitle": "Raamatupidaja", "employerName": "Z", "positionContent": "Oskus kasutada tehisintellekti tööriistu."},
         {"id": 5, "positionTitle": "Kassihoidja", "employerName": "Z", "positionContent": "Kodukülastus, ML Capital Properties."},
         {"id": 6, "positionTitle": "Sales Manager", "employerName": "Bolt", "positionContent": uld.format("")},
         {"id": 7, "positionTitle": "Driver Ops", "employerName": "Bolt", "positionContent": uld.format(".")},
         {"id": 8, "positionTitle": "Designer", "employerName": "Bolt", "positionContent": uld.format("") + " You use AI tools to prototype."}]
    env = dict(os.environ, UUDISED=str(tmp_path))
    r = subprocess.run([sys.executable, "-I", str(UUENDUS / "ai_tood.py"), str(_tulemus(tmp_path, k, 8))],
                       env=env, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    d = json.loads((tmp_path / "ai_tookuulutused.json").read_text())
    ruhm = {x["id"]: x["ruhm"] for x in d["kuulutused"]}
    # 3 = "data communication", 5 = firmanimi: ei ole AI- ega andmetöö.
    assert ruhm == {1: "ai_amet", 2: "andmeamet", 4: "ai_oskus", 6: "ai_firma_noue", 7: "ai_firma_noue", 8: "ai_oskus"}
    assert d["kuulutusi_kokku"] == 8 and d["portaali_kokku"] == 8
    assert d["kuulutused"][0].keys() == {"id", "ruhm", "pealkiri", "tooandja", "maakond", "kaugtoo", "avaldatud", "url", "uus"}
    assert "positionContent" not in json.dumps(d)
    # Teisel käivitusel on kõik juba nähtud.
    subprocess.run([sys.executable, "-I", str(UUENDUS / "ai_tood.py"), str(_tulemus(tmp_path, k, 8))], env=env, check=True)
    d = json.loads((tmp_path / "ai_tookuulutused.json").read_text())
    assert all(g["uusi"] == 0 for g in d["ruhmad"].values())
