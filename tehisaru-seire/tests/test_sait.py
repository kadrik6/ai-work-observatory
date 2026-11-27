"""Uue saidi (sait/) testid: pealkirjade numbrid tulevad andmetest, eri klassid ei ole ühel teljel, lingid töötavad."""

import csv
import html
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
    # Reegel, mitte aasta: kui Eurostat avaldab 2026. aasta võrreldava rea, ei tohi igapäevane andmetöö kukkuda
    assert andmekiht.leia(A, EB, "EE", "uusim:alus")["aasta"] >= 2025


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
    # Kadri 14.11.2026: ploki pealkiri on küsimus ja vastus; koht on üks kord (plaat ja see pealkiri)
    assert f"Kus on Eesti ELis? {koht}. kohal" in h
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
    # Kadri 14.11.2026: Ettevõtete siht on tahvli esimesel real ja „Kuidas lugeda“ loendis, mitte kolmandat korda sihireal
    kas = _jaotis(sait["ettevotted.html"], "kasutus")
    assert 'class="siht-rida"' not in kas and '<span class="mark-l s">Siht</span>' in kas
    # 26.11.2026: tahvli rida vastab sõnaga; siht on rea nähtavas osas (numbri all ja pildil), mitte ainult avatud märkuses
    rida1 = _jaotis(sait["ettevotted.html"], "tahvel").split('<details class="vt-r">')[1].split("</summary>")[0]
    assert "siht 75% (2030)" in tekst(rida1) and 'class="tv-siht"' in rida1
    # Kadri 14.11.2026: endised alamlehed on teemalehe plokid
    assert _jaotis(sait["ettevotted.html"], "digi").count('class="siht-rida"') == 1
    assert _jaotis(sait["ettevotted.html"], "ta").count('class="siht-rida"') == 1
    assert _jaotis(sait["inimesed.html"], "digi").count('class="siht-rida"') == 1
    assert not any('id="siht-' in h for h in sait.values())
    assert 'id="sihid"' not in sait["tehisaru-maarus.html"]


def test_kokkupuute_osad_summeeruvad_ja_pealkiri_tuleb_andmetest(A, sait):
    K = A["kokkupuude"]
    assert abs(sum(K["osa"].values()) + K["liigitamata"] - 100) < 0.01
    assert K["ilo_ameteid"] == 427 and K["ilo_avatud_ameteid"] == 112  # ILO WP140 tabel A1
    # Kadri 14.11.2026: h2 ei korda h1 (30% avatud ametites); h2 vastab, kui paljud on kõige avatumates, 30% on lisareal
    h2 = re.search(r'<h2 id="h-kokkupuude">(.*?)</h2>\s*<p class="h-lisa">(.*?)</p>', sait["too.html"], re.S)
    assert f'{komponendid.pr(K["avatud"], 0)}%' in h2.group(2)
    assert f'<b>{komponendid.pr(K["korge"], 0)}% töötajatest on kõige avatumates ametites</b>' in h2.group(1)


def test_kokkupuude_ei_ole_moju_ja_el_vordlus_on_eraldi(sait):
    s = sait["too.html"]
    jaotis = s[s.index('id="kokkupuude"'):s.index('id="hoive"')]
    assert "Kokkupuude ei ole mõju" in jaotis
    # ELi ligikaudne võrdlus on tekstis, mitte Eesti 4-kohalise numbriga samal graafikul
    graafik = jaotis[jaotis.index("<figure"):jaotis.index("</figure>")]
    assert "ELile" not in graafik and "EL " not in graafik


def test_astmete_naited_on_suurimad_nimega_ametid(tmp_path):
    """Kadri 26.11.2026: astme juures on kolm suurimat ametit. Nimi tuleb Statistikaameti tabelist PA633,
    jääkrühm „mujal liigitamata“ ei ole näide ja nimeta amet peatab ehituse."""
    import shutil
    sisu = JUUR / "sait" / "sisu"
    K = andmekiht.arvuta_kokkupuude(sisu)
    assert set(K["naited"]) == set(andmekiht.ASTMED)
    ilo = {r["isco4"]: r["aste"] for r in andmekiht.loe_csv(sisu / "ilo-kokkupuude-2025.csv")}
    ee = [r for r in andmekiht.loe_csv(sisu / "ee-tootajad-ametid-2022.csv") if len(r["kood"]) == 4 and r["kood"] in ilo]
    assert all(r["nimi_et"] for r in ee)
    for a, naited in K["naited"].items():
        sobib = sorted((r for r in ee if ilo[r["kood"]] == a and "mujal liigitamata" not in r["nimi_et"]),
                       key=lambda r: (-int(r["tootajad_fte"]), r["kood"]))
        assert [x["kood"] for x in naited] == [r["kood"] for r in sobib[:andmekiht.NAITEID]]
        assert all(x["aste"] == a and "mujal liigitamata" not in x["nimi"] for x in naited)
    assert K["naited"]["4"][0]["nimi"] == "Raamatupidamise kontoritöötajad" and K["naited"]["1"][0]["nimi"] == "Poemüüjad"
    for f in ("ilo-kokkupuude-2025.csv", "ee-tootajad-ametid-2022.csv", "eurostat-hoive-ametid-2025.csv", "eurostat-hoive-ametid-2021-2025.csv"):
        shutil.copy(sisu / f, tmp_path / f)
    p = tmp_path / "ee-tootajad-ametid-2022.csv"
    p.write_text(p.read_text(encoding="utf-8").replace(",Poemüüjad\n", ",\n", 1), encoding="utf-8")
    with pytest.raises(andmekiht.AndmeViga):
        andmekiht.arvuta_kokkupuude(tmp_path)


def test_ametinimi_loetelus():
    import too_tahvel
    assert too_tahvel._naide("Poemüüjad") == "poemüüjad" and too_tahvel._naide("IKT kasutajatoe tehnikud") == "IKT kasutajatoe tehnikud"
    assert too_tahvel._as_x(too_tahvel.AS_LO - 5) == 0 and too_tahvel._as_x(too_tahvel.AS_HI + 5) == 100


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
    s = sait["too.html"]
    jaotis = s[s.index('id="hoive"'):s.index('class="teema-lopp"')]
    assert "kirjeldus, mitte põhjus" in jaotis
    g = A["kokkupuude"]["aeg"][("EE", "T")]
    assert g[2025]["avatud"] / g[2022]["avatud"] < g[2025]["muud"] / g[2022]["muud"]


# ---- Töölaud (5.11.2026)

import lehed_ulevaade  # noqa: E402


def test_avaleht_on_signaalitahvel(A, sait):
    """Kadri 14.11.2026 valis avalehe näidise C: teemade tahvel ja ajajoon; telefonis neli veergu ja avanev rida."""
    h = sait["index.html"]
    main = h[h.index("<main"):h.index("</main>")]
    assert main.index('id="teemad"') < main.index('id="muutus"')
    assert 'class="plaadid' not in main and 'id="el"' not in main and 'aria-label="Sellel lehel"' not in h
    jao = _jaotis(h, "teemad")
    laud = jao[jao.index('class="tbl tv-laud"'):jao.index('class="tv-tel"')]
    assert re.findall(r'<th scope="col">([^<]+)</th>', laud) == ["Teema", "Praegu", "Kulg", "Muutus", "Koht ELis", "Väited", "Siht ja reeglid", "Värskus"]
    read = re.findall(r'<th scope="row"><a href="([^"#]+)', laud)
    assert read == ["inimesed.html", "ettevotted.html", "too.html", "avalik-sektor.html", "hanked.html"]
    assert laud.count("<tr>") == 6 and laud.count('class="tv-riba"') == 2  # ELi koht ainult seal, kus on 27 riigi andmed
    tel = jao[jao.index('class="tv-tel"'):]
    assert tel.count('<details class="tv-r">') == 5 and tel.count("<summary>") == 5
    assert all(f'href="{f}">Ava teema' in tel for f in read)
    css = (ehita.SIIN / "stiil.css").read_text(encoding="utf-8")
    assert ".tv-laud, .tv-aeg-lai { display: none; }" in css and ".tv-tel { display: block; }" in css
    assert "min-height: 56px" in css.split("Avalehe signaalitahvel")[1]
    aeg = _jaotis(h, "muutus")
    assert 'class="tv-aeg"' in aeg and "<h3>Mis muutus (30 päeva)</h3>" in aeg and "<h3>Mis tuleb</h3>" in aeg
    assert re.search(r'id="h-muutus"><span class="kys">Mis muutus ja mis tuleb\?</span> <b>\d+ kannet? 30 päevaga', aeg)



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
    rida = tekst(_jaotis(sait["index.html"], "teemad").split('href="too.html"')[1].split("</tr>")[0])
    assert f"{komponendid.pr(v)}%" in rida and f"töötus · {komponendid.KUUD[int(kuu[5:]) - 1]} {kuu[:4]}" in rida
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
    rida = _jaotis(sait["index.html"], "teemad").split('href="hanked.html"')[1].split("</tr>")[0]
    assert "aastaid veel ei võrrelda" in rida and "aastatulbad" not in sait["index.html"]
    assert 'id="hanked"' not in sait["avalik-sektor.html"]


def test_menuus_on_kaheksa_teemat_ja_usaldus_on_oma_teema(sait):
    # Kadri 6.11.2026 21:59: Hanked on oma menüüpunkt. 22:27 (paigutuse ettepanekud 1–3, 10): Usaldus oma menüükoht
    menuu = re.search(r'<ul class="menu">(.*?)</ul>', sait["index.html"], re.S).group(1)
    # Kadri 11.11.2026 (ülesehituse kontroll D): Avalik sektor, Hanked ja Tehisaru määrus on ühe punkti „Riik“ all
    assert re.findall(r">([^<>]+)</a>", menuu) == ["Avaleht", "Inimesed", "Ettevõtted", "Töö", "Riik", "Uudised", "Usaldus"]
    # Kadri 12.11.2026 („jah kõik“, ettepanek sp-2026-11-11-1): Riik › Riikide strateegiad
    # Kadri 14.11.2026: Tehisaru määrus, Eesti otsused ja Riikide strateegiad on üks leht „Reeglid ja otsused“
    for f in ("avalik-sektor.html", "hanked.html", "hanked-naited.html", "tehisaru-maarus.html"):
        assert '<a href="avalik-sektor.html" aria-current="page">Riik</a>' in sait[f], f
        alam = re.search(r'<ul class="alamlehed">(.*?)</ul>', sait[f]).group(1)
        assert re.findall(r">([^<>]+)</a>", alam) == ["Avalik sektor", "Hanked", "Hangete näited", "Reeglid ja otsused"], f
        assert alam.count('aria-current="page"') == 1 and f'href="{f}" aria-current="page"' in alam, f
    assert '<ul class="sellel"></ul>' not in "".join(sait.values())
    for f in ("kas-see-on-tosi.html", "lahknevused.html"):
        assert '<a href="kas-see-on-tosi.html" aria-current="page">Usaldus</a>' in sait[f], f
    # Kadri 12.11.2026: ettekanded, üritused ja podcastid on uudiste kõrval eraldi alamlehed
    assert re.findall(r'<ul class="alamlehed">(.*?)</ul>', sait["uudised.html"])[0].count("<li>") == 4


def test_lahknevused_ja_varskus_on_usalduse_all_nahtaval(sait):
    # Kadri 6.11.2026 21:38: Eurostati ja Statistikaameti võrdlus jääb nähtavale, kontrollib ministeerium
    osa = _jaotis(sait["lahknevused.html"], "lahknevused")
    assert "selgitamata" in osa and "<details" not in osa.split("</header>")[0]
    assert 'id="varskus"' in sait["lahknevused.html"] and 'id="muutused"' in sait["lahknevused.html"]
    assert 'id="varskus"' not in sait["kuidas-lugeda.html"]


def test_igas_teemavaates_on_numbriplaadid(sait):
    for f in ["tehisaru-maarus.html", "kas-see-on-tosi.html"]:
        assert 'class="vastus' in sait[f], f
    # 14.11.2026: Ettevõtete ja Inimeste numbrid on tahvli ridadel (Kadri valis „B koos C maatriksiga“ ja „A ja B koos“);
    # Töö ja Avalik sektor 17.11 (mõlemal „A ja C koos“), Hanked 19.11 („A ja C koos“)
    # 25.–26.11.2026: tahvli rida vastab sõnaga, number on selle kõrval (Töö 25.11, teised teemalehed 26.11)
    for f in ("ettevotted.html", "inimesed.html", "avalik-sektor.html", "hanked.html", "too.html"):
        assert 'class="vt-n"' in sait[f] and 'class="tv-arv"' not in sait[f], f


def test_koondamiste_visuaali_pealkiri_tuleb_andmetest(A, sait):
    j = A["koondamised"]["juhtumid"]
    arv = lambda r: r["arv_eestis"] if r.get("arv_eestis") is not None else r.get("arv_ulem")  # noqa: E731
    pohjus = sum(arv(r) for r in j if arv(r) and r["roll"] in ("otsene", "osaline"))
    kokku = sum(arv(r) for r in j if arv(r))
    h3 = sait["too.html"].split('id="h-koondamised-v">')[1].split("</h3>")[0]
    assert f"<b>{pohjus} töökoha</b>" in h3
    # Kadri 26.11.2026 (nõrgad numbrid): uudistest kogutud teated ei ole kõigi koondamiste loend. Pealkirjad ütlevad arvu
    # ilma jagajata; kogutud teadete arv ja töökohtade summa on eraldi lauses koos põhjendusega.
    h2 = sait["too.html"].split('id="h-koondamised">')[1].split("</h2>")[0]
    mainib = sum(r["roll"] in ("otsene", "osaline") for r in j)
    assert f'<b>{abi.ARVSONAD[mainib].capitalize()} {"ettevõte" if mainib == 1 else "ettevõtet"}</b> nimetas koondamise põhjusena tehisaru' in h2
    for pealkiri in (h2, h3):
        assert "koondamisest" not in pealkiri and "töökohast" not in pealkiri and not re.search(r"\d-st\b", pealkiri), pealkiri
    ps = sait["too.html"].split('id="h-koondamised-v">')[1].split('<div class="kr-aeg">')[0]
    assert f"Kogutud on {len(j)} koondamisteadet" in ps and f"{kokku} töökohta" in ps and "osakaalu ei arvutata" in ps


