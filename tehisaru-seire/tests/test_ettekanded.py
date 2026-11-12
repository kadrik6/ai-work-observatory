"""Ettekannete igapäevane otsing (Kadri 8.11.2026): kanalite loend, RSS-i lugemine ja teemafilter ilma võrguta."""
import datetime as dt
import importlib.util
import json
import re
from pathlib import Path

JUUR = Path(__file__).resolve().parents[1]
_s = importlib.util.spec_from_file_location("lae_ettekanded", JUUR / "sait" / "lae_ettekanded.py")
L = importlib.util.module_from_spec(_s)
_s.loader.exec_module(L)

RSS = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns:yt="http://www.youtube.com/xml/schemas/2015" xmlns:media="http://search.yahoo.com/mrss/" xmlns="http://www.w3.org/2005/Atom">
 <entry><yt:videoId>AAAAAAAAAAA</yt:videoId><title>Generative AI and the future of work</title><published>2026-11-01T10:00:00+00:00</published>
  <media:group><media:description>Panel on jobs</media:description></media:group></entry>
 <entry><yt:videoId>BBBBBBBBBBB</yt:videoId><title>Ocean policy outlook</title><published>2026-11-02T10:00:00+00:00</published>
  <media:group><media:description>Fisheries</media:description></media:group></entry>
 <entry><yt:videoId>CCCCCCCCCCC</yt:videoId><title>Tehisaru avalikus sektoris</title><published>2024-01-02T10:00:00+00:00</published></entry>
</feed>"""


def test_kanalite_loend_on_kadri_valik():
    K = json.loads((JUUR / "kataloog" / "ettekannete-kanalid.json").read_text(encoding="utf-8"))
    ids = [k["id"] for k in K["kanalid"]]
    assert ids == ["ut-dss", "latitude59", "startup-day", "arenguseire", "oecd", "oecd-ai", "ilo", "stanford-hai", "tds"]
    for k in K["kanalid"]:
        allikaid = [x for x in ("leht", "kanal", "esitusloend", "kasutaja") if k.get(x)]
        assert len(allikaid) == 1, k["id"]
        assert k.get("miks") and k.get("nimi")
        if k.get("kanal"):
            assert re.fullmatch(r"UC[\w-]{22}", k["kanal"])


def test_voog_ja_teemafilter():
    rr = L.voog(RSS, "oecd")
    assert [r["id"] for r in rr] == ["AAAAAAAAAAA", "BBBBBBBBBBB", "CCCCCCCCCCC"]
    assert rr[0]["avaldatud"] == "2026-11-01" and rr[0]["url"].endswith("v=AAAAAAAAAAA")
    assert [L.teemas(r) for r in rr] == [True, False, True]


def test_uued_kandidaadid_vanad_ja_tuntud_valja():
    tana = dt.date(2026, 11, 8)
    rr = L.voog(RSS, "oecd") + [dict(L.voog(RSS, "x")[0], id="DDDDDDDDDDD")]
    for r in rr:
        r["filter"] = True
    k = []
    uued = L.uuenda(k, rr, {"DDDDDDDDDDD"}, tana, esimene=False)
    assert uued == ["AAAAAAAAAAA"]
    assert {x["id"]: x["olek"] for x in k} == {"AAAAAAAAAAA": "uus", "BBBBBBBBBBB": "teemaväline", "CCCCCCCCCCC": "vana"}
    assert L.uuenda(k, rr, set(), tana, esimene=False) == ["DDDDDDDDDDD"]  # juba nähtud ei tule uuesti
    k2 = []
    assert L.uuenda(k2, rr, set(), tana, esimene=True) == [] and {x["olek"] for x in k2} == {"vana"}


def test_seminarilehe_lingid_ja_kanali_id():
    html = '<a href="https://youtu.be/jmSmB9Sd5CI">x</a><a href="https://www.youtube.com/watch?v=-s_-paRRbeo">y</a><a href="https://youtu.be/jmSmB9Sd5CI?si=1">z</a>'
    assert [r["id"] for r in L.lehe_videod(html, "ut-dss")] == ["jmSmB9Sd5CI", "-s_-paRRbeo"]
    leht = '<link rel="canonical" href="https://www.youtube.com/channel/UCVSEYuF5-xS99L8vhVfn34A">'
    assert L.kanali_id("@x", get=lambda u: leht) == "UCVSEYuF5-xS99L8vhVfn34A"


def test_tuntud_ettekanded_ei_tule_kandidaadiks(tmp_path, monkeypatch):
    f = tmp_path / "ettekanded.json"
    f.write_text(json.dumps({"ettekanded": [{"video": "https://youtu.be/V9qubnxvJV0?t=1076"}]}), encoding="utf-8")
    monkeypatch.setattr(L, "TUNTUD", f)
    assert L.tuntud_videod() == {"V9qubnxvJV0"}
