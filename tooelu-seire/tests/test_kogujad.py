"""Kogujate testid ilma võrguta: sünteetilised vastused, duplikaadid, versioonid, vigade logi."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import proov  # noqa: E402
from kogujad import allikad, yhine  # noqa: E402

ARXIV = b"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
  <entry>
    <id>http://arxiv.org/abs/2610.01234v2</id>
    <title>Generative AI and
      Occupational Exposure in Europe</title>
    <published>2026-10-01T00:00:00Z</published><updated>2026-10-20T00:00:00Z</updated>
    <arxiv:doi>10.1234/naide.1</arxiv:doi>
  </entry>
  <entry>
    <id>http://arxiv.org/abs/2610.05678v1</id>
    <title>Large Language Models in Hiring: A Field Experiment</title>
    <published>2026-10-10T00:00:00Z</published><updated>2026-10-10T00:00:00Z</updated>
  </entry>
</feed>"""

OPENALEX = json.dumps({"results": [
    {"id": "https://openalex.org/W1", "display_name": "Generative AI and occupational exposure in Europe",
     "type": "article", "doi": "https://doi.org/10.1234/NAIDE.1", "publication_date": "2026-10-15",
     "updated_date": "2026-10-25T00:00:00"},
    {"id": "https://openalex.org/W2", "display_name": "Wages after automation: evidence from administrative data",
     "type": "preprint", "doi": None, "publication_date": "2026-10-12", "updated_date": "2026-10-12T00:00:00"},
]}).encode()

RSS = """<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel>
  <item><title>Tehas koondab 120 töötajat</title><link>https://naide.ee/1</link><guid>g1</guid>
    <pubDate>Wed, 29 Oct 2026 10:00:00 +0200</pubDate></item>
  <item><title>Ettevõte värbab 50 inimest juurde</title><link>https://naide.ee/2</link><guid>g2</guid></item>
  <item><title>Ilm on homme vihmane</title><link>https://naide.ee/3</link><guid>g3</guid></item>
</channel></rss>""".encode()

EUROSTAT = json.dumps({"label": "Enterprises using AI technologies", "updated": "2026-10-15T23:00:00+0200",
                       "value": {"0": 23.4}, "dimension": {"time": {"category": {"index": {"2025": 0}}}}}).encode()


def vale_hae(vastused):
    """Asendab võrgupäringu: aadressi algus -> vastus või viga."""
    def hae(url):
        for algus, vastus in vastused.items():
            if url.startswith(algus):
                if isinstance(vastus, Exception):
                    raise vastus
                return vastus
        raise yhine.KogujaViga(f"{url}: testis puudub")
    return hae


KOIK = {allikad.ARXIV_URL: ARXIV, allikad.OPENALEX_URL: OPENALEX, allikad.ERR_URL: RSS,
        "https://ec.europa.eu/eurostat": EUROSTAT}


def test_arxiv_versioon_ja_pealkiri():
    k = allikad.arxiv_kirjed(ARXIV)
    assert [x["voti"] for x in k] == ["2610.01234", "2610.05678"]
    assert k[0]["versioon"] == 2 and k[1]["versioon"] == 1
    assert k[0]["pealkiri"] == "Generative AI and Occupational Exposure in Europe"
    assert k[0]["doi"] == "10.1234/naide.1"


def test_openalex_liik():
    k = allikad.openalex_kirjed(OPENALEX)
    assert [x["voti"] for x in k] == ["W1", "W2"]
    assert [x["allika_liik"] for x in k] == ["artikkel", "eeltrukk"]


def test_rss_kahepoolne_filter():
    k = allikad.rss_kirjed(RSS)
    assert [(x["voti"], x["suund"]) for x in k] == [("g1", "kadu"), ("g2", "loomine")]


def test_tyhi_voog_on_viga_aga_sobimatud_kirjed_mitte(tmp_path):
    tyhi = b'<?xml version="1.0"?><rss version="2.0"><channel></channel></rss>'
    k = proov.kaivita(tmp_path / "a", hae=vale_hae({**KOIK, allikad.ERR_URL: tyhi}))
    assert k["allikad"]["err"]["olek"] == "viga"
    k = proov.kaivita(tmp_path / "b", hae=vale_hae(KOIK))
    assert k["allikad"]["err"] == {**k["allikad"]["err"], "olek": "ok", "voos": 3, "kirjeid": 2}


def test_eurostat_vintage():
    k = allikad.eurostat_kirje("isoc_eb_ain2", EUROSTAT)
    assert k["uuendatud"] == "2026-10-15T23:00:00+0200" and k["viimane_periood"] == "2025"


