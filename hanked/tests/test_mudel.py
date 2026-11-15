import numpy as np

import mudel as M


def test_kaalutud_moodikud_kaal_muudab_tulemust():
    y = [1, 1, 0, 0]
    e = [1, 0, 1, 0]
    # ilma kaaluta täpsus 0,5; kui valepositiivne rida esindab 9 hanget, langeb täpsus 0,1-ni
    assert M.kaalutud_moodikud(y, e, [1, 1, 1, 1])["tapsus"] == 0.5
    assert M.kaalutud_moodikud(y, e, [1, 1, 9, 1])["tapsus"] == 0.1


def test_levimus_kolme_reegel_nullkihis():
    margendid = ([{"kiht": "a", "silt": "AI"}] * 5 + [{"kiht": "a", "silt": "EI"}] * 5
                 + [{"kiht": "b", "silt": "EI"}] * 100)
    t = M.levimus(margendid, {"a": 10, "b": 10000})
    assert t["hinnang"] == 5  # kiht a on täielikult valimis, kiht b annab 0
    assert t["vahemik_95"][1] >= 5 + 300  # 0 leidu 100 seas ei tähenda nulli: kolme reegel 3/100 * 10000


def test_mudel_opib_lihtsa_eristuse():
    tekstid = ["kõnetuvastuse mudel"] * 6 + ["teede remont"] * 6
    y = np.array([1] * 6 + [0] * 6)
    m = M.Mudel().sobita(tekstid, y)
    p = m.toenaosus(["kõnetuvastuse arendus", "teede hooldus"])
    assert p[0] > 0.5 > p[1]


def test_lehe_reegel_on_lukus_ja_sonavara_valim_stabiilne():
    """Kadri otsus 15.11.2026: lehe reegel ei vahetu ise. Uus hange muudab sõnavara valimit kõige rohkem ühe rea võrra."""
    import mudel as M
    assert M.LEHE_REEGEL == "mudel_voi_marksona"
    votmed = [f"eforms:{i}" for i in range(3000)]
    a = {votmed[i] for i in M.stabiilne_valim(votmed, 1000)}
    b = {(votmed + ["eforms:uus"])[i] for i in M.stabiilne_valim(votmed + ["eforms:uus"], 1000)}
    assert len(a - b) <= 1 and len(b - a) <= 1
