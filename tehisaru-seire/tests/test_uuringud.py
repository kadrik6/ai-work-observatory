"""Küsimuste ja uuringute seose testid (ühine kiht, 3.11.2026)."""

import csv
import json
from collections import Counter
from pathlib import Path

JUUR = Path(__file__).resolve().parent.parent
LEIUD = JUUR.parent / "tooelu-seire" / "leiud.json"
SUURIM = 3  # ühe küsimuse juures näidatakse kuni nii palju uuringuid


def read():
    with open(JUUR / "kataloog" / "uuringud.csv", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def test_veerud_ja_seos_olemas():
    r = read()
    assert r and list(r[0]) == ["kusimus", "uuring", "seos"]
    assert all(x["seos"].strip() for x in r)


def test_iga_kusimus_on_kataloogis():
    with open(JUUR / "kataloog" / "moisted.csv", encoding="utf-8", newline="") as f:
        moisted = {x["id"] for x in csv.DictReader(f)}
    assert {x["kusimus"] for x in read()} <= moisted


def test_iga_uuring_on_leidudes():
    uuringud = {u["id"] for u in json.loads(LEIUD.read_text(encoding="utf-8"))["uuringud"]}
    puudu = {x["uuring"] for x in read()} - uuringud
    assert not puudu, f"leiud.json-is pole: {sorted(puudu)}"


def test_kordusi_pole_ja_kusimuse_kohta_kuni_kolm():
    r = read()
    paarid = Counter((x["kusimus"], x["uuring"]) for x in r)
    assert max(paarid.values()) == 1
    assert max(Counter(x["kusimus"] for x in r).values()) <= SUURIM
