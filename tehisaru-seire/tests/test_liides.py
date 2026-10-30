"""Liidesetest: väljaspool seda repot on leht, mis loeb seire faile lukustatud koopiast (vt tests/liides.json).

See leht ei ole repos, nii et selle enda testid siin ei jookse. See test kontrollib siinpool, et failid on alles
ja nende veerud (CSV) või võtmed (JSON) ei muutunud. Kui muutus on teadlik, uuenda tests/liides.json ja anna
lehe hooldajale teada, enne kui lehe lukk uuendatakse.
"""

import csv
import json
from pathlib import Path

import pytest

JUUR = Path(__file__).resolve().parent.parent
LIIDES = json.loads((Path(__file__).resolve().parent / "liides.json").read_text(encoding="utf-8"))["failid"]


def kuju(p):
    if p.suffix == ".json":
        return sorted(json.loads(p.read_text(encoding="utf-8")))
    with open(p, encoding="utf-8", newline="") as f:
        return next(csv.reader(f))


@pytest.mark.parametrize("nimi", sorted(LIIDES))
def test_liidese_fail_on_alles_ja_sama_kujuga(nimi):
    p = JUUR / nimi
    assert p.exists(), f"{nimi} puudub"
    assert kuju(p) == LIIDES[nimi], f"{nimi}: veerud või võtmed muutusid"
