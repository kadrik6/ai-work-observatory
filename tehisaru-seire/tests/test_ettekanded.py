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
    assert ids == ["ut-dss", "latitude59", "startup-day", "arenguseire", "oecd", "oecd-ai", "ilo", "stanford-hai", "uttv", "tds", "lex-fridman", "mindscape"]
    for k in K["kanalid"]:
        allikaid = [x for x in ("leht", "kanal", "esitusloend", "kasutaja", "uttv_alates", "rss") if k.get(x)]
        assert len(allikaid) == 1, k["id"]
        assert k.get("miks") and k.get("nimi")
        if k.get("kanal"):
            assert re.fullmatch(r"UC[\w-]{22}", k["kanal"])


def test_voog_ja_teemafilter():
    rr = L.voog(RSS, "oecd")
    assert [r["id"] for r in rr] == ["AAAAAAAAAAA", "BBBBBBBBBBB", "CCCCCCCCCCC"]
    assert rr[0]["avaldatud"] == "2026-11-01" and rr[0]["url"].endswith("v=AAAAAAAAAAA")
    assert [L.teemas(r) for r in rr] == [True, False, True]


def test_sool_jatab_tehisaru_ja_viskab_uldise_too_valja():
    """Kadri 27.11.2026: liiga palju teemaväliseid kandidaate. Üldsõnad (work, jobs, skills, digital) üksi ei piisa."""
    sees = ["Artificial intelligence and creative professions: threats or opportunities?",
            "Lessons from 25 years of crowd (and A.I.) forecasting",
            "From results to the next cycle: Just transition and human capacity in the AI era",
            "TDS2026 - Building the agentic nation: what governments need to get right first",
            "Tehisintellekt juristi töölaual", "AI-põhine klienditeenindus", "The Future of Work in Africa Starts Now"]
    valjas = ["Roadmaps for more and better jobs through sustainable investment",
              "How productivity ecosystems can drive decent work in Viet Nam?",
              "What workers' organizations can do to support quality apprenticeships",
              "XIV Pärandtehnoloogia konverents", "Kogukonna- ja huvijuhtide üliõpilastööde konverents 2026 I osa"]
    assert all(L.teemas({"pealkiri": t}) for t in sees)
    assert not any(L.teemas({"pealkiri": t}) for t in valjas)


def test_kursuse_tunnid_ja_tseremooniad_ei_tule_ka_teemakanalilt():
    for t in ["Programmeerimine - Nädal 13 - 25.11.2026 - objektorienteeritud programmeerimine.", "A&A Tasemetöö 2 kordamine",
              "Tartu Ülikooli teenetemärkide üleandmine 2026", "Tallinn Digital Summit 2026 I Official Aftermovie",
              "Best Bits from the Tallinn Digital Summit | TDS 2026", "TDS2026 - Closing Ceremony",
              "Doctoral defence: Tauri Tölpt", "Behind the scenes - Why languages matter at the OECD (English)"]:
        assert L.hinda({"pealkiri": t, "filter": False}) == "teemaväline", t
    assert L.hinda({"pealkiri": "Teachers and technology | TDS 2026", "filter": False}) == "uus"  # teemakanal
    assert L.hinda({"pealkiri": "Teachers and technology | TDS 2026", "filter": True}) == "teemaväline"


def test_soelu_uuesti_muudab_ainult_ootel_kandidaate():
    kanalid = [{"id": "tds", "filter": False}, {"id": "ilo"}]
    k = [{"id": "a", "allikas": "ilo", "pealkiri": "Decent Work in Action", "olek": "uus"},
         {"id": "g", "allikas": "ilo", "pealkiri": "Decent Work in Action", "olek": "uus", "leitud": "2026-11-27"},
         {"id": "b", "allikas": "ilo", "pealkiri": "Artificial intelligence and creative professions", "olek": "uus"},
         {"id": "c", "allikas": "tds", "pealkiri": "Rules and innovation | TDS 2026", "olek": "uus"},
         {"id": "d", "allikas": "tds", "pealkiri": "TDS2026 - Closing Ceremony", "olek": "uus"},
         {"id": "e", "allikas": "ilo", "pealkiri": "Decent Work in Action", "olek": "vana"},
         {"id": "f", "allikas": "uttv", "pealkiri": "Astronoomialoeng:&nbsp;&bdquo;Tähe teekond&quot;", "olek": "uus"}]
    assert L.soelu_uuesti(k, kanalid, dt.date(2026, 11, 27)) == ["a", "d", "f"]
    assert [x["olek"] for x in k] == ["teemaväline", "uus", "uus", "uus", "teemaväline", "vana", "teemaväline"]  # g: uue sõelaga leitud
    assert L.soelu_uuesti(k, kanalid, dt.date(2026, 11, 28)) == []
    assert k[0]["soelutud"] == "2026-11-27" and "soelutud" not in k[1]


