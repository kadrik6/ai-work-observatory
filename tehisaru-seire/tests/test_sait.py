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
import abi  # noqa: E402
import lehed_teemad  # noqa: E402
import lehed_usaldus  # noqa: E402

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
        # Kadri 10.11.2026: pikk mall jaguneb „ ¦ “ kohalt lühikeseks h1-ks ja lead-iks; numbrid peavad olema nende kahe sees
        h1 = re.search(r'<h1>(.*?)</h1>(?:\s*<p class="lead">(.*?)</p>)?', sait[v["fail"]], re.S)
        h1 = h1.group(1) + " " + (h1.group(2) or "")
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


def test_uks_h1_ja_iga_valmis_vaade_on_ehitatud(sait):
    for f, h in sait.items():
        assert h.count("<h1") == 1, f
    for v in ehita.lae_vaated():
        if v["olek"] == "valmis":
            assert v["fail"] in sait, v["id"]


def test_ehitamata_teema_pole_link():
    vaated = [{"id": "x", "fail": "x.html", "olek": "kavas"}, {"id": "y", "fail": "y.html", "olek": "valmis"}]
    assert "href" not in abi.link(vaated, "x", "X")
    assert 'href="y.html#a"' in abi.link(vaated, "y", "Y", "a")


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
    # Kadri 11.11.2026: Eesti eraldi silti kaardil pole; number tuleb hõljudes ja kõrvaltabelist
    assert 'class="k2 fookus"' in graafik and 'data-n="Eesti" data-v="23,4%"' in graafik and "kaart-silt" not in graafik
    assert "EL keskmine 20,0%" in tekst(graafik)


# ------------------------------------------------------------------ uued vaated (5.11.2026)

def _vaade(vid):
    return next(v for v in ehita.lae_vaated() if v["id"] == vid)


def _muudetud(vid, vana, uus):
    v = dict(_vaade(vid))
    assert vana in v["h1"], v["h1"]
    v["h1"] = v["h1"].replace(vana, uus)
    return v


def test_alus_ja_sama_tohivad_olla_uhel_teljel_osaliselt_mitte():
    alus = {"klass": "alus", "naitaja": "n", "geo": "EE", "aasta": 2025}
    komponendid.uks_klass([alus, dict(alus, klass="sama", geo="NO")])
    with pytest.raises(komponendid.VorreldavusViga):
        komponendid.uks_klass([alus, dict(alus, klass="osaliselt", geo="DK")])


@pytest.mark.parametrize("vid, vana, uus, ehitaja", [
    ("avalik-sektor", "Iga neljas", "Iga kolmas", lehed_teemad.avalik_sektor),
    ("kas-tosi", "kaks Eurostati", "kolm Eurostati", lehed_usaldus.kas_tosi),
    ("reeglid", "2.12.2027", "2.08.2027", lehed_teemad.reeglid),
    ("kuidas", "21 allikast", "20 allikast", lehed_usaldus.kuidas),
])
def test_pealkiri_mida_mall_ei_kata_kontrollitakse_andmetest(A, vid, vana, uus, ehitaja):
    with pytest.raises(andmekiht.AndmeViga):
        ehitaja(A, _muudetud(vid, vana, uus), ehita.lae_vaated())


def test_avaliku_sektori_h1_kukub_kui_numbrid_muutuvad(A):
    A2 = dict(A, avalik={k: (dict(r, vaartus="40") if r["id"] == "genai-kesk" else r) for k, r in A["avalik"].items()})
    with pytest.raises(andmekiht.AndmeViga):
        lehed_teemad.avalik_sektor(A2, _vaade("avalik-sektor"), ehita.lae_vaated())


def test_hoive_muutus_ainult_molemal_aastal_avaldatud_lahtritest(A):
    g = A["kokkupuude"]["aeg_uhtlane"][("EE", "T")]
    assert round((g[max(g)]["muud"] / g[2022]["muud"] - 1) * 100, 1) == 3.7


def test_vahter_silt_ja_wef_ilma_nimeta(A):
    assert A["uuringud"]["vahter2026"]["silt"] == "tugev andmestik, nõrk tulemus"
    assert not any("Hundimägi" in (v["kes"] + v["valjaanne"] + v["selgitus"]) for v in A["vaited"])


def test_oecd_28_protsenti_on_48_170st(A):
    gk = next(r for r in A["avalik"].values() if r["id"] == "genai-kesk")
    assert (int(gk["lugeja"]), int(gk["nimetaja"])) == (48, 170)
    assert round(48 / 170 * 100) == int(gk["vaartus"]) == 28


def test_tahtajad_loetakse_tanasest_paevast(A):
    v, vaated = _vaade("reeglid"), ehita.lae_vaated()
    nyyd = tekst(lehed_teemad.reeglid(A, v, vaated, tana="2026-11-05"))
    assert "viis on möödas, kolm on veel ees" in nyyd
    hiljem = tekst(lehed_teemad.reeglid(A, v, vaated, tana="2028-12-01"))
    assert "kaheksa on möödas, null on veel ees" in hiljem


def test_vaited_kuuluvad_valjaandele_mitte_inimesele(sait):
    h = tekst(sait["kas-see-on-tosi.html"])
    assert "Hundimägi" not in h
    assert "ERR, Vikerraadio päevakommentaar" in h


def test_avalik_sektor_pohineb_avalikul_raportil(sait):
    h = sait["avalik-sektor.html"]
    assert "c2c09a06-en" in h or "strengthening-the-innovative-capacity" in h
    for k in ("38/109", "Restricted", "webinar"):
        assert k not in h


def _jaotis(h, ank):
    return h.split(f'id="{ank}"')[1].split("</section>")[0]


def test_sihid_on_oma_teema_juures_ja_eesti_siht_on_fookuses(sait):
    # Sisuloogika 6.11.2026, Kadri otsus 4: sihid teemade juurde, määruse lehel ainult tähtajad.
    # Paigutus 6.11.2026 22:27 (ettepanek 4): siht on üks rida näitaja enda plokis, mitte eraldi plokk
    assert _jaotis(sait["ettevotted.html"], "kasutus").count('class="sihiriba fookus"') == 1
    assert _jaotis(sait["ettevotted-voimekus.html"], "digi").count('class="siht-rida"') == 1
    assert _jaotis(sait["ettevotted-voimekus.html"], "ta").count('class="siht-rida"') == 1
    assert _jaotis(sait["inimesed-oskused.html"], "digi").count('class="siht-rida"') == 1
    assert not any('id="siht-' in h for h in sait.values())
    assert 'id="sihid"' not in sait["tehisaru-maarus.html"]


def test_kokkupuute_osad_summeeruvad_ja_pealkiri_tuleb_andmetest(A, sait):
    K = A["kokkupuude"]
    assert abs(sum(K["osa"].values()) + K["liigitamata"] - 100) < 0.01
    assert K["ilo_ameteid"] == 427 and K["ilo_avatud_ameteid"] == 112  # ILO WP140 tabel A1
    h2 = re.search(r'<h2 id="h-kokkupuude">(.*?)</h2>', sait["too-ametid.html"], re.S).group(1)
    assert f'{komponendid.pr(K["avatud"], 0)}%' in h2
    assert f'<b>{komponendid.pr(K["korge"], 0)}% kõige avatumates</b>' in h2


def test_kokkupuude_ei_ole_moju_ja_el_vordlus_on_eraldi(sait):
    s = sait["too-ametid.html"]
    jaotis = s[s.index('id="kokkupuude"'):s.index('id="hoive"')]
    assert "Kokkupuude ei ole mõju" in jaotis
    # ELi ligikaudne võrdlus on tekstis, mitte Eesti 4-kohalise numbriga samal graafikul
    graafik = jaotis[jaotis.index("<figure"):jaotis.index("</figure>")]
    assert "ELile" not in graafik and "EL " not in graafik


def test_kokkupuute_andmed_kukuvad_valjult(tmp_path):
    import shutil
    sisu = JUUR / "sait" / "sisu"
    for f in ("ilo-kokkupuude-2025.csv", "ee-tootajad-ametid-2022.csv", "eurostat-hoive-ametid-2025.csv"):
        shutil.copy(sisu / f, tmp_path / f)
    p = tmp_path / "ilo-kokkupuude-2025.csv"
    p.write_text(p.read_text(encoding="utf-8").replace("1111,ei,", "1111,kõrge,", 1), encoding="utf-8")
    with pytest.raises(andmekiht.AndmeViga):
        andmekiht.arvuta_kokkupuude(tmp_path)


def test_hoive_aegrida_naised_ja_mehed_annavad_kokku(tmp_path):
    read = list(csv.DictReader(open(JUUR / "sait" / "sisu" / "eurostat-hoive-ametid-2021-2025.csv", encoding="utf-8")))
    ee = {(r["sugu"], r["isco"]): r for r in read if r["geo"] == "EE"}
    for (sugu, isco), r in ee.items():
        if sugu != "T" or ("F", isco) not in ee:
            continue
        for y in ("2021", "2022", "2023", "2024", "2025"):
            f, m, t = ee[("F", isco)][y], ee[("M", isco)][y], r[y]
            if f and m and t:
                assert abs(float(f) + float(m) - float(t)) <= 0.15, (isco, y)


def test_hoive_muutuse_jaotis_on_kirjeldus_mitte_pohjus(A, sait):
    s = sait["too-ametid.html"]
    jaotis = s[s.index('id="hoive"'):s.index('</main>')]
    assert "kirjeldus, mitte põhjus" in jaotis
    g = A["kokkupuude"]["aeg"][("EE", "T")]
    assert g[2025]["avatud"] / g[2022]["avatud"] < g[2025]["muud"] / g[2022]["muud"]


# ---- Töölaud (5.11.2026)

import lehed_ulevaade  # noqa: E402


def test_ulevaade_on_toolaud_kaardi_ja_jarjestusega_samal_real(A, sait):
    h = sait["index.html"]
    assert h.count('class="plaat') == 6
    rida = h.split('class="el-rida"')[1].split("</section>")[0]
    # Kadri 7.11.2026: loendi asemel järjestuse muutus aastate kaupa; kaart jääb samale reale
    assert 'class="el-kaart"' in rida and 'class="bump-k"' in rida
    koik = re.search(r'<div class="bump-v" data-n="27".*?</div>', rida, re.S).group(0)
    nimed = set(re.findall(r'<g class="bs[^"]*" data-s="[^"]+" tabindex="-?[01]" role="button" aria-label="([^"]+)"', koik))
    assert len(nimed) == len(A["el_riigid"])
    for n in nimed:
        assert f'data-n="{n}"' in rida.split('class="el-bump"')[0]  # sama nimi ka kaardil


def test_teemalehel_on_kaart_ja_jarjestus_korvuti(sait):
    # Kadri 11.11.2026: „kaart ja selle graafik peaks alati olema täpselt kõrvuti“. Mõlemad joonised on samas
    # .kaart-paar reas ja muu sisu (vastavus, numbrid, usaldus) tuleb nende järel.
    for leht in ("ettevotted.html", "inimesed.html"):
        j = sait[leht].split('id="kasutus"')[1].split("</section>")[0]
        paar = j.split('class="ruut3 kaart-paar"')[1].split('class="kulg-all"')[0]
        assert paar.count("<figure") == 2, leht
        assert 'id="g-kasutus"' in paar and 'id="g-jrj"' in paar, leht
        assert paar.index('id="g-kasutus"') < paar.index('id="g-jrj"'), leht
        assert paar.count('class="kp-sisu"') == 2, leht


def test_ulevaate_tootuse_kuunumber_tuleb_failist(sait):
    kuu, v = lehed_ulevaade.tootus()["EE"][-1]
    assert f"töötus oli {lehed_ulevaade.kuu_seesytlev(kuu)} {komponendid.pr(v)}%" in tekst(sait["index.html"])
    # 5.11 sisuloogika: töötus ei ole avalehe h1-s tehisaru kasutuse kõrval
    assert "töötus" not in re.search(r"<h1>(.*?)</h1>", sait["index.html"], re.S).group(1)


def test_kuu_seesytlev_on_eesti_keeles():
    assert [lehed_ulevaade.kuu_seesytlev(f"2026-{k:02d}") for k in (3, 5, 9)] == ["märtsis", "mais", "septembris"]


def test_too_vaates_on_eesti_tooturg_praegu(A, sait):
    h = sait["too.html"]
    assert 'id="tootus-kuud"' in h and 'id="koondamised"' in h
    juhtumid = A["koondamised"]["juhtumid"]
    assert 'class="kk"' not in h  # kaardid võeti maha (Kadri 7.11.2026 08:48)
    # pealkiri ütleb, mitu nimetas tehisaru otsese põhjusena; see tuleb andmetest
    otsene = sum(r["roll"] == "otsene" for r in juhtumid)
    assert ("mitte ükski" if otsene == 0 else abi.ARVSONAD[otsene]) in h.split('id="h-koondamised">')[1].split("</h2>")[0]
    # koondamised on ainult Töö vaates
    assert 'id="koondamised"' not in sait["index.html"]


def test_hangete_aastaid_ei_vorrelda_enne_inimese_kontrolli(sait):
    # Kadri otsus 5 (6.11.2026): ainult viimase aasta arv sildiga „katseline“, kuni 100 hanget on pimesi märgistatud
    osa = _jaotis(sait["hanked.html"], "aastad")
    # Kadri 8.11.2026 16:29: pimeülevaatus tehtud, „katseline“ ära; aastaid ikka ei võrrelda enne klassifikaatori uuendust
    assert "katseline" not in osa and "pimesi" in osa and "tulbad2" not in osa
    assert "pimesi" in _jaotis(sait["index.html"], "hanked") and "aastatulbad" not in _jaotis(sait["index.html"], "hanked")
    assert 'id="hanked"' not in sait["avalik-sektor.html"]


