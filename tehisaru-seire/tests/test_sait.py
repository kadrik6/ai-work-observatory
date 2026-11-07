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
    assert 'class="k2 fookus"' in graafik and "Eesti 23,4%" in tekst(graafik)
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
    assert "viis on kehtima hakanud, kolm on veel ees" in nyyd
    hiljem = tekst(lehed_teemad.reeglid(A, v, vaated, tana="2028-12-01"))
    assert "kaheksa on kehtima hakanud, null on veel ees" in hiljem


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
    assert 'class="el-kaart"' in rida and 'class="jrj"' in rida
    # järjestuses on kõik 27 riiki ja iga nimi on ka kaardil (hiire seos)
    nimed = re.findall(r'class="jrj-r[^"]*" role="listitem" data-n="([^"]+)"', rida)
    assert len(nimed) == len(A["el_riigid"])
    for n in nimed:
        assert f'data-n="{n}"' in rida.split('class="jrj"')[0]


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
    assert "katseline" in osa and "pimesi" in osa and "tulbad2" not in osa
    assert "pimesi" in _jaotis(sait["index.html"], "hanked") and "aastatulbad" not in _jaotis(sait["index.html"], "hanked")
    assert 'id="hanked"' not in sait["avalik-sektor.html"]


def test_menuus_on_kaheksa_teemat_ja_usaldus_on_oma_teema(sait):
    # Kadri 6.11.2026 21:59: Hanked on oma menüüpunkt. 22:27 (paigutuse ettepanekud 1–3, 10): Usaldus oma menüükoht
    menuu = re.search(r'<ul class="menu">(.*?)</ul>', sait["index.html"], re.S).group(1)
    assert re.findall(r">([^<>]+)</a>", menuu) == ["Inimesed", "Ettevõtted", "Töö", "Avalik sektor", "Hanked", "Tehisaru määrus", "Uudised", "Usaldus"]
    assert '<a href="hanked.html" aria-current="page">Hanked</a>' in sait["hanked.html"]
    assert '<ul class="sellel"></ul>' not in "".join(sait.values())
    for f in ("kas-see-on-tosi.html", "lahknevused.html", "varskus.html"):
        assert '<a href="kas-see-on-tosi.html" aria-current="page">Usaldus</a>' in sait[f], f
    assert 'class="alamlehed"' not in sait["uudised.html"]


def test_lahknevused_ja_varskus_on_usalduse_all_nahtaval(sait):
    # Kadri 6.11.2026 21:38: Eurostati ja Statistikaameti võrdlus jääb nähtavale, kontrollib ministeerium
    osa = _jaotis(sait["lahknevused.html"], "lahknevused")
    assert "selgitamata" in osa and "<details" not in osa.split("</header>")[0]
    assert 'id="varskus"' in sait["varskus.html"] and 'id="muutused"' in sait["varskus.html"]
    assert 'id="varskus"' not in sait["kuidas-lugeda.html"]


def test_igas_teemavaates_on_numbriplaadid(sait):
    for f in ["inimesed.html", "ettevotted.html", "too.html", "avalik-sektor.html", "tehisaru-maarus.html", "hanked.html", "kas-see-on-tosi.html"]:
        assert 'class="vastus"' in sait[f], f


def test_koondamiste_visuaali_pealkiri_tuleb_andmetest(A, sait):
    j = A["koondamised"]["juhtumid"]
    arv = lambda r: r["arv_eestis"] if r.get("arv_eestis") is not None else r.get("arv_ulem")  # noqa: E731
    pohjus = sum(arv(r) for r in j if arv(r) and r["roll"] in ("otsene", "osaline"))
    kokku = sum(arv(r) for r in j if arv(r))
    h2 = sait["too.html"].split('id="h-koondamised-v">')[1].split("</h3>")[0]
    assert f"<b>{pohjus} töökoha</b>" in h2 and f"{kokku}-st" in h2


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
    h = sait["hanked.html"]
    L = A["hanked_leht"]["loend"]
    tabel = h.split('class="h-tabel"')[1].split("</table>")[0]
    assert tabel.count("<tr data-hea") == len(L)
    assert tabel.count('data-hea="1"') == sum(r.get("hea") == 3 for r in L)
    assert f'<b>{sum(r.get("hea") == 3 for r in L)} head näidet</b> {len(L)}-st' in h
    assert tabel.count("viitenumber") == sum(1 for r in L if not r.get("url"))