PODCAST_RSS = """<?xml version="1.0" encoding="UTF-8"?><rss version="2.0" xmlns:content="http://purl.org/rss/1.0/modules/content/"><channel>
<item><title>#505 &#8211; Jane Doe: AI Agents and the Future of Programming</title>
 <link>https://lexfridman.com/jane-doe/?utm_source=rss&amp;utm_medium=rss</link><pubDate>Tue, 24 Nov 2026 20:00:00 +0000</pubDate>
 <description><![CDATA[<p>Jane builds coding agents.</p><p><b>Transcript:</b><br /><a href="https://lexfridman.com/jane-doe-transcript">x</a></p>]]></description></item>
<item><title>#504 &#8211; Russia-Ukraine War</title><link>https://lexfridman.com/ukraine-war/</link><pubDate>Tue, 10 Nov 2026 23:52:44 +0000</pubDate>
 <description><![CDATA[<p>Military analysts.</p><p>Thank you for listening. SPONSORS: Fin: AI agent for customer service.</p>]]></description></item>
<item><title>Blog post</title><link>https://preposterousuniverse.com/blog/2026/11/01/x/</link><pubDate>Sun, 01 Nov 2026 10:00:00 +0000</pubDate></item>
</channel></rss>"""


def test_podcasti_voog_ja_transkriptsioon():
    """Kadri 27.11.2026: podcastid tulevad ise. Lex Fridmani ja Mindscape'i osadel on avalik tekst, Kadri arvutit pole vaja."""
    rr = L.podcasti_voog(PODCAST_RSS, "lex-fridman")
    assert [r["id"] for r in rr] == ["lex-fridman-jane-doe", "lex-fridman-ukraine-war", "lex-fridman-x"]
    assert rr[0]["url"] == "https://lexfridman.com/jane-doe/" and rr[0]["avaldatud"] == "2026-11-24"
    assert rr[0]["pealkiri"] == "#505 – Jane Doe: AI Agents and the Future of Programming"
    assert rr[0]["tekst_url"] == "https://lexfridman.com/jane-doe-transcript"
    assert rr[1]["tekst_url"] == rr[1]["url"]
    assert [L.teemas(r) for r in rr[:2]] == [True, False]  # sponsori „AI agent“ ei tee osa teemaks
    assert L.hinda({"pealkiri": "AMA | November 2026", "filter": False}) == "teemaväline"
    assert [r["id"] for r in L.podcasti_voog(PODCAST_RSS, "mindscape", tee="/podcast/")] == []
    for r in rr:
        r["filter"] = True
    k = []
    assert L.uuenda(k, rr, {"https://lexfridman.com/ukraine-war/"}, dt.date(2026, 11, 27), esimene=False) == ["lex-fridman-jane-doe"]
    assert k[0]["tekst_url"].endswith("-transcript") and len(k) == 2  # tuntud osa (saidil) ei tule kandidaadiks
    assert L.vajab_teksti_teade(k).startswith("Kõigil")


def test_tuntud_podcasti_osa_lehe_jargi(tmp_path, monkeypatch):
    f = tmp_path / "ettekanded.json"
    f.write_text(json.dumps({"ettekanded": [{"id": "lex-503", "uritus_url": "https://lexfridman.com/math-ai-crisis/"}]}), encoding="utf-8")
    monkeypatch.setattr(L, "TUNTUD", f)
    assert L.tuntud_videod() == {"lex-503", "https://lexfridman.com/math-ai-crisis/"}


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


UTTV_LEHT = """<html><body><ul><li>Avaleht</li><li>Videod</li></ul><h4>Eesti Õigusteadlaste päevad 39 | Tehisintellekt juristi töölaual</h4>
<p>Klipi teostus: UTTV<br>24.09.2026<br>176 vaatamist</p><p>Juristid tegutsevad üha enam keskkonnas, kus tehisintellekt ...</p></body></html>"""


def test_uttv_video_ja_uued():
    """Kadri 12.11.2026: Tartu Ülikooli UTTV videod ettekannete otsingusse (RSS-i pole, loeme video lehti id järgi)."""
    r = L.uttv_video(UTTV_LEHT, 43702)
    assert r["id"] == "uttv-43702" and r["avaldatud"] == "2026-09-24" and r["url"].endswith("naita?id=43702")
    assert r["pealkiri"].startswith("Eesti Õigusteadlaste päevad 39") and L.teemas(r)
    assert L.uttv_video("<html><body>Otsingu tulemused</body></html>", 1) is None
    lehed = {43703: UTTV_LEHT, 43705: UTTV_LEHT}
    read, suurim = L.uttv_uued(43702, get=lambda u: lehed[int(u.rsplit("=", 1)[1])], samm=10, tuhi=3)
    assert [x["id"] for x in read] == ["uttv-43703", "uttv-43705"] and suurim == 43705  # tühjad lehed vahel ei peata kohe
