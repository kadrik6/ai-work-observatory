"""Töötuse kuurea laadija (sait/lae_tootus.py): võrguta, Eurostati vastuse kuju järgi."""
import csv
import sys
from pathlib import Path

import pytest

JUUR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(JUUR / "sait"))

import lae_tootus  # noqa: E402
import lehed_ulevaade  # noqa: E402


def vastus(kuid=27, el_viimane=True, ee_viimane=False):
    """JSON-stat nagu Eurostat annab: EL enne, Eesti järel; viimasel kuul võib number puududa."""
    kuud = [f"{2024 + (8 + i) // 12}-{(8 + i) % 12 + 1:02d}" for i in range(kuid)]
    n = len(kuud)
    v, margid = {}, {}
    for g, alus in ((0, 6.0), (1, 7.0)):
        for i in range(n):
            if i == n - 1 and not (ee_viimane if g else el_viimane):
                continue
            v[str(g * n + i)] = round(alus + i / 10, 1)
    margid[str(1 * n + n - 2)] = "p"
    return {"updated": "2026-12-02T11:00:00+0100", "value": v, "status": margid,
            "dimension": {"geo": {"category": {"index": {"EU27_2020": 0, "EE": 1}}},
                          "time": {"category": {"index": {k: i for i, k in enumerate(kuud)}}}}}, kuud


def test_uusim_kuu_on_viimane_kus_on_nii_eesti_kui_eli_number():
    d, kuud = vastus(el_viimane=True, ee_viimane=False)
    read = lae_tootus.read_vastusest(d)
    assert len(read) == 2 * lae_tootus.KUID
    assert {r[1] for r in read} == set(kuud[-26:-1])  # viimane kuu jääb välja: Eesti numbrit pole
    assert read[-1][0] == "EE" and read[-1][1] == kuud[-2] and read[-1][3] == "p"
    aasta_varem = f"{int(kuud[-2][:4]) - 1}{kuud[-2][4:]}"
    assert aasta_varem in {r[1] for r in read}  # lehe „aasta varem“ vajab seda kuud


def test_liiga_luhike_vastus_on_viga():
    d, _ = vastus(kuid=20)
    with pytest.raises(ValueError):
        lae_tootus.read_vastusest(d)


def test_fail_muutub_ainult_siis_kui_number_muutus():
    d, _ = vastus()
    read = lae_tootus.read_vastusest(d)
    esimene = lae_tootus.uus_seis([], read, "2026-12-02")
    assert esimene and {r["uuendatud"] for r in esimene} == {"2026-12-02"}
    vanad = [{k: str(v) for k, v in r.items()} for r in esimene]
    assert lae_tootus.uus_seis(vanad, read, "2026-12-09") is None  # sama number: kuupäev jääb
    g, k, p, m = read[-1]
    muudetud = read[:-1] + [(g, k, p + 0.1, m)]
    assert {r["uuendatud"] for r in lae_tootus.uus_seis(vanad, muudetud, "2026-12-09")} == {"2026-12-09"}


def test_repo_failis_on_uuendamise_kuupaev_ja_leht_loeb_selle_failist():
    with open(lae_tootus.FAIL, encoding="utf-8") as f:
        read = list(csv.DictReader(f))
    assert list(read[0]) == lae_tootus.VALJAD
    assert len(read) == 2 * lae_tootus.KUID and {r["geo"] for r in read} == set(lae_tootus.GEOD)
    assert lehed_ulevaade.UNE_UUENDATUD == read[0]["uuendatud"] == lehed_ulevaade.tootuse_uuendatud()


def test_igapaevane_too_laeb_tootuse_ja_paneb_faili_commiti():
    yml = (JUUR.parent / ".github" / "workflows" / "sait-andmed.yml").read_text(encoding="utf-8")
    assert "python sait/lae_tootus.py" in yml
    assert "tehisaru-seire/sait/sisu/eurostat-tootus-kuud.csv" in yml.split("git add")[1].split("git diff")[0]


