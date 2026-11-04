"""Uue saidi (sait/) testid: pealkirjade numbrid tulevad andmetest, eri klassid ei ole ühel teljel, lingid töötavad."""

import csv
import json
import re
import sys
from pathlib import Path

import pytest

JUUR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(JUUR / "sait"))
import andmekiht  # noqa: E402
import komponendid  # noqa: E402
import pealkiri  # noqa: E402

# tests/kuld/ehita.py kannab sama moodulinime, seepärast laaditakse generaator failiteelt
import importlib.util  # noqa: E402

_spec = importlib.util.spec_from_file_location("sait_ehita", JUUR / "sait" / "ehita.py")
ehita = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ehita)

EB = "ettevotete-tehisaru-kasutus"


@pytest.fixture(scope="module")
def A():
    return andmekiht.lae()


@pytest.fixture(scope="module")
def sait(A, tmp_path_factory):
    kaust = tmp_path_factory.mktemp("sait")
    failid = ehita.ehita(kaust, A)
    return {f: (kaust / f).read_text(encoding="utf-8") for f in failid}


def tekst(h):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", h))


def test_igal_vaatlusel_on_klass_ja_allikas(A):
    assert A["vaatlused"]
    for v in A["vaatlused"]:
        assert v["klass"] in andmekiht.KLASSID
        assert v["url"].startswith("http")


def test_iga_2026_number_saab_moodiku_kataloogist(A):
    uued = [r for r in csv.DictReader(open(JUUR / "allikad" / "numbrid-2026.csv", encoding="utf-8")) if r["vaartus"]]
    for r in uued:
        v = [x for x in A["vaatlused"] if x["naitaja"] == r["naitaja"] and x["geo"] == r["riik"] and x["aasta"] == int(r["aasta"])
             and x["klass"] != "alus"]
        assert v, f"{r['naitaja']} {r['riik']} {r['aasta']} puudub vaatlustest"


def test_eesti_ettevotete_2026_ei_ole_elii_skaalaga_sama_klass(A):
    ee26 = andmekiht.leia(A, EB, "EE", 2026)
    assert ee26["klass"] == "osaliselt"  # uus klassifikaator EMTAK 2025 (kataloog: sa-it1490)
    assert andmekiht.leia(A, EB, "EE", "uusim:alus")["aasta"] == 2025


def test_skaala_keeldub_eri_klassidest(A):
    segu = [andmekiht.leia(A, EB, "EE", 2025), andmekiht.leia(A, EB, "EE", 2026)]
    with pytest.raises(komponendid.VorreldavusViga):
        komponendid.ribad(segu, 50)
    skaalal, muud = komponendid.jaga_klassid(segu)
    assert [v["aasta"] for v in skaalal] == [2025] and [v["aasta"] for v in muud] == [2026]


def test_mall_kukub_kui_vaatlust_pole(A):
    with pytest.raises(andmekiht.AndmeViga):
        pealkiri.taida("{ettevotete-tehisaru-kasutus|XX|2025|p1}", A)


def test_ummardus_pooled_ules():
    assert komponendid.pr(19.95) == "20,0"
    assert pealkiri.pr(34.1, 0) == "34"


def test_h1_numbrid_on_samad_mis_andmetes(A, sait):
    vaated = ehita.lae_vaated()
    for v in vaated:
        if v["olek"] != "valmis":
            continue
        h1 = re.search(r"<h1>(.*?)</h1>", sait[v["fail"]], re.S).group(1)
        for naitaja, geo, aasta, vorm in pealkiri.viited(v["h1"]):
            oodatud = pealkiri.vaartus(A, naitaja, geo, aasta, vorm)
            assert oodatud in tekst(h1), f"{v['fail']}: {naitaja} {geo} {aasta} = {oodatud} puudub pealkirjast"


def test_ettevotete_h1_vaide_klapib_andmetega(A):
    """„keskmisest ees, Soomest, Rootsist ja Taanist taga“ peab andmetes kehtima."""
    ee = andmekiht.leia(A, EB, "EE", "uusim:alus")
    eu = andmekiht.leia(A, EB, andmekiht.EL, ee["aasta"])
    assert ee["vaartus"] > eu["vaartus"]
    for g in ("FI", "SE", "DK"):
        assert andmekiht.leia(A, EB, g, ee["aasta"])["vaartus"] > ee["vaartus"]


def test_ettevotete_koht_ja_el_keskmine_lehel(A, sait):
    h = tekst(sait["ettevotted.html"])
    koht = andmekiht.koht(A, EB, "EE", 2025)
    assert f"Eesti 27 riigi seas {koht}. kohal" in h
    assert "EL 20,0%" in h  # Eurostat 19,95


def test_eurostati_skaalal_on_ainult_el_riigid(A, sait):
    h = sait["ettevotted.html"]
    graafik = h.split('id="g-kasutus"')[1].split("</figure>")[0]
    for riik in ("Norra", "Ühendkuningriik", "Kanada"):
        assert riik not in graafik


def test_uks_h1_ja_ehitamata_teema_pole_link(sait):
    for f, h in sait.items():
        assert h.count("<h1") == 1, f
        assert 'href="inimesed.html"' not in h  # Inimesed on veel „kavas“


def test_mitteavalik_sisu_puudub(sait):
    keelatud = ["38/109", "35% + 32%", "Restricted", "DRO", "AIAT", "tööplaan"]
    for f, h in sait.items():
        for k in keelatud:
            assert k not in h, f"{f}: {k}"


def test_sihid_klapivad_naitajate_registriga(A):
    reg = json.loads((JUUR / "naitajad.json").read_text(encoding="utf-8"))
    for s in A["sihid"].values():
        n = next(x for x in reg["naitajad"] if x["id"] == s["naitaja"])
        assert any(float(x["vaartus"]) == float(s["siht"]) for x in n.get("sihid", [])), s["id"]


def test_kontroll_leiab_katkise_lingi():
    with pytest.raises(ehita.EhitusViga):
        ehita.kontrolli("x.html", '<h1>a</h1><a href="puudub.html">x</a>', {"x.html"})
    with pytest.raises(ehita.EhitusViga):
        ehita.kontrolli("x.html", "<h1>a</h1><h3>b</h3>", {"x.html"})


def test_kaardil_on_koik_27_riiki_oige_varviga(A, sait):
    """Kaart tulpade asemel (4.11.2026): iga ELi riik on oma klassis, Eesti esile tõstetud."""
    graafik = sait["ettevotted.html"].split('id="g-kasutus"')[1].split("</figure>")[0]
    el = andmekiht.el27_aasta(A, EB, 2025)
    for g, v in el.items():
        k = max(i for i, p in enumerate((0, 10, 20, 30, 40)) if v["vaartus"] >= p)
        nimi = komponendid.riik(g)
        assert re.search(rf'<path class="k{k}( fookus)?" d="[^"]+" data-n="{nimi}" data-v="{komponendid.pr(v["vaartus"])}%"', graafik), g
    assert 'class="k2 fookus"' in graafik and "Eesti 23,4%" in tekst(graafik)
    assert "EL keskmine 20,0%" in tekst(graafik)
