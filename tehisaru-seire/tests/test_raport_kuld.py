"""Seireraporti regressioonitest: raport ehitatakse külmutatud sisendist ja iga leht peab olema baidi täpsusega
sama mis avaldatud versioon (viited failis tests/kuld/viited.json).

Kui test kukub, on raporti kood (koosta.py, analuus.py, pildid.py, stiil.css või seire/ teek) muutnud lehti.
Kui muutus on tahtlik, vaata erinevus üle ja käivita: python tests/kuld/ehita.py --uuenda
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "kuld"))
import ehita  # noqa: E402


def test_raport_on_sama_mis_viide(tmp_path):
    viited = json.loads(ehita.VIITED.read_text(encoding="utf-8"))["failid"]
    uued = ehita.ehita(tmp_path)
    assert sorted(uued) == sorted(viited), "lehtede loend muutus"
    erinevad = [f for f in viited if uued[f] != viited[f]]
    assert not erinevad, f"need lehed muutusid: {', '.join(erinevad)}"


def test_sisend_ei_soltu_paris_andmetest(tmp_path):
    """Külmutatud sisend peab sisaldama kõiki andmefaile, mida raport loeb; päris andmete muutus testi ei mõjuta."""
    for nimi in ["naitajad.json", "kataloog/moodikud.csv", "kataloog/vaatlused-valis.csv", "raportid/riskid.csv"]:
        assert (ehita.SISEND / nimi).exists(), nimi