def test_iga_koondamine_on_tulbal_ja_tabelis_arvu_pohjuse_ja_lingiga(A, sait):
    # Kadri MKUS-i kommentaar 7.11.2026 08:48: kaardid maha, koondatute arv, põhjus ja link alumisse tabelisse
    from lehed_ulevaade import koondamise_arv
    h = sait["too.html"]
    tulbad = re.findall(r'<div class="kr" data-k="([^"]+)"', h)
    # Kadri 26.11.2026: teated ajajärjekorras (uuemad üleval), mitte suuruse järgi; kuu on vahepealkiri
    kp_ = {r["id"]: r["kuupaev"] for r in A["koondamised"]["juhtumid"]}
    assert [kp_[k] for k in tulbad] == sorted(kp_.values(), reverse=True)
    vis = h[h.index('id="koondamised-visuaal"'):h.index('class="kr-leg"')]
    kuud = re.findall(r'<p class="kr-kuu">(.*?)</p>', vis)
    assert len(kuud) == len({v[:7] for v in kp_.values()}) == vis.count('class="kr-ribad"')
    assert kuud[0] == f'{komponendid.KUUD[int(max(kp_.values())[5:7]) - 1].capitalize()} {max(kp_.values())[:4]}'
    assert "uuemad üleval" in vis and "ei ole kõigi Eesti koondamiste loend" in vis
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
    # Kadri 11.11.2026: Eesti ja maailm on sakkides, vaikimisi Eesti; arv on saki nupul
    assert f'id="tab-eesti-uudised" aria-controls="eesti-uudised" aria-selected="true">Eesti <span class="arv">{n_ee}</span>' in h
    assert 'id="maailma-uudised" aria-labelledby="tab-maailma-uudised" hidden>' in h


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
    assert f'{a1["aasta"]}. aastal <b>' in h.split("<h1")[1].split("</h1>")[0]
    # h2 ei korda h1 numbrit (Kadri 14.11.2026), vaid ütleb suurima teema
    assert "Suurim teema on" in h.split('id="h-uuritakse">')[1].split("</h2>")[0]


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
    assert f"({abi.sonaga(kuulutusi)} kuulutust)" in h2


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
    assert h.count('class="ps u-seis"') == 2 and f"Viimane kontroll {kp(paev)}" in h
    # Kadri 11.11.2026: „uus“-märki uudistel pole („nobody does that“); värskust näitab ajajoon
    assert 'class="u-l uus"' not in h and "„Uus“ on " not in h


def test_uudised_on_ajajoonel_paevade_kaupa(A, sait):
    """Kadri 11.11.2026: katsetest D1 ajajoon kompaktsena, samad nupud ja filtrid nagu teistel lehtedel."""
    import datetime
    h = sait["uudised.html"]
    for rid, p in (("eesti-uudised", lambda r: r["piirkond"] == "EE"), ("maailma-uudised", lambda r: r["piirkond"] != "EE")):
        osa = h.split(f'id="{rid}"')[1].split("</section>")[0]
        read = [r for r in A["uudised"] if p(r)]
        alg = datetime.date.fromisoformat(A["uudiste_olek"]["viimane_kontroll"][:10])
        paevad = sorted({r["kuupaev"][:10] for r in read if (alg - datetime.date.fromisoformat(r["kuupaev"][:10])).days < lehed_uudised.PAEVI}, reverse=True)
        assert re.findall(r'<div class="u-paev[^"]*" data-paev="([0-9-]+)"', osa) == paevad, rid
        assert len(re.findall(r'class="u-paev[ "]', osa)) == len(paevad) + len({r["kuupaev"][:7] for r in read if r["kuupaev"][:10] not in paevad})
        assert osa.count(" uusim") == 1  # ainult uusim nähtav päev on sinine
        for alg_, sisu in re.findall(r'(<div class="u-paev[ "][^>]*>)(.*?)</ul></div>', osa, re.S):  # päev ilma nähtava uudiseta on peidus
            assert alg_.endswith(" hidden>") == (re.search(r'<li (?![^>]*\bhidden\b)[^>]*>', sisu) is None), alg_
    assert '<div class="p-tabs u-sakid" role="tablist" aria-label="Piirkond">' in h
    assert 'href="ettekanded.html">Ettekanded</a>' in h and 'href="podcastid.html">Podcastid</a>' in h
    js = (ehita.SIIN / "sait.js").read_text(encoding="utf-8")
    assert "s.textContent = v === 0 ? 'täna' : 'eile'" in js  # täna/eile lugeja kuupäeva järgi, mitte ehitamise päeva järgi
    assert "g.hidden = !g.querySelector('.u-voog li:not([hidden])')" in js


def test_ettekanded_uritused_ja_podcastid_eraldi_lehtedel(A, sait):
    """Kadri 12.11.2026: „löö ettekanded, üritused ja podcastid uudiste kõrvale lahku“."""
    import copy
    from komponendid import kp
    assert 'id="tulekul"' in sait["uritused.html"] and 'id="tulekul"' not in sait["ettekanded.html"]
    assert 'href="tehisaru-maarus.html#eesti-otsused">Eesti otsused</a>' in sait["uritused.html"]
    assert 'data-liik="podcast"' not in sait["ettekanded.html"] and 'data-liik="podcast"' in sait["podcastid.html"]
    assert 'data-liik="seminar"' not in sait["podcastid.html"]
    assert 'data-k="liik"' not in sait["podcastid.html"]  # ühe valikuga liigirida jääb ära
    vaade = copy.deepcopy(next(v for v in ehita.lae_vaated() if v["id"] == "uudised"))
    B = copy.deepcopy(A)
    B["uudised"] = [dict(A["uudised"][0], teema="riik", tahtaeg=t, pealkiri=f"Üritus {t}", url=f"https://n.ee/{t}")
                    for t in ("2026-12-01", "2026-11-20", "2026-11-01")]
    ees, sec = lehed_uudised.tulekul(B, "2026-11-11")
    assert [r["tahtaeg"] for r in ees] == ["2026-11-20", "2026-12-01"]  # möödunud kaob, lähim eespool
    assert sec.index("Üritus 2026-11-20") < sec.index("Üritus 2026-12-01") and f'<span class="d">{kp("2026-11-20")}</span>' in sec
    lehed_uudised.ettekanded(B, vaade, "2026-11-11")
    h1 = next(s for s in vaade["alamlehed"] if s["fail"] == "uritused.html")["h1"]
    assert f"**{kp('2026-11-20')}**" in h1
    assert "praegu pole" in lehed_uudised.tulekul({**B, "uudised": []}, "2026-11-11")[1]


def test_uus_margid_on_oranzid(sait):
    # Kadri 7.11.2026: „värvi kõik uus märgid oranziks“; „suur uudis“ jääb siniseks
    assert '<span class="u-l suur">uus</span>' not in sait["uudised.html"]
    assert '<span class="t uus">uus number</span>' not in "".join(sait.values())  # Kadri 8.11: ainult „uus“
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
    assert 'id="hoive"' in sait["too.html"] and 'id="uuritakse"' in sait["too-kirjandus.html"] and 'id="uuritakse"' not in sait["too.html"]


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
    ev = sait["ettevotted.html"]  # 14.11.2026: avalehelt läks järjestus teemalehele (avaleht on signaalitahvel)
    osa = ev[ev.rindex("<section", 0, ev.index(">esikümme<")):]
    osa = osa[:osa.index("</section>")]
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
    assert "data-kiht" not in h and "pl-lyl" not in h  # 14.11.2026: avalehel plaate pole (signaalitahvel)
    for pid, osad in lehed_ulevaade.KPI_VER1.items():
        # 8.11.2026: ver1 laiendati alamlehtede päisele; iga plaat on täpselt ühel lehel
        lehed = [f for f, s in sait.items() if f'data-kpi="{pid}"' in s]
        assert len(lehed) == 1, (pid, lehed)
        pl = sait[lehed[0]].split(f'data-kpi="{pid}"')[1].split('</div>')[0].split('<span class="src">')[0]
        assert ('class="muut"' in pl) == ("muutus" in osad), pid
        assert ('class="kriba' in pl) == ("riba" in osad), pid
        assert ('class="tekst"' in pl) == ("tekst" in osad), pid
    # 8.11.2026 (Kadri: vähem teksti): legend on märk + sõna, mitte „oranž/tume kriips:“
    assert "ELi siht 80% (2030)" in h  # tahvli siht
    assert 'aria-label="kesk 28%; KOV 27%"' in sait["avalik-sektor.html"]  # 17.11.2026: plaadi asemel tahvli rida
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
    # 8.11 õhtu: h1 algab Eestist (läbivaatus P4). 26.11.2026 Kadri: „ei selgu, kas vähendab“ jättis mulje, et mõju pole;
    # uus h1 ütleb mõõdetud mõju (tööalane kasutus, IT71 hõivatud) ja jätab lahtiseks ainult koondamiste põhjuse.
    assert h1("too.html").startswith("Tehisaru muudab Eestis juba tööd")
    hanked = _jaotis(sait["hanked.html"], "tahvel")  # 19.11.2026: hangete arv on tahvli esimesel real
    avaleht = _jaotis(sait["index.html"], "teemad").split('href="hanked.html"')[1].split("</tr>")[0]
    assert re.search(r'class="tv-arv"[^>]*>(\d+)<', avaleht).group(1) == re.search(r'class="vt-n"[^>]*>umbes (\d+)<', hanked).group(1)
    assert "jaan" not in avaleht


def test_avalehe_tahvel_numbrid_ja_skaalad(A, sait):
    """Kadri 14.11.2026 (näidis C): iga rida on oma skaalal; ettevõtete kulg on Eurostati rida ja öeldakse nii."""
    jao = _jaotis(sait["index.html"], "teemad")
    rida = lambda f: jao.split(f'<th scope="row"><a href="{f}"')[1].split("</tr>")[0]  # noqa: E731
    assert "Iga rida on oma skaalal" in jao and "ELi keskmine" in jao
    assert "Eurostat" in rida("ettevotted.html") and "aastaga ei võrrelda" in rida("ettevotted.html")
    assert "küsimus võib erineda" in rida("inimesed.html") and "ELi siht 80%" in rida("inimesed.html")
    assert "siht 75%" in rida("ettevotted.html") and 'class="tv-siht"' in rida("ettevotted.html")
    assert "kõrgeim töötus" in rida("too.html") and "põhjust kuunumber ei ütle" in rida("too.html")
    assert "esimene mõõtmine" in rida("avalik-sektor.html") and "100 ruutu = kõik hanked" in rida("hanked.html")
    for f in ("inimesed.html", "ettevotted.html", "too.html", "avalik-sektor.html", "hanked.html"):
        assert 'class="v-tapp' in rida(f), f



def test_iga_vaide_on_avalehe_tabelis_teemaga(A):
    import lehed_ulevaade
    for v in A["vaited"]:
        assert lehed_ulevaade.vaite_teema(v) in {"inimesed", "ettevotted", "too", "avalik-sektor", "hanked"}


def test_too_leht_teemamall_a(sait):
    """Kadri 8.11.2026: teemaleht A järgi: number, andmed sakkides, uuringud, väited, reeglid, allikad; vanad ankrud alles."""
    h = sait["too.html"]
    # 17.11.2026: numbriplaatide asemel tahvel, tõendikaart ja astmed; plokid on nende all kokkupandult
    # 25.11.2026 (oluline enne valikulist): tahvli all on nähtaval töötus, koondamised ja astmed; tõendikaart on üksikasjades
    jrk = [h.index(x) for x in ('id="tahvel"', 'id="tootus-kuud"', 'id="koondamised"', 'id="astmed"', 'id="toendid"', 'id="andmed"',
                                'id="t-vaited"', 'id="t-reeglid"', 'id="t-allikad"')]
    assert jrk == sorted(jrk)
    assert 'id="t-uuringud"' not in h  # Kadri 11.11.2026: uuringud on alamlehel Töö › Uuringud
    for vana in ("tootus-kuud", "koondamised", "tootus-el", "palkamine", "vabad-kohad", "toopakkumised", "ai-kuulutused", "tulevik"):
        assert f'id="{vana}"' in h, vana
    sakid = re.findall(r'role="tab" id="sakk-([a-z-]+)-n" aria-controls="sakk-\1" aria-selected="(true|false)"', h)
    assert len(sakid) == 5 and [s for s, v in sakid if v == "true"] == ["vabad"]
    assert len(re.findall(r'class="sakk-sisu" hidden>', h)) == 4
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
        # iga sakkidega plokk näitab korraga ühte sakki (Ettevõtetel on kolm sakkidega plokki, Kadri 14.11.2026)
        assert len(re.findall(r'class="sakk-sisu">', h)) == h.count('class="p-tabs andmesakid"') >= 1, f


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
    assert "kõige kaugemal" not in sait["index.html"]
    # P2: iga „viimati“ ütleb, mille kohta see on
    assert h2("index.html", "muutus").startswith("Mis muutus ja mis tuleb? ")
    assert h2("lahknevused.html", "muutused").startswith("Mis allikates viimati muutus? Viimane logikanne on")
    # P3: alamlehtede h1 on vastus, mitte teema nimi
    for f, nimi in [("too-kirjandus.html", "Mida maailmas ja Eestis tehisarust ja tööst kirjutatakse")]:
        assert h1(f) != nimi and len(h1(f)) > len(nimi) and "<b>" in re.search(r"<h1>(.*?)</h1>", sait[f], re.S).group(1), f
    # P5: saidikaardil pole sisemärkmeid ega olekuveergu
    # Autori nimi on saidil teadlikult (Kadri 11.11.2026); sisemärkmeid („Kadri 8.11 …“) ei tohi olla
    assert "Kadri" not in sait["saidikaart.html"] and "Eelvaate" not in sait["saidikaart.html"]
    assert ">Olek<" not in sait["saidikaart.html"]
    # P6, P7, P8
    assert h2("hanked.html", "tapsus").endswith("masinmärgendite järgi")
    assert "hindamata" not in h2("index.html", "teemad")
    assert "kolm puhul" not in sait["lahknevused.html"]
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


