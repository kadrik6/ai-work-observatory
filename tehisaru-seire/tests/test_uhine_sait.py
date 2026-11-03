"""Ühise saidi testid (Kadri otsus 3.11.2026): seire ja „Tehisaru ja töö“ on üks sait, numbrid ja uuringud eraldi."""

import re
import sys
from pathlib import Path

JUUR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(JUUR / "raportid"))
import koosta  # noqa: E402
from seire import kataloog  # noqa: E402


def uuring(i, meetod="katse"):
    return {"id": f"u{i}", "autorid": "Autor", "aasta": 2025, "pealkiri": f"Pealkiri {i}", "url": "https://naide.ee",
            "kus": "Eesti", "meetod": meetod, "retsenseeritud": True, "leid": "Leid.", "seos": f"Seos {i}.", "toend": "tugev"}


def test_kast_naitab_kuni_kolme_uuringut_ja_utleb_et_see_pole_statistika():
    D = {"uuringud": {"q": [uuring(i) for i in range(5)]}}
    h = koosta.uuringute_kast(D, {"moiste": {"id": "q"}})
    assert h.count('class="study"') == koosta.UURINGUID_KUNI
    assert "mitte ametlik statistika" in h and "Tugev tõend" in h and 'id="uuringud"' in h
    assert f'href="{koosta.TOOELU_LEHT}"' in h


def test_kasti_pole_kui_kusimust_voi_uuringuid_pole():
    assert koosta.uuringute_kast({"uuringud": {}}, {"moiste": {"id": "q"}}) == ""
    assert koosta.uuringute_kast({"uuringud": {"q": [uuring(1)]}}, {"moiste": None}) == ""


def test_uuringud_loetakse_leidudest_seose_jargi():
    U = koosta.lae_uuringud()
    assert U, "kataloog/uuringud.csv ja tooelu-seire/leiud.json peavad andma vähemalt ühe seose"
    for rida in [u for uu in U.values() for u in uu]:
        assert rida["seos"] and rida["pealkiri"] and rida["meetod"] in koosta.MEETOD


def test_kusimuste_kaart_katab_iga_kusimuse_uks_kord():
    D = koosta.lae()
    for x in D["naitajad"]:
        x["k"] = None
    K = kataloog.lae()
    h = koosta.kusimuste_kaart(D, K)
    kokku = sum(int(n) for n in re.findall(r'<h3>[^<]*<span class="n">(\d+)</span></h3>', h))
    assert kokku == len(K["moisted"])


def test_osade_riba_on_igal_lehel_ja_naitab_praegust_osa():
    riba = koosta.osade_riba("mootmine")
    assert 'aria-current="page"><b>Mida mõõdetakse' in riba and f'href="{koosta.TOOELU_LEHT}"' in riba
