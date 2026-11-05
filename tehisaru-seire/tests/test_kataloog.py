"""Kataloogi ja allikate võrdluse testid. NB: siinsed numbrid on väljamõeldud testandmed, mitte päris statistika.

Erand: test_paris_kataloog_on_kooskolas loeb päris kataloogifaile, et iga muudatus neis oleks kontrollitud.
"""

import csv
import json

from seire import kataloog

MOODIKU_VALJAD = ["id", "moiste", "nimi", "allikas", "andmestik", "filtrid", "populatsioon", "uhik", "periood",
                  "maaratlus", "klassifikaator", "vorreldavus", "erinevused", "naitaja", "registri_naitaja", "olek", "url",
                  "koopia"]
VAATLUSE_VALJAD = ["moodik", "riik", "aasta", "vaartus", "avaldatud", "kontrollitud", "kuidas", "url", "markus"]


def kirjuta(p, valjad, read):
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=valjad)
        w.writeheader()
        for r in read:
            w.writerow({k: r.get(k, "") for k in valjad})


def moodik(id, vorreldavus, olek="andmed", **lisa):
    return {"id": id, "moiste": "m1", "nimi": id, "vorreldavus": vorreldavus, "olek": olek, **lisa}


def naidiskataloog(juur, moodikud=None, vaatlused=None):
    k = juur / "kataloog"
    kirjuta(k / "kategooriad.csv", ["kood", "ulem", "nimi", "kirjeldus"],
            [{"kood": "T", "nimi": "Teema"}, {"kood": "T.A", "ulem": "T", "nimi": "Alateema"}])
    kirjuta(k / "moisted.csv", ["id", "kategooria", "nimi", "kusimus", "vordlusalus", "markus"],
            [{"id": "m1", "kategooria": "T.A", "nimi": "Testmõiste", "vordlusalus": "alus"}])
    kirjuta(k / "moodikud.csv", MOODIKU_VALJAD, moodikud or [
        moodik("alus", "alus", "seires", allikas="INT-EUROSTAT", naitaja="testnaitaja"),
        moodik("sama", "sama", registri_naitaja="testnaitaja"),
        moodik("osa", "osaliselt"),
        moodik("teine", "erinev"),
    ])
    kirjuta(k / "vaatlused-api.csv", VAATLUSE_VALJAD, vaatlused if vaatlused is not None else [
        {"moodik": "sama", "riik": "EE", "aasta": "2024", "vaartus": "10.0"},
        {"moodik": "sama", "riik": "EE", "aasta": "2025", "vaartus": "21.0"},
        {"moodik": "osa", "riik": "EE", "aasta": "2026", "vaartus": "30.5"},
        {"moodik": "osa", "riik": "FI", "aasta": "2025", "vaartus": "40.5"},
        {"moodik": "teine", "riik": "UK", "aasta": "2026", "vaartus": "35"},
        {"moodik": "teine", "riik": "EE", "aasta": "2025", "vaartus": "50"},
    ])
    kirjuta(juur / "andmed" / "testnaitaja.csv", ["geo", "time", "vaartus", "margend"], [
        {"geo": "EE", "time": "2024", "vaartus": "10.02"},
        {"geo": "EE", "time": "2025", "vaartus": "20.0"},
        {"geo": "FI", "time": "2025", "vaartus": "40.0"},
    ])
    (juur / "andmed" / "testnaitaja.meta.json").write_text(json.dumps(
        {"allikas_uuendas": "2026-06-15", "kontrollitud": "2026-10-27", "url": "https://example.org"}), encoding="utf-8")
    return kataloog.lae(juur)


def v(vaartus):
    return {"vaartus": float(vaartus), "tapsus": kataloog.tapsus(vaartus)}


def test_tapsus_loeb_komakohad_kirjapildist():
    assert kataloog.tapsus("22.2") == 1
    assert kataloog.tapsus("59") == 0
    assert kataloog.tapsus("23.4026") == 4


def test_hinda_vahe_eristab_ymardamist_vaikest_vahet_ja_lahknevust():
    assert kataloog.hinda_vahe(v("2.77"), v("2.8"))["staatus"] == "kooskolas"
    assert kataloog.hinda_vahe(v("5.19"), v("5.1"))["staatus"] == "vaike_vahe"
    assert kataloog.hinda_vahe(v("23.40"), v("22.2"))["staatus"] == "lahknevus"
    # Täisarvuna avaldatud number: lubatud on pool protsendipunkti.
    assert kataloog.hinda_vahe(v("42.03"), v("42"))["staatus"] == "kooskolas"


def test_lae_votab_seire_numbrid_andmefailist_eurostati_tapsusega(tmp_path):
    K = naidiskataloog(tmp_path)
    alus = [x for x in K["vaatlused"] if x["moodik"] == "alus"]
    assert len(alus) == 3
    assert all(x["tapsus"] == 2 for x in alus)
    assert {x["kuidas"] for x in alus} == {"seire põhiandmed"}


def test_vordle_ei_arvuta_vahet_erineva_moodikuga(tmp_path):
    V = kataloog.vordle(naidiskataloog(tmp_path), "m1")
    assert {p["moodik"] for p in V["paarid"]} == {"sama", "osa"}
    staatus = {(p["moodik"], p["aasta"]): p["staatus"] for p in V["paarid"]}
    assert staatus[("sama", 2024)] == "kooskolas"
    assert staatus[("sama", 2025)] == "lahknevus"


