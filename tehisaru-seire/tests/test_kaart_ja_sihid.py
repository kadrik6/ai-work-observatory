"""ELi kaardi, sihtide ja aegrea alguse testid (3.11.2026). Numbrid on väljamõeldud testandmed."""

import json
import sys
from pathlib import Path

import run

JUUR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(JUUR / "raportid"))
import koosta  # noqa: E402

EL27 = "AT BE BG CY CZ DE DK EE EL ES FI FR HR HU IE IT LT LU LV MT NL PL PT RO SE SI SK".split()


def json_stat(geod, aastad, vaartused):
    """vaartused: {(geo, aasta): väärtus}."""
    return {
        "id": ["geo", "time"], "size": [len(geod), len(aastad)],
        "dimension": {"geo": {"category": {"index": {g: i for i, g in enumerate(geod)}}},
                      "time": {"category": {"index": {a: i for i, a in enumerate(aastad)}}}},
        "value": {str(geod.index(g) * len(aastad) + aastad.index(a)): v for (g, a), v in vaartused.items()},
    }


def test_paringu_filtrid_lisab_alguse_ainult_kui_see_on_antud():
    n = {"filtrid": {"unit": "PC_GDP"}}
    assert run.paringu_filtrid(n) == {"unit": "PC_GDP"}
    assert run.paringu_filtrid({**n, "alates": 2012}) == {"unit": "PC_GDP", "sinceTimePeriod": "2012"}
    assert n["filtrid"] == {"unit": "PC_GDP"}  # registrit ei muudeta


def test_kaardi_aasta_on_viimane_piisavate_riikidega():
    vv = {(g, "2024"): float(i) for i, g in enumerate(EL27)}
    vv.update({(g, "2025"): 50.0 for g in EL27[:3]})  # 2025 on alles 3 riigi kohta
    read = run.kaardi_read({"id": "x"}, json_stat(EL27, ["2024", "2025"], vv))
    assert {r["time"] for r in read} == {"2024"}
    assert len(read) == 27
    vv.update({(g, "2025"): 50.0 for g in EL27[:run.KAARDI_VAHEMALT]})
    assert {r["time"] for r in run.kaardi_read({"id": "x"}, json_stat(EL27, ["2024", "2025"], vv))} == {"2025"}


def naitaja(sihid, seeria):
    return {"n": {"id": "test", "nimi": "Test", "sihid": sihid}, "seeria": seeria,
            "aastad": sorted({a for s in seeria.values() for a in s})}


def test_siht_on_tulpade_seas_katkendjoonega_ja_skaala_arvestab_seda():
    x = naitaja([{"riik": "EE", "aasta": 2030, "vaartus": 75, "allikas": "Arengukava"}],
                {"EE": {2025: (23.4, "")}, "FI": {2025: (37.8, "")}, "EU27_2020": {2025: (20.0, "")}})
    h = koosta.tulbad(x, 2025)
    assert 'class="is-target"' in h and "Siht 2030 (Eesti)" in h and ">75%<" in h
    assert h.index("is-target") < h.index("Soome")  # järjestus väärtuse järgi
    assert 'style="width:100.0%"' in h  # siht on suurim, nii et skaala tipp on siht


def test_ilma_sihita_tulbad_ei_muutu():
    x = naitaja([], {"EE": {2025: (23.4, "")}, "FI": {2025: (37.8, "")}})
    assert "is-target" not in koosta.tulbad(x, 2025)


def test_vaikeste_vaartuste_aegrida_ja_sihijoon():
    x = naitaja([{"riik": "EU27_2020", "aasta": None, "vaartus": 3, "allikas": "ERA"}],
                {"EE": {2012 + i: (1.2 + i / 10, "") for i in range(14)}, "EU27_2020": {2024: (2.26, "")}})
    svg = koosta.jooned(x)
    assert svg.count('class="gridline"') == 7 and ">0,5<" in svg  # tipp 3: samm 0,5 (0 … 3), mitte 10
    assert 'class="target"' in svg and "Siht (EL kokku): 3%" in svg
    assert ">2012<" not in svg and ">2013<" in svg and ">2025<" in svg  # 14 aastat: iga teine silt


def test_kaardi_klassid_katavad_koik_vaartused():
    piirid, _ = koosta.kaardi_klassid([5.21, 23.4, 42.03])
    assert piirid[0] <= 5.21 and piirid[-1] >= 42.03 and len(piirid) == koosta.KAARDI_KLASSE + 1
    assert koosta.klass(5.21, piirid) == 0 and koosta.klass(42.03, piirid) == koosta.KAARDI_KLASSE - 1


def test_kaardi_kujud_ja_registri_riigid_klapivad():
    kuju = json.loads((JUUR / "raportid" / "euroopa.json").read_text(encoding="utf-8"))
    reg = json.loads((JUUR / "naitajad.json").read_text(encoding="utf-8"))
    assert sorted(kuju["el"]) == sorted(reg["kaardi_riigid"]) == sorted(EL27)


def test_igal_sihil_on_allikas_link_ja_kontrollikuupaev():
    reg = json.loads((JUUR / "naitajad.json").read_text(encoding="utf-8"))
    sihid = [s for n in reg["naitajad"] for s in n.get("sihid", [])]
    assert sihid
    for s in sihid:
        assert s["allikas"] and s["url"].startswith("https://") and s["kontrollitud"]
        assert s["riik"] in reg["riigid"]


def test_t_ja_a_kulu_jaab_valisele_lehele_aga_kataloogis_pole_topelt():
    """Tehisaru 2027 leht loeb T&A kulu failist vaatlused-valis.csv. Seire loeb sama numbri oma andmefailist."""
    from seire import kataloog
    rida = (JUUR / "kataloog" / "vaatlused-valis.csv").read_text(encoding="utf-8")
    assert "eurostat-rd-e-gerdtot" in rida
    assert kataloog.kontrolli(kataloog.lae()) == []