def test_menuus_on_kaheksa_teemat_ja_usaldus_on_oma_teema(sait):
    # Kadri 6.11.2026 21:59: Hanked on oma menüüpunkt. 22:27 (paigutuse ettepanekud 1–3, 10): Usaldus oma menüükoht
    menuu = re.search(r'<ul class="menu">(.*?)</ul>', sait["index.html"], re.S).group(1)
    # Kadri 11.11.2026 (ülesehituse kontroll D): Avalik sektor, Hanked ja Tehisaru määrus on ühe punkti „Riik“ all
    assert re.findall(r">([^<>]+)</a>", menuu) == ["Avaleht", "Inimesed", "Ettevõtted", "Töö", "Riik", "Uudised", "Usaldus"]
    for f in ("avalik-sektor.html", "hanked.html", "hanked-naited.html", "tehisaru-maarus.html", "eesti-otsused.html"):
        assert '<a href="avalik-sektor.html" aria-current="page">Riik</a>' in sait[f], f
        alam = re.search(r'<ul class="alamlehed">(.*?)</ul>', sait[f]).group(1)
        assert re.findall(r">([^<>]+)</a>", alam) == ["Avalik sektor", "Hanked", "Hangete näited", "Tehisaru määrus", "Eesti otsused"], f
        assert alam.count('aria-current="page"') == 1 and f'href="{f}" aria-current="page"' in alam, f
    assert '<ul class="sellel"></ul>' not in "".join(sait.values())
    for f in ("kas-see-on-tosi.html", "lahknevused.html", "varskus.html"):
        assert '<a href="kas-see-on-tosi.html" aria-current="page">Usaldus</a>' in sait[f], f
    # Kadri 8.11.2026 valis „Uudised › Ettekanded“: uudistel on nüüd kaks alamlehte
    assert re.findall(r'<ul class="alamlehed">(.*?)</ul>', sait["uudised.html"])[0].count("<li>") == 2


def test_lahknevused_ja_varskus_on_usalduse_all_nahtaval(sait):
    # Kadri 6.11.2026 21:38: Eurostati ja Statistikaameti võrdlus jääb nähtavale, kontrollib ministeerium
    osa = _jaotis(sait["lahknevused.html"], "lahknevused")
    assert "selgitamata" in osa and "<details" not in osa.split("</header>")[0]
    assert 'id="varskus"' in sait["varskus.html"] and 'id="muutused"' in sait["varskus.html"]
    assert 'id="varskus"' not in sait["kuidas-lugeda.html"]


def test_igas_teemavaates_on_numbriplaadid(sait):
    for f in ["inimesed.html", "ettevotted.html", "too.html", "avalik-sektor.html", "tehisaru-maarus.html", "hanked.html", "kas-see-on-tosi.html"]:
        assert 'class="vastus' in sait[f], f  # Avalik sektor: „vastus kpi-pais“ (KPI ver1)


def test_koondamiste_visuaali_pealkiri_tuleb_andmetest(A, sait):
    j = A["koondamised"]["juhtumid"]
    arv = lambda r: r["arv_eestis"] if r.get("arv_eestis") is not None else r.get("arv_ulem")  # noqa: E731
    pohjus = sum(arv(r) for r in j if arv(r) and r["roll"] in ("otsene", "osaline"))
    kokku = sum(arv(r) for r in j if arv(r))
    h2 = sait["too.html"].split('id="h-koondamised-v">')[1].split("</h3>")[0]
    assert f"<b>{pohjus} töökoha</b>" in h2 and f"{kokku} koondatud töökohast" in h2


def test_iga_koondamine_on_tulbal_ja_tabelis_arvu_pohjuse_ja_lingiga(A, sait):
    # Kadri MKUS-i kommentaar 7.11.2026 08:48: kaardid maha, koondatute arv, põhjus ja link alumisse tabelisse
    from lehed_ulevaade import koondamise_arv
    h = sait["too.html"]
    tulbad = re.findall(r'<div class="kr" data-k="([^"]+)"', h)
    tabel = _jaotis(h, "palkamine")
    read = re.findall(r'<div class="pk-k" id="pk-([^"]+)"', tabel)
    assert sorted(tulbad) == sorted(read) == sorted(r["id"] for r in A["koondamised"]["juhtumid"])
    for r in A["koondamised"]["juhtumid"]:
        rida = tabel.split(f'id="pk-{r["id"]}"')[1]
        assert f"<b>{koondamise_arv(r)}</b>" in rida.split("</div>")[0]
        osa = rida.split("</tr>")[0]
        assert komponendid.e(r["pohjus"]) in osa and f'href="{komponendid.e(r["url"])}"' in osa, r["id"]
    for k in ("<th scope=\"col\">Koondab Eestis</th>", "<th scope=\"col\">Põhjus ettevõtte sõnul</th>"):
        assert k in tabel


# ---- Uudised, Hanked, Töö publikatsioonid (Kadri 5.11.2026 23:17) ----
import lehed_uudised  # noqa: E402


def test_uudised_eesti_ja_maailm_eraldi(A, sait):
    h = sait["uudised.html"]
    ee = h.split('id="eesti-uudised"')[1].split("</section>")[0]
    mm = h.split('id="maailma-uudised"')[1].split("</section>")[0]
    n_ee = sum(r["piirkond"] == "EE" for r in A["uudised"])
    assert ee.count("<li ") == n_ee and mm.count("<li ") == len(A["uudised"]) - n_ee
    assert f"<b>{n_ee} uudist</b>" in ee


def test_iga_uudis_on_liigiga_ja_arvamus_on_margitud(A, sait):
    h = sait["uudised.html"]
    assert h.count('class="u-l') >= len(A["uudised"])
    assert h.count('class="u-l arv">arvamus') == sum(r["liik"] == "arvamus" for r in A["uudised"])


def test_tundmatu_uudise_liik_peatab_ehituse(A):
    B = dict(A, uudised=[dict(A["uudised"][0], liik="kuulujutt")])
    with pytest.raises(andmekiht.AndmeViga):
        lehed_uudised.uudised(B, next(v for v in ehita.lae_vaated() if v["id"] == "uudised"))


def test_uudised_ja_hanked_vajavad_andmeid(A):
    vaated = {v["id"]: v for v in ehita.lae_vaated()}
    with pytest.raises(andmekiht.AndmeViga):
        lehed_uudised.uudised(dict(A, uudised=None), vaated["uudised"])
    with pytest.raises(andmekiht.AndmeViga):
        lehed_uudised.hanked(dict(A, hanked_leht=None), vaated["hanked"])
    assert lehed_uudised.uuringud_too(dict(A, publikatsioonid=None)) == ""


def test_hangete_loend_on_taielik_ja_head_naited_tulevad_andmetest(A, sait):
    h = sait["hanked-naited.html"]  # Kadri 11.11.2026 (F): loend on oma lehel
    assert 'class="h-tabel"' not in sait["hanked.html"]
    L = A["hanked_leht"]["loend"]
    tabel = h.split('class="h-tabel"')[1].split("</table>")[0]
    assert tabel.count("<tr data-hea") == len(L)
    assert tabel.count('data-hea="1"') == sum(r.get("hea") == 3 for r in L)
    assert f'<b>{sum(r.get("hea") == 3 for r in L)} hanget {len(L)}-st</b>' in h  # h1 (Kadri 11.11.2026, F)
    assert tabel.count("viitenumber") == sum(1 for r in L if not r.get("url"))


def test_hanked_on_katseline_ja_tapsus_tuleb_andmetest(A, sait):
    h = sait["hanked.html"]
    hm = A["hanked_leht"]["hindamine"]["hindamine"]
    t = hm["tulemused"][hm["valitud"]]
    # 8.11.2026: 100 hanget käsitsi pimesi üle vaadatud; klassifikaator veel uuendamata
    # 8.11.2026 16:29 (Kadri): katselisusele viitavaid märke enam pole
    assert "katseline" not in h and "vaadati käsitsi pimesi üle" in h and "Kontrollimata masinmärgistus" not in h
    assert "katseline" not in sait["index.html"]
    assert f'<b>{komponendid.pr(t["saagis"] * 100, 0)}%</b>' in h.split('id="h-tapsus">')[1].split("</h2>")[0]


def test_too_vaates_on_publikatsioonid(A, sait):
    h = sait["too-kirjandus.html"]  # Kirjandus on oma alamleht (Kadri 6.11.2026 22:27, ettepanek 7)
    P = A["publikatsioonid"]
    assert 'id="uuritakse"' in h and 'id="publikatsioonid"' in h and 'id="eesti-allikad"' in h
    a1 = [r for r in P["aastad"] if not r["poolik"]][-1]
    assert f'{a1["aasta"]}. aastal <b>' in h.split('id="h-uuritakse">')[1].split("</h2>")[0]


def test_ulevaade_ja_avalik_sektor_viitavad_uutele_vaadetele(sait):
    assert 'href="uudised.html"' in sait["index.html"] and 'href="hanked.html"' in sait["index.html"]
    assert 'href="hanked.html"' in sait["avalik-sektor.html"]


def test_eesti_energia_koondamine_on_too_vaates(sait):
    # Kadri 6.11.2026: Eesti Energia koondamine oli uudistes, aga mitte Töö vaate koondamistes
    h = sait["too.html"]
    assert 'data-k="eesti-energia-2026-11"' in h and "vähemalt 390" in h


def test_uudise_koondamine_lisandub_kandidaadina(A):
    import copy
    B = copy.deepcopy(A)
    B["uudised"].append({"kuupaev": "2026-11-06", "piirkond": "EE", "teema": "koondamine", "ettevote": "Näidis AS",
                         "ai_roll": "osaline", "pealkiri": "Näidis AS koondab", "url": "https://naide.ee/x", "allikas": "ERR",
                         "pohjus": "Kulud.", "liik": "uudis"})
    n = len(B["koondamised"]["juhtumid"])
    andmekiht.lisa_uudiste_koondamised(B)
    uus = [j for j in B["koondamised"]["juhtumid"] if j["ettevote"] == "Näidis AS"]
    assert len(B["koondamised"]["juhtumid"]) == n + 1 and uus[0]["kandidaat"] and uus[0]["arv_eestis"] is None
    andmekiht.lisa_uudiste_koondamised(B)  # sama ettevõtet teist korda ei lisata
    assert len(B["koondamised"]["juhtumid"]) == n + 1


def test_palkamise_pealkiri_tuleb_andmetest(A, sait):
    F = A["koondajad"]["firmad"]
    k = [f for f in F.values() if f["otsib"].get("kontrollitud")]
    kuulutusi = sum(len(f["otsib"]["ametid"]) for f in k)
    h2 = sait["too.html"].split('id="h-palkamine">')[1].split("</h2>")[0]
    assert f"(kokku {abi.sonaga(kuulutusi)} kuulutust)" in h2


def test_uudise_levik_on_valjaannete_arv(A):
    import copy
    B = copy.deepcopy(A)
    B["uudised"][0]["levik"] = {"arv": 9, "allikad": ["ERR", "Delfi"], "kontrollitud": "2026-11-06"}
    h = lehed_uudised.uudised(B, next(v for v in ehita.lae_vaated() if v["id"] == "uudised"))
    assert "9 väljaannet</span>" in h and "Kajastasid: ERR, Delfi" in h


def test_uudiste_paneel_ytleb_kas_viimasel_kontrollil_lisandus(A, sait):
    from komponendid import kp
    h = sait["uudised.html"]
    paev = A["uudiste_olek"]["viimane_kontroll"][:10]
    assert h.count('class="ps u-seis"') == 2
    # Kadri 11.11.2026: „uus“ järgib avaldamise kuupäeva (kontrollipäev ja eelmine päev), mitte lisamise päeva
    alates = lehed_uudised.uus_alates(A["uudiste_olek"]["viimane_kontroll"])
    uued = sum(r["kuupaev"][:10] >= alates for r in A["uudised"])
    assert h.count('<span class="u-l uus">uus</span>') == uued
    assert "„Uus“ on " in h and f"–{kp(paev)} avaldatud uudis." in h
    for li in re.findall(r'<li data-teema.*?</li>', h, re.S):
        d = re.search(r'<span class="d">([^<]+)</span>', li).group(1)
        on_uus = '<span class="u-l uus">uus</span>' in li
        assert on_uus == (d in {kp(paev), kp(alates)}), (d, on_uus)


def test_uus_margid_on_oranzid(sait):
    # Kadri 7.11.2026: „värvi kõik uus märgid oranziks“; „suur uudis“ jääb siniseks
    assert '<span class="u-l suur">uus</span>' not in sait["uudised.html"]
    assert '<span class="t s">uus number</span>' not in sait["index.html"]
    assert sait["index.html"].count('<span class="t uus">uus</span>') + sait["index.html"].count('<span class="t">number</span>') >= 1  # Kadri 8.11: ainult „uus“
    assert '<span class="t uus">uus number</span>' not in sait["index.html"]
    css = (ehita.SIIN / "stiil.css").read_text(encoding="utf-8")
    assert ".u-l.uus, .voog .t.uus { background: #f2a65e; color: #2b1a05; }" in css  # U8, Kadri 8.11.2026