def test_allikad_ja_kuupaevad_iga_tabel_eraldi(sait):
    # Kadri 26.11.2026: avalehel on iga numbri allikas, tabel ja allika viimane uuendus, uusim üleval; hiline uuendus
    # (IT1490 avaldati 16.09, uuendati 21.10) on näha. Päise kuupäevarida („Numbrid … · uudised …“) on kõigilt lehtedelt ära.
    import csv as _csv
    from datetime import date as _d
    for f, h in sait.items():
        if f.endswith(".html"):
            assert 'class="seis"' not in h and "Numbrid " not in re.search(r"<header.*?</header>", h, re.S).group(0), f
    p = re.search(r'<details class="allikad-l">.*?</details>', sait["index.html"], re.S).group(0)
    kp_ = re.findall(r'<li><time datetime="(\d{4}-\d{2}-\d{2})">', p)
    assert len(kp_) >= 9 and kp_ == sorted(kp_, reverse=True), kp_
    U = {(r["allikas"], r["tabel"]): r["uuendatud"]
         for r in _csv.DictReader(open(Path(__file__).resolve().parents[1] / "sait" / "sisu" / "tabelite-uuendused.csv", encoding="utf-8"))}
    for (allikas, tabel), k in U.items():
        li = re.search(rf'<li><time datetime="{k}">[^<]*</time>(?:(?!</li>).)*>{tabel}</a>', p, re.S)
        assert li, (allikas, tabel, k)
    assert "une_rt_m</a> · Eesti uusim kuu: " in p
    # 15:21: iga rea nimi viib saidil selle numbri juurde (leht ja ankur on olemas)
    for leht, ank in re.findall(r'<li><time[^>]*>[^<]*</time><span><b><a href="([a-z-]+\.html)#([a-z0-9-]+)">', p):
        assert f'id="{ank}"' in sait[leht], (leht, ank)
    assert len(re.findall(r'<li><time[^>]*>[^<]*</time><span><b><a href="[a-z-]+\.html#', p)) == len(kp_)
    for k in kp_:
        assert _d.fromisoformat(k) <= _d.today()
    if U[("Statistikaamet", "IT1490")] > "2026-09-16":
        assert "uuendati hiljem, esmalt 16.09.2026" in p


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
    assert [s["fail"] for s in vaade["alamlehed"]] == ["uudised.html", "ettekanded.html", "uritused.html", "podcastid.html"]
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
    assert "alamlehed" not in vaade  # Kadri 14.11.2026: üks leht „Reeglid ja otsused“
    h = lehed_teemad.eesti_otsused({**A, "uudised": []}, vaade, None, "2026-11-09")
    assert "pole kogumine veel leidnud" in h
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
    assert "<b>2 kirjet</b>" in h and "Näita kõiki 2 kirjet" in h
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
    for i in ("teekond", "liigid", "moju", "asutused", "kupsus", "rahastus"):  # 17.11.2026: etapid → teekond, oskused → asutused
        assert f'id="{i}"' in av, i
    assert "Prototüübist hindamiseni jõuab 22 protsendipunkti vähem projekte" in tekst(av) and "83% uuendusrahast tuli ELilt" in tekst(av)
    ev = sait["ettevotted.html"]
    assert 'id="arenguseire"' in ev and 'id="pohjamaad"' in ev and "Arvutatud: indeks" in ev
    kl = sait["kuidas-lugeda.html"]
    assert 'id="moisted"' in kl and 'id="numbrid-ei-naita"' in kl and "Seitse asja" in kl
    assert 'id="eesti-otsused"' in sait["tehisaru-maarus.html"] and 'id="strateegiad"' in sait["tehisaru-maarus.html"]


def test_a1_kujundus_kogu_saidil(sait):
    # Kadri 8.11.2026 23:41: „A1 teema sobib kõige paremini“ (katseleht kirjeldused/stiilid/t2027-seire)
    import kest
    css = (ehita.SIIN / "stiil.css").read_text(encoding="utf-8")
    assert "html[data-t] .plaat" in css and ".pea-rahu" in css
    assert "setAttribute('data-t','1')" in kest.TEEMA_JS  # artefaktis kirjutatakse <html> üle
    pehme = css.split(':root[data-seire-teema="soft"] {', 1)[1].split("}", 1)[0]
    # 26.11.2026 Kadri valis heledaks teemaks V9 („Let's apply version 9 for now“): A1 paigutus jääb, valge leht ja
    # hallid asendusid jaheda heleda lehe ja sinakate hallidega (vt test_hele_teema_v9)
    assert "--page: #f5f7fb" in pehme and "--surface-2: #eef1f8" in pehme
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
    assert "Kadri" not in h  # sisemärkmeid ega nime pole (nimi võeti ära 27.11.2026)


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
    # avalehe päis: hele pilt kahes reeglis (arvuti, telefon); alamlehtede päis (27.11.2026) kasutab sama pilti eraldi
    avaleht = [r for r in css.split("}") if ".pea-rahu.pilt::before" in r]
    assert sum(r.count('url("pilt/avaleht.jpg")') for r in avaleht) == 2


def test_avalehe_pilt_on_lehe_taust():
    # Kadri 25.11.2026: „put this picture in the main page as a background … more see-through … save some more space
    # on the upper part“ – pilt on kogu avalehe ülaosa taust (ka tahvli taga), nõrgem, ja päisel pole oma kõrgust
    import re
    css = (Path(__file__).resolve().parent.parent / "sait" / "stiil.css").read_text(encoding="utf-8")
    reeglid = css.split("}")
    pais = next(r for r in reeglid if "html[data-t] .pea-rahu.pilt { position" in r)
    assert "min-height" not in pais and "padding-bottom: 0" in pais
    # isolation tooks pildi sisu peale, kui pilt ulatub päisest allapoole; pilt peab jääma kogu sisu taha
    assert "isolation:" not in pais
    koik = [r for r in reeglid if ".pea-rahu.pilt::before" in r]
    # V9 (Kadri 26.11.2026 „apply version 9“): heleda teema toonireegel tuleb lisaks neljale pildireeglile
    toon = [r for r in koik if '[data-seire-teema="soft"] .pea-rahu.pilt::before' in r]
    pildid = [r for r in koik if r not in toon]
    # Kadri 27.11.2026: telefonis tundus pilt erksam – heleda teema 42% kirjutas üle telefoni nõrgema nähtavuse.
    # Telefoni toonireegel hoiab sama vahekorda nagu hallis pildis (24/30).
    tel = [r for r in toon if "@media (max-width: 680px)" in r]
    toon = [r for r in toon if r not in tel]
    assert len(pildid) == 4 and len(toon) == 1 and len(tel) == 1
    tel_n = float(re.search(r"opacity: (\.\d+)", tel[0]).group(1))
    assert abs(tel_n - .42 * .24 / .3) < .01, tel_n
    assert "z-index: -1" in pildid[0] and "pointer-events: none" in pildid[0]
    # pilt on päisest kõrgem (ulatub tahvli taha) ja hajub alla lehe taustaks
    assert int(re.search(r"height: (\d+)px", pildid[0]).group(1)) >= 460
    assert all("linear-gradient(0deg, var(--page) 0%" in r for r in pildid)
    # heledus- ja kontrastifilter muutis ka katte värvi ja jättis pildi alla serva
    assert "filter: grayscale(1);" in pildid[0] and "brightness(" not in "".join(koik)
    nahtavus = [float(x) for r in pildid for x in re.findall(r"opacity: (\.\d+)", r)]
    assert len(nahtavus) == 4 and max(nahtavus) <= .3
    # heledas teemas: pilt sinise tooniga, filter ei muuda katte värvi, nähtavus nagu laboris (42%), tume ei muutu
    assert "filter: none" in toon[0] and "luminosity" in toon[0] and "opacity: .42" in toon[0]
    # Kadri 26.11.2026 14:50: pilt natuke vähem küllastatud; 15:28 valis liugurilt 40% → toon #546ab6 (enne #3f60cc ~58%)
    import colorsys
    tk = re.search(r"background-color: #([0-9a-f]{6})", toon[0]).group(1)
    assert abs(colorsys.rgb_to_hls(*(int(tk[i:i + 2], 16) / 255 for i in (0, 2, 4)))[2] - 0.40) < 0.015, tk
    assert "dark" not in toon[0]


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
    assert "aastaga ei võrrelda" in tekst(_jaotis(sait["index.html"], "teemad").split('href="ettevotted.html"')[1].split("</tr>")[0])
    assert "aastaga ei võrrelda" in tekst(_jaotis(sait["ettevotted.html"], "tahvel").split("Kui paljud kasutavad?")[1].split("</tr>")[0])
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
    # Riigikontroll 30.05.2025, p 58 käib avaliku sektori kohta: Avaliku sektori lehel (Kadri 14.11.2026)
    assert "33 asutusel puudus asutusesisene kord" not in tekst(sec)
    assert "33 asutusel puudus asutusesisene kord" in tekst(_jaotis(sait["avalik-sektor.html"], "ametnikud"))
    otsused = sec.split('class="lp-lisa"')[0]  # taustaplokkide tabelid ei ole otsused
    assert otsused.count("<tr>") == len(S) + 1  # päis + üks rida otsuse kohta
    assert all("kontroll" not in r for r in S)  # sisemine kontrollimärge ei lähe saidile


def test_ligipaasu_taust_teised_riigid_ja_uuringud(sait, A):
    # Kadri „jah, avalda“ 9.11.2026 19:59: kaks taustaplokki samas jaotises; ainult avalikud allikad, iga rida lingiga,
    # meie soovitust (keskne leht, värav) saidil pole
    K = A.get("ligipaas_kontekst") or {}
    if not K:
        pytest.skip("sisu/ligipaas-kontekst.json puudub")
    # Kadri 14.11.2026: ametnike juhendid on Avaliku sektori lehel, katsed Ettevõtete lehel küsimuse „Kas tehisaru tõstab tootlikkust?“ all
    leht = {"ligipaas-riigid": _jaotis(sait["avalik-sektor.html"], "ametnikud"), "ligipaas-uuringud": _jaotis(sait["ettevotted.html"], "kasu")}
    sec = leht["ligipaas-riigid"] + leht["ligipaas-uuringud"]
    for plokk, read, pk in [("ligipaas-riigid", K["riigid"], "Soome, Holland, Ühendkuningriik ja USA lubavad ametnikel tehisaru kasutada tingimustega"),
                            ("ligipaas-uuringud", K["uuringud"], "Kasu on päris, aga mitte igas ülesandes")]:
        osa = leht[plokk]
        pk_osa = osa
        osa = osa[osa.index(f'id="{plokk}"'):]
        osa = osa[:osa.index("</table>")]
        assert pk in tekst(pk_osa)
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
    for leht in ("inimesed.html", "ettevotted.html"):  # 14.11.2026: avalehel kaarti pole (signaalitahvel)
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
    m = re.search(r'aria-label="Sellel lehel">(.*?)</nav>', sait["index.html"], re.S)  # 14.11.2026: avalehel kaks plokki, rida puudub
    if m:
        kiibid = re.findall(r">([^<>]+)</a>", m.group(1))
        menuu = re.findall(r">([^<>]+)</a>", re.search(r'<ul class="menu">(.*?)</ul>', sait["index.html"], re.S).group(1))
        assert not set(kiibid) & set(menuu), set(kiibid) & set(menuu)
    # C: alamlehtede rida on menüürida teema nimega, mitte sakk
    assert '<span class="alam-silt">Töö:</span>' in sait["too-kirjandus.html"]
    css = (ehita.SIIN / "stiil.css").read_text(encoding="utf-8").split("Alamlehtede rida on menüü, mitte sakk")[1]
    assert "border-bottom: 0" in css and "overflow-x: auto" in css
    # E: Usalduse esimene leht ütleb, mida osa tervikuna näitab
    assert "Usaldus kontrollib kolme asja" in sait["kas-see-on-tosi.html"]
    # F: vanad lingid hangete loendile viivad uuele lehele
    assert not any('href="hanked.html#loend"' in h for h in sait.values())


def _ettekannete_arv():
    """Kinnitatud ettekannete arv saidi sisus: (ettekanded ja seminarid, podcastid). Uued kinnitused ei murra teste."""
    d = json.loads((JUUR / "sait" / "sisu" / "ettekanded.json").read_text(encoding="utf-8"))
    pod = {a["id"] for a in d["allikad"] if a.get("liik") == "podcast"}
    p = sum(1 for e in d["ettekanded"] if e["allikas"] in pod)
    return len(d["ettekanded"]) - p, p


def test_podcastid_ettekannete_lehel(sait):
    """Kadri 11.11.2026: Lex Fridmani ja Mindscape'i podcastid Ettekannete lehel, uus rühm „Taust“."""
    h = sait["podcastid.html"]
    assert 'id="ek-taust"' in h and "Taust: mõistus ja informatsioon" in h
    n_ek, n_pod = _ettekannete_arv()
    assert n_pod >= 18 and h.count('data-liik="podcast"') == n_pod
    k = sait["ettekanded.html"]
    assert n_ek >= 10 and k.count('data-liik="seminar"') + k.count('data-liik="veebiseminar"') == n_ek
    assert '<span class="u-l arv">podcast</span>' in h and "lõik algab 0:15:28" in h
    assert "Lex Fridman Podcast" in h and "Mindscape (Sean Carroll)" in h
    assert "lex-452" not in h and "Dario Amodei" not in h  # aegunud osa jäeti välja (Kadri 11.11)


def test_koondamised_ei_ole_esikohal(sait):
    """Kadri 11.11.2026: koondamised olid liiga suure fookuse all (esimese saki 3/4). Uudiste filtris pole koondamisel
    oma nuppu: see on töö all (Kadri 11.11.2026: „võta koondamine siit ära, see info peaks koonduma töö alla“).
    Kadri 25.11.2026 valis Töö lehe põhigraafikuteks töötuse kuu kaupa ja koondamised: töötus on koondamiste ees, mõlemad
    on nähtaval (mitte sakis) ja pikk tabel „Keda koondajad otsivad“ avaneb koondamiste graafiku all klõpsuga."""
    h = sait["too.html"]
    sakid = re.findall(r'role="tab" id="sakk-([a-z-]+)-n"[^>]*>([^<]+)</button>', h)
    assert [s for s, _ in sakid] == ["vabad", "portaalid", "ai-tood", "tootus-el", "prognoos"]
    nahtav = h[h.index('id="tootus-kuud"'):h.index('id="astmed"')]
    assert nahtav.index('id="reg-tootud"') < nahtav.index('id="koondamised"') < nahtav.index('<details class="tt-pl tt-yksi" id="d-palkamine">') < nahtav.index('id="palkamine"')
    assert 'role="tabpanel"' not in nahtav and nahtav.count("<details") == h[h.index('id="palkamine"'):h.index('id="astmed"')].count("<details") + 1
    # vana jagatud link (?sakk=sakk-koondamised) leiab ploki üles: plokk kannab vana saki nime ja sait.js kerib sinna
    assert 'id="koondamised" data-vana-sakk="sakk-koondamised"' in h and 'id="tootus-kuud" data-vana-sakk="sakk-tootus"' in h
    assert "data-vana-sakk" in (JUUR / "sait" / "sait.js").read_text(encoding="utf-8")
    u = sait["uudised.html"]
    for rid in ("eesti-uudised", "maailma-uudised"):
        osa = u[u.index(f'id="{rid}"'):]
        osa = osa[osa.index('aria-label="Vali teema"'):]
        nupud = re.findall(r'<button type="button" data-f="([a-z_]*)"', osa[:osa.index("</div>")])
        assert nupud[0] == "" and "koondamine" not in nupud, (rid, nupud)
    assert lehed_uudised.TEEMA_FILTER["koondamine"] == "too"
    assert 'data-teema="koondamine"' not in u
    assert "riigi otsus, statistika, üle 50 koondatu" in u