def test_vordle_hoiab_eri_klasside_numbrid_eri_veergudes(tmp_path):
    V = kataloog.vordle(naidiskataloog(tmp_path), "m1")
    ee = V["riigid"]["EE"]
    assert ee["alus"]["aasta"] == 2025
    assert ee["uuem"]["moodik"] == "osa" and ee["uuem"]["aasta"] == 2026
    assert [x["moodik"] for x in ee["muud"]] == ["teine"]
    # Soome osaliselt võrreldav number pole uuem kui võrdlusalus, nii et seda uuemana ei näidata.
    assert V["riigid"]["FI"]["uuem"] is None
    assert V["riigid"]["UK"]["alus"] is None


def test_kriitiline_lahter_ja_koopia_on_eraldi(tmp_path):
    """C5 juhtum: üldine määr võib olla hea, aga Eesti viimase aasta lahter ei klapi. Koopia ei loe kinnituseks."""
    K = naidiskataloog(tmp_path, moodikud=[
        moodik("alus", "alus", "seires", allikas="INT-EUROSTAT", naitaja="testnaitaja"),
        moodik("sama", "sama"),
        moodik("koopia", "sama", koopia="jah"),
    ], vaatlused=[
        {"moodik": "sama", "riik": "EE", "aasta": "2024", "vaartus": "10.0"},
        {"moodik": "sama", "riik": "EE", "aasta": "2025", "vaartus": "21.0"},
        {"moodik": "sama", "riik": "FI", "aasta": "2025", "vaartus": "40.0"},
        {"moodik": "koopia", "riik": "EE", "aasta": "2025", "vaartus": "20.0"},
        {"moodik": "koopia", "riik": "FI", "aasta": "2025", "vaartus": "40.0"},
    ])
    V = kataloog.vordle(K, "m1")
    kriitilised = {(p["moodik"], p["riik"], p["aasta"]) for p in V["paarid"] if p["kriitiline"]}
    # Soome pole kriitiline riik, Eesti 2024 pole viimane aasta.
    assert kriitilised == {("sama", "EE", 2025), ("koopia", "EE", 2025)}
    kl = kataloog.klappimine(V["paarid"])
    assert (kl["kriitilised"]["klapib"], kl["kriitilised"]["kokku"]) == (0, 1)
    assert [(p["riik"], p["aasta"]) for p in kl["kriitilised"]["lahknevused"]] == [("EE", 2025)]
    assert (kl["koik"]["klapib"], kl["koik"]["kokku"]) == (2, 3)
    assert kl["koopiaid"] == 2


def test_moodikud_on_jarjestatud_vorreldavuse_jargi(tmp_path):
    V = kataloog.vordle(naidiskataloog(tmp_path), "m1")
    assert [m["id"] for m in V["moodikud"]] == ["alus", "sama", "osa", "teine"]


def test_kontrolli_leiab_vead(tmp_path):
    K = naidiskataloog(tmp_path, moodikud=[
        moodik("alus", "alus", "seires", naitaja="testnaitaja"),
        moodik("vale", "sama", moiste="puudub"),
        moodik("kavas", "osaliselt", "kavandatud"),
    ], vaatlused=[
        {"moodik": "kavas", "riik": "EE", "aasta": "2025", "vaartus": "1.0"},
        {"moodik": "kavas", "riik": "EE", "aasta": "2025", "vaartus": "1.0"},
        {"moodik": "tundmatu", "riik": "EE", "aasta": "2025", "vaartus": "1.0"},
    ])
    vead = " ".join(kataloog.kontrolli(K))
    assert "mõistet puudub pole" in vead
    assert "on kaks korda" in vead
    assert "mõõdikut tundmatu pole" in vead
    assert "Muuda olekuks „andmed“" in vead


def test_kooskola_leiab_erineva_kasitsi_numbri(tmp_path):
    K = naidiskataloog(tmp_path)
    kirjuta(tmp_path / "allikad" / "numbrid-2026.csv", ["naitaja", "riik", "aasta", "vaartus", "allikas"], [
        {"naitaja": "testnaitaja", "riik": "EE", "aasta": "2025", "vaartus": "21.0", "allikas": "klapib"},
        {"naitaja": "testnaitaja", "riik": "EE", "aasta": "2024", "vaartus": "11.0", "allikas": "erineb"},
        {"naitaja": "testnaitaja", "riik": "LV", "aasta": "2025", "vaartus": "5.0", "allikas": "puudub"},
    ])
    tulem = {r["kirje"].split("(")[1].rstrip(")"): r["staatus"] for r in kataloog.kooskola(K, tmp_path)}
    assert tulem == {"klapib": "klapib", "erineb": "erineb", "puudub": "kataloogis puudub"}


def test_paris_kataloog_on_kooskolas():
    K = kataloog.lae()
    assert kataloog.kontrolli(K) == []
    # "kataloogis puudub" on töö järjekord (lehel näha), aga erinev number on viga.
    assert [r for r in kataloog.kooskola(K) if r["staatus"] == "erineb"] == []
