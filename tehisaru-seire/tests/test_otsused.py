"""Osa „Mida otsustatakse“: seaduste tähtajad ja sihid (3.11.2026)."""

import csv
import json
import re
import sys
from pathlib import Path

JUUR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(JUUR / "raportid"))
import koosta  # noqa: E402

VEERUD = ["id", "kuupaev", "tapsus", "tase", "liik", "nimi", "mida_tahendab", "kelle_jaoks", "allikas", "url", "kontrollitud"]


def read():
    with open(JUUR / "kataloog" / "otsused.csv", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def naitajad():
    return json.loads((JUUR / "naitajad.json").read_text(encoding="utf-8"))["naitajad"]


def test_veerud_kuupaevad_ja_allikad():
    r = read()
    assert r and list(r[0]) == VEERUD
    assert len({x["id"] for x in r}) == len(r)
    for x in r:
        for k in VEERUD:
            assert x[k].strip(), (x["id"], k)
        muster = {"paev": r"\d{4}-\d{2}-\d{2}", "kuu": r"\d{4}-\d{2}", "aasta": r"\d{4}"}[x["tapsus"]]
        assert re.fullmatch(muster, x["kuupaev"]), x["id"]
        assert x["url"].startswith("https://"), x["id"]
        assert x["liik"] == "seadus" and x["tase"] in ("EL", "Eesti"), x["id"]
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", x["kontrollitud"])


def koik(monkeypatch=None):
    return koosta.lae_otsused({"naitajad": [{"n": n} for n in naitajad()]})


def test_iga_siht_on_ajajoonel_ja_jarjestus():
    OO = koik()
    sihte = sum(len(n.get("sihid") or []) for n in naitajad())
    assert sum(1 for o in OO if o["liik"] == "siht") == sihte
    assert len(OO) == sihte + len(read())
    kuup = [o["kuupaev"] for o in OO]
    datega = [k for k in kuup if k]
    assert datega == sorted(datega) and kuup[len(datega):] == [""] * (len(kuup) - len(datega))


def test_kehtimine_ja_aja_kuju():
    o = lambda k, t, liik="seadus": {"kuupaev": k, "tapsus": t, "liik": liik}
    assert koosta.otsus_kehtib(o("2026-08-02", "paev"), "2026-11-03")
    assert not koosta.otsus_kehtib(o("2026-12", "kuu"), "2026-11-30")
    assert koosta.otsus_kehtib(o("2026-12", "kuu"), "2026-12-01")
    assert koosta.otsuse_aeg(o("2026-12", "kuu")) == "detsember 2026"
    assert koosta.otsuse_aeg(o("2030", "aasta", "siht")) == "aastaks 2030"
    assert koosta.otsuse_aeg(o("2027-12-02", "paev")) == "02.12.2027"
    assert koosta.otsuse_aeg(o("", "")) == "aastata"


def test_tyhi_loend_ei_kuku(monkeypatch, tmp_path):
    monkeypatch.setattr(koosta, "OTSUSED", tmp_path / "puudub.csv")
    s = koosta.otsused_leht({"naitajad": []}, "2026-11-03")
    assert "Mida see leht ei näita" in s and "otsjoon" not in s


def test_leht_naitab_iga_otsust(tmp_path, monkeypatch):
    monkeypatch.setattr(koosta, "VALJA", tmp_path / "html")
    koosta.main()
    s = (tmp_path / "html" / koosta.OTSUSED_LEHT).read_text(encoding="utf-8")
    for x in read():
        assert koosta.e(x["nimi"]) in s and x["url"] in s
    assert s.count('<li class="decision"') == len(koik())
    assert '<svg class="otsjoon"' in s and 'title="seadused ja sihid" aria-current="page"><b>Mida otsustatakse' in s
    # Siht ja praegune number ei ole samal lehel kõrvuti: sihi juures on ainult link näitaja lehele, numbrit mitte.
    for n in naitajad():
        for sh in n.get("sihid") or []:
            assert koosta.e(sh["allikas"]) in s
    assert "% praegu" not in s and "Vaata, kus number" not in s


def test_moodunud_siht_ja_loenduse_grammatika():
    siht = {"kuupaev": "2025", "tapsus": "aasta", "liik": "siht"}
    seadus = {"kuupaev": "2025-02-02", "tapsus": "paev", "liik": "seadus"}
    tulev = {"kuupaev": "2027-12-02", "tapsus": "paev", "liik": "seadus"}
    assert koosta.otsus_kehtib(siht, "2026-11-03") and not koosta.otsus_kehtib({**siht, "kuupaev": "2026"}, "2026-11-03")
    assert koosta.otsuste_loendus([siht, seadus], [tulev]) == "Käes või möödas 1 seaduse tähtaeg ja 1 siht; ees 1 seaduse tähtaeg"
    assert koosta.otsuste_loendus([], [tulev, tulev]) == "Ees 2 seaduse tähtaega"
    assert koosta.otsuste_loendus([], []) == "Otsuseid pole"


def test_sihi_nimi_hoiab_lyhendi_ja_riigi_taseme():
    n = {"id": "x", "nimi": "VKEde digiintensiivsus", "uhik": "% ettevõtetest",
         "sihid": [{"riik": "FI", "aasta": 2030, "vaartus": 90, "allikas": "a"}]}
    o = koosta.lae_otsused({"naitajad": [{"n": n}]})[-1]
    assert "VKEde" in o["nimi"] and o["tase"] == koosta.riik("FI")


def test_ajajoone_punktid_ei_kattu_ega_lahe_valja():
    OO = [{"id": str(i), "kuupaev": "2026-08-0" + str(i % 9 + 1), "tapsus": "paev", "liik": "seadus", "nimi": "n"}
          for i in range(6)]
    svg = koosta.otsuste_joon(OO, "2026-11-03")
    ys = [int(y) for y in re.findall(r'cy="(\d+)"', svg)]
    assert len(ys) == 6 and min(ys) >= 6


def test_avalehe_lingid_on_osade_jarjekorras(tmp_path, monkeypatch):
    monkeypatch.setattr(koosta, "VALJA", tmp_path / "html")
    koosta.main()
    s = (tmp_path / "html" / "index.html").read_text(encoding="utf-8")
    edasi = s[s.index('class="edasi"'):]
    jarg = [edasi.index(f'href="{f}"') for f in (koosta.TOOELU_LEHT, koosta.VAITED_LEHT, koosta.OTSUSED_LEHT)]
    assert jarg == sorted(jarg)
