"""Kinnituskord (Kadri 8.11.2026 21:36): automaatsed uuringu- ja väitemustandid lähevad saidile alles pärast
Kadri „jah“-i; OECD valvur annab uuest väljaandest teada."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "sait"))

import andmekiht  # noqa: E402
import oecd_valvur  # noqa: E402
import ootel  # noqa: E402
import vota_kaasa  # noqa: E402


def _kaust(tmp_path):
    (tmp_path / "tooelu-leht-andmed").mkdir()
    (tmp_path / "tooelu-uudised").mkdir()
    (tmp_path / "seire-uks-sait").mkdir()
    (tmp_path / "tooelu-leht-andmed" / "leiud-lisa.json").write_text(json.dumps({"kirjeldus": "x", "uuringud": [
        {"id": "u1", "autorid": "A", "aasta": 2026, "pealkiri": "P", "meetod": "kirjeldav", "kus": "USA", "leid": "L",
         "url": "https://n", "kandidaat": "OpenAlex:W1"},
        {"id": "u2", "autorid": "B", "aasta": 2026, "pealkiri": "Q", "meetod": "kirjeldav", "kus": "USA", "leid": "M",
         "url": "https://m"}]}), encoding="utf-8")
    (tmp_path / "tooelu-uudised" / "vaited.json").write_text(json.dumps([
        {"id": "v1", "vaide": "V", "kes": "ERR", "hinnang": "osaliselt", "seire_olek": "varasem"},
        {"id": "v2", "vaide": "W", "kes": "ERR", "hinnang": "liialdab"}]), encoding="utf-8")
    return tmp_path


def test_ootel_kirjed_ja_kinnitamine(tmp_path):
    k = _kaust(tmp_path)
    assert [r["id"] for _, r in ootel.ootel(k)] == ["u1", "u2", "v2"]
    assert ootel.muuda(k, "kinnitatud", ["u1"], tana="2026-11-09") == ["u1"]
    assert ootel.muuda(k, "tagasi", ["v2"], tana="2026-11-09") == ["v2"]
    assert [r["id"] for _, r in ootel.ootel(k)] == ["u2"]
    md = ootel.kokkuvote(k)
    assert "## u2 · uuring" in md and "u1" not in md
    with pytest.raises(SystemExit):
        ootel.muuda(k, "kinnitatud", ["puudub"])
    assert ootel.muuda(k, "kinnitatud", ["koik"]) == ["u2"]


def test_saidi_ettepanekud_on_kinnitusjarjekorras(tmp_path):
    # Kadri 10.11.2026: suurte uudiste järgi saidi muutmise ettepanekud ootavad samuti „jah ID“-d
    k = _kaust(tmp_path)
    (k / "seire-uks-sait" / "saidi-ettepanekud.json").write_text(json.dumps({"kirjeldus": "x", "ettepanekud": [
        {"id": "sp-1", "tegevus": "uuenda", "vaade": "ettevotted", "osa": "Kasutus", "mis_muutub": "Uus number.",
         "andmed": [{"naitaja": "kasutab", "vaartus": 36.1, "aasta": 2026, "allikas": "Statistikaamet", "url": "https://s"}],
         "vorreldavus": "K1", "uudised": ["https://u"], "miks": "M"}]}), encoding="utf-8")
    assert [r["id"] for _, r in ootel.ootel(k) if r["id"].startswith("sp")] == ["sp-1"]
    md = ootel.kokkuvote(k)
    assert "## sp-1 · saidi muudatus (uuenda)" in md and "ettevotted › Kasutus" in md and "kasutab 36.1 (2026, Statistikaamet)" in md
    assert ootel.muuda(k, "kinnitatud", ["sp-1"], tana="2026-11-10") == ["sp-1"]
    d = json.loads((k / "seire-uks-sait" / "saidi-ettepanekud.json").read_text(encoding="utf-8"))
    assert d["kirjeldus"] == "x" and d["ettepanekud"][0]["seire_olek"] == "kinnitatud"


def test_saidile_lahevad_ainult_kinnitatud(tmp_path):
    k = _kaust(tmp_path)
    ootel.muuda(k, "kinnitatud", ["u1"], tana="2026-11-09")
    uu = json.loads((k / "tooelu-leht-andmed" / "leiud-lisa.json").read_text(encoding="utf-8"))["uuringud"]
    vaited = json.loads((k / "tooelu-uudised" / "vaited.json").read_text(encoding="utf-8"))
    lisa = vota_kaasa.kinnitatud_uuringud(uu)
    assert [u["id"] for u in lisa] == ["u1"]
    assert "kandidaat" not in lisa[0] and lisa[0]["seire_kinnitatud"] == "2026-11-09"
    assert [v["id"] for v in vota_kaasa.naidatavad_vaited(vaited)] == ["v1"]  # v2 ootab


def test_kinnitatud_uuring_laheb_kogusse(tmp_path):
    p = tmp_path / "lisa.json"
    p.write_text(json.dumps([{"id": "u1", "meetod": "kirjeldav", "leid": "L"}, {"id": "olemas", "meetod": "kirjeldav"}]))
    A = {"tooelu": {"kindlus": {"keskmine": ["kirjeldav"]}}, "uuringud": {"olemas": {"id": "olemas", "leid": "repo"}}}
    andmekiht.lisa_kinnitatud_uuringud(A, p)
    assert A["uuringud"]["u1"]["lisa"] is True and A["uuringud"]["olemas"]["leid"] == "repo"
    p.write_text(json.dumps([{"id": "u9", "meetod": "tundmatu"}]))
    with pytest.raises(andmekiht.AndmeViga):
        andmekiht.lisa_kinnitatud_uuringud(A, p)


def test_oecd_valvur_leiab_ainult_uue_eesti_valjaande():
    items = [
        {"DOI": "10.1787/c2c09a06-en", "title": ["Strengthening the Innovative Capacity of the Public Sector of Estonia"],
         "published": {"date-parts": [[2026, 11, 3]]}},
        {"DOI": "10.1787/aaa", "title": ["Digital Government Review of Estonia 2027"], "published": {"date-parts": [[2027, 2]]}},
        {"DOI": "10.1787/bbb", "title": ["Public sector innovation in Latvia"], "published": {"date-parts": [[2027, 1, 5]]}},
        {"DOI": "10.1787/ccc", "title": ["Estonia: tax policy review"], "published": {"date-parts": [[2027, 1, 5]]}},
    ]
    tul = oecd_valvur.kontrolli(laadi=lambda url: {"message": {"items": items}}, tana="2027-02-10")
    assert [u["doi"] for u in tul["uued"]] == ["10.1787/aaa"]
    assert tul["uued"][0]["kuupaev"] == "2027-02-01" and tul["kontrollitud"] == "2027-02-10"
    assert "prefix%3A10.1787" in oecd_valvur.paring("2026-11-03")


def test_mis_uueneb_tabel_naitab_kinnituskorda():
    import ehita  # noqa: F401
    s = (Path(__file__).resolve().parents[1] / "valjund" / "sait" / "kuidas-lugeda.html")
    if not s.exists():
        pytest.skip("sait ehitamata")
    h = s.read_text(encoding="utf-8")
    assert "saidile pärast kinnitust" in h and "uue väljaande otsing ise" in h
    assert "inimene kinnitab" in h


def test_valja_jaetud_ettevote_ei_ole_ukski_loendis():
    A = {"koondamised": {"juhtumid": [{"ettevote": "EKKM"}, {"ettevote": "Telia"}]},
         "uudised": [{"ettevote": "EKKM "}, {"ettevote": "Pipedrive"}, {}], "koondajad": {"firmad": {"EKKM": {}, "Telia": {}}}}
    andmekiht.jata_valja(A)
    assert [j["ettevote"] for j in A["koondamised"]["juhtumid"]] == ["Telia"]
    assert [r.get("ettevote") for r in A["uudised"]] == ["Pipedrive", None]
    assert list(A["koondajad"]["firmad"]) == ["Telia"]


def test_ekkm_pole_saidil():
    d = Path(__file__).resolve().parents[1] / "valjund" / "sait"
    if not d.exists():
        pytest.skip("sait ehitamata")
    for f in d.glob("*.html"):
        assert "EKKM" not in f.read_text(encoding="utf-8"), f.name