def test_pikad_teemad_on_alamlehtedeks_jagatud(sait):
    # Kadri 6.11.2026: Töö, Inimesed ja Uudised eraldi alamlehtedeks; alamlehtede rida igal alamlehel
    vaated = ehita.lae_vaated()
    for v in vaated:
        t = next(x for x in vaated if x["id"] == v["teema"]) if v.get("teema") else v  # nt Hanked on Riigi all
        for s in v.get("alamlehed", []):
            h = sait[s["fail"]]
            assert f'<a href="{s["fail"]}" aria-current="page">' in h, s["fail"]
            assert all(f'href="{x["fail"]}"' in h for x in v["alamlehed"])
            assert f'<a href="{t["fail"]}" aria-current="page">{t["menuu"]}</a>' in h  # teema jääb menüüs valituks
    assert 'id="hoive"' in sait["too-ametid.html"] and 'id="hoive"' not in sait["too.html"]


def test_ankurlink_teisele_lehele_peab_olemas_olema():
    with pytest.raises(ehita.EhitusViga):
        ehita.kontrolli_ankrud({"a.html": '<a href="b.html#x">x</a>', "b.html": '<p id="y"></p>'})


def test_vaite_juures_ei_ole_inimeste_nimesid(sait):
    import vota_kaasa
    assert vota_kaasa.ilma_nimedeta("ERR News 3.11.2026 (Sinisalu, Hiiemaa, Töötukassa)") == "ERR News 3.11.2026"
    assert "(sarnaselt ERR News 3.11)" in vota_kaasa.ilma_nimedeta("ERR 5.11.2026 (sarnaselt ERR News 3.11)")
    assert "Sinisalu" not in sait["kas-see-on-tosi.html"]


def test_saidi_ulesehitus_orbude_tupikute_ja_menuu_kontroll(sait):
    # Oskus andmesaidi-ulesehitus (Kadri 6.11.2026: „pidevad kontrollid on olulised“): iga ehitus kontrollib struktuuri
    import struktuur
    M = struktuur.moodik(sait)
    assert struktuur.vead(M) == []
    assert not [h for h in struktuur.hoiatused(M) if "tükeldamise piir ületatud" in h]


def test_struktuuri_kontroll_leiab_orvu_ja_tupiku():
    import struktuur
    leht = lambda keha: f'<title>{keha}</title><ul class="menu"><a aria-current="page">x</a></ul><main><h1>{keha}</h1>{keha}</main>'  # noqa: E731
    M = struktuur.moodik({"index.html": leht('<a href="a.html">a</a>'), "a.html": leht("tupik"), "b.html": leht('<a href="index.html">i</a>')})
    v = struktuur.vead(M)
    assert "a.html: tupik, siit ei pääse edasi" in v and "b.html: orb, ükski leht ei vii siia" in v


def test_vana_aadress_suunab_uuele(tmp_path, A):
    ehita.ehita(tmp_path, A)
    for vana, uus in ehita.VANAD_AADRESSID.items():
        assert f'url={uus}"' in (tmp_path / vana).read_text(encoding="utf-8")


def test_avaleht_viib_lahknevusteni_ja_plaadid_on_lingid(sait):
    h = sait["index.html"]
    assert 'href="lahknevused.html#lahknevused"' in h
    assert re.findall(r'<span class="lbl"><a href="', h).__len__() == 6
    assert 'href="lahknevused.html#lahknevused"' in sait["ettevotted.html"]
    assert ">Allikas</a>" not in sait["kuidas-lugeda.html"]


def test_kasutusloogika_kontroll_leiab_puuduva_oleku():
    # Oskus kasutusloogika (6.11.2026): igal tasandil üks aktiivne märge, nupurühmas üks valitud, igal nupul nimi
    import struktuur
    leht = ('<title>t</title><ul class="menu"><a aria-current="page">x</a></ul><main><h1>t</h1><a href="index.html">i</a>'
            '<ul class="alamlehed"><a href="a.html">a</a></ul><div class="u-f" role="group"><button type="button">k</button></div>'
            '<button type="button"></button></main>')
    M = struktuur.moodik({"index.html": leht.replace("<title>t", "<title>i") + '<a href="a.html">a</a>', "a.html": leht})
    v = " ".join(struktuur.vead(M))
    assert "aktiivne märge" in v and "valitud nupp" in v and "ilma nimeta" in v


def test_seotud_rida_avaliku_sektori_ja_hangete_vahel(sait):
    # Kadri 6.11.2026 22:27, ettepanek 8. 11.11.2026 (D): Riigi alamlehtede rida viib samadele lehtedele, „Seotud“ rida jäi ära
    for f, teine in (("avalik-sektor.html", "hanked.html"), ("hanked.html", "avalik-sektor.html")):
        assert 'class="seotud"' not in sait[f]
        assert f'href="{teine}"' in re.search(r'<ul class="alamlehed">(.*?)</ul>', sait[f]).group(1)


def _seotud(h):
    return h.split('class="seotud"')[1].split("</nav>")[0]


def test_koondamised_on_uks_plokk(sait):
    # Kadri 6.11.2026 22:27, ettepanek 6: graafik ühes plokis; 7.11 08:48 kaardid maha, link tabelisse
    osa = _jaotis(sait["too.html"], "koondamised")
    assert 'id="koondamised-visuaal"' in osa and 'class="kk-v"' not in osa and 'href="#palkamine"' in osa


def test_navigatsioon_b_koik_teemad_sakid_ja_sellel_lehel(sait):
    # Kadri 6.11.2026 22:51 valis navigatsiooni B: „Kõik teemad“ paneel päises, alamlehed sakkidena pealkirja all
    # (mitte päises), „Sellel lehel“ paremal veerus; telefonis „Menüü“ ainult teemade linkidega (22:52).
    vaated = ehita.lae_vaated()
    teemad = [v for v in vaated if v["menuu"] and not v.get("teema") and v["olek"] == "valmis"]
    for f, h in sait.items():
        if not f.endswith(".html"):
            continue
        paneel = re.search(r'<nav class="mega-paneel".*?</nav>', h, re.S).group(0)
        assert all(f'href="{v["fail"]}"' in paneel for v in teemad), f
        pais = re.search(r'<header class="top">.*?</header>', h, re.S).group(0)
        assert 'class="alamlehed"' not in pais, f  # sakid on sisus, mitte päises
    for v in vaated:
        for s in v.get("alamlehed", []):
            h = sait[s["fail"]]
            main = re.search(r"<main.*?</main>", h, re.S).group(0)
            assert main.index('class="alamlehed"') > main.index("</h1>"), s["fail"]  # sakid pealkirja all
            assert '<nav class="rada"' in main
    # R1 (Kadri 8.11.2026 21:24): ainult rida sakkide all, paremat veergu pole ja sisu saab kogu laiuse
    assert 'class="lehel lehel-parem"' not in sait["too.html"] and 'class="lehel lehel-rida"' in sait["too.html"]
    assert ' raamiga' not in re.search(r"<main[^>]*>", sait["too.html"]).group(0)
    # Kleepuv rida on <main> otsene laps, muidu ei jää see kerimisel nähtavale
    for f, s in sait.items():
        if 'lehel-rida' not in s:
            continue
        enne = s[s.index("<main"):s.index('class="lehel lehel-rida"')]
        assert enne.count("<div") == enne.count("</div"), f'{f}: „Sellel lehel“ rida on div-i sees'

    assert '<nav class="rada"' not in sait["index.html"]


def test_publikatsiooni_tsiteeringud_on_pealkirja_korval(A, sait):
    # Kadri MKUS-i kommentaar 7.11.2026 08:50: „tahaks näha kõrval arvu mitu korda on tsiteeritud“
    osa = _jaotis(sait["too-kirjandus.html"], "publikatsioonid")
    assert '<th scope="col" class="v">Tsiteeritud</th><th scope="col">Publikatsioon ja kanal</th>' in osa
    koik = max((r for r in lehed_uudised.alates_aastast(A["publikatsioonid"], lehed_uudised.TSIT_ALATES) if r.get("url")), key=lambda r: r["viiteid"])
    rida = osa.split(f'<a href="{komponendid.e(koik["url"])}"')[0].rsplit("<tr>", 1)[1]
    assert lehed_uudised._arv(koik["viiteid"]) in rida


def test_enim_tsiteeritud_alates_2026(A, sait):
    # Kadri MKUS-i kommentaar 9.11.2026: „siin võiks olla enim tsiteeritud alates 2026“
    osa = _jaotis(sait["too-kirjandus.html"], "publikatsioonid")
    assert "Enim tsiteeritud alates 2026 (" in osa and "alates 2023" not in osa
    read = lehed_uudised.alates_aastast(A["publikatsioonid"], 2026)
    assert read and all(r["avaldatud"] >= "2026" for r in read)
    assert len({r["url"] for r in read}) == len(read)
    paneel = osa.split('id="pub-alates"')[1].split("</table>")[0]
    assert paneel.count("<tr>") == len([r for r in read if r.get("url")]) + 1  # + päis


def test_eesti_toode_pohinumbrid_on_tabelis(A, sait):
    # Kadri MKUS-i kommentaar 7.11.2026 08:53: „näita siin tabelis veel lisaks olulisemaid KPIsid nende tööde kohta“
    osa = _jaotis(sait["too-kirjandus.html"], "eesti-allikad")
    assert '<th scope="col">Põhinumbrid</th>' in osa
    for t in A["publikatsioonid"]["eesti_kpi"]["tood"]:
        for k in t["kpi"]:
            assert f'<b>{komponendid.e(k["vaartus"])}</b>' in osa, t["too"]
    # põhinumbritega tööd on tabeli alguses (vaikimisi on näha 12 rida)
    esimene = osa.split("<tbody>")[1].split("</tr>")[0]
    assert 'class="ee-k"' in esimene


def test_vabad_ametikohad_tulevad_statistikaametist(sait):
    # Kadri 7.11.2026: mida, kus ja mis valdkonnas palgatakse; ametlik osa on Statistikaameti PAV011 ja PAV014
    import csv
    R = list(csv.DictReader(open(ehita.SIIN / "sisu" / "vabad-ametikohad.csv", encoding="utf-8")))
    kv = lambda p: (int(p.split()[0]), ["I", "II", "III", "IV"].index(p.split()[1]))  # noqa: E731
    viimane = max((r["periood"] for r in R if r["tabel"] == "PAV011"), key=kv)
    kokku = next(float(r["vaartus"]) for r in R if r["tabel"] == "PAV011" and r["periood"] == viimane
                 and r["nimi"].startswith("Kokku") and r["naitaja"] == "Vabade ametikohtade arv")
    osa = _jaotis(sait["too.html"], "vabad-kohad")
    h2 = osa.split('id="h-vabad-kohad">')[1].split("</h2>")[0]
    assert f"{kokku:,.0f}".replace(",", " ") + " vaba ametikohta" in h2
    assert "PAV011" in osa and "PAV014" in osa and "Tallinn" in osa


def test_tooportaalid_iga_portaal_eraldi(A, sait):
    # Kadri 7.11.2026: mitu kuulutust portaalides, mis ametid, kus ja kes palkab; portaalide arve ei liideta
    T = A["toopakkumised"]
    osa = _jaotis(sait["too.html"], "toopakkumised")
    for p in T["portaalid"]:
        assert lehed_uudised._arvt(p["kuulutusi_kokku"]) in osa
    kokku = sum(p["kuulutusi_kokku"] for p in T["portaalid"])
    assert lehed_uudised._arvt(kokku) not in osa  # summat ei näidata
    assert "Sobib ka ukrainlastele" not in osa  # lisasildid ei ole ametivaldkonnad


def test_eli_jarjestus_vaikimisi_kumme_ja_kaardil_pole_tumeda_lauset(sait):
    # Kadri MKUS-i kommentaarid 7.11.2026 õhtul: „näita siin defaultina top kümmet“ ja „võta see lause maha“.
    # Hiljem samal õhtul sai loendist järjestuse muutuse graafik: vaikimisi Top 10, Eesti esile tõstetud.
    osa = _jaotis(sait["index.html"], "el")
    assert re.search(r'<button type="button" data-n="10" aria-pressed="true">esikümme<', osa)
    assert '<div class="bump-v" data-n="10">' in osa and "kõik (27)" in osa
    assert re.search(r'<g class="bs f" data-s="[^"]+" tabindex="-?[01]" role="button" aria-label="Eesti">', osa)
    js = (Path(__file__).resolve().parents[1] / "sait" / "sait.js").read_text(encoding="utf-8")
    assert ".jrj[data-piir]" in js and "'kõik ('" in js
    for f, h in sait.items():
        assert "Mida tumedam" not in h, f


def test_vabad_kohad_jarjestuse_muutus_aastate_kaupa(sait):
    # Kadri 7.11.2026 20:41 ja 20:43: tulpade asemel järjestuse muutus aastates (näidise järgi), mitu aastat
    osa = _jaotis(sait["too.html"], "vabad-kohad")
    assert 'class="bump-k"' in osa and 'class="ribad lihtne"' not in osa.split('class="vk-kus"')[0]
    aastad = re.findall(r'<text class="bump-a"[^>]*>(\d{4})</text>', osa)
    assert len(set(aastad)) >= 8  # vähemalt 8 aastat, sama kvartal igal aastal
    assert re.search(r'data-n="5"[^>]*>esiviisik<', osa) and "kõik (" in osa
    assert osa.count('class="bs f"') >= 1  # üks esiletõstetud tegevusala
    vaikimisi = re.search(r'<div class="bump-v" data-n="(\d+)">', osa).group(1)
    assert vaikimisi == "10"
    assert "Haridus" in tekst(osa)


