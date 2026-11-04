import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "leht"))
import ehita  # noqa: E402


def _aasta(a, n, ai, inn=None, ef=None):
    return {"aasta": a, "hankeid": n, "ai_andmed": ai, "ai_andmed_osakaal": round(100 * ai / n, 1),
            "ai_marksonaga": ai // 2, "innovatsioonimark": inn, "eforms_hankeid": ef,
            "innovatsioonimark_osakaal": None if inn is None else round(100 * inn / ef, 1)}


def _viis(ah, kaal, yks, kat):
    return {"hankeid": 100, "ainult_hind_osakaal": ah, "kvaliteedi_kaal_mediaan": kaal,
            "uks_pakkuja_osakaal": yks, "katkes_osakaal": kat}


ANDMED = {
    "aastad": [_aasta(2022, 9000, 90), _aasta(2023, 9000, 100, 19, 5000), _aasta(2024, 8000, 120, 75, 8000),
               _aasta(2025, 9000, 150, 102, 9000), _aasta(2026, 7000, 110, 110, 7000)],
    "eforms_aastad": [2023, 2024, 2025, 2026],
    "hankimise_viis": {"periood": [2024, 2026], "ai_andmed": _viis(20, 30, 25, 10),
                       "it_muud": _viis(40, 20, 30, 12), "koik": _viis(55, 20, 28, 9)},
    "kontsentratsioon": {"hankijaid": 120, "top10_protsenti_hankijaid": 12, "nende_osakaal": 48.0,
                         "uks_hange_hankijaid": 60},
    "hankijad_top": [["Asutus <A>", 30], ["Asutus B", 20]],
    "hindamine": {"hindamine": {"valitud": "marksonaloend", "testi_alates": 2024, "treening": 100, "test": 600,
                                "test_pos": 100, "treening_pos": 20, "tulemused": {
                                    "marksonaloend": {"tapsus": 0.75, "saagis": 0.7, "f1": 0.72, "tp": 1, "fp": 2,
                                                      "fn": 3, "tapsus_95": [0.6, 0.8], "saagis_95": [0.5, 0.9]}}},
                  "levimus": {"valimi_pohjal": {"hinnang": 190, "vahemik_95": [150, 480]}, "hankeid": 30000,
                              "valitud_leidis": 180},
                  "margendid": {"leitud_registrist": 782, "positiivseid": 141}},
    "loend": [{"t": "Kõnetuvastus </script>", "k": "x", "h": "A", "kp": "2026-01-02", "hea": 3}],
}


def test_leht_ehitub_ja_pealkiri_utleb_leiu():
    h = ehita.ehita(ANDMED, "2026-11-04")
    assert "%%" not in h
    assert "2025. aastal <b>150</b>" in h  # fookus on viimane täisaasta, mitte pooleli olev 2026
    assert "sihini 2% jääb 0,4 protsendipunkti" in h  # 2026: 110/7000 = 1,6%
    assert "Asutus &lt;A&gt;" in h  # hankija nimi on varjestatud
    assert "</script>\"" not in h and "<\\/script>" in h  # andmed ei saa skriptiplokki sulgeda


def test_arvu_kirjaviis():
    assert ehita.arv(12345.6, 1) == "12 345,6"
    assert ehita.protsent(None) == "–"