# ---------- registreeritud töötud (sait/lae_reg_tootud.py) ----------

import lae_reg_tootud  # noqa: E402


def reg_vastus(viimane_tyhi=True):
    """json-stat2 nagu Statistikaamet annab: Aasta × Kuu, viimase aasta lõpukuud on tühjad."""
    aastad, kuud = ["2024", "2025", "2026"], [str(k) for k in range(1, 13)]
    v = []
    for a in aastad:
        for k in kuud:
            tyhi = a == "2026" and int(k) > (10 if viimane_tyhi else 12)
            v.append(None if tyhi else 40000 + int(a) % 100 * 10 + int(k))
    return {"id": ["Aasta", "Kuu", "Sugu"], "size": [3, 12, 1], "value": v,
            "dimension": {"Aasta": {"category": {"index": {a: i for i, a in enumerate(aastad)}}},
                          "Kuu": {"category": {"index": {k: i for i, k in enumerate(kuud)}}},
                          "Sugu": {"category": {"index": {"1": 0}}}}}


def test_reg_tootud_viimased_25_kuud_ilma_tyhjade_kuudeta():
    read = lae_reg_tootud.read_vastusest(reg_vastus())
    assert len(read) == 25 and read[0][0] == "2024-10" and read[-1] == ("2026-10", 40000 + 260 + 10)
    assert dict(read)["2025-10"] == 40000 + 250 + 10  # aasta varasem kuu on olemas


def test_reg_tootud_paring_jatab_kuude_keskmise_valja():
    meta = {"variables": [
        {"code": "Aasta", "values": ["2023", "2024", "2025", "2026"], "valueTexts": ["2023", "2024", "2025", "2026"]},
        {"code": "Kuu", "values": ["00"] + [str(k) for k in range(1, 13)], "valueTexts": ["Kuude keskmine"] + ["x"] * 12},
        {"code": "Piirkond/Haldusüksus", "values": ["1", "2"], "valueTexts": ["Kogu Eesti", "Põhja-Eesti"]},
        {"code": "Sugu", "values": ["1", "2"], "valueTexts": ["Mehed ja naised", "Mehed"]},
        {"code": "Vanuserühm", "values": ["1", "2"], "valueTexts": ["Vanuserühmad kokku", "16-24"]}]}
    q = {x["code"]: x["selection"]["values"] for x in lae_reg_tootud.paring(meta, aastaid=3)["query"]}
    assert q["Kuu"] == [str(k) for k in range(1, 13)] and q["Aasta"] == ["2024", "2025", "2026"]
    assert q["Piirkond/Haldusüksus"] == ["1"] and q["Sugu"] == ["1"] and q["Vanuserühm"] == ["1"]


def test_reg_tootud_fail_muutub_ainult_siis_kui_arv_muutus():
    read = lae_reg_tootud.read_vastusest(reg_vastus())
    esimene = lae_reg_tootud.uus_seis([], read, "2026-11-16")
    vanad = [{k: str(v) for k, v in r.items()} for r in esimene]
    assert lae_reg_tootud.uus_seis(vanad, read, "2026-12-15") is None
    assert lae_reg_tootud.uus_seis(vanad, read[1:] + [("2026-11", 41000)], "2026-12-15")[-1]["uuendatud"] == "2026-12-15"


def test_reg_tootud_repo_fail_ja_igapaevane_too():
    kuud, avaldatud = lehed_ulevaade.reg_tootud()
    assert len(kuud) == lae_reg_tootud.KUID and avaldatud >= "2026-11-16"
    yml = (JUUR.parent / ".github" / "workflows" / "sait-andmed.yml").read_text(encoding="utf-8")
    assert "python sait/lae_reg_tootud.py" in yml
    assert "tehisaru-seire/sait/sisu/reg-tootud-kuud.csv" in yml.split("git add")[1].split("git diff")[0]
