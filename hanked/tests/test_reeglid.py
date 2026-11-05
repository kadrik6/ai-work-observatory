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


def test_moju_uuring():
    r = {"pealkiri": "Tehisaru kasutamise mõju analüüs avalikus sektoris", "kirjeldus": "", "cpv": ["73110000"]}
    m = R.moju_uuring(r)
    assert m and m["tyyp"] == "tehisaru" and m["cpv_73_79"] and m["uuring_pealkirjas"]
    r = {"pealkiri": "Digipöörde mõjuhinnang", "kirjeldus": "", "cpv": ["72000000"]}
    assert R.moju_uuring(r)["tyyp"] == "digi või automatiseerimine"
    # süsteemianalüüs ei ole uuring (sõna keskel), ja ilma tehnoloogiasõnata ei loeta
    assert R.moju_uuring({"pealkiri": "Infosüsteemi süsteemianalüüs ja digilahendus", "cpv": ["72000000"]}) is None
    assert R.moju_uuring({"pealkiri": "Tööturu mõjuanalüüs", "cpv": ["73110000"]}) is None
    # uuringusõna ainult kirjelduses ja CPV väljaspool 73/79: ei loeta
    assert R.moju_uuring({"pealkiri": "Tarkvara arendus", "kirjeldus": "AI lahenduse mõju analüüs",
                          "cpv": ["72000000"]}) is None
    assert R.moju_uuring({"pealkiri": "Andmehalduse mõjuanalüüs (Justiits- ja Digiministeerium)",
                          "cpv": ["79000000"]}) is None
