"""Testid. NB: siinsed numbrid on väljamõeldud testandmed, mitte päris statistika."""

import json
from datetime import date

import run
from seire import eurostat, kaart, kontrollid, statistikaamet, usaldus


def naidis_json_stat():
    """Väike väljamõeldud JSON-stat vastus Eurostati vormingus: 3 riiki × 2 aastat."""
    return {
        "label": "Testandmestik",
        "updated": "2025-12-15T23:00:00+0100",
        "id": ["freq", "indic_is", "unit", "geo", "time"],
        "size": [1, 1, 1, 3, 2],
        "dimension": {
            "freq": {"category": {"index": {"A": 0}, "label": {"A": "Annual"}}},
            "indic_is": {"category": {"index": {"E_AI_TANY": 0}, "label": {"E_AI_TANY": "Test AI indicator"}}},
            "unit": {"category": {"index": {"PC_ENT": 0}, "label": {"PC_ENT": "Percentage of enterprises"}}},
            "geo": {"category": {"index": {"EE": 0, "FI": 1, "EU27_2020": 2}, "label": {}}},
            "time": {"category": {"index": {"2024": 0, "2025": 1}, "label": {}}},
        },
        # asukoht = geo * 2 + time
        "value": {"0": 10.0, "1": 20.0, "2": 30.0, "3": 40.0, "4": 15.0, "5": 25.0},
        "status": {"1": "p"},
    }


def test_json_stat_ridadeks_paneb_vaartused_oigesse_kohta():
    read = eurostat.json_stat_ridadeks(naidis_json_stat())
    leitud = {(r["geo"], r["time"]): r["vaartus"] for r in read}
    assert leitud[("EE", "2024")] == 10.0
    assert leitud[("EE", "2025")] == 20.0
    assert leitud[("FI", "2025")] == 40.0
    assert leitud[("EU27_2020", "2024")] == 15.0
    assert next(r for r in read if r["geo"] == "EE" and r["time"] == "2025")["margend"] == "p"


def test_kontroll_leiab_kordused():
    read = [{"geo": "EE", "time": "2025", "vaartus": 1.0, "margend": ""}] * 2
    tasemed = [p["tase"] for p in kontrollid.kontrolli_kordusi(read)]
    assert tasemed == ["viga"]


def test_kontroll_leiab_vahemikust_valja():
    read = [{"geo": "EE", "time": "2025", "vaartus": 120.0, "margend": ""}]
    assert kontrollid.kontrolli_vahemikku(read, 0, 100)[0]["tase"] == "viga"


def test_kontroll_leiab_puuduva_riigi():
    read = eurostat.json_stat_ridadeks(naidis_json_stat())
    probleemid = kontrollid.kontrolli_riike(read, ["EE", "FI", "SE"])
    assert "SE" in probleemid[0]["tekst"]


def test_tuhjad_andmed_on_viga():
    assert kontrollid.kontrolli([], ["EE"])[0]["tase"] == "viga"


def test_varskus_staatused():
    uuendatud = date(2025, 12, 15)
    assert usaldus.varskus(uuendatud, 12, date(2026, 6, 1))["staatus"] == "ajakohane"
    assert usaldus.varskus(uuendatud, 12, date(2026, 12, 1))["staatus"] == "aegumas"
    assert usaldus.varskus(uuendatud, 12, date(2027, 6, 1))["staatus"] == "aegunud"
    assert usaldus.varskus(uuendatud, 12, date(2026, 6, 1))["jargmine_oodatav"] == "2026-12-15"


def test_lisa_kuud_kuu_lopus():
    assert usaldus.lisa_kuud(date(2025, 1, 31), 1) == date(2025, 2, 28)


def test_vordlus_leiab_vastuolu():
    read = [{"geo": "EE", "time": "2025", "vaartus": 22.0, "margend": ""}]
    teised = [
        {"allikas": "A", "riik": "EE", "aasta": 2025, "vaartus": 23.4, "usaldus": "", "url": ""},
        {"allikas": "B", "riik": "EE", "aasta": 2025, "vaartus": 22.2, "usaldus": "", "url": ""},
        {"allikas": "C", "riik": "EE", "aasta": 2030, "vaartus": 50.0, "usaldus": "", "url": ""},
    ]
    tulemus = usaldus.vordle_allikaid(read, teised)
    assert tulemus[0]["vastuolu"] is True and tulemus[0]["vahe"] == 1.4
    assert tulemus[1]["vastuolu"] is False
    assert tulemus[2]["vastuolu"] is None


def test_pealkiri_on_vaide():
    read = eurostat.json_stat_ridadeks(naidis_json_stat())
    pealkiri = kaart.pealkiri_vaitena(read)
    assert pealkiri.startswith("Eesti on 2 riigi seas 2. kohal: 20,0% aastal 2025")
    assert "alla ELi keskmise (25,0%)" in pealkiri


def test_arv_umardab_poole_ules_ja_tuhi_on_kriips():
    assert kaart.arv(19.95) == "20,0"
    assert kaart.arv(5.19) == "5,2"
    assert kaart.arv(None) == "–"
    assert kaart.protsent(None) == "–"
    assert kaart.protsent(23.4) == "23,4%"


