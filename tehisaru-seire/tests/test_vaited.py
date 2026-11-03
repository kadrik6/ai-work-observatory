"""Osa „Mida väidetakse“: avalike lausete kontrolli testid (3.11.2026)."""

import csv
import json
import re
import sys
from pathlib import Path

JUUR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(JUUR / "raportid"))
import koosta  # noqa: E402

VEERUD = ["id", "vaide", "kes", "kus", "kuupaev", "url", "algallikas", "algallika_url", "algallikas_utleb",
          "hinnang", "selgitus", "oige_lause", "kusimus", "uuringud", "kontrollitud"]


def read():
    with open(JUUR / "kataloog" / "vaited.csv", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def test_veerud_ja_kohustuslikud_valjad():
    r = read()
    assert r and list(r[0]) == VEERUD
    for x in r:
        for k in ("id", "vaide", "kes", "kuupaev", "url", "algallikas", "algallika_url", "algallikas_utleb",
                  "hinnang", "selgitus", "oige_lause", "kontrollitud"):
            assert x[k].strip(), (x["id"], k)


def test_lingid_kuupaevad_ja_unikaalsus():
    r = read()
    assert len({x["id"] for x in r}) == len(r)
    for x in r:
        # Iga hinnang peab viitama nii ütlejale kui algallikale, muidu on see anonüümne arvamus.
        assert x["url"].startswith("https://") and x["algallika_url"].startswith("https://"), x["id"]
        assert x["url"] != x["algallika_url"], x["id"]
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", x["kuupaev"]) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", x["kontrollitud"])
        assert x["kuupaev"] <= x["kontrollitud"], x["id"]


def test_hinnangud_on_lubatud_loendis_ka_riskides():
    assert {x["hinnang"] for x in read()} <= set(koosta.HINNANGUD)
    with open(JUUR / "raportid" / "riskid.csv", encoding="utf-8", newline="") as f:
        assert {x["hinnang"] for x in csv.DictReader(f) if x["liik"] == "vaide"} <= set(koosta.HINNANGUD)


def test_viited_kusimustele_ja_uuringutele_on_olemas():
    with open(JUUR / "kataloog" / "moisted.csv", encoding="utf-8", newline="") as f:
        moisted = {x["id"] for x in csv.DictReader(f)}
    leiud = {u["id"] for u in json.loads(koosta.LEIUD.read_text(encoding="utf-8"))["uuringud"]}
    for x in read():
        assert not x["kusimus"] or x["kusimus"] in moisted, x["id"]
        assert set(x["uuringud"].split()) <= leiud, x["id"]


def riskirida(pealkiri, kuupaev, hinnang, naitaja="n", liik="vaide"):
    return {"liik": liik, "naitaja": naitaja, "pealkiri": pealkiri, "allikas": "a", "kuupaev": kuupaev, "url": "",
            "hinnang": hinnang, "selgitus": "s", "mida_teha": "t"}


def test_jarjestus_id_ja_loendus(monkeypatch, tmp_path):
    monkeypatch.setattr(koosta, "VAITED", tmp_path / "puudub.csv")
    riskid = [riskirida("vana täpsustus", "2025-01-01", "Täpsustus puudu"),
              riskirida("uus täpsustus", "2026-01-01", "Suurus ebakindel", naitaja="m"),
              riskirida("vale", "2024-01-01", "Nimetaja vale"),
              riskirida("risk", "", "", liik="risk")]
    V = koosta.lae_vaited(riskid)
    # Enne laused, mis ütlevad muud kui allikas; sama raskuse sees uuem enne.
    assert [v["vaide"] for v in V] == ["vale", "uus täpsustus", "vana täpsustus"]
    # id on näitaja piires järjekorranumber, nii et teise näitaja rida ei nihuta seda.
    assert sorted(v["id"] for v in V) == ["m-1", "n-1", "n-2"]
    _, loend = koosta.vaidete_riba(V)
    assert loend == {0: 1, 1: 2, 2: 0}
    assert koosta.vaidete_lause(V, loend) == "3 kontrollitud lausest 1 ütleb muud kui allikas ja 2 vajab täpsustust."


def test_tundmatu_hinnang_hoiatab_ja_ei_kuku(capsys, monkeypatch, tmp_path):
    monkeypatch.setattr(koosta, "VAITED", tmp_path / "puudub.csv")
    V = koosta.lae_vaited([riskirida("x", "2026-01-01", "Midagi muud")])
    assert "pole lubatud" in capsys.readouterr().err
    riba, loend = koosta.vaidete_riba(V)
    assert loend[1] == 1 and "vbar" in riba


def test_tyhi_loend_annab_lehe_ilma_vigadeta():
    riba, loend = koosta.vaidete_riba([])
    assert riba == "" and koosta.vaidete_lause([], loend) == "Kontrollitud lauseid veel pole."
    D = {"vaited": [], "leiud": {}, "naitajad": []}
    s = koosta.vaited_leht(D, "2026-11-03")
    assert "Kontrollitud lauseid veel pole" in s and '<li class="claim"' not in s


def test_leht_naitab_iga_lauset_ja_parema_lause(tmp_path, monkeypatch):
    monkeypatch.setattr(koosta, "VALJA", tmp_path / "html")
    koosta.main()
    s = (tmp_path / "html" / koosta.VAITED_LEHT).read_text(encoding="utf-8")
    for x in read():
        for k in ("vaide", "oige_lause", "algallikas_utleb"):
            assert koosta.e(x[k]) in s, (x["id"], k)
        assert x["algallika_url"].replace("&", "&amp;") in s
    with open(JUUR / "raportid" / "riskid.csv", encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            if r["liik"] == "vaide":
                assert koosta.e(r["pealkiri"]) in s
    assert 'title="avalike lausete kontroll" aria-current="page"><b>Mida väidetakse' in s
    assert 'href="vaited.html"' in (tmp_path / "html" / "index.html").read_text(encoding="utf-8")


def test_uuring_ilma_valjadeta_ei_kuku():
    v = {"id": "x", "vaide": "v", "kes": "k", "kus": "", "kuupaev": "", "url": "", "algallikas": "a",
         "algallika_url": "", "algallikas_utleb": "u", "hinnang": "Vastab allikale", "selgitus": "s",
         "oige_lause": "", "mida_teha": "", "naitaja": "", "uuringud": ["u1"]}
    s = koosta.vaite_kirje(v, {"leiud": {"u1": {"id": "u1"}}, "naitajad": []})
    assert "u1" in s and 'class="tag ok"' in s
