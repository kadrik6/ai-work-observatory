"""Valdkonna ülevaate testid ilma võrguta."""

import datetime as dt
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import analyys  # noqa: E402
from kogujad import yhine  # noqa: E402

GRUPID = json.dumps({"meta": {"count": 30}, "group_by": [
    {"key": "2025", "key_display_name": "2025", "count": 20},
    {"key": "https://openalex.org/S1", "key_display_name": "Labour Economics", "count": 10},
    {"key": "unknown", "key_display_name": "unknown", "count": 4},
]}).encode()

TOOD = json.dumps({"meta": {"count": 1}, "results": [
    {"id": "https://openalex.org/W9", "display_name": "GenAI and  wages", "publication_date": "2024-05-01",
     "cited_by_count": 412, "type": "article", "doi": "https://doi.org/10.1/x", "is_retracted": False,
     "primary_location": {"source": {"display_name": "Science", "type": "journal", "is_core": True}}},
]}).encode()


def vale_hae(url):
    if "group_by" in url:
        return GRUPID
    if "cited_by_count%3A0" in url:
        raise yhine.KogujaViga("https://api.openalex.org/works: HTTP 503")
    return TOOD


def test_grupid_ja_tood():
    g = analyys.grupid(GRUPID)
    assert [r["voti"] for r in g] == ["2025", "S1"]
    t = analyys.tood(TOOD)[0]
    assert t["pealkiri"] == "GenAI and wages" and t["viiteid"] == 412
    assert t["doi"] == "10.1/x" and t["kanal"] == "Science" and t["kanali_liik"] == "journal" and t["tuum"] is True


def test_teema_paring_on_kitsendus():
    assert analyys.paring("wages").startswith(f"({analyys.PARING}) AND (wages)")
    osad = analyys.osad(dt.date(2026, 10, 30))
    assert {f"teema_{k}" for k in analyys.TEEMAD} <= set(osad)
    assert "publication_year%3A2016-2026" in osad["aastad"][0]
    assert 'NOT ("job shop" OR scheduling)' in analyys.PARING
    assert "authorships.countries%3AEE" in osad["eesti_autorid_aastad"][0] and "language%3Aet" in osad["eesti_keeles"][0]
    assert "group_by=primary_topic.field.id" in osad["valdkonnad"][0] and "publication_year%3A2026%2C" in osad["valdkonnad"][0]
    assert "publication_year%3A2025%2C" in osad["valdkonnad_eelmine"][0]


def test_kaivitus_logib_vea_ja_jatkab(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENALEX_API_KEY", "SALAJANE123")
    t = analyys.kaivita(tmp_path, hae=vale_hae, tana=dt.date(2026, 10, 30), paus=0)
    assert set(t["vead"]) == {"vanad_viiteta"} and "SALAJANE" not in json.dumps(t)
    assert t["osad"]["enim_tsiteeritud"][0]["viiteid"] == 412
    assert json.loads((tmp_path / "analyys.json").read_text(encoding="utf-8"))["osad"]["aastad"]


def test_koik_maha_annab_koodi_1(tmp_path, monkeypatch):
    def maha(url):
        raise yhine.KogujaViga("HTTP 403")
    monkeypatch.setattr(yhine, "hae", maha)
    monkeypatch.setattr(analyys.time, "sleep", lambda s: None)
    assert analyys.main(["--valjund", str(tmp_path)]) == 1