def test_suletud_andmestik_saab_markuse():
    sisu = EUROSTAT.replace(b"Enterprises using AI technologies", b"Job vacancy statistics (2001-2025)")
    assert "suletud" in allikad.eurostat_kirje("jvs_q_nace2", sisu)["markus"]
    assert "markus" not in allikad.eurostat_kirje("isoc_eb_ain2", EUROSTAT)


def test_duplikaat_doi_ja_pealkirja_jargi():
    k = allikad.arxiv_kirjed(ARXIV) + allikad.openalex_kirjed(OPENALEX)
    uued, versioonid, dup = yhine.eralda(k)
    assert len(uued) == 3 and not versioonid
    assert dup[0]["voti"] == "W1" and dup[0]["duplikaat"] == "arxiv:2610.01234"


def test_uus_versioon_eelmise_kaivituse_jargi():
    vana = allikad.arxiv_kirjed(ARXIV.replace(b"01234v2", b"01234v1"))
    uued, versioonid, dup = yhine.eralda(allikad.arxiv_kirjed(ARXIV), vana)
    assert not uued and len(dup) == 1
    assert versioonid[0]["voti"] == "2610.01234" and versioonid[0]["eelmine_versioon"] == 1


def test_openalexi_uuendusaeg_ei_ole_uus_versioon():
    vana = allikad.openalex_kirjed(OPENALEX.replace(b"2026-10-25T00", b"2026-10-20T00"))
    _, versioonid, dup = yhine.eralda(allikad.openalex_kirjed(OPENALEX), vana)
    assert not versioonid and len(dup) == 2


def test_eurostat_uus_uuendus_on_versioon():
    vana = [allikad.eurostat_kirje("isoc_eb_ain2", EUROSTAT.replace(b"2026-10-15", b"2026-04-01"))]
    _, versioonid, _ = yhine.eralda([allikad.eurostat_kirje("isoc_eb_ain2", EUROSTAT)], vana)
    assert len(versioonid) == 1


def test_proov_kirjutab_ainult_valjundisse_ja_logib_vead(tmp_path):
    vastused = dict(KOIK)
    vastused[allikad.ERR_URL] = yhine.KogujaViga("https://www.err.ee/rss: HTTP 403")
    k = proov.kaivita(tmp_path / "v", hae=vale_hae(vastused))
    assert k["toimis"] == len(k["allikad"]) - 1
    vead = yhine.loe_jsonl(tmp_path / "v" / "vead.jsonl")
    assert [v["allikas"] for v in vead] == ["err"] and "403" in vead[0]["viga"]
    assert sorted(p.name for p in (tmp_path / "v").iterdir()) == [
        "duplikaadid.jsonl", "kirjed.jsonl", "koik.jsonl", "kokkuvote.md", "nahtud.jsonl", "olek.json", "vead.jsonl",
        "versioonid.jsonl"]
    assert "KONTROLLIMATA" in (tmp_path / "v" / "kokkuvote.md").read_text(encoding="utf-8")


def test_versioon_vorreldakse_viimase_seisuga():
    vanem = allikad.eurostat_kirje("isoc_eb_ain2", EUROSTAT.replace(b"2026-10-15", b"2026-04-01"))
    viimane = allikad.eurostat_kirje("isoc_eb_ain2", EUROSTAT)
    _, versioonid, dup = yhine.eralda([viimane], [vanem, viimane])
    assert not versioonid and len(dup) == 1
    assert yhine.koonda([vanem], [viimane]) == [viimane]


def test_teine_kaivitus_leiab_duplikaadid(tmp_path):
    proov.kaivita(tmp_path / "a", hae=vale_hae(KOIK))
    assert len(yhine.loe_jsonl(tmp_path / "a" / "nahtud.jsonl")) == len(yhine.loe_jsonl(tmp_path / "a" / "koik.jsonl"))
    k = proov.kaivita(tmp_path / "b", eelmine=[tmp_path / "a" / "nahtud.jsonl"], hae=vale_hae(KOIK))
    assert k["uusi"] == 0 and k["uusi_versioone"] == 0 and k["duplikaate"] > 0


def test_koik_allikad_maha_annab_koodi_1(tmp_path, monkeypatch):
    monkeypatch.setattr(yhine, "hae", vale_hae({}))
    assert proov.main(["--valjund", str(tmp_path / "v")]) == 1


@pytest.mark.parametrize("url", ["https://api.openalex.org/works?search=x&api_key=SALAJANE123&per-page=5",
                                 "https://api.openalex.org/works?mailto=nimi@naide.ee"])
def test_votmed_ei_satu_logisse(url):
    assert "SALAJANE" not in yhine.peida_votmed(url) and "@" not in yhine.peida_votmed(url)
