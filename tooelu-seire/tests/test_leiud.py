"""Kontrollitud leidude faili kuju: igal leiul on allikas, link, kuupäev ja meetod."""

import json
from pathlib import Path

LEIUD = json.loads((Path(__file__).resolve().parents[1] / "leiud.json").read_text(encoding="utf-8"))
UURINGUD = {u["id"]: u for u in LEIUD["uuringud"]}


def test_igal_uuringul_on_allikas_ja_meetod():
    assert len(UURINGUD) == len(LEIUD["uuringud"])
    kindlusega = {m for meetodid in LEIUD["kindlus"].values() for m in meetodid}
    assert kindlusega == set(LEIUD["meetodid"])
    for u in LEIUD["uuringud"]:
        for v in ("autorid", "aasta", "pealkiri", "kanal", "url", "avaldatud", "meetod", "valim", "leid"):
            assert u.get(v) not in (None, ""), (u["id"], v)
        assert u["url"].startswith("https://"), u["id"]
        assert u["meetod"] in LEIUD["meetodid"], u["id"]
        assert isinstance(u["retsenseeritud"], bool)


def test_graafikute_read_viitavad_olemasolevale_uuringule():
    viited = [r["uuring"] for r in LEIUD["kiirus"] + LEIUD["tookohad"]]
    viited += [LEIUD["avatus"]["uuring"], LEIUD["eesti_tootlikkus"]["uuring"]]
    viited += [u for v in LEIUD["vastuolud"] for u in v["uuringud"]]
    assert set(viited) <= set(UURINGUD)


def test_kiiruse_graafikus_on_ainult_katsed():
    # Aja muutus ülesandel on võrreldav ainult katsetes, kus sama ülesannet tehti tehisaruga ja ilma.
    assert {UURINGUD[r["uuring"]]["meetod"] for r in LEIUD["kiirus"]} == {"katse"}


def test_puuduv_mojuhinnang_ei_ole_null():
    tehisaru_yksi = [r for r in LEIUD["eesti_tootlikkus"]["read"] if r["nimi"] == "Tehisaru üksi"][0]
    assert tehisaru_yksi["toostus"] is None and tehisaru_yksi["teenused"] is None
