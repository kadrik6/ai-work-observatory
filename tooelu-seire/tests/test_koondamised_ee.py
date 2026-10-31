"""Eesti koondamiste nimekirja kuju: igal juhtumil on allikas, kuupäev ja tehisaru roll."""

import json
import re
from pathlib import Path

K = json.loads((Path(__file__).resolve().parents[1] / "koondamised_ee.json").read_text(encoding="utf-8"))


def test_igal_juhtumil_on_allikas_ja_roll():
    ids = [j["id"] for j in K["juhtumid"]]
    assert len(ids) == len(set(ids))
    for j in K["juhtumid"]:
        for v in ("kuupaev", "ettevote", "arv_tekst", "roll", "kes_utles", "pohjus", "pealkiri", "url", "allikas"):
            assert j.get(v) not in (None, ""), (j["id"], v)
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", j["kuupaev"]), j["id"]
        assert j["url"].startswith("https://"), j["id"]
        assert j["roll"] in K["rollid"], j["id"]


def test_arv_on_ainult_eesti_kohta():
    # Kui Eesti arvu ei ole teada (näiteks ainult Balti riigid kokku), on arv tühi, mitte hinnatud.
    for j in K["juhtumid"]:
        assert j["arv_eestis"] is None or (isinstance(j["arv_eestis"], int) and j["arv_eestis"] > 0), j["id"]


def test_uuemad_ees():
    kp = [j["kuupaev"] for j in K["juhtumid"]]
    assert kp == sorted(kp, reverse=True)


def test_artikli_teksti_ei_hoita():
    # Põhjus on oma sõnadega ja lühike, mitte tsitaat ega artikli lõik.
    for j in K["juhtumid"]:
        assert len(j["pohjus"]) <= 300, j["id"]
        assert "“" not in j["pohjus"] and "\"" not in j["pohjus"], j["id"]
