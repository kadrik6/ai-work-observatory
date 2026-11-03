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


def test_kusimuste_kaart_katab_iga_kusimuse_uks_kord_ja_oige_rühmaga():
    D = koosta.lae()
    K = kataloog.lae()
    h = koosta.kusimuste_kaart(D, K)
    ids = re.findall(r'data-kusimus="([^"]+)"', h)
    assert sorted(ids) == sorted(K["moisted"])
    # Näitaja lehega küsimus on rühmas „Seire näitaja“ ja selle uuringute link viib näitaja lehe kasti.
    seires = h[h.index("qgroup-seires"):h.index("</ul>", h.index("qgroup-seires"))]
    assert 'data-kusimus="ettevotete-ai-kasutus"' in seires and 'ettevotete-tehisaru-kasutus.html#uuringud' in seires


def test_kusimuse_naitaja_on_sama_mis_naitaja_lehel():
    """Kaks reeglit (võrdlusalus ja näitaja lehe mõõdik) peavad andma sama seose."""
    K = kataloog.lae()
    for mid in K["moisted"]:
        nid = koosta.kusimuse_naitaja(K, mid)
        if nid:
            m = next(m for m in K["moodikud"].values() if m["naitaja"] == nid)
            assert m["moiste"] == mid


def test_osade_riba_on_igal_lehel_ja_lingid_viivad_olemasolevale_lehele(tmp_path):
    koosta.VALJA, vana = tmp_path, koosta.VALJA
    try:
        koosta.main()
    finally:
        koosta.VALJA = vana
    lehed = {p.name for p in tmp_path.glob("*.html")} | {koosta.TOOELU_LEHT}
    for p in tmp_path.glob("*.html"):
        s = p.read_text(encoding="utf-8")
        assert 'aria-current="page"><b>Mida mõõdetakse' in s, p.name
        for siht in re.findall(r'href="([a-z0-9-]+\.html)', s):
            assert siht in lehed, f"{p.name} viitab lehele {siht}, mida pole"
