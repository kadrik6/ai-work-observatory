"""Riskimudeli 1. sammu testid väljamõeldud hangetega."""
import random

import osad as O


def _hange(viide, aasta, info, pakk, tulemus=True, **kw):
    return {"allikas": "eforms", "viitenumber": viide, "aasta": aasta, "esimene_kuupaev": f"{aasta}-03-01",
            "osade_info": info, "osade_pakkumusi": pakk, "tulemus_olemas": tulemus, "cpv": ["72000000"],
            "menetlus": "open", "liik": "services", "eeldatav_maksumus": 50000.0, "kriteeriumid": [], **kw}


def _osa(osa, **kw):
    return {"osa": osa, "cpv": "72000000", "maksumus": 10000.0, "kriteeriumid": [("price", None)],
            "tahtaeg": "2024-03-21", **kw}


def test_osa_voti():
    assert O.osa_voti("LOT-0001") == O.osa_voti("1") == O.osa_voti("Osa 1") == "1"
    assert O.osa_voti("#2") == "#2" and O.osa_voti(None) is None


def test_siht():
    assert [O.siht(x) for x in (None, 0, 1, 2, 7)] == ["puudub", "null", 1, 0, 0]


def test_sidumine():
    hanked = [
        _hange("A", 2024, [_osa("LOT-0001"), _osa("LOT-0002")], {"1": 1, "2": 3}),   # mõlemad seotud
        _hange("B", 2024, [_osa("1")], {"#1": 1, "#2": 2}),                          # üks osa, mitu lepingut
        _hange("C", 2024, [_osa("1"), _osa("2")], {"1": 2, "#3": 1}),                # osa 2 seostamata, #3 üle
        _hange("D", 2024, [_osa("1")], {}, tulemus=False),                           # tulemus puudub
    ]
    read, ainult = O.osade_tabel(hanked)
    assert [(r["hange"], r["sidumine"], r["pakkumusi"]) for r in read] == [
        ("eforms:A", "seotud", 1), ("eforms:A", "seotud", 3), ("eforms:B", "üks osa", 2),
        ("eforms:C", "seotud", 2), ("eforms:C", "ainult hanketeates", None), ("eforms:D", "tulemus puudub", None)]
    k = O.sidumise_kontroll(read, ainult)[(2024, "eforms")]
    assert k["ainult tulemusteates"] == 1 and k["seotud_osakaal"] == round(4 / 5, 3)


def test_ilma_osadeta_hange_saab_yhe_osa():
    read, _ = O.osade_tabel([_hange("E", 2020, [], {"#1": 1}, kriteeriumid=[("price", 100.0)])])
    assert len(read) == 1 and read[0]["siht"] == 1 and read[0]["maksumus"] == 50000.0
    assert read[0]["kriteeriumid"] == [("price", 100.0)]


def test_tunnused_ainult_hanketeatest():
    """Ükski tunnus ei tohi tulla tulemusteatest (pakkumused, võitjad, lepingu summa)."""
    r = O.osade_tabel([_hange("A", 2024, [_osa("1")], {"1": 1}, voitjad=["X"], lepingu_summa=9.0)])[0][0]
    t = O.tunnused(r)
    assert not any(s in k for k in t for s in ("pakk", "voit", "lepingu", "siht", "tulemus"))
    assert t["tahtaeg_paevi"] == 20.0 and t["ainult_hind"] == 1.0 and t["menetlus=avatud"] == 1.0
    assert set(O.tunnused(r, ylesehitus=False)) == {"cpv2=72", "log_maksumus", "aasta"}
    assert "aasta" not in O.tunnused(r, aasta=False)


def test_hinna_kaal():
    r = {"cpv": "72", "maksumus": None, "aasta": 2020, "kuupaev": None, "tahtaeg": None, "osade_arv": 1,
         "kriteeriumid": [["price", 60.0], ["quality", 40.0]], "menetlus": "PT_OPEN"}
    t = O.tunnused(r)
    assert t["hinna_kaal"] == 0.6 and t["maksumus_puudub"] == 1.0 and t["tahtaeg_puudub"] == 1.0


def test_m0_silub_harva_grupi():
    tr = [{"cpv": "72", "siht": 1}] * 2 + [{"cpv": "45", "siht": 0}] * 98
    maarad, yld = O.m0_maarad(tr)
    assert yld == 0.02 and 0.02 < maarad["72"] < 1.0


def test_kalibreeritus():
    assert O.kalibreeritus([0, 1] * 50, [0.5] * 100) == 0.0
    assert O.kalibreeritus([0] * 100, [0.3] * 100) == 30.0


def test_mudelid_ja_testilukk():
    """Ülesehitus (lühike tähtaeg) mõjutab sihttunnust: M2 peab olema M1-st parem. Testiaasta ainult lipuga."""
    rnd = random.Random(3)
    hanked = []
    for i in range(1800):
        a = rnd.choice([2018, 2020, 2022, 2024, 2025])
        paevi = rnd.choice([5, 10, 30, 40])
        yks = rnd.random() < (0.6 if paevi <= 10 else 0.1)
        hanked.append(_hange(f"H{i}", a, [_osa("1", tahtaeg=f"{a}-03-{1 + paevi:02d}" if paevi < 30 else f"{a}-04-{paevi - 28:02d}")],
                             {"1": 1 if yks else 3}))
    read, _ = O.osade_tabel(hanked)
    v = O.mudelid(read)
    assert "test_2025" not in v and v["treening"]["n"] > 0
    h = v["valideerimine_2024"]
    assert h["M2"]["pr_auc"] > h["M1"]["pr_auc"] + 0.1
    assert h["M2-M1"]["jareldus"] == "suurem" and h["bootstrap"]["kordi"] > 900
    assert "test_2025" in O.mudelid(read, test=True)
