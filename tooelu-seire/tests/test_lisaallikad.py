"""Lisaallikate testid ilma võrguta."""

import datetime as dt
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import lisaallikad as la  # noqa: E402
from kogujad import yhine  # noqa: E402

GDELT_LIST = json.dumps({"articles": [{"url": "https://e.ee/1", "title": "AI  ja töö", "seendate": "20261029T101500Z",
                                       "domain": "e.ee", "language": "Estonian", "sourcecountry": "Estonia"}]}).encode()
GDELT_AEG = json.dumps({"timeline": [{"series": "Volume Intensity",
                                      "data": [{"date": "20261001T000000Z", "value": 0.12}]}]}).encode()
VIKI = json.dumps({"items": [{"timestamp": "2026090100", "views": 51234}]}).encode()
HN = json.dumps({"hits": [{"title": "Show HN: a parser", "url": None, "objectID": "7", "points": 150,
                           "num_comments": 3, "created_at": "2026-05-01T10:00:00Z"},
                          {"title": "AI is eating junior jobs", "url": "https://x.com/a", "objectID": "8",
                           "points": 900, "num_comments": 400, "created_at": "2026-06-01T10:00:00Z"}]}).encode()
PANK = json.dumps({"total": 312, "documents": {
    "D1": {"docdt": "2026-09-30T00:00:00Z", "display_title": "Generative AI and jobs in  Europe", "url": "https://wb/1",
           "docty": "Working Paper"},
    "facets": {"x": 1}}}).encode()


RIIGIKOGU = json.dumps([{"link": "https://stenogrammid.riigikogu.ee/1", "date": "2026-09-16T09:00:00Z", "agendaItems": [
    {"title": "<p>Arupärimine  tööturu kohta</p>", "events": [
        {"type": "SPEECH", "speaker": "A", "date": "2026-09-16T16:39:05Z", "text": "AI ehk tehisintellekti levik", "link": None},
        {"type": "SPEECH", "speaker": "B", "date": "2026-09-16T16:40:00Z", "text": "Tehisaru ja töö", "link": "https://s/2"},
        {"type": "SPEECH", "speaker": "C", "date": "2026-09-16T16:41:00Z", "text": "Eelarve", "link": None},
        {"type": "VOTE", "text": "tehisaru", "link": None}]}]}]).encode()


def test_riigikogu():
    k = la.riigikogu(RIIGIKOGU)
    assert [r["koneleja"] for r in k] == ["A", "B"] and k[0]["url"] == "https://stenogrammid.riigikogu.ee/1"
    assert k[0]["pealkiri"] == "Arupärimine tööturu kohta" and k[0]["avaldatud"] == "2026-09-16" and "text" not in k[0]
    kuud = la.riigikogu_kuud(dt.date(2026, 10, 30), 3)
    assert kuud == [(dt.date(2026, 8, 1), dt.date(2026, 8, 31)), (dt.date(2026, 9, 1), dt.date(2026, 9, 30)),
                    (dt.date(2026, 10, 1), dt.date(2026, 10, 30))]
    assert la.riigikogu_kuud(dt.date(2026, 1, 15), 2)[0] == (dt.date(2025, 12, 1), dt.date(2025, 12, 31))


def test_lahtipakkimine():
    a = la.gdelt_artiklid(GDELT_LIST, "gdelt_eesti")[0]
    assert a["pealkiri"] == "AI ja töö" and a["avaldatud"] == "2026-10-29" and a["domeen"] == "e.ee"
    assert la.gdelt_aegrida(GDELT_AEG) == [{"kuupaev": "2026-10-01", "vaartus": 0.12}]
    assert la.viki(VIKI) == [{"kuu": "2026-09", "vaatamisi": 51234}]
    h = la.hn(HN)
    assert h[0]["punkte"] == 900 and h[0]["teemas"] and h[1]["url"] == "https://news.ycombinator.com/item?id=7"
    kokku, k = la.pank(PANK)
    assert kokku == 312 and len(k) == 1 and k[0]["avaldatud"] == "2026-09-30" and k[0]["teemas"]


def test_aadressid():
    tana = dt.date(2026, 10, 30)
    assert "sourcecountry%3AEN" in la.gdelt_url(la.GDELT_EESTI, "artlist") and "timespan=3months" in la.gdelt_url("x", "y")
    assert la.viki_url("et.wikipedia", "Tehisintellekt", tana).endswith("/monthly/20230101/20261001")
    assert "points%3E100" in la.hn_url(tana)


def test_kaivitus_ei_peatu_vigade_tottu(tmp_path):
    def hae(url):
        if "gdeltproject" in url:
            return GDELT_LIST if "artlist" in url else GDELT_AEG
        if "wikimedia" in url:
            raise yhine.KogujaViga("HTTP 403")
        if "algolia" in url:
            return HN
        if "worldbank" in url:
            return PANK
        if "riigikogu" in url:
            return RIIGIKOGU
        if "nber" in url:
            return b"<rss><channel><item><title>Automation and wages</title><link>https://nber.org/1</link></item></channel></rss>"
        raise yhine.KogujaViga(url + ": HTTP 404")

    valmis = []
    t = la.kaivita(tmp_path, hae=hae, tana=dt.date(2026, 10, 30), paus=0, valmis=lambda n, s: valmis.append(n))["allikad"]
    assert valmis == list(t) and t["gdelt_eesti"]["kokku"] == 1 and t["gdelt_eesti"]["aegrida"]
    assert len(t["vikipeedia"]["vead"]) == len(la.VIKI_ARTIKLID)
    assert t["nber"]["kirjed"][0]["url"] == "https://nber.org/1" and t["nber"]["kokku"] == 1
    assert t["riigikogu"]["kokku"] == 2 * la.RIIGIKOGU_KUID and len(t["riigikogu"]["aegrida"]) == la.RIIGIKOGU_KUID
    assert (tmp_path / "lisaallikad.json").exists()