def test_uudiste_teemad_ilma_valdkonnata(sait, A):
    """Kadri 12.11.2026: valdkonna filter on ära (kõik on tehisaruga seotud), teemades on täpsemad läbivad teemad."""
    import copy
    assert lehed_uudised.alamteemad({"pealkiri": "AI makes it harder for young people to land their first job"}) == ["noored"]
    assert lehed_uudised.alamteemad({"pealkiri": "Riik pakub tasuta tööalaseid koolitusi"}) == ["oskused"]
    assert lehed_uudised.alamteemad({"pealkiri": "Eksperdid peavad ohtlikuks registreerida AI-agente"}) == ["agendid"]
    assert lehed_uudised.alamteemad({"pealkiri": "x", "pohjus": "Microsoft offers training"}) == []  # oskused ainult pealkirjast
    B = copy.deepcopy(A)
    B["uudised"] += [dict(B["uudised"][0], teema="strateegia", piirkond="maailm", pealkiri="Riigi tehisarustrateegia", url="https://n.ee/s"),
                     dict(B["uudised"][0], teema="andmed", piirkond="maailm", pealkiri="Avaandmed", url="https://n.ee/a"),
                     dict(B["uudised"][0], teema="ai_too", piirkond="maailm", pealkiri="Youth jobs and AI", url="https://n.ee/y")]
    h = lehed_uudised.uudised(B, next(v for v in ehita.lae_vaated() if v["id"] == "uudised"))
    assert 'aria-label="Vali valdkond"' not in h and "data-vk=" not in h and "data-u=" not in h
    for rid in ("eesti-uudised", "maailma-uudised"):
        osa = h[h.index(f'id="{rid}"'):]
        osa = osa[:osa.index("</section>")]
        assert not re.search(r"<li [^>]*hidden", osa)  # vaikimisi on kõik uudised näha
    m = h[h.index('id="maailma-uudised"'):]
    m = m[:m.index("</section>")]
    assert 'data-f="riik"' in m and '<li data-teema="riik" data-liik' in m  # strateegia on riigi all
    assert '<li data-teema="muu" data-liik' in m
    assert '<li data-teema="too" data-alam="noored"' in m
    nupud = re.findall(r'data-f="([a-z]*)"', m)
    assert nupud.index("too") < nupud.index("noored") < nupud.index("riik")  # täpsem teema põhiteema kõrval
    js = (ehita.SIIN / "sait.js").read_text(encoding="utf-8")
    assert "['ala'," not in js and "getAttribute('data-alam')" in js
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
    n_ek, n_pod = _ettekannete_arv()
    for f, kk, kokku in (("ettekanded.html", ("liik", "kes"), n_ek), ("podcastid.html", ("kes",), n_pod)):
        h = sait[f]
        for k in kk:
            osa = h[h.index(f'class="u-f ek-f" data-k="{k}"'):]
            osa = osa[:osa.index("</div>")]
            nupud = re.findall(r'data-v="([^"]*)" aria-pressed="(true|false)">([^<]+)<span class="arv">(\d+)</span>', osa)
            assert nupud[0][:2] == ("", "true") and int(nupud[0][3]) == kokku
            assert sum(int(n) for _, _, _, n in nupud[1:]) == kokku, k  # iga ettekanne on täpselt ühes nupus
    h = sait["podcastid.html"]
    assert 'data-v="seminar"' in sait["ettekanded.html"] and re.search(r'<li [^>]*data-kes="[a-z0-9-]+"', h)
    assert re.search(r'<li data-liik="podcast" data-allikas="lex-fridman" data-kes="', h)
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


def test_ettekannete_kes_teeb_ja_uksus(A):
    """Kadri 12.11.2026 (UTTV): filter selle järgi, kes sisu teeb; Tartu Ülikooli sarjad on ühe korraldaja all, üksus eraldi."""
    import copy
    from sait import lehed_uudised
    vaade = copy.deepcopy(next(v for v in json.loads((ehita.SIIN / "vaated.json").read_text(encoding="utf-8"))["vaated"] if v["id"] == "uudised"))
    E = {"allikad": [{"id": "ut-dss", "nimi": "TÜ seminar", "url": "https://cs.ut.ee/", "liik": "seminar", "korraldaja": "Tartu Ülikool"},
                     {"id": "uttv", "nimi": "UTTV", "url": "https://uttv.ee/", "liik": "seminar", "korraldaja": "Tartu Ülikool"},
                     {"id": "kratid", "nimi": "Kratid", "url": "https://www.kratid.ee/", "liik": "veebiseminar"}],
         "ettekanded": [dict(id=f"x{i}", esineja="E", pealkiri=f"P{i}", allikas=a, kuupaev="2026-05-27", video="https://youtu.be/def",
                             kokkuvote="K.", ruhm="too", **({"tegija": t} if t else {}))
                        for i, (a, t) in enumerate([("ut-dss", "TÜ arvutiteaduse instituut"), ("uttv", "TÜ majandusteaduskond"),
                                                    ("uttv", "TÜ majandusteaduskond"), ("kratid", None)])]}
    h = lehed_uudised.ettekannete_osad({**A, "ettekanded": E, "ootel": {"ettekanded": 0}}, vaade)["ettekanded"]
    kes = re.findall(r'data-v="([a-z0-9-]+)" aria-pressed="false">([^<]+)<span class="arv">(\d+)', h[h.index('data-k="kes"'):h.index('data-k="uksus"')])
    assert kes == [("tartu-ulikool", "Tartu Ülikool ", "3"), ("kratid", "Kratid ", "1")]
    assert 'data-v="tu-majandusteaduskond"' in h and h.count('data-uksus="tu-majandusteaduskond"') == 2
    assert "· TÜ majandusteaduskond</p>" in h  # üksus on näha ka ettekande real
    js = (ehita.SIIN / "sait.js").read_text(encoding="utf-8")
    assert "['kes', '.ek-f[data-k=\"kes\"] button[data-v]', 'data-v']" in js and "function sobib(l, v2)" in js


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
    assert 'class="src"' in sait["tehisaru-maarus.html"].split('class="vastus kpi-pais"')[1].split("</aside>")[0]  # 19.11.2026: teemalehtedel on tahvel


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


def test_autor_on_igal_lehel(sait):
    """Kadri 11.11.2026: autoriinfo saidile. Kadri 27.11.2026: „palun võta lehelt viide minu nimele ka ära“:
    © märge ja „Autor“ lõik jäävad, aga nime asemel on saidi nimi ja meta author on ära."""
    import kest
    assert kest.AUTOR == "Tehisaru seire" and kest.autori_aastad(2026) == "2026" and kest.autori_aastad(2028) == "2026–2028"
    for f, h in sait.items():
        if 'http-equiv="refresh"' in h:
            continue  # kolinud lehe suunamine
        assert '<meta name="author"' not in h, f
        assert re.search(r'<p class="autor">© 20\d\d(–20\d\d)? <a href="saidist.html#autor">Tehisaru seire</a></p>', h), f
    s = sait["saidist.html"]
    assert 'id="autor"' in s and "kuuluvad oma allikatele" in s
    assert "tehisaru (Claude) abiga" in s and "on autori otsused" in s  # Kadri 12.11.2026: ava, mida tegi tehisaru
    # Kadri 12.11.2026: märge lühike nagu teistel saitidel, ilma „küsi luba“ ja kordamiseta
    assert "luba" not in s.split('id="autor"')[1].split("</section>")[0]


def test_saidil_pole_kadri_nime(A, tmp_path):
    """Kadri 27.11.2026: nime ei ole ühelgi avaldataval lehel ega failis; CSS ja JS lähevad välja ilma märkmeteta,
    sest märkmetes on „Kadri 8.11.2026 …“. Kadrioru on kohanimi ja on lubatud."""
    ehita.ehita(tmp_path, A)  # ehitus ise kukub nime korral (nime_kontroll); siin kontrollitakse veel kord
    for f in sorted(tmp_path.rglob("*")):
        if f.suffix in (".html", ".css", ".js", ".txt", ".xml", ".json", ".csv"):
            t = f.read_text(encoding="utf-8")
            assert not ehita.NIME_KONTROLL.search(t), f
    css = (tmp_path / "stiil.css").read_text(encoding="utf-8")
    js = (tmp_path / "sait.js").read_text(encoding="utf-8")
    assert "/*" not in css and "/*" not in js and not re.search(r"(?m)^\s*//", js)
    assert ehita.ilma_markmeteta("a.js", "var u = 'https://x.ee/a'; // märge\n  // rida\nf();") == "var u = 'https://x.ee/a';\nf();"
    assert ehita.NIME_KONTROLL.search("Kadrioru park") is None and ehita.NIME_KONTROLL.search("Kadri K")


def test_jarjestuse_joon_on_lihtne_tabada_ja_kaardi_vihje_luhike(sait):
    """Kadri 12.11.2026: järjestusgraafiku joont oli raske hõljudes tabada; kaardi vihje lõpus olev allikas kordus igal riigil."""
    h = sait["ettevotted.html"]
    assert h.count('<path class="bh"') == h.count('<path class="bj')
    css = (ehita.SIIN / "stiil.css").read_text(encoding="utf-8")
    m = re.search(r"\.bs \.bh \{[^}]*stroke-width: (\d+)px; pointer-events: stroke; \}", css)
    assert m and 12 <= int(m.group(1)) < 28  # laiem kui joon, kitsam kui ridade vahe
    vihjed = re.findall(r' data-a="([^"]*)"', h)
    assert vihjed and all(re.fullmatch(r"(20\d\d)?", v) for v in vihjed), set(vihjed)


def test_podcastide_kaaned_ja_ettekannete_logod(tmp_path):
    """Kadri 12.11.2026: „lisa podcastidele ka logod, otsi veebist“. Kaas tuleb saate RSS-voost, vähendatakse 64 px PNG-ks;
    ettekannete sarjade domeenid saavad logo samamoodi nagu uudiste allikad."""
    import io
    import lae_logod
    from PIL import Image
    v = io.BytesIO()
    Image.new("RGB", (300, 300), (20, 20, 20)).save(v, "JPEG")
    (tmp_path / "u.jsonl").write_text("", encoding="utf-8")
    (tmp_path / "e.json").write_text(json.dumps({"allikad": [{"id": "s", "url": "https://cs.ut.ee/x"}]}), encoding="utf-8")
    ico = b"\x00\x00\x01\x00" + b"0" * 200
    n = lae_logod.main(lambda u: ico, tmp_path / "logod", tmp_path / "u.jsonl", tmp_path / "e.json",
                       {"lexfridman.com": "https://x/kaas.jpg"}, lambda u: v.getvalue())
    logod = json.loads((tmp_path / "logod" / "logod.json").read_text(encoding="utf-8"))
    assert n == 2 and logod["lexfridman.com"] == "lexfridman.com.png" and "cs.ut.ee" in logod
    assert Image.open(tmp_path / "logod" / "lexfridman.com.png").size == (64, 64)
    assert set(lae_logod.KAANED) == {"lexfridman.com", "preposterousuniverse.com"}
    # Ettekande rida näitab sarja logo, kui see on olemas
    from sait import lehed_uudised
    rida = lehed_uudised._ek_allikas({"nimi": "Lex Fridman Podcast", "url": "https://lexfridman.com/podcast/"}, "")
    assert ('u-logo' in rida) == bool(lae_logod.logo_fail(lehed_uudised.LOGOD, "https://lexfridman.com/podcast/"))
    assert "Lex Fridman Podcast" in rida


def test_aripaeva_logo_on_kadri_antud():
    """Kadri 12.11.2026: Äripäeva uudistel on tema antud logo (punane Ä), mitte automaatselt laetud ikoon."""
    import lae_logod
    logod = json.loads((JUUR / "sait" / "pilt" / "logod" / "logod.json").read_text(encoding="utf-8"))
    assert lae_logod.logo_fail(logod, "https://www.aripaev.ee/uudised/2026/11/06/x") == "aripaev.ee.png"
    # Kadri 12.11.2026: Äritehnoloogia on Äripäeva väljaanne, sama logo
    assert lae_logod.logo_fail(logod, "https://www.aritehnoloogia.ee/uudised/2026/11/10/x") == "aripaev.ee.png"
    assert (JUUR / "sait" / "pilt" / "logod" / "aripaev.ee.png").read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"


def test_uudiste_rida_ei_veni_ule_ekraani():
    """Kadri 12.11.2026: uudiste read ei veni laial ekraanil üle kogu lehe; pikem tekst jääb klõpsuga avatavaks."""
    css = (JUUR / "sait" / "stiil.css").read_text(encoding="utf-8")
    m = re.search(r"\.u-voog li > div \{ max-width: (\d+)ch; \}", css)
    assert m and int(m.group(1)) <= 100
    assert ".u-paev .u-k.kinni { -webkit-line-clamp: 1; }" in css


def test_postimehe_logo_on_kadri_antud():
    """Kadri 12.11.2026: Postimehe uudistel (ka majandus.postimees.ee) on tema antud logo (sinine Pm)."""
    import lae_logod
    logod = json.loads((JUUR / "sait" / "pilt" / "logod" / "logod.json").read_text(encoding="utf-8"))
    assert lae_logod.logo_fail(logod, "https://majandus.postimees.ee/8412345/x") == "postimees.ee.png"
    assert lae_logod.logo_fail(logod, "https://www.postimees.ee/8412345/x") == "postimees.ee.png"
    assert (JUUR / "sait" / "pilt" / "logod" / "postimees.ee.png").read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"


def test_statistikaameti_logo_on_kadri_antud():
    """Kadri 12.11.2026: Statistikaameti uudistel on Eesti Statistika logo märk (9 punkti), mitte tekstina allikas."""
    import lae_logod
    logod = json.loads((JUUR / "sait" / "pilt" / "logod" / "logod.json").read_text(encoding="utf-8"))
    assert lae_logod.logo_fail(logod, "https://stat.ee/et/uudised/x") == "stat.ee.png"
    assert (JUUR / "sait" / "pilt" / "logod" / "stat.ee.png").read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"


def test_kuu_ruhmas_on_lyhike_kuupaev(sait):
    """Kadri 12.11.2026: vanemate kuude real kattus täiskuupäev pealkirjaga. Kuu rühmas on real ainult päev ja kuu."""
    kuud = re.findall(r'<div class="u-paev u-kuu[^"]*"[^>]*>.*?</ul>', sait["uudised.html"], re.S)
    assert kuud, "kuu rühmi pole"
    for g in kuud:
        for d in re.findall(r'class="d">([^<]*)<', g):
            assert re.fullmatch(r"\d{1,2}\.\d{2}\.", d), d

