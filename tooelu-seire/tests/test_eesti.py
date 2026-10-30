"""Eesti allikate testid ilma võrguta."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import eesti  # noqa: E402
from kogujad import yhine  # noqa: E402

RSS = """<?xml version="1.0"?><rss><channel>
<item><title>Raport: tehisaru  kasutus jääb pinnapealseks</title><link>https://n.ee/1</link>
<pubDate>Sun, 21 Jun 2026 10:00:00 +0000</pubDate><description>Tootlikkus</description></item>
<item><title>Konverents</title><link>https://n.ee/2</link><pubDate>Mon, 03 Aug 2026 10:00:00 +0000</pubDate>
<description>Arutame, mida AI teeb tööturuga</description></item>
<item><title>Ilm on ilus</title><link>https://n.ee/3</link><pubDate>Tue, 04 Aug 2026 10:00:00 +0000</pubDate></item>
</channel></rss>""".encode()

DSPACE = json.dumps({"_embedded": {"searchResult": {"page": {"totalElements": 214}, "_embedded": {"objects": [
    {"_embedded": {"indexableObject": {"name": "Tehisintellekt avalikus sektoris", "handle": "10062/1",
                                       "metadata": {"dc.date.issued": [{"value": "2026"}],
                                                    "dc.type": [{"value": "Thesis"}]}}}},
]}}}}).encode()


def test_rss_filter_ja_teemas():
    uudised = eesti.rss(RSS, "novaator", "uudis")
    assert [k["url"] for k in uudised] == ["https://n.ee/1", "https://n.ee/2"]
    assert uudised[0]["avaldatud"] == "2026-06-21" and uudised[0]["pealkiri"] == "Raport: tehisaru kasutus jääb pinnapealseks"
    assert uudised[1]["reegel"] == "ai"
    # Otsingu tulemus jääb alles, aga teemaväline on märgitud.
    otsing = eesti.rss(RSS, "arenguseire", "mõttekoda", reegel="tehisaru")
    assert len(otsing) == 3 and [k["teemas"] for k in otsing] == [True, True, False]


def test_dspace():
    kokku, kirjed = eesti.dspace(DSPACE, "https://dspace.ut.ee/", "tu_dspace", "lõputöö")
    assert kokku == 214 and kirjed[0]["url"] == "https://dspace.ut.ee/handle/10062/1"
    assert kirjed[0]["liik"] == "Thesis" and kirjed[0]["avaldatud"] == "2026"
    assert "query=" in eesti.dspace_url("https://dspace.ut.ee/") and "dc.date.issued%2CDESC" in eesti.dspace_url("https://x/")


def test_wp_lehed_ja_404_on_lopp():
    kysitud = []

    def hae(url):
        kysitud.append(url)
        if "paged=2" in url:
            raise yhine.KogujaViga(url + ": HTTP 404")
        # 10 kirjet = täis leht, seega küsitakse järgmist.
        return RSS.replace(b"</channel>", b"".join(
            b"<item><title>t%d</title><link>https://n.ee/x%d</link></item>" % (i, i) for i in range(7)) + b"</channel>")

    t = eesti.allikas("arenguseire", {"liik": "mõttekoda", "wp": "https://arenguseire.ee/"}, hae, paus=0)
    assert t["vead"] == [] and len(kysitud) == 2 * len(eesti.WP_OTSINGUD)
    assert t["kokku"] == 10 and t["kirjed"][0]["avaldatud"] == "2026-08-04"


def test_proov_ja_vead_ei_peata(tmp_path, monkeypatch):
    def hae(url):
        if "etis" in url:
            raise yhine.KogujaViga(url + ": HTTP 403")
        if "dspace" in url:
            return DSPACE
        if "taltech" in url:
            return b"<html>  tere   maailm </html>"
        return RSS

    allikad = {k: eesti.ALLIKAD[k] for k in ("novaator", "etis", "taltech_digikogu")}
    allikad["tu_dspace"] = {"liik": "lõputöö", "dspace": "https://dspace.ut.ee/"}
    monkeypatch.setattr(eesti, "ALLIKAD", allikad)
    valmis = []
    t = eesti.kaivita(tmp_path, hae=hae, paus=0, valmis=lambda nimi, sisu: valmis.append(nimi))["allikad"]
    assert sorted(valmis) == sorted(t)
    assert t["tu_dspace"]["kokku"] == 214 and t["novaator"]["kokku"] == 2
    assert all(v.endswith("HTTP 403") for v in t["etis"]["proov"].values())
    assert list(t["taltech_digikogu"]["proov"].values())[0] == "OK <html> tere maailm </html>"
    assert json.loads((tmp_path / "eesti.json").read_text(encoding="utf-8"))["allikad"]["etis"]["kirjed"] == []


ETIS = json.dumps([
    {"Guid": "g1", "DisplayInfo": "Mets, U. (2025). Tehisintellekti mõju tööjõu oskuste vajadusele. Tallinn.",
     "PublicationTypeName": "raport", "Title": "Tehisintellekti mõju tööjõu oskuste vajadusele", "TitleTranslation": ""},
    {"Guid": "g2", "DisplayInfo": "Koit, M. (2011). Tehisintellekt. Tartu.", "Title": "Tehisintellekt",
     "TitleTranslation": "Artificial Intelligence"},
]).encode()


def test_etis():
    k = eesti.etis(ETIS, "tehisintellekt")
    assert [r["avaldatud"] for r in k] == ["2025", "2011"] and [r["teemas"] for r in k] == [True, False]
    assert k[0]["url"] == "https://www.etis.ee/Portal/Publications/Display/g1" and k[0]["liik"] == "raport"
    assert "Title=generative+AI" in eesti.etis_url("https://x/api", "generative AI")


def test_vigane_voog_loetakse_kirjete_kaupa():
    vigane = RSS.replace(b"<channel>", b"<channel><description>Praxis & partnerid <b></description>")
    vigane = vigane.replace(b"<title>Konverents</title>", b"<title>Konverents & <katki</title>")
    assert len(eesti.rss(vigane, "praxis", "mõttekoda")) == 1
    html = ("<html>" + "x" * 700 + " Tehisintellekt ja töö </html>").encode()
    assert eesti.proov(html).endswith("Tehisintellekt ja töö </html>") and "[…]" in eesti.proov(html)