def test_kogu_toru_teeb_failid_ja_logib_muutuse(tmp_path, monkeypatch):
    monkeypatch.setattr(run, "ANDMED", tmp_path / "andmed")
    monkeypatch.setattr(run, "KAARDID", tmp_path / "kaardid")
    monkeypatch.setattr(run, "MUUTUSED", tmp_path / "andmed" / "muutused.csv")
    (tmp_path / "andmed").mkdir()
    (tmp_path / "kaardid").mkdir()
    naitaja = {**run.loe_seadistus()["naitajad"][0], "filtrid_kontrollitud": False}
    riigid = ["EE", "FI", "EU27_2020"]

    andmed = naidis_json_stat()
    kokkuvote = run.tootle(naitaja, riigid, andmed, "2026-06-01")
    assert kokkuvote["eesti"] == 20.0
    assert kokkuvote["staatus"] == "ajakohane"
    assert (tmp_path / "kaardid" / f"{naitaja['id']}.md").exists()
    assert not (tmp_path / "andmed" / "muutused.csv").read_text(encoding="utf-8").strip().count("\n")

    andmed["value"]["1"] = 21.0  # Eurostat muutis Eesti 2025. aasta väärtust
    run.tootle(naitaja, riigid, andmed, "2026-07-01")
    logi = (tmp_path / "andmed" / "muutused.csv").read_text(encoding="utf-8")
    assert "2026-07-01" in logi and "20.0" in logi and "21.0" in logi
    kaardi_tekst = (tmp_path / "kaardid" / f"{naitaja['id']}.md").read_text(encoding="utf-8")
    assert "Filtrid on kontrollimata" in kaardi_tekst
    assert "| 2026-07-01 | Eesti 2025 | 20.0 | 21.0 |" in kaardi_tekst


def test_uuem_allikas_leiab_uuema_aasta():
    read = [{"geo": "EE", "time": "2025", "vaartus": 23.4, "margend": ""}, {"geo": "FI", "time": "2026", "vaartus": 40.0, "margend": ""}]
    teised = [
        {"allikas": "A", "riik": "EE", "aasta": 2025, "vaartus": 22.2},
        {"allikas": "B", "riik": "EE", "aasta": 2026, "vaartus": 34.1},
    ]
    assert usaldus.uuem_allikas(read, teised)["allikas"] == "B"
    assert usaldus.uuem_allikas(read, teised[:1]) is None
    assert usaldus.uuem_allikas([], teised) is None


def naidis_pxweb():
    """Väljamõeldud Statistikaameti vastus (json-stat2): väärtused on nimekiri, puuduv väärtus on None."""
    return {
        "id": ["Naitaja", "Aasta"],
        "size": [1, 3],
        "dimension": {
            "Naitaja": {"category": {"index": {"AI": 0}, "label": {"AI": "Tehisaru"}}},
            "Aasta": {"category": {"index": {"2024": 0, "2025": 1, "2026": 2}, "label": {}}},
        },
        "value": [13.9, None, 34.1],
    }


def test_json_stat_nimekirjaga_vaartused():
    read = eurostat.json_stat_ridadeks(naidis_pxweb())
    assert {r["Aasta"]: r["vaartus"] for r in read} == {"2024": 13.9, "2026": 34.1}


def test_statistikaameti_kirje_ja_paring():
    seadistus = {"tabel": "majandus/infotehnoloogia/infotehnoloogia-ettevettes/IT1490", "aasta_moode": "Aasta"}
    kirje = statistikaamet.riiklik_allikas(seadistus, naidis_pxweb())
    assert (kirje["aasta"], kirje["vaartus"], kirje["riik"]) == (2026, 34.1, "EE")
    assert kirje["url"] == "https://andmed.stat.ee/et/stat/majandus__infotehnoloogia__infotehnoloogia-ettevettes/IT1490"
    paring = statistikaamet.koosta_paring({"Aasta": ["2025", "2026"]})
    assert paring["query"][0] == {"code": "Aasta", "selection": {"filter": "item", "values": ["2025", "2026"]}}


def test_statistikaameti_mitu_vaartust_aastas_on_viga():
    andmed = naidis_pxweb()
    andmed["size"] = [2, 3]
    andmed["dimension"]["Naitaja"]["category"]["index"] = {"AI": 0, "ML": 1}
    andmed["value"] = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]
    try:
        statistikaamet.aastate_vaartused(andmed, "Aasta")
    except ValueError:
        return
    raise AssertionError("mitu väärtust aastas peab andma vea")


def test_toru_hoiatab_uuemast_riiklikust_numbrist(tmp_path, monkeypatch):
    monkeypatch.setattr(run, "ANDMED", tmp_path / "andmed")
    monkeypatch.setattr(run, "KAARDID", tmp_path / "kaardid")
    monkeypatch.setattr(run, "MUUTUSED", tmp_path / "andmed" / "muutused.csv")
    (tmp_path / "andmed").mkdir()
    (tmp_path / "kaardid").mkdir()
    naitaja = {**run.loe_seadistus()["naitajad"][0], "teised_allikad": []}
    riiklik = {"allikas": "Statistikaamet, tabel X", "riik": "EE", "aasta": 2026, "vaartus": 34.1, "usaldus": "", "url": ""}

    kokkuvote = run.tootle(naitaja, ["EE", "FI", "EU27_2020"], naidis_json_stat(), "2026-06-01", riiklik, "Tabelit Y ei õnnestunud laadida")
    assert kokkuvote["uuem_allikas"] is True
    meta = json.loads((tmp_path / "andmed" / f"{naitaja['id']}.meta.json").read_text(encoding="utf-8"))
    assert meta["uuem_allikas"]["aasta"] == 2026
    tekstid = [p["tekst"] for p in meta["probleemid"]]
    assert any("Uuem number on juba olemas" in t and "34,1%" in t for t in tekstid)
    assert "Tabelit Y ei õnnestunud laadida" in tekstid