def test_hanked_on_katseline_ja_tapsus_tuleb_andmetest(A, sait):
    h = sait["hanked.html"]
    hm = A["hanked_leht"]["hindamine"]["hindamine"]
    t = hm["tulemused"][hm["valitud"]]
    assert h.count("katseline") >= 3 and "inimene pole neid veel kontrollinud" in h
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
    assert f"(kokku {kuulutusi} kuulutust)" in h2


def test_uudise_levik_on_valjaannete_arv(A):
    import copy
    B = copy.deepcopy(A)
    B["uudised"][0]["levik"] = {"arv": 9, "allikad": ["ERR", "Delfi"], "kontrollitud": "2026-11-06"}
    h = lehed_uudised.uudised(B, next(v for v in ehita.lae_vaated() if v["id"] == "uudised"))
    assert "9 väljaannet</span>" in h and "Kajastasid: ERR, Delfi" in h


def test_uudiste_paneel_ytleb_kas_viimasel_kontrollil_lisandus(A, sait):
    h = sait["uudised.html"]
    paev = A["uudiste_olek"]["viimane_kontroll"][:10]
    uued = sum(r.get("lisatud") == paev for r in A["uudised"])
    assert h.count('class="ps u-seis"') == 2
    assert h.count('<span class="u-l suur">uus</span>') == uued


def test_pikad_teemad_on_alamlehtedeks_jagatud(sait):
    # Kadri 6.11.2026: Töö, Inimesed ja Uudised eraldi alamlehtedeks; alamlehtede rida igal alamlehel
    for v in ehita.lae_vaated():
        for s in v.get("alamlehed", []):
            h = sait[s["fail"]]
            assert f'<a href="{s["fail"]}" aria-current="page">' in h, s["fail"]
            assert all(f'href="{t["fail"]}"' in h for t in v["alamlehed"])
            assert f'<a href="{v["fail"]}" aria-current="page">{v["menuu"]}</a>' in h  # teema jääb menüüs valituks
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
    # Kadri 6.11.2026 22:27, ettepanek 8
    assert 'class="seotud"' in sait["avalik-sektor.html"] and 'href="hanked.html"' in _seotud(sait["avalik-sektor.html"])
    assert 'href="avalik-sektor.html"' in _seotud(sait["hanked.html"])


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
    assert 'class="lehel lehel-parem"' in sait["too.html"] and 'class="lehel lehel-rida"' in sait["too.html"]
    assert '<nav class="rada"' not in sait["index.html"]


def test_publikatsiooni_tsiteeringud_on_pealkirja_korval(A, sait):
    # Kadri MKUS-i kommentaar 7.11.2026 08:50: „tahaks näha kõrval arvu mitu korda on tsiteeritud“
    osa = _jaotis(sait["too-kirjandus.html"], "publikatsioonid")
    assert '<th scope="col" class="v">Tsiteeritud</th><th scope="col">Publikatsioon ja kanal</th>' in osa
    koik = max((r for r in A["publikatsioonid"]["tood"] if r["grupp"] == "koik" and r.get("url")), key=lambda r: r["viiteid"])
    rida = osa.split(f'<a href="{komponendid.e(koik["url"])}">')[0].rsplit("<tr>", 1)[1]
    assert lehed_uudised._arv(koik["viiteid"]) in rida


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
    # Kadri MKUS-i kommentaarid 7.11.2026 õhtul: „näita siin defaultina top kümmet“ ja „võta see lause maha“
    osa = _jaotis(sait["index.html"], "el")
    assert 'class="jrj" role="list" aria-label="ELi riigid järjestuses" data-piir="10"' in osa
    assert osa.count('class="jrj-r') - osa.count("jrj-r pais") - osa.count("jrj-r telg") == 27  # kõik riigid on HTML-is
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
    assert re.search(r'data-n="5"[^>]*>Top 5<', osa) and "kõik (" in osa
    assert osa.count('class="bs f"') >= 1  # üks esiletõstetud tegevusala
    vaikimisi = re.search(r'<div class="bump-v" data-n="(\d+)">', osa).group(1)
    assert vaikimisi == "10"
    assert "Haridus" in tekst(osa)