def test_riikide_strateegiad_tabelina(A):
    """Kadri „jah kõik“ 12.11.2026 (sp-2026-11-11-1): riikide sihid ainult tabelis, ei ühist graafikut ega järjestust."""
    import vota_kaasa
    vaade = _vaade("reeglid")
    h = lehed_teemad.riikide_strateegiad({**A, "strateegiad": None}, vaade)
    assert "pole kogumine veel siia toonud" in h
    sisend = {"kirjeldus": "x", "strateegiad": [
        {"id": "de", "riik": "Saksamaa", "riik_kood": "DE", "pealkiri": "KI-Nation 2030", "asutus": "BMDS", "kuupaev": "2026-11-02",
         "url": "https://bmds.bund.de/a.pdf", "tahtaeg": "2030", "kokkuvote": "sisemine", "markus": "Mõõtmisviis määramata.",
         "kontrollitud": "2026-11-10", "sihid": [
             {"siht": "KMU", "eesti": "VKEd, mis kasutavad tehisaru", "vaartus": "≥ 55%", "aasta": 2030, "lk": 20, "liik": "kasutus"},
             {"siht": "a", "eesti": "hoiak", "vaartus": "≥ 60%", "aasta": 2030, "lk": 15, "liik": "arvamus"},
             {"siht": "b", "eesti": "koolitus", "vaartus": "≥ 65%", "aasta": 2030, "lk": 27, "liik": "oskused"},
             {"siht": "c", "eesti": "majandus", "vaartus": "≥ 10%", "aasta": 2030, "lk": 20, "liik": "majandus"}]},
        {"id": "se", "riik": "Rootsi", "riik_kood": "SE", "pealkiri": "Sweden's AI Strategy", "kuupaev": "2026-02-25",
         "url": "https://government.se/s.pdf", "tahtaeg": "", "markus": "", "sihid": []}]}
    S = vota_kaasa.strateegiad_saidile(sisend)
    assert "kokkuvote" not in S["strateegiad"][0] and "kirjeldus" not in S
    h = lehed_teemad.riikide_strateegiad({**A, "strateegiad": S}, vaade)
    assert "4 arvulist sihti" in h and h.index("Saksamaa") < h.index("Rootsi")  # uusim dokument eespool
    assert h.index("VKEd, mis kasutavad") < h.index("koolitus") < h.index("hoiak")  # kasutus enne hoiakuid
    assert "Veel 1 sihti" in h and "lk 20" in h and "arvulisi sihte pole" in h and "puudub" in h
    assert "<svg" not in h and "<b>Eesti</b>" in h  # Eesti oma siht võrdluseks, ilma graafikuta


def test_uritused_ja_uudiste_plaadid_ilma_korduseta(sait):
    """No UI slop läbivaatus 14.11.2026: ürituste lehel ei korda pealkirjad sama lauset; rühma kirjeldus sobib ka podcastidele."""
    h = sait["uritused.html"]
    assert h.count("lähim eespool") <= 1 and "Praegu tulevad siia" not in h
    assert not re.search(r'<h2 id="h-tulekul">Tulekul', h)
    p = sait["podcastid.html"]
    assert "Kuidas ettevõtted tehisaru kasutusele võtavad" not in p


def test_telefonis_alamlehed_murduvad_ja_nupud_44px():
    """Kadri 14.11.2026 „muuda“: alamlehtede rida murdub telefonis ja nupud on puudutuseks vähemalt 44 px."""
    css = (JUUR / "sait" / "stiil.css").read_text(encoding="utf-8")
    osa = css[css.index("Kadri 14.11.2026 „muuda“"):]
    assert "html[data-t] .alamlehed { flex-wrap: wrap; overflow-x: visible;" in osa
    assert "html[data-t] .u-f button" in osa and "min-height: 44px" in osa


def _kontrast(a, b):
    def hel(h):
        k = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
        k = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in k]
        return 0.2126 * k[0] + 0.7152 * k[1] + 0.0722 * k[2]
    x, y = sorted((hel(a), hel(b)), reverse=True)
    return (x + 0.05) / (y + 0.05)


def test_ligipaasetavus_abitekst_graafik_ja_klopsualad(sait):
    """Ligipääsetavuse ülevaatus 14.11.2026 (Kadri „Jah, kõik viis“): WCAG 2.1 AA 1.4.3, 4.1.2 ja 2.5.8."""
    css = (JUUR / "sait" / "stiil.css").read_text(encoding="utf-8")
    # 1. Abitekst (--ink-3) on igas teemas igal taustal vähemalt 4,5:1.
    plokid = re.findall(r"\{([^{}]*--ink-3:[^{}]*)\}", css)
    assert len(plokid) == 4
    for plokk in plokid:
        t = dict(re.findall(r"--([\w-]+):\s*(#[0-9a-fA-F]{6})", plokk))
        for taust in ("surface", "surface-2", "brand-soft", "panel", "page"):
            if taust in t:
                assert _kontrast(t["ink-3"], t[taust]) >= 4.5, (t["ink-3"], taust, t[taust])
    # 2. Järjestusgraafiku SVG sees on fookustatav joon, seega on SVG rühm, mitte pilt (pilt ei tohi sisaldada nuppe).
    for leht in ("index.html", "too.html"):
        for svg in re.findall(r'<svg class="bump[^>]*>', sait[leht]):
            assert 'role="group"' in svg and 'role="img"' not in svg
    # 3. Puuteala vähemalt 24 px: graafiku joone nähtamatu ala ja uudise kokkuvõte.
    assert int(re.search(r"\.bs \.bh \{[^}]*stroke-width: (\d+)px", css).group(1)) >= 24
    assert re.search(r"\.u-k\.voib \{[^}]*line-height: max\(1.5em, 24px\)", css)


def test_disainikriitika_fookus_skaala_ja_lehel_rida(sait):
    """Disainikriitika 14.11.2026 (Kadri: „tee soovituste põhjal before and after vaade“)."""
    css = (JUUR / "sait" / "stiil.css").read_text(encoding="utf-8")
    # 1. Sinine kaardinumber on ainult pealkirja fookus: avalehel ettevõtted, Töö lehel mitte ükski.
    assert '<span class="big s"' not in sait["index.html"]  # 14.11.2026: avalehel plaate pole, tahvli numbrid on tumedad
    assert 'class="vastus kpi-pais"' not in sait["too.html"]  # 17.11.2026: Töö lehel plaate pole, numbrid on tahvli ridadel
    assert ".vastus.kpi-pais > .plaat:first-child .big:not(.s) { color: var(--ink); }" in css
    # 2. Töötuse kuugraafikul on abijooned koos väärtustega (y-skaala).
    osa = sait["too.html"][sait["too.html"].index('id="tootus-kuud"'):]
    svg = osa[:osa.index("</svg>")]
    assert svg.count('<line class="v"') >= 3
    # 3. „Sellel lehel“ on tekstilingid sildiga, mitte kiibid.
    assert 'content: "Sellel lehel:" / ""' in css
    assert re.search(r"max-width: 680px\) \{[^}]*\n  nav\[aria-label=\"Sellel lehel\"\] \.sellel a \{ min-height: 44px", css)


def test_vaikesed_alamlehed_on_teemalehe_plokid_ja_vanad_aadressid_suunavad(sait, tmp_path):
    """Kadri 14.11.2026 („Jah, kõigil teemadel“): väike alamleht on teemalehe plokk; vana aadress viib ploki ankrule."""
    for f, ankrud in [("inimesed.html", ("digi", "ei-oska")), ("ettevotted.html", ("kasu", "tootlikkus", "voimekus", "digi", "ta", "pohjamaad", "arenguseire")),
                      ("too.html", ("maailm", "ulesanded", "eesti", "kokkupuude", "hoive")),
                      ("tehisaru-maarus.html", ("tahtajad", "eesti-otsused", "strateegiad")), ("lahknevused.html", ("lahknevused", "varskus", "muutused"))]:
        for a in ankrud:
            assert f'id="{a}"' in sait[f], (f, a)
    assert 'class="alamlehed"' not in sait["inimesed.html"] and 'class="alamlehed"' not in sait["ettevotted.html"]
    ehita.ehita(tmp_path)
    for vana in ("inimesed-oskused.html", "ettevotted-voimekus.html", "too-uuringud.html", "too-ametid.html",
                 "eesti-otsused.html", "riikide-strateegiad.html", "varskus.html"):
        uus = ehita.VANAD_AADRESSID[vana]
        assert f'url={uus}"' in (tmp_path / vana).read_text(encoding="utf-8"), vana


def _vt_read(tv):
    """Vastustahvli read: [(ankur, küsimus)]. Iga rea link viib oma plokki."""
    out = []
    for r in tv.split('<details class="vt-r">')[1:]:
        out.append((re.search(r'class="vt-ava"><a href="#([a-z0-9-]+)"', r).group(1), html.unescape(re.search(r'class="vt-k">(.*?)</span>', r).group(1))))
    return out


def test_ettevotted_on_tahvel_maatriks_ja_kokkupandud_plokid(A, sait):
    """Kadri 14.11.2026 valis Ettevõtete lehele „B koos C maatriksiga“: tahvel, Põhjamaade maatriks, siis plokid kokku pandud."""
    import lehed
    h = sait["ettevotted.html"]
    main = re.search(r"<main.*?</main>", h, re.S).group(0)
    # järjekord: h1, tahvel, maatriks, üksikasjad; päises pole numbriplaate ega tühja kõrvalkasti
    assert main.index("</h1>") < main.index('id="tahvel"') < main.index('id="pohjamaad"') < main.index('id="h-uksikasjad"')
    assert 'data-kpi="ev-' not in h and '<aside class="vastus"' not in h
    tv = _jaotis(h, "tahvel")
    read = _vt_read(tv)
    # Kadri 26.11.2026 (nõrgad numbrid): uudistest kogutud välisfirmade otsuste arv ei ole Eesti ettevõtete seis; rida on
    # tahvlilt maas, plokk on üksikasjades. Katsete rida näitab katsete arvu, mitte „3 katses 4-st“.
    assert [r[1] for r in read] == ["Kui paljud kasutavad?", "Kus on Eesti ELis?", "Kas vahe Põhjamaadega kahaneb?",
                                    "Kas tehisaru tõstab tootlikkust?", "Kas võimekus on Põhjamaade tasemel?"]
    assert 'id="ligipaas"' in h and h.index('id="h-uksikasjad"') < h.index('id="ligipaas"')
    assert all(f'id="{a}"' in h for a, _ in read)
    # iga rida ütleb tõendi liigi; katsete numbreid ei liideta (iga katse oma ruut ja oma number märkuses)
    assert tv.count('class="tt-liik ') == len(read)
    K = lehed._ligipaasu_kontekst(A)["uuringud"]
    katsed = tv.split("Kas tehisaru tõstab tootlikkust?")[1].split("</details>")[0]
    assert f'<span class="vt-n">{len(K)} katset</span>' in katsed and "katses" in katsed and not re.search(r"\d+ katses \d+-st", katsed)
    assert "valis seire" in tv.split("Kas võimekus on Põhjamaade tasemel?")[1]
    assert katsed.count('<rect class="tt-r9 ') == len(K) and all(k["uuring"] in html.unescape(katsed) for k in K)
    # maatriks: 9 näitajat × 7 riiki, Eesti veerg raamitud; Põhjamaade võrdlus ei ole enam Võimekuse sakk
    mx = _jaotis(h, "pohjamaad")
    P = lehed.pohjamaade_profiil(A)
    assert mx.count('<td class="ee"') == len(P) == 9 and mx.split("</thead>")[0].count('<th scope="col"') == 9
    tasemel = sum(p["hinnang"] in ("yle", "vahemik") for p in P)
    assert mx.count('class="tt-h ok"') == tasemel and f"{tasemel} / {len(P)}" in tv
    assert 'id="sakk-pm"' not in h
    # plokid on kokkupandult, ankur avab ploki (sait.js avaAnkur)
    for sid in ("andmed", "ligipaas", "kasu", "voimekus", "lopp"):
        assert f'<details class="tt-pl" id="d-{sid}">' in h, sid
    js = (Path(ehita.__file__).parent / "sait.js").read_text(encoding="utf-8")
    assert "details:not([open])" in js


def test_struktuur_ei_loe_telefonikoopiat_ega_kokkupandud_ploki_sisu():
    import struktuur
    s = ('<div class="tv-tel"><p>koopia koopia</p></div><details class="tt-pl" id="d-x"><summary><b>Plokk</b></summary>'
         '<section><h2>Sees</h2><p>peidus sõnad</p></section></details><details class="tt-pl" open><summary>Lahti</summary><h2>Näha</h2></details><p>pärast</p>')
    n = struktuur.nahtav(s)
    assert "koopia" not in n and "peidus" not in n and "Sees" not in n
    assert "Plokk" in n and "Näha" in n and "pärast" in n


def test_inimesed_on_tahvel_sada_inimest_ja_kasutus_oskused(A, sait):
    """Kadri 14.11.2026 valis Inimeste lehele „A ja B koos“: tahvel, sada inimest, kasutus × digioskused, siis plokid kokku pandud."""
    h = sait["inimesed.html"]
    main = re.search(r"<main.*?</main>", h, re.S).group(0)
    assert main.index("</h1>") < main.index('id="tahvel"') < main.index('id="sada"') < main.index('id="kasutus-oskused"') < main.index('id="h-uksikasjad"')
    assert 'data-kpi="in-' not in h and '<aside class="vastus"' not in h
    tv = _jaotis(h, "tahvel")
    read = _vt_read(tv)
    assert len(read) >= 5 and all(f'id="{a}"' in h for a, _ in read)
    assert "küsimus võib erineda" in tv and "kontrollimata" in tv
    # Kadri 26.11.2026 (nõrgad numbrid): naabrite kasvu rida (Eurostati aasta vs riiklik järgmine aasta) on tahvlilt maas;
    # tööl kasutamise jagaja on hõivatud ja oskuste rida näitab mõlema allika arvu
    assert "naabrid" not in tv and [k for _, k in read].count("Kui paljud töötajad kasutavad tööl?") == 1
    th0, th = andmekiht.tooalane_hoivatutest(A)
    too_rida = tv.split("Kui paljud töötajad kasutavad tööl?")[1].split("</details>")[0]
    assert f'<span class="vt-n">{komponendid.pr(th["vaartus"])}%</span>' in too_rida and "hõivatutest" in too_rida
    assert f'aasta varem {komponendid.pr(th0["vaartus"])}%' in too_rida and "Kõigist 16–74-aastastest" in too_rida
    assert f'>{komponendid.pr(th["vaartus"])}% Eesti hõivatutest</b>' in _jaotis(h, "tool")
    os_rida = tv.split("Kui paljusid takistab oskuste puudus?")[1].split("</summary>")[0]
    assert "Eurostat" in os_rida and "Statistikaameti järgi" in os_rida
    # sada inimest: 100 ruutu Eesti ja ELi kohta; rühmad samast küsitlusest ega kattu
    sada = _jaotis(h, "sada")
    assert sada.count('<rect class="tt-w ') == 200
    y = andmekiht.leia(A, "inimeste-tehisaru-kasutus", "EE", "uusim:alus")["aasta"]
    k, t, o = (andmekiht.leia(A, n, "EE", y)["vaartus"] for n in ("inimeste-tehisaru-kasutus", "tooalane-tehisaru-kasutus", "tehisaru-oskuse-puudus"))
    vahvel = sada.split("<svg")[1].split("</svg>")[0]
    assert vahvel.count("tt-w tool") == sum(j + 0.5 <= t for j in range(100))
    assert vahvel.count("tt-w muu") == sum(j + 0.5 > k + o for j in range(100))
    # hajuvusgraafik: 27 riiki, Eesti esile tõstetud, seos ei näita põhjust
    sk = _jaotis(h, "kasutus-oskused")
    for svg in sk.split('class="tt-sc-')[1:]:  # lai ja telefoni kitsas joonis, samad punktid
        svg = svg.split("</svg>")[0]
        assert svg.count('<circle class="tv-c"') + svg.count('<circle class="tv-ee"') == 27 and svg.count('<circle class="tv-ee"') == 1
    assert "ei näita põhjust" in sk and "neid ei liideta" in sk
    for sid in ("andmed", "digi", "ei-oska", "lopp"):
        assert f'<details class="tt-pl" id="d-{sid}">' in h, sid


