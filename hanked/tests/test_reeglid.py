import reeglid as R
from lae import pohitabel


def test_marksonad_kaanded_ja_sonapiir():
    m = R.marksonad("Tehisintellektiga dokumendihaldus. Andmelao arendus. Pai lasteaed. Maitse.")
    assert "tehisintellekt" in m["ai"] and "andmelao" in m["andmed"]
    assert "ai" not in m["ai"]  # "pai" ja "maitse" ei tohi anda "ai"


def test_kriteeriumid():
    assert R.kriteeriumid([]) == {"ainult_hind": None, "kvaliteedi_kaal": None}
    assert R.kriteeriumid([("price", None)])["ainult_hind"] is True
    assert R.kriteeriumid([("price", 70), ("quality", 30)]) == {"ainult_hind": False, "kvaliteedi_kaal": 30.0}
    assert R.kriteeriumid([("price", None), ("quality", None)])["kvaliteedi_kaal"] is None


def test_innovatsiooni_mark():
    assert R.innovatsiooni_mark({"strateegiline": ["inn-pur"]})
    assert not R.innovatsiooni_mark({"strateegiline": ["none"], "innovatsioon": ["none"]})


def test_pohitabel_viimane_versioon_ja_tulemus():
    cn = [{"allikas": "eforms", "viitenumber": "1", "kuu": "2024-01", "kuupaev": "2024-01-02", "versioon": "01",
           "pealkiri": "vana"},
          {"allikas": "eforms", "viitenumber": "1", "kuu": "2024-02", "kuupaev": "2024-02-10", "versioon": "02",
           "pealkiri": "uus"}]
    can = [{"allikas": "eforms", "viitenumber": "1", "pakkumusi": 2, "tulemused": ["selec-w"], "voitjad": ["A"],
            "lepingu_summa": 10.0}]
    h = pohitabel(cn, can)
    assert len(h) == 1 and h[0]["pealkiri"] == "uus" and h[0]["teateid"] == 2
    assert h[0]["esimene_kuupaev"] == "2024-01-02" and h[0]["aasta"] == 2024 and h[0]["pakkumusi"] == 2


def test_voti():
    assert R.voti({"allikas": "eforms", "viitenumber": "123", "rhr_id": "9"}) == "eforms:123"
    assert R.voti({"allikas": "ted_esender", "teate_id": "u-1"}) == "ted_esender:u-1"