def test_tootus_eli_jarjestus_aastate_kaupa(sait):
    # Kadri 7.11.2026 20:53: järjestuse graafik ka teistele andmetele, mis näitavad muutust ajas
    osa = _jaotis(sait["too.html"], "tootus-el")
    aastad = set(re.findall(r'<text class="bump-a"[^>]*>(\d{4})</text>', osa))
    assert len(aastad) >= 8 and 'class="bs f"' in osa and "kõik (27)" in osa
    assert "kõrgeim" in tekst(osa) and "une_rt_a" in osa


def test_el_jarjestuse_viimane_koht_klapib_registriga(A):
    # graafiku 2025. aasta koht peab olema sama, mis pealkirjas registrist (muidu ehitus katkeb)
    y = andmekiht.leia(A, "ettevotete-tehisaru-kasutus", "EE", "uusim:alus")["aasta"]
    koht = andmekiht.koht(A, "ettevotete-tehisaru-kasutus", "EE", y)
    _, k, aastad, _, _ = lehed_ulevaade.el_jarjestus("ettevotete-tehisaru-kasutus", koht_praegu=koht, aasta_praegu=y)
    assert k[y] == koht and aastad[0] <= 2021


# ---- Lihtsustamine (Kadri 7.11.2026: „liiga palju infot ühel valgel taustal … teksti on liiga palju“) ----

def test_faktid_peidavad_neutraalsed_taepsustused():
    h = komponendid.faktid([("Piirang", "", "p"), ("Kontrollimata", "risk", "k"), ("Ümardus", "", "u")])
    nahtav, peidus = h.split("<details", 1)
    assert "Kontrollimata" in nahtav and "Piirang" not in nahtav
    assert "<summary>Täpsustused: piirang, ümardus</summary>" in peidus
    ainult_neutraalne = komponendid.faktid([("EL", "", "x"), ("Siht", "", "y")])
    assert ainult_neutraalne.startswith('<ul class="faktid"><li><span class="mark-l ">EL</span>')
    assert "Täpsustused: siht" in ainult_neutraalne
    assert "<details" not in komponendid.faktid([("Piirang", "", "p")], koik_lahti=True)


def test_uudistel_pole_teema_silti_ega_topelt_jatkulugu(A, sait):
    h = sait["uudised.html"]
    assert "Jätkulugu:" not in h and "jätkulugu:" not in h
    assert h.count('<p class="u-k">') == len(A["uudised"])
    assert '<span class="u-t">tehisaru ja töö</span>' not in h
    assert h.count('class="u-l vaikne">uudis<') == sum(r["liik"] == "uudis" for r in A["uudised"])


def test_koondajate_tabel_on_viie_veeruga_ja_selgitus_klopsu_taga(sait):
    t = _jaotis(sait["too.html"], "palkamine")
    assert t.split("<thead>")[1].split("</thead>")[0].count("<th ") == 5
    assert "<summary>Täpsustused: ametiliigid ja mida tabel ei näita</summary>" in t


def test_avalehe_voos_on_ainult_esimene_lause():
    import lehed_ulevaade
    assert lehed_ulevaade._esimene_lause("Esimene lause on siin. Teine lause.") == "Esimene lause on siin."
    assert lehed_ulevaade._esimene_lause("2026. aastal kasvas 5%.") == "2026. aastal kasvas 5%."


def test_ettevotete_uued_riiklikud_numbrid_on_oma_paneelis(sait):
    # Kadri 7.11.2026 (pilt ettevõtete paneelist): liiga palju infot ühel taustal
    h = sait["ettevotted.html"]
    kasutus, uued = _jaotis(h, "kasutus"), _jaotis(h, "kasutus-uued")
    assert "<table" in uued and "Taani" in uued and "Danmarks Statistik" not in kasutus
    assert 'class="vrd">ei ole otse võrreldav' not in h and 'class="usaldus3"' not in kasutus


def test_kpi_plaadid_jargivad_lukustatud_valikut_ver1(sait):
    # Kadri 7.11.2026 21:46 „lukusta ver1“ (KPI-labor): kontekst plaatide kaupa, lugeja seda ei muuda
    import lehed_ulevaade
    h = sait["index.html"]
    assert '<div class="plaadid kaks"' in h and "data-kiht" not in h and "pl-lyl" not in h
    for pid, osad in lehed_ulevaade.KPI_VER1.items():
        # 8.11.2026: ver1 laiendati alamlehtede päisele; iga plaat on täpselt ühel lehel
        lehed = [f for f, s in sait.items() if f'data-kpi="{pid}"' in s]
        assert len(lehed) == 1, (pid, lehed)
        pl = sait[lehed[0]].split(f'data-kpi="{pid}"')[1].split('</div>')[0].split('<span class="src">')[0]
        assert ('class="muut"' in pl) == ("muutus" in osad), pid
        assert ('class="kriba' in pl) == ("riba" in osad), pid
        assert ('class="tekst"' in pl) == ("tekst" in osad), pid
    # 8.11.2026 (Kadri: vähem teksti): legend on märk + sõna, mitte „oranž/tume kriips:“
    assert '<i class="lg s"></i>siht 75% (2030)' in h and "ELi siht 80% (2030)" in h
    assert '<i class="lg v"></i>omavalitsused 27%' in sait["avalik-sektor.html"]
    assert "kriips:" not in "".join(sait.values())


def test_alamlehtede_paise_numbrid_on_ver1_plaadid(sait):
    # Kadri 8.11.2026: teiste lehtede päise numbrid ver1 kujule, iga plaat käsitsi valitud kontekstiga
    for f, h in sait.items():
        assert '<aside class="vastus"' not in h, f
        for pl in h.split('class="plaat kp"')[1:]:
            pl = pl.split('<span class="src">')[0]
            assert '<span class="lbl">' in pl and '<span class="ctx">' in pl, f


def test_hanked_litsentsid_ja_ai_kuulutused(sait):
    # Kadri 8.11.2026: milliseid litsentse mis asutused hangivad ja milleks; AI- ja andmetööde kuulutused seiresse
    h = sait["hanked.html"]
    assert 'id="litsentsid"' in h and 'class="lits-m"' in h and "litsentse hangib" in h
    assert "Eesmärk</th>" in h and "Kuidas litsentsihanked leiti" in h
    t = sait["too.html"]
    if 'id="ai-kuulutused"' in t:  # andmed tulevad igapäevasest kogumisest (sisu/ai-tookuulutused.json)
        osa = t.split('id="ai-kuulutused"')[1].split("</section>")[0]
        assert osa.count('class="plaat kp"') == 3 and "Firma üldnõue" in osa and "data-piir" in osa


def test_ai_kuulutused_filtreeritavad_ruhma_ja_maakonna_jargi(sait):
    h = sait["too.html"]
    jao = h[h.index('id="ai-kuulutused"'):]
    jao = jao[:jao.index("</section>")]
    assert 'class="h-otsing" data-uhik="kuulutust"' in jao
    assert 'aria-label="Otsi kuulutustest"' in jao
    assert '<select data-kus aria-label="Maakond">' in jao
    assert 'data-r="ai_amet"' in jao and 'data-r="andmeamet"' in jao
    assert 'table class="h-tabel"' in jao
    import re
    read = re.findall(r'<tr data-ruhm="([^"]+)" data-kus="([^"]*)" data-otsi="([^"]+)">', jao)
    assert read and all(o == o.lower() for _, _, o in read)
    valikud = set(re.findall(r'<option value="([^"]+)">', jao))
    assert {k for _, k, _ in read if k} == valikud


def test_neli_vaiteparandust_8_11(sait):
    """Sisuloogika ülevaatus 8.11.2026: ELi kohtadel aasta, kasvu võrreldavus, Töö h1 USA kohta, hangete üks number."""
    h1 = lambda f: tekst(re.search(r"<h1>(.*?)</h1>", sait[f], re.S).group(1))  # noqa: E731
    assert re.search(r"ELis \d+\. ja ettevõtted \d+\. kohal \(20\d\d\)", h1("index.html"))  # ELi kohal on aasta
    assert "aastaga" not in h1("inimesed.html")
    assert "küsimus võib erineda" in sait["inimesed.html"] and "küsimus võib erineda" in sait["index.html"]
    assert h1("too.html").startswith("Eesti andmetest")  # 8.11 õhtu: h1 algab Eestist (läbivaatus P4)
    plaat = lambda f, pid: re.search(rf'data-kpi="{pid}">(.*?)</div>', sait[f], re.S).group(1)  # noqa: E731
    avaleht, hanked = plaat("index.html", "hanked"), plaat("hanked.html", "hk-arv")
    suur = lambda h: re.search(r'class="big[^"]*">(\d+)<', h).group(1)  # noqa: E731
    assert suur(avaleht) == suur(hanked), (avaleht, hanked)
    assert "jaan" not in avaleht


def test_avalehe_teematabel_naidis_c(sait):
    """Kadri 8.11.2026: avalehel KPI-plaatide all tabel, read on teemad, tühi lahter = „hindamata“."""
    h = sait["index.html"]
    assert h.index('class="plaadid kaks"') < h.index('id="teemad"') < h.index('id="el"')
    jao = h[h.index('id="teemad"'):]
    jao = jao[:jao.index("</section>")]
    veerud = re.findall(r'<th scope="col">([^<]+)</th>', jao)
    assert veerud == ["Teema", "Mõõdetud", "Uuritud", "Väidetud", "Sihid ja reeglid", "Värskus"]
    read = re.findall(r'<th scope="row"><a href="([^"#]+)', jao)
    assert read == ["inimesed.html", "ettevotted.html", "too.html", "avalik-sektor.html", "hanked.html"]
    tuhjad = jao.count('<span class="m-puud">hindamata</span>')
    assert f"{abi.sonaga(tuhjad).capitalize()} lahtrit on veel hindamata" in jao
    assert len(re.findall(r"<td data-v=", jao)) == 5 * 5


def test_iga_vaide_on_avalehe_tabelis_teemaga(A):
    import lehed_ulevaade
    for v in A["vaited"]:
        assert lehed_ulevaade.vaite_teema(v) in {"inimesed", "ettevotted", "too", "avalik-sektor", "hanked"}


def test_too_leht_teemamall_a(sait):
    """Kadri 8.11.2026: teemaleht A järgi: number, andmed sakkides, uuringud, väited, reeglid, allikad; vanad ankrud alles."""
    h = sait["too.html"]
    jrk = [h.index(x) for x in ('class="vastus kpi-pais"', 'id="andmed"', 'id="t-vaited"', 'id="t-reeglid"', 'id="t-allikad"')]
    assert jrk == sorted(jrk)
    assert 'id="t-uuringud"' not in h  # Kadri 11.11.2026: uuringud on alamlehel Töö › Uuringud
    for vana in ("tootus-kuud", "koondamised", "tootus-el", "palkamine", "vabad-kohad", "toopakkumised", "ai-kuulutused", "tulevik"):
        assert f'id="{vana}"' in h, vana
    sakid = re.findall(r'role="tab" id="sakk-([a-z-]+)-n" aria-controls="sakk-\1" aria-selected="(true|false)"', h)
    assert len(sakid) == 7 and [s for s, v in sakid if v == "true"] == ["tootus"]
    assert len(re.findall(r'class="sakk-sisu" hidden>', h)) == 6
    assert "august 2026" in h[h.index('id="t-allikad"'):]


def test_struktuur_loeb_ainult_nahtavat_sakki():
    import struktuur
    s = '<main><p>yks kaks</p><div role="tabpanel" id="a" hidden><div><p>peidus tekst siin</p></div><h2>x</h2></div><h2>y</h2></main>'
    m = struktuur.moodik({"x.html": s})["x.html"]
    assert m["sonu"] == 3 and m["h2"] == 1


def test_eli_jarjestuses_ainult_top10_ja_koik(sait):
    """Kadri 8.11.2026 16:28 (avalehe kommentaar): „jäta alles ainult top 10 ja kõik valikud“."""
    for f in ("index.html", "too.html"):
        for osa in re.findall(r'<div class="kogus bump-n"[^>]*>(.*?)</div>', sait[f], re.S):
            if "(27)" in osa:
                assert re.findall(r">(esikümme|esiviisik|esimesed \d+|kõik \(\d+\))<", osa) == ["esikümme", "kõik (27)"], (f, osa)


def test_koik_teemalehed_jargivad_malli_a(sait):
    """Kadri 8.11.2026: sama plokijärjekord igal teemalehel."""
    for f in ("inimesed.html", "ettevotted.html", "too.html", "avalik-sektor.html", "hanked.html"):
        h = sait[f]
        jrk = [h.find(x) for x in ('id="andmed"', 'id="t-uuringud"', 'id="t-vaited"', 'id="t-reeglid"', 'id="t-allikad"')]
        # Uuringud ja väited võivad puududa, kui teemal neid pole (Kadri 11.11.2026); olemasolevate järjekord on sama
        assert jrk[0] != -1 and jrk[3] != -1 and jrk[4] != -1, f
        jrk = [i for i in jrk if i != -1]
        assert jrk == sorted(jrk), f
        assert len(re.findall(r'class="sakk-sisu">', h)) == 1, f