def test_vahvel_ei_luba_ule_saja_protsendi():
    import teema_tahvel
    with pytest.raises(andmekiht.AndmeViga):
        teema_tahvel.vahvel([("tool", 60), ("oska", 50)], "x")


def test_too_on_tahvel_toendikaart_ja_astmed(A, sait):
    """Kadri 17.11.2026 valis Töö lehele „A ja C koos“: tahvel, kus on tõendeid, hõive avatuse astme järgi, siis plokid kokku pandud.
    Kadri 25.11.2026 (oluline enne valikulist): tahvel, töötus, koondamised ja astmed on nähtaval; tõendikaart on üksikasjade esimene rida."""
    h = sait["too.html"]
    main = re.search(r"<main.*?</main>", h, re.S).group(0)
    assert (main.index("</h1>") < main.index('id="tahvel"') < main.index('id="tootus-kuud"') < main.index('id="koondamised"')
            < main.index('id="astmed"') < main.index('id="h-uksikasjad"') < main.index('id="toendid"'))
    assert 'data-kpi="too-' not in h and '<aside class="vastus"' not in h
    tv = _jaotis(h, "tahvel")
    read = re.findall(r'<details class="vt-r"><summary><span class="vt-k">(.*?)</span><span class="vt-v"><span class="vt-s"><b>(.*?)</b><span class="vt-n">(.*?)</span>', tv)
    lingid = re.findall(r'<p class="vt-ava"><a href="([a-z]*(?:\.html)?)#([a-z-]+)">', tv)
    # rea link viib oma plokki; tööalase kasutuse graafik on Inimeste lehel (Kadri 26.11.2026 „Jah, vaheta“)
    assert len(read) == len(lingid) == 6 and all(f'id="{a}"' in (sait[leht] if leht else h) for leht, a in lingid)
    assert [leht for leht, _ in lingid if leht] == ["inimesed.html"]
    # Kadri 26.11.2026 (nõrgad numbrid): jagaja on hõivatud, mitte kõik 16–74-aastased; kõigi arv on märkuses
    too_rida = next(r for r in tv.split('<details class="vt-r">')[1:] if "Kui paljud töötajad kasutavad tehisaru tööl?" in r)
    _, too_uus = andmekiht.tooalane_kasutus(A)
    _, th = andmekiht.tooalane_hoivatutest(A)
    assert th["vaartus"] > too_uus["vaartus"] and th["aasta"] == too_uus["aasta"]
    assert f'<span class="vt-n">{komponendid.pr(th["vaartus"])}%</span>' in too_rida and "hõivatutest" in too_rida.split("</summary>")[0]
    assert f'16–74-aastastest (ka töötud, õpilased ja pensionärid) {komponendid.pr(too_uus["vaartus"])}%' in too_rida
    assert f'>{komponendid.pr(th["vaartus"])}% Eesti hõivatutest</b>' in sait["inimesed.html"]  # sama number mis Inimeste lehel
    # koondamiste rida: arv ilma jagajata, pildil üks ruut teate kohta
    k_rida = next(r for r in tv.split('<details class="vt-r">')[1:] if "Kas koondatakse tehisaru tõttu?" in r)
    assert not re.search(r"\d+-st", k_rida.split("</summary>")[0]) and "osakaalu ei arvutata" in k_rida
    assert k_rida.count('<rect class="tt-jr ') == len(A["koondamised"]["juhtumid"])
    assert 'href="#ai-kuulutused"' in too_rida and "Kas tehisaruoskust otsitakse?" not in h  # kuulutused jäävad üksikasjadesse
    assert h.index('id="h-uksikasjad"') < h.index('id="ai-kuulutused"')
    assert all(sona.strip() and not re.search(r"\d+[,.]?\d*\s*%", sona) for _, sona, _ in read)  # vastus on sõna, protsent on selle kõrval
    assert "ei näita, kas muutuse põhjus on tehisaru" in tv
    # tahvli ees ei ole lugemisjuhist ega all loendurite rida; märkus, tõend ja allikas on rea sees
    assert "<table" not in tv and 'class="tt-us"' not in tv and "Rida viib oma plokki" not in tv
    assert tv.count("<dt>Märkus</dt>") == tv.count("<dt>Allikas</dt>") == 6
    # tõendikaart: iga rida on küsimus, neli kohta; lahtrite numbreid ei võrrelda; Eesti töökohtade ridadel pole rühmi võrdlevat uuringut
    tk = _jaotis(h, "toendid")
    ridu = re.findall(r'<tr><th scope="row"><a href="#([a-z-]+)">.*?</tr>', tk, re.S)
    assert len(ridu) >= 6 and all(f'id="{a}"' in h for a in ridu)
    for rida in re.findall(r'<tr><th scope="row">.*?</tr>', tk, re.S):
        assert rida.count("<td class=\"tk-") == 4
        if "tootlikkus" not in rida:
            assert not rida.split("</th>")[1].startswith('<td class="tk-p"'), rida[:80]
    assert "Eri lahtrite numbreid ei võrrelda" in tk
    # astmed: kuus astet, Eesti ja EL igal real; kirjeldus, mitte põhjus
    am = _jaotis(h, "astmed")
    # Kadri 26.11.2026: aste üksi ei ütle midagi; iga rea all on kolm suurimat ametit Eestis (Statistikaamet PA633)
    import too_tahvel
    read = re.findall(r'<li class="as-r[^"]*">(.*?)</li>', am, re.S)
    assert len(read) == 6
    K = A["kokkupuude"]
    for (k, nimi), rida in zip(too_tahvel.ASTE, read):
        assert rida.count('class="as-ee"') == 1 and rida.count('class="as-el"') == 1
        assert tekst(re.search(r'<div class="as-n"><b>(.*?)</b>', rida).group(1)) == nimi
        naited = tekst(re.search(r"<small>(.*?)</small>", rida).group(1)).split(" · ")
        assert [n.lower() for n in naited] == [x["nimi"].lower() for x in K["naited"][k]] and len(naited) == 3
        assert "Eesti " in tekst(re.search(r'<span class="peidus">(.*?)</span>', rida).group(1))  # sama info sõnadega
    assert "Statistikaamet, PA633" in am and "<svg" not in am[am.index("<figure"):am.index("</figure>")]
    assert "kirjeldus, mitte põhjus" in am and "lfsa_egai2d" in am
    plokid = re.findall(r'<details class="tt-pl" id="d-([a-z]+)">', h)
    assert plokid == ["toendid", "andmed", "maailm", "eesti", "ametid", "lopp"]


def test_jaotusriba_ei_luba_ule_saja_protsendi():
    import too_tahvel
    with pytest.raises(andmekiht.AndmeViga):
        too_tahvel.jaotusriba([("s", 70), ("m", 40)], "liiga palju")


def test_avalik_sektor_on_tahvel_teekond_ja_asutused(A, sait):
    """Kadri 17.11.2026 valis Avaliku sektori lehele „A ja C koos“: tahvel, uuenduse teekond, 48 asutust, siis plokid kokku pandud."""
    h = sait["avalik-sektor.html"]
    main = re.search(r"<main.*?</main>", h, re.S).group(0)
    assert main.index("</h1>") < main.index('id="tahvel"') < main.index('id="teekond"') < main.index('id="asutused"') < main.index('id="h-uksikasjad"')
    assert 'data-kpi="' not in h and 'class="vastus' not in h
    tv = _jaotis(h, "tahvel")
    read = _vt_read(tv)
    assert len(read) == 6 and all(f'id="{a}"' in h for a, _ in read)
    # väiteid avaliku sektori kohta pole: lehel pole väidete linki, mis viiks tühja kohta
    assert 'href="#t-vaited"' not in h
    # teekond: viis etappi laias ja kitsas joonises, fookus pärast suurimat langust
    tk = _jaotis(h, "teekond")
    for svg in tk.split('class="tt-svg tt-sc-')[1:]:
        svg = svg.split("</svg>")[0]
        assert svg.count('<rect class="tv-v"') == 2 and svg.count('<rect class="tt-jr m"') == 3
    assert "Prototüübist hindamiseni jõuab 22 protsendipunkti vähem projekte" in tekst(tk) and "Katse (RCT)" in tk
    # asutused: üks ruut = üks vastanud asutus; korrata asutused on kasutajate hulgas
    asu = _jaotis(h, "asutused")
    R = {r["ruhm"]: int(r["vaartus"]) for r in A["leiud_arvud"] if r["leid"] == "rk-ai-kord"}
    assert asu.count('<i class="av-q a"></i>') == R["korrata"] + 1  # + legend
    assert asu.count('<i class="av-q b"></i>') == R["kasutab"] - R["korrata"] + 1
    assert asu.count('<i class="av-q c"></i>') == R["vastas"] - R["kasutab"] + 1
    assert "Ei ole kõigi Eesti asutuste kohta" in asu and "riigikontroll.ee" in asu
    # sama joonis pole kaks korda: etapid ja oskused on ainult tahvli all
    assert 'id="etapid"' not in h and 'id="oskused"' not in h and 'id="g-hindamine"' not in h
    for sid in ("andmed", "ametnikud", "lopp"):
        assert f'<details class="tt-pl" id="d-{sid}">' in h, sid


def test_avaliku_sektori_tahvel_kukub_kui_andmed_pealkirja_ei_toeta(A):
    import avalik_tahvel
    muuda = lambda i, x: dict(A, avalik={k: (dict(r, vaartus=x) if r["id"] == i else r) for k, r in A["avalik"].items()})  # noqa: E731
    with pytest.raises(andmekiht.AndmeViga):
        avalik_tahvel.Andmed(muuda("etapp-hindamine", "50"))  # suurim langus ei ole enam prototüübist hindamiseni
    with pytest.raises(andmekiht.AndmeViga):
        avalik_tahvel.Andmed(muuda("indeks-moju-max", "0.3"))  # mõju ei ole enam alla 0,25
    arvud = [dict(r, vaartus="45") if r["leid"] == "rk-ai-kord" and r["ruhm"] == "korrata" else r for r in A["leiud_arvud"]]
    with pytest.raises(andmekiht.AndmeViga):
        avalik_tahvel.Andmed(dict(A, leiud_arvud=arvud))  # korrata asutusi ei saa olla rohkem kui kasutajaid


def test_hanked_on_tahvel_kuidas_ja_head_naited(A, sait):
    """Kadri 19.11.2026 valis Hangete lehele „A ja C koos“: tahvel, kuidas hangitakse, head näited, siis plokid kokku pandud."""
    h = sait["hanked.html"]
    H = A["hanked_leht"]
    main = re.search(r"<main.*?</main>", h, re.S).group(0)
    assert main.index("</h1>") < main.index('id="tahvel"') < main.index('id="kuidas"') < main.index('id="naited-kokku"') < main.index('id="h-uksikasjad"')
    assert 'data-kpi="' not in h and 'class="vastus' not in h
    tv = _jaotis(h, "tahvel")
    read = _vt_read(tv)
    # Kadri 26.11.2026 (nõrgad numbrid): täpsuse rida on tahvlilt maas (meetodi info on esimese rea märkuses ja plokis
    # #tapsus); innovatsioonihangete rida ei võrdle hankija märget sihiga, mille ühik on kontrollimata
    assert len(read) == 5 and all(f'id="{a}"' in h for a, _ in read) and 'id="tapsus"' in h
    assert "Kui täpne on hangete leidmine?" not in tv and 'href="#tapsus"' in tv.split("</details>")[0]
    assert re.search(r'<span class="vt-n">umbes \d+</span>', tv.split("</details>")[0])
    inn = tv.split("Kui palju on innovatsioonihankeid?")[1].split("</details>")[0]
    assert "Veel mitte" not in tv and "tv-siht" not in inn and "sihiga ei võrrelda" in inn and "hangete eelarvest" in inn
    inn_plokk = _jaotis(h, "innovatsioon")
    assert "vr-siht" not in inn_plokk and "Sihijoont joonisel ei ole" in inn_plokk
    assert "→ siht" not in tekst(_jaotis(sait["index.html"], "teemad").split('href="hanked.html"')[1].split("</tr>")[0])
    assert 'href="#t-vaited"' not in h
    # kuidas: kolm näitajat kolmes rühmas, lai ja kitsas joonis; sakis sama joonist enam pole
    V = H["hankimise_viis"]
    ku = _jaotis(h, "kuidas")
    assert ku.count('class="tt-svg tt-sc-') == 2 and ku.count('<circle class="tv-pf"') == 2 * 3 + 1  # + legend
    assert f'Kvaliteeti hinnatakse {100 - V["ai_andmed"]["ainult_hind_osakaal"]:.0f}% hangetest' in tekst(ku)
    assert 'id="viis"' not in h and "Hindas ka kvaliteeti, %" not in h
    # head näited: kolm tingimust; täidetud + täitmata + teadmata = kõik hanked; link näidete lehele
    L = H["loend"]
    na = _jaotis(h, "naited-kokku")
    hea = sum(1 for r in L if r.get("hea") == 3)
    assert f"{hea} hanget {len(L)}-st vastab kõigile kolmele tingimusele" in tekst(na) and 'href="hanked-naited.html"' in na
    for jah, ei, tea in re.findall(r'<p><span>[^<]+</span><b>(\d+)</b></p>.*?<small>[^<]*? (\d+) · teadmata (\d+)</small>', na, re.S):
        assert int(jah) + int(ei) + int(tea) == len(L)
    # hankijate arv on kogu loendi pealt, nii ka periood (enne oli silt hankimise viisi perioodist)
    a0, a1 = min(r["a"] for r in L), max(r["a"] for r in L)
    assert f"Kõik leitud hanked {a0}–{a1}." in _jaotis(h, "hankijad")
    for sid in ("andmed", "lopp"):
        assert f'<details class="tt-pl" id="d-{sid}">' in h, sid


