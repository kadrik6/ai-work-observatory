"""ADR-1 (14.11.2026): ettekannete tekstid tehakse Kadri arvutis skriptiga sait/tee_tekstid.py, mitte repo."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "sait"))
import lae_ettekanded as le  # noqa: E402
import tee_tekstid as tt  # noqa: E402

VTT = """WEBVTT
Kind: captions

00:00:01.000 --> 00:00:03.000
<c>tere</c> kõigile

00:00:03.000 --> 00:00:05.000
tere kõigile
täna räägime tehisarust

01:02:03.500 --> 01:02:05.000
lõpp
"""


def test_vtt_read_ajaga_ja_kordusteta():
    assert tt.vtt_read(VTT) == ["[0:00:01] tere kõigile", "[0:00:03] täna räägime tehisarust", "[1:02:03] lõpp"]


def test_vtt_lyhike_ajavorm():
    assert tt.vtt_read("WEBVTT\n\n01:05.000 --> 01:07.000\nüks\n") == ["[0:01:05] üks"]


def test_video_url():
    assert tt.video_url("uttv-43880") == "https://uttv.ee/pls/uttv/naita?id=43880"
    assert tt.video_url("JMw4WSis80k") == "https://www.youtube.com/watch?v=JMw4WSis80k"


def test_valik_ainult_uued_ja_saidilt_puuduvad():
    k = [{"id": "a", "olek": "uus"}, {"id": "b", "olek": "vana"}, {"id": "c", "olek": "uus"}, {"id": "d", "olek": "teemaväline"}]
    assert [x["id"] for x in tt.vali(k, {"c"})] == ["a"]
    assert [x["id"] for x in tt.vali(k, set(), kuni=1)] == ["a"]


def test_valik_id_jargi_ka_kandidaatide_valjast():
    v = tt.vali([{"id": "a", "olek": "vana", "url": "u"}], set(), ["a", "uttv-43501"])
    assert [x["id"] for x in v] == ["a", "uttv-43501"] and v[1]["url"].endswith("id=43501")


def test_tekstid_ei_lahe_repo(tmp_path):
    assert not tt.kaust_repost_valjas(tt.REPO / "tehisaru-seire" / "tekstid")
    assert not tt.kaust_repost_valjas(tt.REPO)
    assert tt.kaust_repost_valjas(tmp_path)


def test_main_keeldub_repo_kaustast(capsys):
    assert tt.main(["--kaust", str(tt.REPO / "tehisaru-seire" / "tekstid")]) == 2
    assert "repo sees" in capsys.readouterr().out


def test_meedia_lingid():
    html = '<video src="https://x.ut.ee/a/b.mp4?t=1"></video><source src="https://x.ut.ee/c/i.m3u8">' \
           '<a href="https://x.ut.ee/a/b.mp4?t=1">'
    assert tt.meedia_lingid(html) == ["https://x.ut.ee/a/b.mp4?t=1", "https://x.ut.ee/c/i.m3u8"]


def test_tuntud_videod_id_ja_youtube(tmp_path):
    f = tmp_path / "e.json"
    f.write_text(json.dumps({"ettekanded": [{"id": "uttv-1", "video": "https://uttv.ee/x"},
                                            {"id": "y", "video": "https://www.youtube.com/watch?v=JMw4WSis80k"}]}))
    assert {"uttv-1", "JMw4WSis80k"} <= tt.tuntud_videod(f)


def test_kogumine_annab_valju_teate():
    assert "::warning::2 ootel" in le.vajab_teksti_teade(
        [{"id": "a", "olek": "uus", "subtiitrid": False}, {"id": "uttv-5", "olek": "uus"},
         {"id": "b", "olek": "uus", "subtiitrid": True}, {"id": "c", "olek": "vana", "subtiitrid": False}])
    assert "::warning::" not in le.vajab_teksti_teade([{"id": "b", "olek": "uus", "subtiitrid": True}])