def test_uus_leht_avaneb_ulevalt():
    # Kadri MKUS-i kommentaar 8.11.2026: „suuna navigeerimisel alati lehe ülaossa, isegi kui olen eelmises vaates
    # alla scrollinud“. Brauseri kerimise taastamine on välja lülitatud; erand on #ankur ja tagasi-nupp.
    js = (Path(__file__).resolve().parents[1] / "sait" / "sait.js").read_text(encoding="utf-8")
    assert "history.scrollRestoration = 'manual'" in js
    assert "n.type === 'back_forward'" in js and "sessionStorage.setItem(VOTI" in js
    assert "if (location.hash || liigutas) return;" in js
    assert "}, true); // püüdefaasis" in js


def test_labivaatus_8_11_parandused(sait):
    """Läbivaatus 8.11.2026 õhtul (doc 8BK9uy4sZcCP8Qvvjm34NW), parandused P1–P8 ja kopeeritav fakt."""
    h1 = lambda f: tekst(re.search(r"<h1>(.*?)</h1>", sait[f], re.S).group(1))  # noqa: E731
    h2 = lambda f, i: tekst(re.search(rf'id="h-{i}">(.*?)</h2>', sait[f], re.S).group(1))  # noqa: E731
    # P1: sihte ei järjestata
    assert "kõige kaugemal" not in sait["index.html"] and "siht on 75% aastaks 2030" in h2("index.html", "sihid")
    # P2: iga „viimati“ ütleb, mille kohta see on
    assert h2("index.html", "muutus").startswith("Mis muutus: uus number viimati ")
    assert h2("varskus.html", "muutused").startswith("Allikate ja lahknevuste logis")
    # P3: alamlehtede h1 on vastus, mitte teema nimi
    for f, nimi in [("inimesed-oskused.html", "Digioskused ja oskuse puudus"),
                    ("ettevotted-voimekus.html", "Tootlikkus, digiintensiivsus ja teadus- ja arendustegevus"),
                    ("too-uuringud.html", "Mida uuringud tehisaru ja töö kohta leidsid"),
                    ("too-kirjandus.html", "Mida maailmas ja Eestis tehisarust ja tööst kirjutatakse"),
                    ("too-ametid.html", "Millised Eesti ametid on tehisarule avatud")]:
        assert h1(f) != nimi and len(h1(f)) > len(nimi) and "<b>" in re.search(r"<h1>(.*?)</h1>", sait[f], re.S).group(1), f
    assert re.search(r"digioskused on \d+,\d% Eesti 16–74-aastastest", h1("inimesed-oskused.html"))
    # P5: saidikaardil pole sisemärkmeid ega olekuveergu
    assert "Kadri" not in sait["saidikaart.html"] and "Eelvaate" not in sait["saidikaart.html"]
    assert ">Olek<" not in sait["saidikaart.html"]
    # P6, P7, P8
    assert h2("hanked.html", "tapsus").endswith("masinmärgendite järgi")
    assert "hindamata" not in h2("index.html", "teemad")
    assert "kolm puhul" not in sait["varskus.html"] and "korra" not in h2("index.html", "trend")
    # Kopeeritav fakt: ainult välise allika lingiga plaatidel, lause sisaldab allika lingi
    for f, h in sait.items():
        for m in re.finditer(r'<div class="plaat kp" data-kpi="([^"]+)">(.*?)</div>', h, re.S):
            nupp = re.search(r'data-fakt="([^"]+)"', m.group(2))
            valine = re.search(r'<span class="src">.*?href="https?://', m.group(2), re.S)
            assert bool(nupp) == bool(valine and not m.group(1).startswith("tk-")), (f, m.group(1))
            if nupp:
                assert "Allikas: " in nupp.group(1) and "https://" in nupp.group(1), (f, m.group(1))
                # Kadri 8.11 20:18: nupp on ikoon, sõna tuleb hõljudes (data-silt), ekraanilugejale aria-label
                b = re.search(r'<button[^>]*class="kopeeri".*?</button>', m.group(2), re.S).group(0)
                assert "<svg" in b and 'data-silt="' in b and 'aria-label="' in b, (f, m.group(1))
                assert re.sub(r"<[^>]+>", "", b).strip() == "", (f, m.group(1))
    # Esmakordne lugeja (kolleeg lingiga): avalehel ütleb üks lause, mis sait see on, ja viitab lugemisjuhendile
    tut = re.search(r'<p class="tutvus">(.*?)</p>', sait["index.html"], re.S)
    assert tut and "allikaga" in tut.group(1)
    # Kadri 8.11.2026: allikad ja lugemisjuhend on ühe lühikese lingi taga, mitte päises paremal
    allikad = re.search(r'<details class="allikad-l"><summary>Allikad ja kuupäevad</summary>(.*?)</details>', sait["index.html"], re.S)
    assert allikad and "kuidas-lugeda.html" in allikad.group(1) and "Statistikaamet" in allikad.group(1)
    assert 'class="seis-t"' not in sait["index.html"]
    js = (Path(__file__).resolve().parents[1] / "sait" / "sait.js").read_text(encoding="utf-8")
    assert "button.kopeeri" in js and "navigator.clipboard" in js and "execCommand('copy')" in js


def test_eksitav_silt_on_heleroosa(sait):
    # Kadri 8.11.2026 22:02: „eksitav silt võiks olla heleroosades toonides“
    assert '<span class="u-l risk">eksitav</span>' in sait["uudised.html"]
    css = (ehita.SIIN / "stiil.css").read_text(encoding="utf-8")
    assert ".u-l.risk { background: var(--eksitav-bg); color: var(--eksitav-ink); box-shadow: var(--eksitav-aar); }" in css
    assert "--eksitav-bg: #fce4ee; --eksitav-ink: #a3184f;" in css
    # tume teema: variant C punakam (Kadri 8.11.2026 22:14)
    assert ':root[data-seire-teema="dark"] { --eksitav-bg: transparent; --eksitav-ink: #ffa8b4; --eksitav-aar: inset 0 0 0 1px #e86a78; }' in css


def test_tehisaru_eitamine_on_oma_roll(sait):
    # Kadri 8.11.2026: „kuidas saab olla, et tehisaru ei mainita, kui isegi pealkirjas on sõna tehisaru“.
    # Kui ettevõte ütleb otse, et tehisaru pole põhjus, on roll ei_pohjus, mitte ei_mainita.
    from sait import lehed_uudised, lehed_ulevaade
    assert lehed_uudised.ROLL["ei_pohjus"] == "tehisaru pole põhjus"
    assert lehed_ulevaade.ROLL_NIMI["ei_pohjus"] == "pole põhjus"
    K = json.loads((ehita.SIIN.parent.parent / "tooelu-seire" / "koondamised_ee.json").read_text(encoding="utf-8"))
    assert "ei_pohjus" in K["rollid"]
    assert next(j for j in K["juhtumid"] if j["id"] == "eesti-energia-2026-11")["roll"] == "ei_pohjus"


def test_vaiketeema_on_pehme_ka_tumedas_seadmes():
    # Kadri 8.11.2026: Vercelis avanes tume teema, sest seade oli tumedas režiimis; vaikimisi peab olema Pehme.
    from sait import kest
    assert "prefers-color-scheme" not in kest.TEEMA_JS
    assert "t='soft'" in kest.TEEMA_JS


def test_kaks_teemat_hele_ja_tume():
    # Kadri 8.11.2026 22:15: Pehme on nüüd Hele (vaikimisi) ja senine valge Hele eemaldati.
    js = (ehita.SIIN / "sait.js").read_text(encoding="utf-8")
    assert "var JARG = ['soft', 'dark'];" in js and "soft: 'Hele', dark: 'Tume'" in js
    assert "'light'" not in js.split("var JARG")[1].split(";")[0]


def test_ettekanded_alamleht(A):
    # Kadri 8.11.2026: usaldatud seminaride ja konverentside ettekannete kokkuvõtted, „Uudised › Ettekanded“.
    import copy
    from sait import lehed_uudised
    from andmekiht import AndmeViga
    vaade = copy.deepcopy(next(v for v in json.loads((ehita.SIIN / "vaated.json").read_text(encoding="utf-8"))["vaated"] if v["id"] == "uudised"))
    assert [s["fail"] for s in vaade["alamlehed"]] == ["uudised.html", "ettekanded.html"]
    E = {"allikad": [{"id": "ut-dss", "nimi": "TÜ seminar", "url": "https://cs.ut.ee/", "liik": "seminar"}],
         "ettekanded": [{"id": "x", "esineja": "Mari Maasikas", "amet": "juht", "pealkiri": "Pealkiri", "allikas": "ut-dss",
                         "uritus": "Seminar", "kuupaev": "2025", "video": "https://youtu.be/abc?t=1", "kokkuvote": "Lühike.",
                         "mottes": ["üks", "kaks", "kolm"], "teemad": ["too"]},
                        {"id": "y", "esineja": "Jaan", "pealkiri": "Uuem", "allikas": "ut-dss", "kuupaev": "2026-05-27",
                         "video": "https://youtu.be/def", "kokkuvote": "Teine."}]}
    h = lehed_uudised.ettekanded({**A, "ettekanded": E, "ootel": {"ettekanded": 0}}, vaade)
    assert h.index("Uuem") < h.index("Pealkiri")  # uuemad eespool, ka siis kui kuupäev on ainult aasta
    assert '<span class="d">2025</span>' in h and "27.05.2026" in h and "<li>kaks</li>" in h
    assert "2 kokkuvõtet" in next(s for s in vaade["alamlehed"] if s["fail"] == "ettekanded.html")["h1"]
    # Tühi olek ütleb, mitu ootab kinnitust
    assert "3 ootab" in lehed_uudised.ettekanded({**A, "ettekanded": None, "ootel": {"ettekanded": 3}}, vaade)
    # Allikas peab olema usaldatud loendis
    E["ettekanded"][0]["allikas"] = "tundmatu"
    with pytest.raises(AndmeViga):
        lehed_uudised.ettekanded({**A, "ettekanded": E}, vaade)


def test_ettekanded_ainult_kinnitatud():
    from sait.vota_kaasa import kinnitatud_ettekanded
    d = {"allikad": [], "ettekanded": [{"id": "a", "seire_olek": "kinnitatud", "liik": "ettekanne"}, {"id": "b"}, {"id": "c", "seire_olek": "tagasi"}]}
    v = kinnitatud_ettekanded(d)
    assert [r["id"] for r in v["ettekanded"]] == ["a"] and "liik" not in v["ettekanded"][0]


def test_pohimenuu_on_m2_keskel_ilma_joonteta():
    # Kadri 8.11.2026 22:50 „kasuta M2 riba“: teemad päise keskel, hallid jooned läbipaistvad; 9.11 tavakirjas
    css = (ehita.SIIN / "stiil.css").read_text(encoding="utf-8")
    m2 = css.split("Põhimenüü M2")[1]
    assert "justify-content: center" in m2 and "font-weight: 400" in m2  # teemad tavakirjas (Kadri 9.11.2026)
    assert ".top { border-bottom-color: transparent; }" in m2 and "border-left" not in m2


def _vaade(vid):
    import copy
    return copy.deepcopy(next(v for v in json.loads((ehita.SIIN / "vaated.json").read_text(encoding="utf-8"))["vaated"] if v["id"] == vid))


def test_eesti_otsused_tulevad_kogumisest(A):
    # Kadri 8.11.2026 23:02: riigi otsused ja tähtajad leiab kogumine ise (teema „riik“), käsitsi neid ei kanta
    from andmekiht import AndmeViga
    vaade = _vaade("reeglid")
    assert [s["fail"] for s in vaade["alamlehed"]] == ["tehisaru-maarus.html", "eesti-otsused.html"]
    alam = lambda: next(s for s in vaade["alamlehed"] if s["fail"] == "eesti-otsused.html")  # noqa: E731
    h = lehed_teemad.eesti_otsused({**A, "uudised": []}, vaade, None, "2026-11-09")
    assert "pole kogumine veel leidnud" in h and "igapäevasest uudistekogumisest" in alam()["h1"]
    U = [{"kuupaev": "2026-11-09", "piirkond": "EE", "teema": "riik", "riigi_liik": "hange", "tahtaeg": "2026-11-12",
          "pealkiri": "Gigatehaste ühishange", "url": "https://www.justdigi.ee/x", "allikas": "justdigi.ee", "liik": "uudis",
          "pohjus": "Pakkumused 12.11.", "kontrollitud": True},
         {"kuupaev": "2026-11-09", "piirkond": "EE", "teema": "riik", "riigi_liik": "otsus", "pealkiri": "Valitsuse otsus",
          "url": "https://valitsus.ee/y", "allikas": "valitsus.ee", "liik": "uudis", "pohjus": "", "kontrollitud": True},
         {"kuupaev": "2026-11-08", "piirkond": "EE", "teema": "ai_too", "pealkiri": "Muu uudis", "url": "https://err.ee/z",
          "allikas": "ERR", "liik": "uudis", "pohjus": ""}]
    h = lehed_teemad.eesti_otsused({**A, "uudised": U}, vaade, None, "2026-11-09")
    assert "Gigatehaste ühishange" in h and "Valitsuse otsus" in h and "Muu uudis" not in h
    assert "tähtaeg 12.11.2026" in h and "Ees olevad tähtajad (1)" in h
    assert "järgmine tähtaeg on 12.11.2026" in alam()["h1"] and "2 Eesti riigi" in alam()["h1"]
    U[0]["riigi_liik"] = "tundmatu"
    with pytest.raises(AndmeViga):
        lehed_teemad.eesti_otsused({**A, "uudised": U}, vaade, None, "2026-11-09")