def test_hangete_tahvel_kukub_kui_andmed_pealkirja_ei_toeta(A):
    import hanked_tahvel
    from lehed_uudised import KASITSI
    H = A["hanked_leht"]
    V = H["hankimise_viis"]
    v2 = dict(V, ai_andmed=dict(V["ai_andmed"], ainult_hind_osakaal=V["it_muud"]["ainult_hind_osakaal"]))  # kvaliteeti sama sageli
    with pytest.raises(andmekiht.AndmeViga):
        hanked_tahvel.Andmed(dict(H, hankimise_viis=v2), KASITSI)
    with pytest.raises(andmekiht.AndmeViga):  # kontsentratsioon pole kogu loendi pealt
        hanked_tahvel.Andmed(dict(H, kontsentratsioon=dict(H["kontsentratsioon"], nende_osakaal=H["kontsentratsioon"]["nende_osakaal"] + 5)), KASITSI)
    i = next(i for i, r in enumerate(H["loend"]) if r.get("hea") != 3)
    loend = H["loend"][:i] + [dict(H["loend"][i], hea=3)] + H["loend"][i + 1:]
    with pytest.raises(andmekiht.AndmeViga):  # hea näite märge ei vasta tingimustele
        hanked_tahvel.Andmed(dict(H, loend=loend), KASITSI)


def test_koondamiste_kuupaev_on_viimase_teate_oma(A, sait):
    # Kadri 25.11.2026: nimekiri täieneb uudistest iga päev, „kontrollitud 8.11“ näitas seda vanana
    viimane = komponendid.kp(max(r["kuupaev"] for r in A["koondamised"]["juhtumid"]))
    h = sait["too.html"]
    assert f"viimane teade {viimane}" in tekst(_jaotis(h, "tahvel"))
    assert f"(viimane teade {viimane})" in tekst(_jaotis(h, "koondamised"))
    assert "kontrollitud " + komponendid.kp(A["koondamised"]["kontrollitud"]) not in tekst(_jaotis(h, "tahvel"))


# Telefon: külgsuunas ei kerita, tabeli rida jääb üheks reaks (Kadri 25.11.2026)
_TBL = re.compile(r'<div class="(tbl[^"]*)"(?: style="([^"]*)")?>\s*<table([^>]*)>(.*?)</table>', re.S)
# Need tabelid laotakse telefonis ümber omaette reeglitega (stiil.css), tbl_div märget nad ei vaja.
_TELEFONIS_OMA_KUJU = ("tv-laud", "tt-mx", "tk-laud")


def _tabelid(sait):
    for f, h in sait.items():
        if not f.endswith(".html"):
            continue
        for m in _TBL.finditer(h):
            pea = re.search(r"<thead>\s*<tr[^>]*>(.*?)</tr>", m.group(4), re.S)
            veerge = len(re.findall(r"<th\b", pea.group(1))) if pea else 0
            yield f, m.group(1).split(), m.group(2) or "", m.group(3) + m.group(4)[:200], veerge


def test_tbl_div_kirjutab_telefonireeglid_klassideks():
    assert komponendid.tbl_div() == '<div class="tbl">'
    assert komponendid.tbl_div("-3 -5 1:6em") == '<div class="tbl tf tp-3 tp-5" style="--t1:6em">'
    assert komponendid.tbl_div("v3 1:30%", "kaart") == '<div class="tbl tf kaart tv3" style="--t1:30%">'
    assert 'class="tbl tf tp-2"' in komponendid.tabel(["A", "B"], [["1", "2"]], tel="-2")


def test_lai_tabel_ei_jaa_telefonis_margita(sait):
    """Nelja ja enama veeruga tabel peab ütlema, kuidas ta telefonis ära mahub; muidu hakkab leht jälle külgsuunas kerima."""
    margita = sorted({(f, veerge) for f, kl, _, tabel, veerge in _tabelid(sait)
                      if veerge >= 4 and "tf" not in kl and not set(kl) & set(_TELEFONIS_OMA_KUJU)
                      and "Riikide tehisarustrateegiad" not in tabel})  # #strateegiad laotakse telefonis kaartideks
    assert not margita, margita


def test_telefonis_on_tabelis_kuni_viis_veergu_ja_reeglid_viitavad_olemasolevale_veerule(sait):
    naha = 0
    for f, kl, stiil, tabel, veerge in _tabelid(sait):
        if "tf" not in kl:
            continue
        naha += 1
        peidus = [int(k[3:]) for k in kl if k.startswith("tp-")]
        laiused = [int(n) for n in re.findall(r"--t(\d+):", stiil)]
        assert all(1 <= n <= veerge for n in peidus + laiused), (f, kl, stiil, veerge)
        assert not set(peidus) & set(laiused), (f, kl, stiil)  # peidetud veerule laiust ei anta
        jaab = 4 if "tv3" in kl else veerge - len(peidus)
        assert jaab <= 5 or 'class="lits-m"' in tabel, (f, kl, veerge)  # viis mahub ainult arvudega; litsentside maatriksis on telefonis ainult arvud
        assert 1 not in peidus or veerge - len(peidus) >= 2, (f, kl)
    assert naha >= 20


def test_telefoni_stiil_ei_keri_kylgsuunas_ja_nupp_toob_koik_veerud():
    css = (JUUR / "sait" / "stiil.css").read_text(encoding="utf-8")
    osa = css[css.index("Telefon: miski ei keri külgsuunas"):]
    assert "html[data-t] .lehel-rida .sellel, html[data-t] .top .sellel { flex-wrap: wrap; overflow-x: visible; }" in osa
    assert "html[data-t] .lehel-rida { position: static; }" in osa
    kitsas = osa[osa.index("@media (max-width: 560px)"):]
    assert "html[data-t] .tbl.tf:not(.koik) table { table-layout: fixed; width: 100%; min-width: 0; }" in kitsas
    for n in range(1, 7):  # iga veerunumber, mida tbl_div võib kirjutada, on stiilis olemas
        assert f"tr > :nth-child({n}) {{ width: var(--t{n}, auto); }}" in kitsas
        assert f"html[data-t] .tbl.tp-{n}:not(.koik) tr > :nth-child({n})" in kitsas
    assert "html[data-t] .tbl.tv3:not(.koik) tr > :not(:first-child):not(:nth-last-child(-n+3)) { display: none; }" in kitsas
    assert ".kogus.veerud { display: none; }" in osa  # arvutis nuppu ei ole
    js = (JUUR / "sait" / "sait.js").read_text(encoding="utf-8")
    assert "'.tbl.tf[class*=\" tp-\"], .tbl.tf.tv3, .tbl.tf.tl'" in js
    assert "Näita kõiki veerge" in js and "Näita ainult põhiveerge" in js and "classList.toggle('koik')" in js
    assert "getComputedStyle(r).position === 'sticky'" in js  # ankur ei arvesta rida, mis telefonis ei kleepu


def test_registreeritud_tootud_on_eraldi_plokis_ja_ei_ole_maar(sait):
    # Kadri 25.11.2026: töötuse määr on septembri oma; uuem kuu on olemas ainult registreeritud töötute kohta
    kuud, avaldatud = lehed_ulevaade.reg_tootud()
    kuu, n = kuud[-1]
    h = sait["too.html"]
    assert h.index('id="tahvel"') < h.index('id="tootus-kuud"') < h.index('id="reg-tootud"') < h.index('id="koondamised"')
    osa = tekst(_jaotis(h, "reg-tootud"))
    assert f"{n:,}".replace(",", " ") in osa.replace(" ", " ") and lehed_ulevaade.kuu_seesytlev(kuu) in osa
    assert "ei ole töötuse määr" in osa and "ei võrrelda" in osa and "TT065" in osa
    assert "%" not in re.search(r'<h2 id="h-reg-tootud">(.*?)</h2>', h, re.S).group(1)  # pealkirjas on arv, mitte määr
    assert _jaotis(h, "reg-tootud").count("<svg") == 1


def test_ai_kuulutuste_allikarida_ei_luba_igapaevast_kogumist_kui_fail_on_vana(A, sait):
    import datetime as dt
    vanus = (dt.date.fromisoformat(A["toopakkumised"]["uuendatud"][:10]) - dt.date.fromisoformat(A["ai_kuulutused"]["uuendatud"][:10])).days
    rida = [r for r in sait["too.html"][sait["too.html"].index('id="t-allikad"'):].split("</tr>") if "CV.ee" in r and "AI- ja andmetööde" in r][0]
    assert ("kogutakse iga päev" in rida) == (vanus <= 3)
    assert ("kogumine on katkenud" in rida) == (vanus > 3)



def test_too_tahvli_sona_tuleb_andmetest():
    """Kadri 25.11.2026: tahvli rida vastab sõnaga. Sõna arvutatakse numbrist kindla piiriga, mitte ei kirjutata käsitsi."""
    import types
    import too_tahvel as tt_
    D = types.SimpleNamespace(t_ee=8.0, t_ee0=7.1, v_muut=-19.2, k_pohjusena=[1, 2], kj=list(range(10)))
    assert tt_.sona_tootus(D) == "Jah" and tt_.sona_vabad(D) == "Jah" and tt_.sona_koondamised(D) == "Mõni ettevõte ütleb nii"
    D.t_ee0, D.v_muut, D.k_pohjusena = 7.9, 2.0, []
    assert tt_.sona_tootus(D) == "Püsib samal tasemel" and tt_.sona_vabad(D) == "Umbes sama palju"
    assert tt_.sona_koondamised(D) == "Ükski ettevõte ei öelnud nii"
    D.t_ee0, D.v_muut, D.k_pohjusena = 8.6, 7.0, list(range(6))
    # koondamiste sõna ei ütle „enamik“: teated on uudistest kogutud valik, mitte kõigi koondamiste loend (26.11.2026)
    assert tt_.sona_tootus(D) == "Ei, väheneb" and tt_.sona_vabad(D) == "Ei, rohkem" and tt_.sona_koondamised(D) == "Mõni ettevõte ütleb nii"
    D.k_pohjusena = [1]
    assert tt_.sona_koondamised(D) == "Üks ettevõte ütleb nii"
    D.t_ee0 = None
    with pytest.raises(andmekiht.AndmeViga):
        tt_.sona_tootus(D)
    # hõive: alla valimivea piiri (PIIR_HOIVE_PR, seire hinnang) ei öelda suunda (Kadri 26.11.2026: −0,9% ei ole „veidi vähem“)
    assert tt_.PIIR_HOIVE_PR == 5
    assert [tt_.sona_hoive(v) for v in (-6.0, -4.9, -0.9, 0.3, 4.9, 5.0)] == ["Jah"] + ["Selget muutust ei ole"] * 4 + ["Ei, rohkem"]


def test_too_uks_kusimus_uks_number(A, sait):
    """Läbivaatus 25.11.2026: „Kas avatud ametites on tööd vähem?“ oli kolmes plokis kahe eri numbriga (+0,7% ja −0,9%).
    Tahvli rida ja nähtav joonis räägivad nüüd samast rühmast (aste 3–4) sama numbriga; teine rühm on rea märkuses."""
    import too_tahvel as tt_
    h = sait["too.html"]
    D = tt_.Andmed(A)
    rida = [r for r in _jaotis(h, "tahvel").split('<details class="vt-r">') if "kõige avatumates ametites on tööd vähem" in r]
    assert len(rida) == 1
    kokku, markus = rida[0].split("</summary>")
    assert f'<span class="vt-n">{tt_.mt(D.ee_k)}</span>' in kokku and tt_.mt(D.ee_av) not in tekst(kokku)
    assert 'href="#astmed"' in markus and f"(aste 1–4) {tt_.mt(D.ee_av)}" in tekst(markus)
    assert komponendid.pr(abs(D.ee_k)) + "%" in tekst(re.search(r'<h2 id="h-astmed">(.*?)</h2>', h, re.S).group(1))


def test_tagasi_nupp_viib_ankrult_tagasi():
    """Viga leitud 25.11.2026: tahvli realt plokki hüpates ei viinud tagasi-nupp tahvli juurde (kerimise taastamine on käsitsi
    ja saki avamine kirjutas lahkumise koha aadressi üle). Skript jätab koha meelde ja ankur ei kirjuta ?sakk=… aadressi."""
    js = (JUUR / "sait" / "sait.js").read_text(encoding="utf-8")
    assert "olek.keri = Math.round(window.scrollY)" in js and "window.addEventListener('popstate'" in js
    assert "if (!window.seireAnkurAvab) sea(" in js and "window.seireAnkurAvab = true" in js


def test_teemalehtede_tahvel_vastab_sonaga(sait):
    """Kadri 25.11.2026: oluline enne valikulist, „this logic needs to be redone in other pages as well“.
    Igal teemalehel on tahvli rida küsimus, vastus sõnaga, üks number ja pilt; märkus, tõend ja allikas avanevad real."""
    for f in ("inimesed.html", "ettevotted.html", "avalik-sektor.html", "hanked.html", "too.html"):
        tv = _jaotis(sait[f], "tahvel")
        read = tv.split('<details class="vt-r">')[1:]
        assert 5 <= len(read) <= 6, f
        assert "<table" not in tv and 'class="tt-us"' not in tv and "Rida viib oma plokki" not in tv, f
        for r in read:
            kokku, lahti = r.split("</summary>")
            sona, arv = re.search(r'<span class="vt-s"><b>(.*?)</b><span class="vt-n">(.*?)</span>', kokku, re.S).groups()
            assert sona.strip() and not re.search(r"\d,\d|%", sona), (f, sona)        # sõna, mitte teine number
            assert len(re.findall(r"\d+(?:,\d+)?%", tekst(arv))) <= 1, (f, arv)         # üks küsimus, üks number
            assert "<svg" in kokku and "<dt>Märkus</dt>" in lahti and "<dt>Allikas</dt>" in lahti and 'class="tt-liik ' in lahti, f
            assert "<dt>Märkus</dt>" not in kokku and 'class="tt-liik ' not in kokku, f


def test_tahvli_sonade_piirid():
    """Sõna tuleb numbrist kindla piiriga (piirid on Claude'i valik, kirjas failis UUENDUSED.md 26.11.2026)."""
    import avalik_tahvel
    import hanked_tahvel
    import teema_tahvel as tt_
    osa = {0.9: "Umbes iga 100.", 4.7: "Umbes iga 20.", 13: "Umbes iga 8.", 20: "Umbes iga viies", 24: "Umbes veerand", 28: "Umbes veerand",
           33: "Umbes kolmandik", 36.9: "Umbes kolmandik", 44: "Alla poole", 50: "Umbes pooled", 60: "Üle poole", 65: "Umbes kaks kolmandikku",
           75: "Umbes kolmveerand", 83: "Enamik", 97: "Peaaegu kõik", "28": "Umbes veerand"}
    assert {p: tt_.sona_osa(p) for p in osa} == osa
    for vale in (-1, 101, None, "palju"):
        with pytest.raises(andmekiht.AndmeViga):
            tt_.sona_osa(vale)
    assert [tt_.sona_koht(k, 27) for k in (2, 3, 4, 9, 10, 18, 19, 27)] == ["Esikolmikus"] * 2 + ["Esimeses kolmandikus"] * 2 + ["Keskmiste seas"] * 2 + ["Viimases kolmandikus"] * 2
    with pytest.raises(andmekiht.AndmeViga):
        tt_.sona_koht(28, 27)
    assert [tt_.sona_muutus(v, 1, "kasvab", "kahaneb", "sama") for v in (6.5, 0.9, -0.1, -1.0)] == ["kasvab", "sama", "sama", "kahaneb"]
    assert [avalik_tahvel.sona_katse(p) for p in (6, "6", 20)] == ["Umbes iga 15. hindamine on katse"] * 2 + ["Umbes iga viies hindamistest on katse"]
    assert [avalik_tahvel.sona_kord(41, kr) for kr in (0, 8, 33)] == ["kõigil oli", "enamikul oli", "enamikul veel mitte"]
    with pytest.raises(andmekiht.AndmeViga):
        avalik_tahvel.sona_kord(41, 42)
    assert [avalik_tahvel.sona_raha(p) for p in (83, 55, 20)] == ["Peamiselt ELilt", "Üle poole ELilt", "Osaliselt ELilt"]
    assert [hanked_tahvel.sona_hankijad(p) for p in (60, 44, 20)] == ["Peamiselt mõni suur hankija", "Suur osa vähestelt hankijatelt", "Paljud eri hankijad"]


def test_norgad_numbrid_26_11(A, sait):
    """Kadri 26.11.2026 („We can't compare it like that“): tahvlite nõrgad numbrid. Jagaja sobib küsimusega, uudistest
    kogutud teateid ei näidata osakaaluna ja Eesti hõive väikest muutust ei tõlgendata suunana."""
    import too_tahvel as tt_
    D = tt_.Andmed(A)
    too = sait["too.html"]
    # 1. Hõive: alla valimivea piiri ei ütle pealkiri suunda (ei „vähenes“ ega „kasvas vähem kui teistes“)
    astmed = tekst(too.split('id="h-astmed">')[1].split("</h2>")[0])
    hoive = tekst(too.split('id="h-hoive">')[1].split("</h2>")[0])
    if not tt_.selge_muutus(D.ee_k):
        assert "selget muutust ei ole" in astmed and "vähenes Eesti hõive" not in astmed
    if abs(D.ee_av - D.ee_mu) < tt_.PIIR_HOIVE_PR:
        assert "liiga väike, et suunda öelda" in hoive and "vähem kui teistes" not in hoive.split("¦")[0]
    assert "seire hinnang" in _jaotis(too, "astmed") and "usalduspiire pole kontrollitud" in _jaotis(too, "astmed")
    # 2. Koondamised: tõendikaardil ei ole „N juhtum M-st“
    tk = _jaotis(too, "toendid")
    assert "juhtum" not in tk and re.search(r"ettevõtet? (ei )?ütleb? nii", tk)
    # 3. Hõivatute mõõdik on kataloogis oma klassiga ja laadija küsib sama rühma
    m = A["moodikud"][andmekiht.HOIVATUD]
    assert m["vorreldavus"] == "osaliselt" and "SAL_SELF_FAM" in m["filtrid"] and not m["naitaja"]
    lae_p = (JUUR / "kataloog" / "lae.py").read_text(encoding="utf-8")
    assert f'("{andmekiht.HOIVATUD}"' in lae_p and '"Isikute rühm": ["SAL_SELF_FAM"]' in lae_p
    th0, th = andmekiht.tooalane_hoivatutest(A)
    assert th0 and th0["aasta"] == th["aasta"] - 1 and th["vaartus"] > andmekiht.tooalane_kasutus(A)[1]["vaartus"]
    # 4. Avalik sektor: korra rea jagaja on valmislahendusi kasutanud asutused ja aasta on vastuses näha
    import avalik_tahvel
    DA = avalik_tahvel.Andmed(A)
    kord = _jaotis(sait["avalik-sektor.html"], "tahvel").split("Kas asutustel on tehisaru kord?")[1].split("</details>")[0]
    assert f'<span class="vt-n">{DA.k - DA.kr} / {DA.k}</span>' in kord and f'{DA.rk["aasta"]}. aastal' in kord and "võib olla muutunud" in kord
    moju = _jaotis(sait["avalik-sektor.html"], "tahvel").split("Kas uuenduste mõju mõõdetakse?")[1].split("</details>")[0]
    assert "hindamistest" in moju.split("</summary>")[0] and "koondhinnang, mitte osakaal" in moju


def test_hele_teema_v9(sait):
    """Kadri 26.11.2026: valge hele teema oli „paper clean“; laborist valis ta V9 („Let's apply version 9 for now“)."""
    css = (JUUR / "sait" / "stiil.css").read_text(encoding="utf-8")
    hele = re.search(r':root\[data-seire-teema="soft"\] \{([^}]*)\}', css).group(1)
    t = dict(re.findall(r"--([\w-]+):\s*(#[0-9a-fA-F]{6})", hele))
    # sinine on V4 (#1c3faa) ja endise (#0030de) vahel; leht ei ole enam puhas valge
    assert t["signal"] == "#0f39c2" and t["mark-signal"] == "#0f39c2" and t["page"] == "#f5f7fb"
    assert t["panel"] == "#ffffff" and t["ink"] == "#0f1a38"
    # tekst, abitekst ja sinine on lehe ja kasti taustal loetavad, graafikute hall vähemalt 3:1
    for taust in ("page", "surface-2", "brand-soft"):
        assert _kontrast(t["ink-3"], t[taust]) >= 4.5 and _kontrast(t["signal"], t[taust]) >= 4.5, taust
    assert _kontrast(t["mark-ctx"], t["page"]) >= 3
    # kaardi skaala lõpeb sama sinisega; tume teema jääb endiseks
    assert "--k4: #0f39c2" in css
    tume = re.search(r':root\[data-seire-teema="dark"\] \{([^}]*)\}', css).group(1)
    assert "--signal: #9fb0f5" in tume and "--page: #1f2023" in tume


def test_andmestiku_margendid(sait, A):
    """Kadri 27.11.2026 (nähtavus otsingus, punkt 2): teemalehtedel schema.org Dataset, avalehel DataCatalog.
    Iga kataloogi näitaja on mõnel lehel, märgend viitab olemasolevale ankrule ja kirjeldus vastab Google'i nõudele."""
    import margendid
    D = margendid.andmestikud(A)
    assert set(A["naitajad"]) <= set(margendid.KOHAD)
    assert len(D) >= len(A["naitajad"]) + 1  # + töötus (+ hanked, kui andmed on)
    for d in D:
        assert margendid.kirjeldus_on_piisav(d), d["name"]
        assert d["url"].startswith("https://www.tehisaruseire.ee/") and ".html" not in d["url"]
        assert re.fullmatch(r"\d{4}(-\d{2}(-\d{2})?)?/\d{4}(-\d{2}(-\d{2})?)?", d["temporalCoverage"]), d["temporalCoverage"]
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", d["dateModified"]) and d["isBasedOn"] and d["creator"]
        assert f'id="{d["_ankur"]}"' in sait[d["_fail"]]
    for f, h in sait.items():
        for m in re.findall(r'<script type="application/ld\+json">(.*?)</script>', h, re.S):
            o = json.loads(m)
            assert o["@context"] == "https://schema.org" and "_fail" not in m, f
    k = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', sait["index.html"], re.S).group(1))
    kat = next(x for x in k["@graph"] if x["@type"] == "DataCatalog")
    assert len(kat["dataset"]) == len(D)
    assert "Kadri" not in json.dumps(k, ensure_ascii=False)


def test_alamlehe_pais_pildiga(sait):
    """Kadri 27.11.2026: alamlehtedel sama pilt nagu avalehel, aga väiksemalt; „uudistele D, aga muudele A“."""
    css = (ehita.SIIN / "stiil.css").read_text(encoding="utf-8")
    a = re.search(r"html\[data-t\] main > \.pea::before \{([^}]*)\}", css).group(1)
    assert "height: 250px" in a and 'url("pilt/avaleht.jpg")' in a and "opacity: .3" in a
    assert 'main[data-teema="uudised"] > .pea::before { height: auto; bottom: 0;' in css  # D: täpselt päise ala
    assert 'main[data-teema="uudised"] > .pea::after' in css  # D: peenike joon all
    assert 'html[data-t][data-seire-teema="dark"] main > .pea::before' in css and "avaleht-tume.jpg" in css
    assert 'html[data-t][data-seire-teema="soft"] main > .pea::before { filter: none; background-color: #546ab6;' in css
    for f in ("ettekanded.html", "uritused.html", "podcastid.html", "uudised.html"):
        assert '<main id="sisu" class="wrap" data-teema="uudised">' in sait[f], f
    assert '<main id="sisu" class="wrap" data-teema="too">' in sait["too.html"]
    assert 'class="pea' not in sait["index.html"].replace('class="pea-', "")  # avalehe päis (pea-rahu) ei muutu


def test_koondajate_avatus_seos_mitte_pohjus(A, sait):
    """Kadri 26.11.2026 (valik A) ja 27.11 „kõigile jah“: koondajate kaotatud ametite tehisarule avatus (ILO 2025)
    ja „koondab ja palkab“ signaal, märgitud seoseks, mitte põhjuseks."""
    F = A["koondajad"]["firmad"]
    t = sait["too.html"]
    rida = re.search(r'<p class="ps kr-avatus">(.*?)</p>', t, re.S).group(1)
    assert "Seos, mitte põhjus" in rida and "ILO 2025" in rida and 'href="#palkamine"' in rida
    korge = [f for f, x in F.items() if (x.get("avatus") or {}).get("tase") == "kõrge"]
    sig = [f for f, x in F.items() if (x.get("koondab_ja_palkab") or {}).get("signaal")]
    for f in korge:
        assert html.escape(f) in rida, f
    # käänded: „Neljal koondajal“, mitte „Neli koondajal“; mitu firmat „otsivad“
    assert not re.search(r"\b(Kaks|Kolm|Neli|Viis|Kuus|Seitse|Kaheksa) koondaja", rida), rida
    if len([f for f in sig if f in rida]) > 1:
        assert "otsivad samal ajal" in rida
    # tabelis: igal avatusega firmal oma märge, signaal ainult signaaliga firmadel
    pal = t[t.index('id="palkamine"'):]
    pal = pal[:pal.index("</section>")]
    assert pal.count('class="pk-av"') >= len([f for f in korge if f"<b>{html.escape(f)}</b>" in pal]) > 0
    assert pal.count('class="pk-sig"') == len([f for f in sig if f"<b>{html.escape(f)}</b>" in pal])
def test_arendajate_toovahendite_leht(sait):
    """Kadri 27.11.2026: arendajate tööriistad eraldi lehel ja visualiseeritult, ka käsurea (CLI) kasutus."""
    h = sait["too-toovahendid.html"]
    for jid in ("agendid", "agendi-pr", "kasurida", "ide", "h-tv-uksikasjad"):
        assert f'id="{jid}"' in h, jid
    # Neli käsurea tööriista, igaühel oma graafik ja allikas
    for nimi in ("Claude Code", "OpenAI Codex CLI", "GitHub Copilot CLI", "Gemini CLI"):
        assert f'<h3 class="gt">{nimi}</h3>' in h, nimi
    assert h.count('href="https://www.npmjs.com/package/') == 4
    # Allalaadimisi ei esitata kasutajatena ega võrrelda tööriistade vahel
    t = tekst(h)
    assert "Allalaadimine ei ole kasutaja." in t and "ei saa tööriistu nende arvude järgi omavahel võrrelda" in t
    # Eri allikaid ei liideta: agentide graafik ainult JetBrains, arenduskeskkonnad ainult Stack Overflow
    agendid = _jaotis(h, "agendid")
    assert "JetBrains" in agendid and "stackoverflow" not in agendid
    assert "survey.stackoverflow.co" in _jaotis(h, "ide") and "jetbrains" not in _jaotis(h, "ide")
    assert "Eesti kohta eraldi numbrit ei ole" in t
    assert '<span class="alam-silt">Töö:</span>' in h


def test_toovahendite_andmetes_on_iga_rea_juures_link():
    import toovahendid
    U = toovahendid.uuring()
    assert U and all(r["url"].startswith("https://") and r["allikas"] for r in U)
    L = toovahendid.allalaadimised()
    for t in L.values():
        kuud = [k for k, _ in t["read"]]
        assert kuud == sorted(set(kuud)) and kuud[-1] < t["laaditud"][:7], t["pakett"]  # ainult täis kuud
        assert t["url"].startswith("https://")


def test_toovahendid_staazi_jargi(sait):
    """Kadri 27.11.2026: mis tööriistu kasutavad kogenud arendajad võrreldes teistega (Stack Overflow toorandmed)."""
    import toovahendid
    K = toovahendid.kogemus()
    # Kogu valim klapib Stack Overflow' avaldatud arvudega (65,9% n 17 464; Claude Code 65,5% n 12 255; VS Code 70,9%)
    assert (K[("AISelect", "Kasutab koodiassistenti või koodiagenti", "kõik")]["osa"],
            K[("AISelect", "Kasutab koodiassistenti või koodiagenti", "kõik")]["valim"]) == (65.9, 17464)
    assert K[("AICodeAgent", "Claude Code", "kõik")]["osa"] == 65.5 and K[("AICodeAgent", "Claude Code", "kõik")]["valim"] == 12255
    assert K[("DevIDE", "Visual Studio Code", "kõik")]["osa"] == 70.9
    osa = sait["too-toovahendid.html"].split('id="kogemus"')[1].split('id="ide"')[0]
    t = tekst(osa)
    assert "Staaž on aastad tööl, mitte ametinimetus" in t and "Eestist vastas 35 inimest" in t
    assert "github.com/StackExchange/Survey" in osa