def test_pohjamaade_profiil_arvutab_indeksi_otse_kataloogist(A):
    import lehed
    P = lehed.pohjamaade_profiil(A)
    assert len(P) == 9 and sum(p["seirest"] for p in P) == 6
    for p in P:
        assert p["n_po"] >= 3 and p["n"] >= 6  # Eesti ja vähemalt viis teist riiki
        oodatud = (p["pk"] / p["ee"] if p["vp"] else p["ee"] / p["pk"]) * 100
        assert abs(p["indeks"] - oodatud) < 1e-9
    oskus = next(p for p in P if p["mid"] == "eurostat-isoc-ai-iaiuxr-oskus")
    assert oskus["vp"]  # „ei oska“: väiksem on parem, indeks pööratakse
    # Kolm näitajat tulevad kataloogist (kataloog/lae_valis.py laeb need iga päev otse API-st), mitte teise lehe failist
    uis = next(p for p in P if p["mid"] == "uis-teadlased")
    assert not uis["seirest"] and "UIS" in uis["allikas"][0]
    import copy
    B = copy.copy(A)
    B["valis_vaatlused"] = [r for r in A["valis_vaatlused"] if r["moodik"] != "uis-teadlased"]
    with pytest.raises(andmekiht.AndmeViga):
        lehed.pohjamaade_profiil(B)


def test_sait_ei_loe_teiste_lehtede_faile():
    # Kadri 8.11.2026: sait ei võta infot Kadri teistelt lehtedelt; kõik tuleb otse allikatest
    from pathlib import Path
    sait_kaust = Path(__file__).resolve().parent.parent / "sait"
    for p in sait_kaust.glob("*.py"):
        t = p.read_text(encoding="utf-8")
        for keelatud in ("analuus-andmed.csv", "digiriik-2027", "jagatav-", "Tehisaru 2027 lehe"):
            assert keelatud not in t, (p.name, keelatud)
    for p in (sait_kaust / "sisu").glob("*.csv"):
        assert "Tehisaru 2027" not in p.read_text(encoding="utf-8"), p.name


def test_uuringutulemused_ja_metoodika_on_seire_saidil(sait):
    # Kadri 8.11.2026: uuringutulemused ja metoodika ühes kohas, otse allikatest, samade reeglitega
    av = sait["avalik-sektor.html"]
    for i in ("etapid", "liigid", "moju", "oskused", "kupsus", "rahastus"):
        assert f'id="{i}"' in av, i
    assert "22 protsendipunkti väiksem osa" in tekst(av) and "83% uuendusrahast tuli ELilt" in tekst(av)
    ev = sait["ettevotted-voimekus.html"]
    assert 'id="arenguseire"' in ev and 'id="pohjamaad"' in ev and "Arvutatud: indeks" in ev
    kl = sait["kuidas-lugeda.html"]
    assert 'id="moisted"' in kl and 'id="numbrid-ei-naita"' in kl and "Seitse asja" in kl
    assert "eesti-otsused.html" in sait and 'href="eesti-otsused.html"' in sait["tehisaru-maarus.html"]


def test_a1_kujundus_kogu_saidil(sait):
    # Kadri 8.11.2026 23:41: „A1 teema sobib kõige paremini“ (katseleht kirjeldused/stiilid/t2027-seire)
    import kest
    css = (ehita.SIIN / "stiil.css").read_text(encoding="utf-8")
    assert "html[data-t] .plaat" in css and ".pea-rahu" in css
    assert "setAttribute('data-t','1')" in kest.TEEMA_JS  # artefaktis kirjutatakse <html> üle
    pehme = css.split(':root[data-seire-teema="soft"] {', 1)[1].split("}", 1)[0]
    assert "--page: #ffffff" in pehme and "--surface-2: #f9f9f9" in pehme
    h1 = re.search(r"<h1>(.*?)</h1>", sait["index.html"], re.S).group(1)
    assert re.fullmatch(r"Tehisaru kasutuses on Eesti inimesed ELis \d+\. ja <b>ettevõtted \d+\. kohal</b> \(20\d\d\)", h1), h1


def test_liikumine_l2_aeglane_ja_vahendatud_liikumise_austus():
    """Kadri 9.11.2026 „use L2 + aeglane“: ainult lehe üleminek ja ribade kasv, kõik reduced-motion kaitse all."""
    css = (ehita.SIIN / "stiil.css").read_text(encoding="utf-8")
    osa = css.split("Liikumine L2")[1]
    plokk = osa.split("@media (prefers-reduced-motion: no-preference) {", 1)[1]
    assert "@view-transition { navigation: auto; }" in plokk and "l-riba 1050ms" in plokk
    assert "@view-transition" not in css.split("Liikumine L2")[0]  # liikumist pole mujal kaitseta


def test_tutvustuse_leht_uuele_lugejale(A, sait):
    # Kadri 9.11.2026: leht uuele lugejale, kes tahab aru saada, mis see sait on
    h = sait["saidist.html"]
    for jaotis in ("kellele", "teemad", "sisuliigid", "kuidas-tootab", "mida-ei-ole"):
        assert f'id="{jaotis}"' in h
    for f in ("inimesed.html", "ettevotted.html", "too.html", "hanked.html", "kas-see-on-tosi.html", "kuidas-lugeda.html#uuendused"):
        assert f'href="{f}"' in h
    assert 'href="saidist.html">Mis see sait on?</a>' in sait["index.html"]  # avalehelt leitav
    assert 'href="saidist.html">Mis see sait on</a>' in sait["inimesed.html"]  # jaluses igal lehel
    assert "Kadri" not in h


def test_avatumad_ametid_on_tulpdiagramm(A, sait):
    # Kadri 9.11.2026: „see siin vajab normaalset visuaali“ – ametite tabel tulpadeks, tabel klõpsu taga
    leht = next(h for h in sait.values() if 'id="kokkupuude"' in h)
    osa = _jaotis(leht, "kokkupuude")
    K = A["kokkupuude"]
    assert len(re.findall(r'class="ar-r( a4)?"', osa)) == len(K["ametid"])
    assert osa.count('class="ar-r a4"') == sum(1 for r in K["ametid"] if str(r["aste"]) == "4")
    assert 'class="ar" data-piir="12"' in osa
    assert osa.index('class="ar"') < osa.index("<summary>Näita andmetabelit</summary>")


def test_gem_eksperthinnang_on_eraldi_sakis(A, sait):
    # Kadri 9.11.2026 („lisa“): GEM-i ekspertide hinnang Eurostati kasutuse kõrvale, selgelt märgitud ja oma skaalal
    L = A["leiud"]["gem-ai-teadlikkus"]
    v = next(r for r in A["leiud_arvud"] if r["leid"] == L["id"])["vaartus"]
    assert L["url"].startswith("https://www.gemconsortium.org/") and L["koht"] and L["kontrollitud"]
    h = sait["ettevotted.html"]
    assert 'id="sakk-gem-n"' in h
    osa = _jaotis(h, "gem")
    assert "Eksperthinnang, mitte mõõtmine." in osa
    assert f"Eesti {v.replace('.', ',')}" in osa
    # ei ole Eurostati %-teljel ega samas plokis kui ELi kaart
    assert 'class="gem-skaala"' in osa and 'class="gem-skaala"' not in _jaotis(h, "kasutus")
    assert "ei ole võrreldavad" in tekst(osa)


def test_paise_pilt_teema_jargi():
    # Kadri 9.11.2026 07:18: „tumedas A ja heledas B“ – tumedal teemal oma pilt, ka telefonis
    css = (Path(__file__).resolve().parent.parent / "sait" / "stiil.css").read_text(encoding="utf-8")
    tume = [r for r in css.split("}") if 'data-seire-teema="dark"] .pea-rahu.pilt::before' in r]
    assert len(tume) == 2 and all("pilt/avaleht-tume.jpg" in r for r in tume)
    assert css.count('url("pilt/avaleht.jpg")') == 2


def test_ai_kuulutuste_leiud_asukoht_ja_uks_tooandja(A, sait):
    # Kadri 9.11.2026: mustandi leiud 1 (asukoht) ja 2 (üks tööandja) AI-kuulutuste jaotisse; numbrid failidest
    K = A["ai_kuulutused"]
    if not K or not K.get("kuulutused"):
        pytest.skip("kuulutuste andmed puuduvad")
    leht = next(h for h in sait.values() if 'id="ai-kuulutused"' in h)
    assert leht.index('id="ai-kuulutused"') < leht.index('id="tk-kus"') < leht.index('id="tk-yks"')
    pk = [r for r in K["kuulutused"] if r["ruhm"] in ("ai_amet", "andmeamet", "ai_oskus")]
    harju = sum(1 for r in pk if r.get("maakond") == "Harjumaa")
    assert f"{round(harju / len(pk) * 100)}% on Harjumaal" in tekst(_jaotis(leht, "tk-kus"))
    import collections as _c
    top, n = _c.Counter(r.get("tooandja") for r in K["kuulutused"]).most_common(1)[0]
    osa = tekst(_jaotis(leht, "tk-yks"))
    assert f"{round(n / len(K['kuulutused']) * 100)}% on ühelt tööandjalt ({top})" in osa
    assert f"{n} / {len(K['kuulutused'])}" in osa


def test_paise_pilt_ei_tee_saiti_laiemaks():
    # Kadri 9.11.2026 07:30: „ära tee saiti piltide pärast laiemaks“ – 100vw pilt ei tohi tekitada rõhtsat kerimisriba
    css = (Path(__file__).resolve().parent.parent / "sait" / "stiil.css").read_text(encoding="utf-8")
    assert "html[data-t] body { overflow-x: clip; }" in css


def test_sait_ei_tee_ise_vigu_mille_eest_hoiatab(sait):
    # Sisuloogika läbivaatus 9.11.2026 (Kadri „jah“): sait ei tohi teha samu vigu, mida ta väidete kontrollis parandab
    avaleht, ettevotted = (tekst(sait[f]) for f in ("index.html", "ettevotted.html"))
    # 2025 ja 2026 on eri klassifikaatoriga: ettevõtete kasvu ei arvutata
    assert "aastaga ei võrrelda" in avaleht.split("Ettevõtted, kes kasutavad tehisaru")[1][:200]
    assert "aastaga ei võrrelda" in ettevotted.split("Kasutab tehisaru (10+ hõivatut)")[1][:200]
    # number on vähemalt 10 hõivatuga ettevõtete kohta
    assert "vähemalt 10 hõivatuga Eesti ettevõtetest" in tekst(re.search(r"<h1[^>]*>(.*?)</h1>", sait["ettevotted.html"], re.S).group(1))
    # registriandmete seos, mitte põhjus
    assert "tõstab tootlikkust" not in avaleht
    # tööl kasutamine on kõigi 16–74-aastaste osa
    assert "16–74-aastastest" in tekst(re.search(r"<h1[^>]*>(.*?)</h1>", sait["inimesed.html"], re.S).group(1))
    # hangete aastaid veel ei võrrelda
    assert "2025 kokku" not in avaleht


def test_ai_tooriistade_ligipaas_ettevotete_lehel(sait, A):
    # Kadri 9.11.2026 12:32: ligipääsu plokk saidile kohe, märkega „töös, kogumine käib“; valim on uudistepõhine
    S = (A.get("ligipaas") or {}).get("sundmused") or []
    if not S:
        pytest.skip("sisu/ligipaas.json puudub")
    h = sait["ettevotted.html"]
    sec = h[h.index('id="ligipaas"'):]
    sec = sec[:sec.index("</section>")]
    assert "Töös: kogumine käib" in sec
    assert f"{abi.sonaga(len(S), 'seestytlev').capitalize()} kogutud otsusest" in tekst(sec)
    assert "Näitame arve, mitte osakaale" in sec
    assert "33 asutusel puudus asutusesisene kord" in tekst(sec)  # Riigikontroll 30.05.2025, p 58
    otsused = sec.split('class="lp-lisa"')[0]  # taustaplokkide tabelid ei ole otsused
    assert otsused.count("<tr>") == len(S) + 1  # päis + üks rida otsuse kohta
    assert all("kontroll" not in r for r in S)  # sisemine kontrollimärge ei lähe saidile


def test_ligipaasu_taust_teised_riigid_ja_uuringud(sait, A):
    # Kadri „jah, avalda“ 9.11.2026 19:59: kaks taustaplokki samas jaotises; ainult avalikud allikad, iga rida lingiga,
    # meie soovitust (keskne leht, värav) saidil pole
    K = A.get("ligipaas_kontekst") or {}
    if not K:
        pytest.skip("sisu/ligipaas-kontekst.json puudub")
    h = sait["ettevotted.html"]
    sec = h[h.index('id="ligipaas"'):]
    sec = sec[:sec.index("</section>")]
    for plokk, read, pk in [("ligipaas-riigid", K["riigid"], "Soome, Holland, Ühendkuningriik ja USA lubavad ametnikel tehisaru kasutada tingimustega"),
                            ("ligipaas-uuringud", K["uuringud"], "Kasu on päris, aga mitte igas ülesandes, ja kasutaja hinnang võib eksida")]:
        osa = sec[sec.index(f'id="{plokk}"'):]
        osa = osa[:osa.index("</table>")]
        assert pk in tekst(osa)
        assert osa.count("<tr>") == len(read) + 1
        for r in read:
            assert r["url"].startswith("https://") and f'href="{r["url"]}"' in osa
    assert {r["riik"] for r in K["riigid"]} == {"Soome", "Holland", "Ühendkuningriik", "USA (föderaal)"}
    assert "Tõendi liik" in sec and "eeltrükk, väike valim" in sec
    assert "värav" not in tekst(sec).lower()
    # kriitiku läbivaatus 9.11.2026: pealkiri ei üldista „teisi riike“; tööriistakeelu vastunäide on algallikaga
    assert "Teised riigid ei keela" not in tekst(sec)
    assert "direction-001-2025-deepseek" in sec
    assert "süstemaatiline ülevaade" in tekst(sec)
    # sama uuring on Töö lehel 14%; taustaplokk ei tohi näidata teist numbrit
    assert "tunnis 14% rohkem pöördumisi" in tekst(sec)


def test_ligipaasu_sundmused_votab_uudised_ja_tagasivaate():
    import vota_kaasa
    uud = [{"kuupaev": "2026-11-05", "ettevote": "A", "ligipaas": "piirab_rolliga", "ligipaas_pohjus": "risk", "arv_tekst": "x", "url": "u"},
           {"kuupaev": "2026-11-06", "ettevote": "B", "arv_tekst": "ei ole ligipääsu otsus", "url": "u"}]
    tv = [{"kuupaev": "2023-05-02", "ettevote": "C", "ligipaas": "keelab", "tekst": "y", "url": "u", "kontroll": "sisemine", "kontrollitud": True},
          {"kuupaev": "2024-01-01", "ettevote": "D", "ligipaas": "keelab", "tekst": "z", "url": "u", "kontrollitud": False}]
    S = vota_kaasa.ligipaasu_sundmused(uud, tv)
    assert [r["ettevote"] for r in S] == ["A", "C"]
    assert all("kontroll" not in r for r in S)


def test_pealkirjad_on_luhikesed(sait):
    """Kadri 10.11.2026: pealkirjad olid liiga pikad ja lärmakad. h1 on lühike vastus, detail on lead-is või h2 all."""
    for f, h in sait.items():
        if not f.endswith(".html"):
            continue
        assert "¦" not in h, f
        h1 = tekst(re.search(r"<h1>(.*?)</h1>", h, re.S).group(1)).strip()
        assert len(h1) <= 80, (f, len(h1), h1)
    import kest
    proov = kest.lyhenda_pealkirjad('<h1>Lühike ¦ detail</h1>\n<p class="lead">Lead.</p><h2 id="x">Kaks ¦ <b>teine</b></h2>')
    assert '<h1>Lühike</h1>\n<p class="lead">Detail. Lead.</p>' in proov and '<p class="h-lisa"><b>Teine</b>.</p>' in proov


def test_voo_silt_uus_ainult_14_paeva():
    """Kadri 10.11.2026: üle 14 päeva vana number ei ole „uus“."""
    from datetime import date
    from lehed_ulevaade import voo_silt
    tana = date(2026, 11, 10)
    assert voo_silt("2026-10-30", "uus number", tana) == '<span class="t uus">uus</span>'
    assert voo_silt("2026-10-21", "uus number", tana) == '<span class="t">number</span>'
    assert voo_silt("2026-09-16", "uus number", tana) == '<span class="t">number</span>'
    assert voo_silt("2026-11-05", "väide", tana) == '<span class="t">väide</span>'


def test_kasutusloogika_klaviatuur_puude_jagatud_link(sait):
    """Kasutusloogika 11.11.2026, uus nurk (klaviatuur, puude, jagatud link, tühi olek)."""
    # 1. Järjestusgraafikus on üks Tab-peatus SVG kohta, mitte iga joon (enne 76 avalehel, 148 Töö lehel).
    for leht in ("index.html", "too.html", "ettevotted.html"):
        for svg in re.findall(r'<svg class="bump.*?</svg>', sait[leht], re.S):
            assert svg.count('class="bs') > 1
            assert svg.count('tabindex="0"') == 1, leht
    js = (Path(__file__).resolve().parents[1] / "sait" / "sait.js").read_text(encoding="utf-8")
    assert "ArrowDown" in js and "koik[j].focus()" in js  # nooled liiguvad joonte vahel
    # 2. Kaart reageerib ka koputusele, mitte ainult hiirele.
    kaart = js[js.index("document.querySelectorAll('.kaart')"):js.index("// Kaart ja kõrvaltabel")]
    assert "addEventListener('click'" in kaart
    # 3. Filtri link saab jaotise ankru, et saadetud link avaneks filtri juures.
    assert "function jaotis(el)" in js and "sea(k, v, el)" in js.replace("function sea(k, v, el)", "sea(k, v, el)")
    # 4. Tühi otsing ütleb, mida teha.
    assert "Ei leitud ühtegi" in js


def test_kaart_ilma_eesti_sildita_ja_seotud_korvaltabeliga(sait):
    """Kadri 11.11.2026: kaardil pole Eesti eraldi silti; riigi peal hõljudes tuleb sama riik esile ka teisel pool."""
    js = (Path(__file__).resolve().parents[1] / "sait" / "sait.js").read_text(encoding="utf-8")
    for leht in ("index.html", "inimesed.html", "ettevotted.html"):
        h = sait[leht]
        assert 'class="kaart"' in h and "kaart-silt" not in h, leht
        jaotis = h[h.rindex("<section", 0, h.index('class="kaart"')):]
        jaotis = jaotis[:jaotis.index("</section>")]
        kaardil = set(re.findall(r'<path class="k\d[^"]*" d="[^"]*" data-n="([^"]+)"', jaotis))
        teisel = set(re.findall(r'class="jrj-r[^"]*" role="listitem" data-n="([^"]+)"', jaotis)) | \
            set(re.findall(r'<g class="bs[^"]*" data-s="[^"]+" tabindex="-?[01]" role="button" aria-label="([^"]+)"', jaotis))
        assert teisel and teisel <= kaardil, leht  # nimed klapivad, muidu seos ei leia riiki
    seos = js[js.index("// Kaart ja kõrvaltabel"):js.index("// Pikk tabel")]
    assert "seire-riik" in js and "k.seireRiik" in seos and "'.bs[aria-label]'" in seos and "'.jrj-r[data-n]'" in seos
def test_innovatsioonimarge_on_hankija_oma(sait):
    """Kadri 11.11.2026: „innovatsioon“ silt on hankija märge, mitte meie hinnang."""
    h = sait["hanked-naited.html"]
    assert '<span class="u-t">innovatsioon</span>' not in h
    assert "hankija märge: innovatsioon" in h


def test_tuhja_uuringute_ja_vaidete_plokki_ei_naidata(sait):
    """Kadri 11.11.2026: „pole veel hinnatud“ plokid ja nende nupud tegid navigatsiooni segaseks."""
    import teemamall as tm
    assert tm.uuringute_plokk([], [], [("x", "Mujal", "")]) == ""
    for f, h in sait.items():
        assert "pole veel hinnatud" not in h, f
        m = re.search(r'<nav class="lehel[^"]*" aria-label="Sellel lehel">(.*?)</nav>', h, re.S)
        for ank in re.findall(r'href="#([^"]+)"', m.group(1) if m else ""):
            assert f'id="{ank}"' in h, (f, ank)  # „Sellel lehel“ ei viita puuduvale plokile
    assert 'id="t-vaited"' not in sait["hanked.html"] and 'id="t-uuringud"' not in sait["hanked.html"]

def test_ettekanded_on_valdkonna_ruhmades(sait):
    """Kadri 11.11.2026: ühes nimekirjas oli kõik segamini; ettekanded on valdkonna rühmades, igas uuemad eespool."""
    from sait import lehed_uudised
    h = sait["ettekanded.html"]
    ruhmad = re.findall(r'<div class="ek-r" id="ek-([a-z-]+)">', h)
    assert len(ruhmad) >= 2 and "muu" not in ruhmad  # igal kinnitatud kirjel on rühm
    assert ruhmad == [k for k in lehed_uudised.ETTEKANDE_RUHM if k in ruhmad]  # kindel järjekord
    for k in ruhmad:  # valikurea iga link viib olemasolevale rühmale
        assert f'href="#ek-{k}"' in h
    E = json.loads((ehita.SIIN / "sisu" / "ettekanded.json").read_text(encoding="utf-8"))
    assert all(r.get("ruhm") in lehed_uudised.ETTEKANDE_RUHM for r in E["ettekanded"])


def test_teemalehel_ainult_oma_reegel_ja_uuringud_ei_kordu(sait):
    """Kadri 11.11.2026 („kõigiga nõus“): teemalehel üks reegel, tähtajad ühes kohas; uuringud ei kordu."""
    for f in ("inimesed.html", "ettevotted.html", "too.html", "avalik-sektor.html", "hanked.html"):
        r = re.search(r'<section class="pn" id="t-reeglid".*?</section>', sait[f], re.S).group(0)
        assert r.count("<li>") == 1, f
        assert 'href="tehisaru-maarus.html#tahtajad"' in r, f
    inim = re.search(r'<section class="pn" id="t-uuringud".*?</section>', sait["inimesed.html"], re.S).group(0)
    assert inim.count("<li>") == 1 and "GDS" not in inim and "veel pole" not in inim


def test_ulesehituse_kontroll_a_b_c_e(sait):
    """Kadri 11.11.2026 „kõigile jah“ (ülesehituse kontroll): vähem nupuridu ja selgem roll igal real."""
    import kest
    # A: „Sellel lehel“ rida ainult siis, kui linke on vähemalt neli
    for f, h in sait.items():
        m = re.search(r'aria-label="Sellel lehel">(.*?)</nav>', h, re.S)
        if m:
            assert m.group(1).count("<li>") >= kest.LEHEL_MIN, f
    assert 'aria-label="Sellel lehel"' not in sait["ettekanded.html"] and 'aria-label="Valdkonnad"' in sait["ettekanded.html"]
    # B: avalehe kiibid ei kanna teemalehtede nimesid
    kiibid = re.findall(r">([^<>]+)</a>", re.search(r'aria-label="Sellel lehel">(.*?)</nav>', sait["index.html"], re.S).group(1))
    menuu = re.findall(r">([^<>]+)</a>", re.search(r'<ul class="menu">(.*?)</ul>', sait["index.html"], re.S).group(1))
    assert not set(kiibid) & set(menuu), set(kiibid) & set(menuu)
    # C: alamlehtede rida on menüürida teema nimega, mitte sakk
    assert '<span class="alam-silt">Töö:</span>' in sait["too-uuringud.html"]
    css = (ehita.SIIN / "stiil.css").read_text(encoding="utf-8").split("Alamlehtede rida on menüü, mitte sakk")[1]
    assert "border-bottom: 0" in css and "overflow-x: auto" in css
    # E: Usalduse esimene leht ütleb, mida osa tervikuna näitab
    assert "Usaldus kontrollib kolme asja" in sait["kas-see-on-tosi.html"]
    # F: vanad lingid hangete loendile viivad uuele lehele
    assert not any('href="hanked.html#loend"' in h for h in sait.values())


def test_podcastid_ettekannete_lehel(sait):
    """Kadri 11.11.2026: Lex Fridmani ja Mindscape'i podcastid Ettekannete lehel, uus rühm „Taust“."""
    h = sait["ettekanded.html"]
    assert 'id="ek-taust"' in h and "Taust: mõistus ja informatsioon" in h
    assert h.count('data-liik="podcast"') == 18 and h.count('data-liik="seminar"') + h.count('data-liik="veebiseminar"') == 10
    assert '<span class="u-l arv">podcast</span>' in h and "lõik algab 0:15:28" in h
    assert "Lex Fridman Podcast" in h and "Mindscape (Sean Carroll)" in h
    assert "lex-452" not in h and "Dario Amodei" not in h  # aegunud osa jäeti välja (Kadri 11.11)


def test_koondamised_ei_ole_esikohal(sait):
    """Kadri 11.11.2026: koondamised olid liiga suure fookuse all. Töö lehel on töötus esimene sakk üksi ja koondamised
    oma sakis koos tabeliga „Keda koondajad otsivad“. Uudiste filtris pole koondamisel oma nuppu: see on töö all
    (Kadri 11.11.2026: „võta koondamine siit ära, see info peaks koonduma töö alla“)."""
    h = sait["too.html"]
    sakid = re.findall(r'role="tab" id="sakk-([a-z-]+)-n"[^>]*>([^<]+)</button>', h)
    assert [s for s, _ in sakid] == ["tootus", "tootus-el", "vabad", "portaalid", "ai-tood", "koondamised", "prognoos"]
    assert dict(sakid)["tootus"] == "Töötus"
    esimene = h[h.index('id="sakk-tootus"'):h.index('id="sakk-tootus-el"')]
    assert 'id="tootus-kuud"' in esimene and 'id="koondamised"' not in esimene
    koond = h[h.index('id="sakk-koondamised"'):h.index('id="sakk-prognoos"')]
    assert 'id="koondamised"' in koond and 'id="palkamine"' in koond
    u = sait["uudised.html"]
    for rid in ("eesti-uudised", "maailma-uudised"):
        osa = u[u.index(f'id="{rid}"'):]
        osa = osa[osa.index('aria-label="Vali teema"'):]
        nupud = re.findall(r'<button type="button" data-f="([a-z_]*)"', osa[:osa.index("</div>")])
        assert nupud[0] == "" and "koondamine" not in nupud, (rid, nupud)
    assert lehed_uudised.TEEMA_FILTER["koondamine"] == "too"
    assert 'data-teema="koondamine"' not in u
    assert "riigi otsus, statistika, üle 50 koondatu" in u


def test_uudiste_valdkond_ja_teema(sait, A):
    """Kadri 11.11.2026: andmed ja tehisaru eraldi, riigi uudistel filter ka maailmas, vaikimisi tehisaru."""
    import copy
    assert lehed_uudised.valdkond({"teema": "andmed", "pealkiri": "x"}) == "andmed"
    assert lehed_uudised.valdkond({"teema": "koondamine", "ai_roll": "ei_mainita", "pealkiri": "x"}) == "muu"
    assert lehed_uudised.valdkond({"teema": "koondamine", "ai_roll": "osaline", "pealkiri": "x"}) == "tehisaru"
    assert lehed_uudised.valdkond({"teema": "riik", "pealkiri": "Andmete teabevärav uueneb"}) == "andmed"
    assert lehed_uudised.valdkond({"teema": "riik", "pealkiri": "Tehisaru koolitused raamatukogudes"}) == "tehisaru"
    assert lehed_uudised.valdkond({"teema": "riik", "pealkiri": "Andmed", "valdkond": "tehisaru"}) == "tehisaru"  # väli võidab
    B = copy.deepcopy(A)
    B["uudised"] += [dict(B["uudised"][0], teema="strateegia", piirkond="maailm", pealkiri="Riigi tehisarustrateegia", url="https://n.ee/s"),
                     dict(B["uudised"][0], teema="andmed", piirkond="maailm", pealkiri="Avaandmed", url="https://n.ee/a")]
    h = lehed_uudised.uudised(B, next(v for v in ehita.lae_vaated() if v["id"] == "uudised"))
    for rid in ("eesti-uudised", "maailma-uudised"):
        osa = h[h.index(f'id="{rid}"'):]
        osa = osa[:osa.index("</section>")]
        vk = osa[osa.index('aria-label="Vali valdkond"'):]
        vk = vk[:vk.index("</div>")]
        assert re.findall(r'data-u="([a-z]*)" aria-pressed="(true|false)"', vk)[:1] == [("tehisaru", "true")]
        assert 'data-u="andmed"' in vk and 'data-u="koik"' in vk
        for li in re.findall(r'<li data-teema="[^"]*" data-vk="([a-z]+)"[^>]*?( hidden)?>', osa):
            assert (li[0] == "tehisaru") == (li[1] == ""), li  # vaikimisi on näha ainult tehisaru
    m = h[h.index('id="maailma-uudised"'):]
    m = m[:m.index("</section>")]
    assert 'data-f="riik"' in m and '<li data-teema="riik" data-vk="tehisaru"' in m  # strateegia on riigi all
    assert '<li data-teema="muu" data-vk="andmed"' in m
    assert ">tehisaru ja töö<" not in h and 'data-f="ai_uldine"' not in h
    js = (ehita.SIIN / "sait.js").read_text(encoding="utf-8")
    assert "['ala', '.u-f[aria-label=\"Vali valdkond\"] button[data-u]', 'data-u']" in js
    assert "b.disabled = !!v && k === 0" in js


def test_uudiste_allika_logo(A, tmp_path, monkeypatch):
    """Kadri 11.11.2026: allikad logodena uudise kõrval, nimi hõljudes; logota allikas jääb tekstiks."""
    import json
    import lae_logod
    png = b"\x89PNG\r\n\x1a\n" + b"0" * 200
    laetud = []

    def laadija(url):
        laetud.append(url)
        if "news.err.ee" in url or "doi.org" in url:
            raise OSError("pole")
        if "err.ee" in url or "theguardian.com" in url:
            return png
        return b"<html>404</html>"
    (tmp_path / "u.jsonl").write_text("\n".join(json.dumps({"url": u}) for u in (
        "https://news.err.ee/1", "https://www.err.ee/2", "https://www.theguardian.com/x", "https://doi.org/10.1/x",
        "https://tundmatu.example/y")), encoding="utf-8")
    assert lae_logod.main(laadija, tmp_path / "logod", tmp_path / "u.jsonl") == 2
    logod = json.loads((tmp_path / "logod" / "logod.json").read_text(encoding="utf-8"))
    assert logod == {"err.ee": "err.ee.png", "theguardian.com": "theguardian.com.png"}  # news.err.ee → err.ee
    assert not any("doi.org" in u for u in laetud)
    assert lae_logod.main(laadija, tmp_path / "logod", tmp_path / "u.jsonl") == 0  # olemasolevat uuesti ei laeta
    assert lae_logod.logo_fail(logod, "https://news.err.ee/a") == "err.ee.png"
    assert lae_logod.logo_fail(logod, "https://tundmatu.example/y") is None
    monkeypatch.setattr(lehed_uudised, "LOGOD", logod)
    r = dict(A["uudised"][0], url="https://news.err.ee/1", allikas="ERR News")
    h = lehed_uudised._uudis(r)
    assert '<span class="u-a u-logo" title="ERR News"><img src="pilt/logod/err.ee.png" alt="ERR News"' in h
    h = lehed_uudised._uudis(dict(r, url="https://tundmatu.example/y", allikas="Tundmatu"))
    assert '<span class="u-a">Tundmatu</span>' in h
    tk = (ehita.SIIN.parents[1] / "turvakontroll" / "kontrolli.py").read_text(encoding="utf-8")
    assert '"tehisaru-seire/sait/pilt/logod/*"' in tk


def test_ettekannete_filter_liigi_ja_allika_jargi(sait, A):
    """Kadri 11.11.2026: „lisa allika põhine filtreerimine ettekannete juurde + ettekande meetod (podcastid, seminarid jms)“."""
    h = sait["ettekanded.html"]
    for k in ("liik", "allikas"):
        osa = h[h.index(f'class="u-f ek-f" data-k="{k}"'):]
        osa = osa[:osa.index("</div>")]
        nupud = re.findall(r'data-v="([^"]*)" aria-pressed="(true|false)">([^<]+)<span class="arv">(\d+)</span>', osa)
        assert nupud[0][:2] == ("", "true") and int(nupud[0][3]) == 28
        assert sum(int(n) for _, _, _, n in nupud[1:]) == 28, k  # iga ettekanne on täpselt ühes nupus
    assert 'data-v="podcast"' in h and 'data-v="seminar"' in h and 'data-v="mindscape"' in h
    assert re.search(r'<li data-liik="podcast" data-allikas="lex-fridman">', h)
    assert 'class="ps ek-tyhi" hidden' in h
    # Allika liik peab olema lubatud
    import copy
    from andmekiht import AndmeViga
    from sait import lehed_uudised
    vaade = copy.deepcopy(next(v for v in json.loads((ehita.SIIN / "vaated.json").read_text(encoding="utf-8"))["vaated"] if v["id"] == "uudised"))
    E = {"allikad": [{"id": "s", "nimi": "S", "url": "https://x.ee/", "liik": "raadio"}],
         "ettekanded": [{"id": "y", "esineja": "J", "pealkiri": "P", "allikas": "s", "kuupaev": "2026-05-27",
                         "video": "https://youtu.be/def", "kokkuvote": "T."}]}
    with pytest.raises(AndmeViga):
        lehed_uudised.ettekanded({**A, "ettekanded": E, "ootel": {"ettekanded": 0}}, vaade)


def test_tootukassa_pole_tooandja_tulp(sait):
    """Kadri 11.11.2026: „Töötukassa kaudu“ tulp tööandjate graafikus pole kasulik; see on märkusena graafiku all."""
    osa = _jaotis(sait["too.html"], "ai-kuulutused")
    graafik = osa[osa.index("Kes otsib"):osa.index("Kus: maakond")]
    assert "Töötukassa kaudu (eri" not in graafik.split('class="ps"')[0]
    assert re.search(r"Lisaks \d+ kuulutust Töötukassa kaudu", graafik)


def test_tooportaalide_valdkonna_filter(A):
    """Kadri 11.11.2026: „tahaks et teised väljad oleks valdkonna järgi filtreeritavad“. Kui kogumine annab
    `valdkonniti`, saab valdkonna valida ja linnad ning tööandjad näitavad selle valdkonna jaotust."""
    import copy
    from sait import lehed_uudised
    B = copy.deepcopy(A)
    cv = next(p for p in B["toopakkumised"]["portaalid"] if p["portaal"] == "CV.ee")
    for p_ in B["toopakkumised"]["portaalid"]:
        p_.pop("valdkonniti", None)
    assert "tp-vk" not in lehed_uudised.toopakkumised(B)  # andmeteta filtrit pole
    v0 = next(r["nimi"] for r in cv["ametivaldkond"] if r["nimi"] not in lehed_uudised.LISASILDID)
    cv["valdkonniti"] = [{"nimi": v0, "arv": 10, "linnad": [{"nimi": "Narva", "arv": 7}, {"nimi": "Tartu", "arv": 3}],
                          "tooandjad": [{"nimi": "Firma OÜ", "arv": 5}]},
                         {"nimi": "Pole kategooria", "arv": 1, "linnad": [{"nimi": "X", "arv": 1}], "tooandjad": []}]
    cv["valdkonniti"][0]["tooandjad"].append({"nimi": "Siseministeeriumi infotehnoloogia- ja arenduskeskus", "arv": 2})
    h = lehed_uudised.toopakkumised(B)
    # Kadri 11.11.2026: eraldi nupurida raiskas ruumi; valdkonna tulp on ise filter
    assert "u-f tp-vk" not in h and "ek-f-silt" not in h.split('data-vk-sisu=""')[1].split("</div>")[0]
    vaikimisi = h[h.index('data-vk-sisu=""'):h.index(f'data-vk-sisu="{v0}"')]
    assert re.findall(r'data-vk="([^"]*)" role="button"', vaikimisi) == [v0]  # tundmatu valdkond jääb välja
    assert 'aria-pressed="true"' not in vaikimisi and "klõpsa valdkonnal" in vaikimisi
    osa = h[h.index(f'data-vk-sisu="{v0}" hidden'):]
    osa = osa[:osa.index('data-vk-sisu', 20) if 'data-vk-sisu' in osa[20:] else len(osa)]
    assert "Narva" in osa and "Firma OÜ" in osa and f"valdkonnas {v0.lower()}" in osa
    assert re.search(r'<div class="rida fookus tp-v" data-vk="' + re.escape(v0) + '" role="button" tabindex="0" aria-pressed="true"', osa)
    assert '<button type="button" class="tp-koik" data-vk="">kõik valdkonnad</button>' in osa
    # Kadri 11.11.2026: pikk nimi lühendina, täisnimi hõljutades
    assert '<abbr title="Siseministeeriumi infotehnoloogia- ja arenduskeskus">SMIT</abbr>' in osa



def test_tootukassa_oma_sakis_cv_ee_kaudu(A, sait):
    """Kadri 11.11.2026: Töötukassa CV.ee ja CV Keskuse kõrval detailsema statistikaga. Jaotus tuleb CV.ee kaudu
    vahendatud kuulutustest ja lugeja näeb, et see ei klapi Töötukassa kogu arvuga."""
    tk = next((p for p in A["toopakkumised"]["portaalid"] if p["portaal"] == "Töötukassa"), None)
    if not tk or not isinstance(tk.get("ametivaldkond"), list):
        pytest.skip("Töötukassa jaotust pole andmetes")
    osa = _jaotis(sait["too.html"], "toopakkumised")
    assert 'aria-controls="tp-töötukassa"' in osa
    tk_osa = osa[osa.index('id="tp-töötukassa"'):]
    assert "Jaotused on " in tk_osa and "mõõdavad eri asja" in tk_osa and 'class="ribad lihtne tp-vk"' in tk_osa


def test_uudiste_numbriplaadid_on_tihedad_ilma_allikareata(sait):
    """Kadri 11.11.2026: „Seire uudistekogumine“ rida ei andnud infot ja võttis ruumi; plaadid väiksemaks."""
    u = sait["uudised.html"]
    pais = u[u.index('<aside class="vastus kpi-pais tihe"'):]
    pais = pais[:pais.index("</aside>")]
    assert pais.count('class="plaat kp"') == 4
    assert "Seire uudistekogumine" not in u and 'class="src"' not in pais
    # teiste lehtede plaatidel on allikas alles
    assert 'class="src"' in sait["index.html"].split('class="plaadid kaks"')[1]


def test_valislingid_avanevad_uues_vahelehes(sait):
    """Kadri 11.11.2026: uudis (ja iga välislink) avaneb uues vahelehes, et sait jääks lahti. Saidi enda lingid mitte."""
    valis = sise = 0
    for f, h in sait.items():
        for a in re.findall(r"<a [^>]*>", h):
            href = re.search(r'href="([^"]*)"', a)
            if not href:
                continue
            if re.match(r"https?://", href.group(1)):
                valis += 1
                assert 'target="_blank"' in a and 'rel="noopener"' in a, (f, a)
            else:
                sise += 1
                assert 'target="_blank"' not in a, (f, a)
    assert valis > 100 and sise > 100
    u = sait["uudised.html"]
    assert re.search(r'<a [^>]*href="https?://[^"]*"[^>]*target="_blank"', u.split('id="eesti-uudised"')[1])
