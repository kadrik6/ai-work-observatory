"""Teemavaated: Inimesed, Töö, Avalik sektor, Reeglid ja sihid (5.11.2026).

Iga vaate järjekord nagu Ettevõtetel: vastus (h1 ja kast), peamine tõend koos võrdlusega, mida see ei näita,
mida see tähendab, siis üksikasjad ja allikad. Mõõdetud number ja uuring kohtuvad küsimuse juures, mitte samal teljel.
"""
import datetime
from pathlib import Path

import andmekiht as andmed
from abi import SEESTYTLEV, ARVSONAD, a, alam_h1, kontrolli, link, jaga, pea, seotud
from andmekiht import EL, AndmeViga
from komponendid import (aastatulbad, ajajoon, allikarida, e, ei_naita, faktid, hantlid, kaart, kp, lihtribad,
                         margend, muutus, osad, pr, riik, ribad, sihiriba, tabel, vastavus)

VORDLUS = ["EE", "FI", "SE", "DK", "NO", "DE", "NL", EL]
IN, TOO, OS, DS = "inimeste-tehisaru-kasutus", "tooalane-tehisaru-kasutus", "tehisaru-oskuse-puudus", "inimeste-digioskused"
EB = "ettevotete-tehisaru-kasutus"
EUROSTAT = "https://ec.europa.eu/eurostat/databrowser/view/{}/default/table"


def _risk(A, liik, naitaja, sisaldab=""):
    for r in A["riskid"]:
        if r["liik"] == liik and r["naitaja"] == naitaja and sisaldab in r["pealkiri"]:
            return r
    raise AndmeViga(f"riskid.csv: rida puudub ({liik}, {naitaja}, {sisaldab})")


def _el_tabel(A, nid, y, pealdis):
    el = andmed.el27_aasta(A, nid, y)
    jarjest = sorted(el.values(), key=lambda v: -v["vaartus"])
    read = [[e(riik(v["geo"])), pr(v["vaartus"]) + margend(v["margend"])] for v in jarjest]
    return tabel(["Riik", f"{y}, %"], read, fookus_rida=[v["geo"] for v in jarjest].index("EE"), piir=True, pealdis=pealdis)


def _vordlus_ribad(A, nid, y, lopp, samm=10):
    """Eesti, Põhjamaad, Saksamaa, Holland ja ELi keskmine (tumehall tulp, mitte eraldi joon)."""
    vv = [andmed.leia(A, nid, g, y) for g in VORDLUS if g != EL and andmed.vali(A, nid, g, y, klass="alus")]
    return ribad(vv + [andmed.leia(A, nid, EL, y)], lopp, samm=samm)


# ---------------------------------------------------------------- Inimesed

def inimesed(A, vaade, vaated=None):
    n_in, m_in = A["naitajad"][IN], A["meta"][IN]
    ee = andmed.leia(A, IN, "EE", "uusim")
    ee25 = andmed.leia(A, IN, "EE", "uusim:alus")
    y = ee25["aasta"]
    if ee["aasta"] != y + 1 or ee["klass"] not in andmed.VORRELDAVAD:
        raise AndmeViga("Inimeste kasutuse aastane kasv eeldab kahte järjestikust võrreldavat aastat")
    kasv = ee["vaartus"] - ee25["vaartus"]
    ds, ds23 = andmed.leia(A, DS, "EE", "uusim:alus"), andmed.leia(A, DS, "EE", 2023)
    if abs(ds["vaartus"] - ds23["vaartus"]) >= 0.5:
        raise AndmeViga("Digioskused ei ole enam „paigal“: pealkiri tuleb üle vaadata")

    eu = andmed.leia(A, IN, EL, y)
    koht = andmed.koht(A, IN, "EE", y)
    el = andmed.el27_aasta(A, IN, y)
    jarjest = sorted(el.values(), key=lambda v: -v["vaartus"])
    # Statistikaameti 2026. aasta tööalane number on registris eraldi näitaja nime all (numbrid-2026.csv)
    too25 = andmed.leia(A, TOO, "EE", "uusim:alus")
    too_uued = [v for v in andmed.vali(A, TOO + "-uus", "EE") + andmed.vali(A, "inimeste-tehisaru-kasutus-too", "EE")
                if v["klass"] in andmed.VORRELDAVAD and v["aasta"] > too25["aasta"]]
    too = max(too_uued, key=lambda v: v["aasta"]) if too_uued else too25
    # Kasutuse lehe pealkiri räägib ainult sellest, mis sellel lehel on (Kadri 6.11.2026 22:27, ettepanek 5)
    kontrolli(vaade, f"tööl kasutab seda {pr(too['vaartus'])}% kõigist 16–74-aastastest")

    # Aasta jooksul: 2025 Eurostat → 2026 riiklik number, ainult kataloogi järgi sama mõõdikuga riigid
    paarid = []
    for g in ["EE", "NO", "SE", "FI", "DK"]:
        uued = [v for v in andmed.vali(A, IN, g, y + 1) if v["klass"] in andmed.VORRELDAVAD]
        if uued:
            paarid.append((andmed.leia(A, IN, g, y), uued[0]))
    kasvud = ", ".join(f"{riik(v1['geo'])}s {pr(v1['vaartus'] - v0['vaartus'], 0)}" for v0, v1 in
                       sorted(paarid, key=lambda p: -(p[1]["vaartus"] - p[0]["vaartus"])))
    g_aasta = hantlid(paarid, 30, 80, 10, "%", k=1)
    se = next((v1 for v0, v1 in paarid if v1["geo"] == "SE"), None)
    # ELi järjestus (Kadri 9.11.2026): sama vaade nagu ettevõtetel. Eurostat mõõtis inimeste kasutust esimest korda
    # {y}. aastal; kui tuleb teine aasta (lae_el_jarjestus.py), muutub loend ise järjestuse muutuse graafikuks.
    from lehed_ulevaade import el_jarjestus, jarjestus
    b_in = el_jarjestus(IN, koht_praegu=koht, aasta_praegu=y, lai=(640, 130, 140), min_aastaid=2)
    if b_in:
        b_g, b_k, b_a, b_tbl, _ = b_in
        g_jrj = f'<div class="el-bump">{b_g}</div>'
        gt_jrj = f"Eesti koht ELis aastate kaupa, {b_a[0]}–{b_a[-1]}"
        gs_jrj = "Generatiivse tehisaru kasutajad, % 16–74-aastastest. Klõpsa real, et see esile tõsta."
    else:
        lopp = max(10 * -(-max(v["vaartus"] for v in el.values()) // 10), 50)
        g_jrj = jarjestus(list(el.values()), lopp, eu["vaartus"], f"EL {pr(eu['vaartus'])}")
        gt_jrj = f"ELi riigid järjestuses, {y}, % 16–74-aastastest"
        gs_jrj = (f"Eurostat mõõtis seda esimest korda {y}. aastal. Kui {y + 1}. aasta number tuleb, "
                  "näitab see graafik ka koha muutust.")
    it71 = _risk(A, "piirang", IN, "kaks eri protsenti")
    sa_m = A["moodikud"]["sa-it71"]

    usaldus = faktid([
        ("Piirang", "", f'Statistikaameti tabelis IT71 on ka internetikasutajate protsent, mis on suurem (2026: '
                        f'{pr(andmed.kataloogist(A, "sa-it71-internetikasutajad", "EE", y + 1)["vaartus"])}%). '
                        f'Siin on kõigi 16–74-aastaste protsent, sama mis Eurostatil ({a(it71["url"], "IT71")}).'),
        ("Kontrollimata", "risk", f'Kas {y + 1}. aasta küsimus on sõnastatud täpselt nagu {y}. aastal, ei ole veel '
                                  f'kontrollitud. Kood ja {y}. aasta number klapivad Eurostatiga: {pr(andmed.kataloogist(A, "sa-it71", "EE", y)["vaartus"])}% ja {pr(ee25["vaartus"], 2)}%.'),
        ("Ümardus", "", f'Rootsi {y + 1}. aasta number on täisarvuni ümardatud ja SCB veapiir on ±2 protsendipunkti '
                        f'({a(se["url"], "SCB, TAB6388")}).' if se else "Teiste riikide uued numbrid on riiklikest tabelitest."),
    ])
    sec_kasutus = f"""
<section class="jaotis" id="kasutus" aria-label="Kasutus ELis">
  <div class="ruut3 kaart-paar">
    <figure aria-labelledby="g-kasutus">
      <figcaption><span class="gt" id="g-kasutus">Tehisaru kasutanud inimesed ELi riikides, {y}, % 16–74-aastastest</span>
        <span class="gs">Generatiivse tehisaru tööriistad viimase 3 kuu jooksul, inimeste enda vastused.</span></figcaption>
      <div class="kp-sisu">{kaart(list(el.values()), (0, 10, 20, 30, 40), viide=eu["vaartus"], viite_nimi=f"EL keskmine {pr(eu['vaartus'])}%")}
      <p class="peidus">Eesti on {koht}. kohal. Eespool on {", ".join(riik(v["geo"]) for v in jarjest[:koht - 1])}.</p>
      {allikarida([("Eurostat, isoc_ai_iaiu", EUROSTAT.format("isoc_ai_iaiu"), "uuendatud " + kp(m_in["allikas_uuendas"]))])}</div>
    </figure>
    <figure aria-labelledby="g-jrj">
      <figcaption><span class="gt" id="g-jrj">{gt_jrj}</span>
        <span class="gs">{gs_jrj}</span></figcaption>
      <div class="kp-sisu">{g_jrj}
      {allikarida([("Eurostat, isoc_ai_iaiu", EUROSTAT.format("isoc_ai_iaiu"), "uuendatud " + kp(m_in["allikas_uuendas"]))])}</div>
    </figure>
  </div>
  <div class="kulg-all">
    <div class="kulg">
      {vastavus("osaliselt", f"Eurostati uusim aasta on {y}. Eesti, Norra ja Rootsi {y + 1}. aasta numbrid on riiklikest tabelitest, aga sama küsimustikuga; ELi keskmist {y + 1}. aasta kohta veel pole.")}
      <figure class="plokk" aria-labelledby="g-aasta">
        <figcaption><span class="gt" id="g-aasta">Kasv aastaga, {y} → {y + 1}, % 16–74-aastastest</span>
          <span class="gs">{y} Eurostat, {y + 1} riiklik statistikaamet. Punkte juurde: {kasvud}.</span></figcaption>
        {g_aasta}
        {allikarida([(sa_m["nimi"], sa_m["url"], kp(ee["avaldatud"]))] + [(v1["allikas"], v1["url"], "") for _, v1 in paarid if v1["geo"] != "EE"])}
      </figure>
    </div>
    {usaldus}
  </div>
  <details>
    <summary>Näita andmetabelit ja määratlust</summary>
    <div>
      <p class="gt">Kõik ELi riigid, {y}, %</p>
      {_el_tabel(A, IN, y, f"ELi riigid {y}")}
      <p class="gt">Mida see number ei näita</p>
      {ei_naita(n_in["piirangud"])}
      {allikarida([("Eurostat, isoc_ai_iaiu", m_in["url"].split("?")[0], "kontrollitud " + kp(m_in["kontrollitud"]))])}
    </div>
  </details>
</section>"""

    # Tööalane kasutus
    m_too = A["meta"][TOO]
    k_too = andmed.koht(A, TOO, "EE", y)
    eu_too = andmed.leia(A, TOO, EL, y)
    p_too = _risk(A, "piirang", TOO)
    sec_too = f"""
<section class="jaotis" id="tool" aria-labelledby="h-tool">
  <header>
    <h2 id="h-tool">Tööl kasutab tehisaru <b>{pr(too["vaartus"])}% Eesti 16–74-aastastest</b> ({too["aasta"]}); ELi skaalal oli Eesti {y}. aastal {k_too}. kohal</h2>
    <p class="alam">Protsent on kõigist 16–74-aastastest, ka töötutest, õpilastest ja pensionäridest. Töötajate seas on osakaal suurem.</p>
  </header>
  <div class="kaks">
    <figure aria-labelledby="g-tool">
      <figcaption><span class="gt" id="g-tool">Tehisaru tööalaselt kasutanud, {y}, % 16–74-aastastest</span></figcaption>
      {_vordlus_ribad(A, TOO, y, 40)}
      {allikarida([("Eurostat, isoc_ai_iaiu", EUROSTAT.format("isoc_ai_iaiu"), "uuendatud " + kp(m_too["allikas_uuendas"]))])}
    </figure>
    <div class="kulg">
      {vastavus("osaliselt", "Number näitab, kui paljud kasutasid tehisaru tööks, aga mitte seda, kui suur osa töötajatest kasutab või mida tööga tehti.")}
      <div class="plokk">
        <h3>Eestis kasvas tööalane kasutus {pr(too25["vaartus"])}%-lt {pr(too["vaartus"])}%-ni</h3>
        <div class="vahe">
          <div><span class="big s">{pr(too25["vaartus"])} → {pr(too["vaartus"])}%</span><p>Eesti, {y} → {too["aasta"]} (Eurostat → Statistikaamet, sama küsimus)</p></div>
          <div><span class="big">{pr(eu_too["vaartus"])}%</span><p>ELi keskmine, {y}</p></div>
        </div>
      </div>
      {faktid([("Piirang", "", f'{e(p_too["selgitus"])} ({a(p_too["url"], "Eurostat")})')])}
    </div>
  </div>
  <details>
    <summary>Näita andmetabelit</summary>
    <div>{_el_tabel(A, TOO, y, f"Tööalane kasutus ELi riikides {y}")}</div>
  </details>
</section>"""

    # Digioskused
    n_ds, m_ds = A["naitajad"][DS], A["meta"][DS]
    siht = A["sihid"]["el-digioskused-80"]
    eu_ds, eu_ds23 = andmed.leia(A, DS, EL, ds["aasta"]), andmed.leia(A, DS, EL, 2023)
    k_ds = andmed.koht(A, DS, "EE", ds["aasta"])
    pd = [(andmed.leia(A, DS, g, 2023), andmed.leia(A, DS, g, ds["aasta"])) for g in VORDLUS]
    p_test = _risk(A, "piirang", DS, "testil")
    p_siht = _risk(A, "piirang", DS, "ELi sihid")
    sec_digi = f"""
<section class="jaotis" id="digi" aria-labelledby="h-digi">
  <header>
    <h2 id="h-digi"><span class="kys">Kas digioskused paranevad?</span> <b>Ei, sama palju kui 2023</b> ¦ ELi 2030. aasta siht on {siht["siht"]}%</h2>
  </header>
  <div class="kaks">
    <figure aria-labelledby="g-digi">
      <figcaption><span class="gt" id="g-digi">Vähemalt baastaseme digioskused, 2023 → {ds["aasta"]}, % 16–74-aastastest</span>
        </figcaption>
      {hantlid(pd, 40, 90, 10, "%", viide=float(siht["siht"]), viite_nimi=f"ELi siht {siht['aasta']}: {siht['siht']}% (ELi kohta tervikuna)")}
      {allikarida([("Eurostat, isoc_sk_dskl_i21", EUROSTAT.format("isoc_sk_dskl_i21"), "uuendatud " + kp(m_ds["allikas_uuendas"])), ("ELi siht", siht["url"], siht["allikas"])])}
    </figure>
    <div class="kulg">
      {vastavus("osaliselt", "Number põhineb sellel, mida inimesed ütlevad end teinud olevat (e-kirjad, internetipank, tabelarvutus), mitte oskuste testil.")}
      <div class="vahe">
        <div><span class="big s">{pr(ds23["vaartus"])} → {pr(ds["vaartus"])}%</span><p>Eesti, 2023 → {ds["aasta"]}; ELi skaalal {k_ds}. koht</p></div>
        <div><span class="big">{pr(eu_ds23["vaartus"])} → {pr(eu_ds["vaartus"])}%</span><p>ELi keskmine, 2023 → {ds["aasta"]}</p></div>
      </div>
      {faktid([("Siht", "", f'{e(p_siht["selgitus"])} ({a(p_siht["url"], "Eurostat")})'),
               ("Tõlgendus", "s", "Tehisaru kasutus kasvab, üldised digioskused on paigal. Kas see on probleem, sõltub sellest, milleks tehisaru kasutatakse; seda statistika ei mõõda.")])}
    </div>
  </div>
  <details>
    <summary>Näita andmetabelit ja määratlust</summary>
    <div>
      {_el_tabel(A, DS, ds["aasta"], f"Digioskused ELi riikides {ds['aasta']}")}
      {ei_naita(n_ds["piirangud"], f'<p class="vaikne">{e(p_test["selgitus"])}</p>')}
    </div>
  </details>
</section>"""

    # „Ei oska“
    n_os, m_os = A["naitajad"][OS], A["meta"][OS]
    os_ee, os_eu = andmed.leia(A, OS, "EE", "uusim:alus"), andmed.leia(A, OS, EL, y)
    k_os = 28 - andmed.koht(A, OS, "EE", y)  # 1 = väikseim osakaal
    it72 = andmed.kataloogist(A, "sa-it72-oskus", "EE", y)
    it72_uus = andmed.kataloogist(A, "sa-it72-oskus", "EE", y + 1)
    c6 = next(l for l in A["lahknevused"] if l["kood"] == "C6")
    p_langus = _risk(A, "piirang", OS, "langus")
    vaide = _risk(A, "vaide", OS)
    sec_os = f"""
<section class="jaotis" id="ei-oska" aria-labelledby="h-ei-oska">
  <header>
    <h2 id="h-ei-oska"><span class="kys">Kui paljusid takistab oskuste puudus?</span> Oskuse puudusel jätab tehisaru kasutamata <b>{pr(os_ee["vaartus"])}% Eesti 16–74-aastastest</b> ¦ ELis {pr(os_eu["vaartus"])}% ({y})</h2>
    <p class="alam">ELi 27 riigi seas on Eestis {k_os}. väikseim osakaal. Põhjus on osaliselt see, et rohkem inimesi juba kasutab tehisaru.</p>
  </header>
  <div class="kaks">
    <figure aria-labelledby="g-ei-oska">
      <figcaption><span class="gt" id="g-ei-oska">Ei kasutanud tehisaru, sest ei osanud, {y}, % 16–74-aastastest</span>
        <span class="gs">Iga mittekasutaja on ühe põhjuse all.</span></figcaption>
      {_vordlus_ribad(A, OS, y, 12, samm=2)}
      {allikarida([("Eurostat, isoc_ai_iaiuxr", EUROSTAT.format("isoc_ai_iaiuxr"), "uuendatud " + kp(m_os["allikas_uuendas"]))])}
    </figure>
    <div class="kulg">
      {vastavus("osaliselt", f"Sama küsitluse kohta annab Statistikaamet {y}. aastaks {pr(it72['vaartus'])}%, peaaegu kolm korda rohkem kui Eurostat. Põhjus on {e(c6['staatus'])} (lahknevus C6).")}
      {faktid([
          ("Lahknevus C6", "risk", f'Statistikaameti tabelis IT72 võib üks inimene olla mitme põhjuse all, Eurostatis ühe all. Riikide võrdluseks kasuta Eurostati, Eesti muutuse jaoks ainult Statistikaameti numbreid ({a(it72["url"], "IT72")}). ' + link(vaated, "kas-tosi", "Kõik lahknevused", "lahknevused") + "."),
          ("Muutus", "", f'Statistikaameti järgi langes „puudus oskus“ {pr(it72["vaartus"])}%-lt {pr(it72_uus["vaartus"])}%-le ({y} → {y + 1}). {e(p_langus["reegel"].split(". ", 1)[1] if ". " in p_langus["reegel"] else "")}'),
          ("Väide", "risk", f'Statistikaameti uudis ütles, et tehisarust mitteteadlikke oli mittekasutajate seas 1,4%. Tegelikult on see 1,4% kõigist 16–74-aastastest, mittekasutajatest umbes 5% ({a(vaide["url"], "Statistikaamet, " + kp(vaide["kuupaev"]))}).'),
      ])}
    </div>
  </div>
  <details>
    <summary>Näita andmetabelit ja määratlust</summary>
    <div>
      {_el_tabel(A, OS, y, f"Oskuse puudus ELi riikides {y}")}
      {ei_naita(n_os["piirangud"])}
    </div>
  </details>
</section>"""

    if too["aasta"] != too25["aasta"] + 1:
        raise AndmeViga("Tööalase kasutuse muutus eeldab kahte järjestikust võrreldavat aastat")
    lead = (f"Kasutajaid on aastaga {pr(kasv / ee25['vaartus'] * 100, 0)}% rohkem, kui {ee['aasta']}. aasta küsimus on sama mis {y}. aastal; seda pole veel kontrollitud.")
    # Teemamall A (Kadri 8.11.2026, Töö järel teine teema)
    import teemamall as tm
    from lehed_ulevaade import vaite_teema
    U = A["uuringud"]
    sec_andmed = tm.andmesakid("inimesed", tm.kys("Kus on Eesti ELis?", f"{koht}. kohal {len(el)} riigi seas ({y})"),
                               f'{pr(ee25["vaartus"])}% inimestest, EL {pr(eu["vaartus"])}%. ELi võrdlus on Eurostati aasta, uusim Eesti number Statistikaameti oma; '
                               "tööalane kasutus on eraldi sakis.", [
        ("kasutus", "Kasutus ELis", sec_kasutus),
        ("tool", "Tööl", sec_too),
    ])
    lyh = lambda k: e(tm.esimene_lause(U[k]["leid"]))  # noqa: E731
    t_uuringud = tm.uuringute_plokk(vaated, [
        ("USA", f'{lyh("bick2024")} ({e(U["bick2024"]["autorid"].split(",")[0])} jt {U["bick2024"]["aasta"]})', "too", "ulesanded"),
    ], [("inimesed", "Oskused", "digi"), ("too", "Uuringud töö kohta", "maailm")])
    t_vaited = tm.vaidete_plokk(A, vaated, "inimesed", vaite_teema)
    # Kadri 11.11.2026: teemalehel ainult selle teema reegel, kõik tähtajad on Tehisaru määruse lehel
    t_reeglid = tm.reeglite_plokk(A, vaated, ["ai-keelud-kirjaoskus"])
    t_allikad = tm.allikate_plokk([
        (f"Kasutus, {ee['allikas']}", ee["url"], ee["avaldatud"], f"{ee['aasta']}, 16–74-aastased"),
        (f"Tööl, {too['allikas']}", too["url"], too["avaldatud"], f"{too['aasta']}, kõigist 16–74-aastastest"),
        ("ELi võrdlus, Eurostat isoc_ai_iaiu", EUROSTAT.format("isoc_ai_iaiu"), eu.get("avaldatud") or None, f"{y}, ELi riigid"),
    ])
    # ---- Töölaud (Kadri 14.11.2026 valis „A ja B koos“): tahvel, sada inimest, kasutus × digioskused, siis plokid kokku pandud
    import teema_tahvel as tt
    from avaleht_tahvel import el_jaotus, osariba, ribarida
    from lehed_usaldus import _raskus
    J_IN, J_TOO, J_OS, J_DS = el_jaotus(A, IN), el_jaotus(A, TOO), el_jaotus(A, OS, vaiksem_parem=True), el_jaotus(A, DS)
    if {J["y"] for J in (J_IN, J_TOO, J_OS, J_DS)} != {y} or J_IN["koht"] != koht:
        raise AndmeViga("Inimeste tahvli ELi aastad või koht ei klapi ploki „Kus on Eesti ELis?“ numbritega")
    pp = sorted(paarid, key=lambda p: -(p[1]["vaartus"] - p[0]["vaartus"]))
    teised = ", ".join(f'{riik(v1["geo"])} +{tt.p1(v1["vaartus"] - v0["vaartus"])}' for v0, v1 in pp if v1["geo"] != "EE")
    read = [
        dict(kys="Kui paljud kasutavad?", ank="kasutus", arv=f'{tt.p1(ee["vaartus"])}%', all=f'{ee["aasta"]}, 16–74-aastased',
             pilt=osariba(ee["vaartus"], 100, silt=f'{tt.p1(ee["vaartus"])}%'),
             mrk=f'{y}: {pr(ee25["vaartus"])}% (Eurostat), küsimus võib erineda; seda pole veel kontrollitud.',
             liik="mõõdetud", allikas="Statistikaamet " + ee["allikas"].split("tabel ")[-1], kuup=kp(ee["avaldatud"])),
        dict(kys="Kus on Eesti ELis?", ank="kasutus", arv=f"{koht}.", all=f'{J_IN["n"]} riigist, {y}', pilt=ribarida(J_IN),
             mrk=f'Eesti {pr(J_IN["ee"])}%, <span class="tv-lg eu"></span>EL {pr(J_IN["eu"])}%. Eurostat mõõtis seda esimest korda {y}. aastal.',
             liik="mõõdetud", allikas="Eurostat isoc_ai_iaiu", kuup=str(y)),
    ]
    if len(pp) > 1:
        read.append(dict(kys="Kas naabrid kasvavad sama kiiresti?", ank="kasutus", arv=f'+{tt.p1(kasv)} p', all=f"Eesti, {y} → {y + 1}",
                         pilt=tt.mini_hantlid(pp, riik), mrk=f"{teised}. {y} Eurostat, {y + 1} riiklik statistika; küsimuse samasus kontrollimata.",
                         liik="arvutatud", allikas="riiklikud statistikaametid", kuup=f"{y} ja {y + 1}"))
    read += [
        dict(kys="Kui paljud kasutavad tööl?", ank="tool", arv=f'{tt.p1(too["vaartus"])}%', all=f'{too["aasta"]}, kõigist 16–74-aastastest',
             pilt=ribarida(J_TOO), mrk=f'Arvus on ka töötud, õpilased ja pensionärid. ELi skaalal {J_TOO["koht"]}. koht ({y}: Eesti {pr(J_TOO["ee"])}%, EL {pr(J_TOO["eu"])}%).',
             liik="mõõdetud", allikas="Statistikaamet " + too["allikas"].split("tabel ")[-1], kuup=kp(too["avaldatud"]) if too.get("avaldatud") else str(too["aasta"])),
        dict(kys="Kas digioskused paranevad?", ank="digi", arv=f'{tt.p1(ds["vaartus"])}%', all=f'{ds["aasta"]}, vähemalt baastase',
             pilt=osariba(ds["vaartus"], 100, float(siht["siht"]), silt=f'{pr(ds["vaartus"])}%, ELi siht {siht["siht"]}%'),
             mrk=f'Ei: 2023 oli {pr(ds23["vaartus"])}%. <span class="tv-lg siht"></span>ELi siht {siht["siht"]}% ({siht["aasta"]}) on kogu ELi kohta.',
             liik="mõõdetud", allikas="Eurostat isoc_sk_dskl_i21", kuup=str(ds["aasta"])),
        dict(kys="Kui paljusid takistab oskuste puudus?", ank="ei-oska", arv=f'{pr(J_OS["ee"])}%', all=f"{y}, ei kasutanud, sest ei osanud",
             pilt=ribarida(J_OS), mrk=f'ELis {J_OS["koht"]}. väikseim, EL {pr(J_OS["eu"])}%. Statistikaamet annab {pr(it72["vaartus"])}%, sest seal võib inimesel olla mitu põhjust (lahknevus C6).',
             liik="mõõdetud", allikas="Eurostat isoc_ai_iaiuxr", kuup=str(y)),
    ]
    vv = [v for v in A["vaited"] if vaite_teema(v) == "inimesed"]
    O = {o["id"]: o for o in A["otsused"]}
    tana = datetime.date.today().isoformat()
    reeglid = [(O[i]["nimi"], (O[i]["kuupaev"] + ("-01" if O[i].get("tapsus") == "kuu" else "")) < tana) for i in ["ai-keelud-kirjaoskus"]]
    allikad = [d for d in (ee["avaldatud"], too.get("avaldatud"), eu.get("avaldatud")) if d]
    us = tt.usaldusriba(len(vv), sum(_raskus(v) == 0 for v in vv), reeglid, 3, max(allikad))
    sec_tahvel = tt.tahvel("tahvel", "Mis on inimeste seis?", f"{len(read)} küsimust, iga rida üks pilk",
                           "Iga rida on oma skaalal; eri ridade numbreid ei võrrelda. Rida viib oma plokki.", read, us)
    # Sada inimest: neli rühma samast Eurostati küsitlusest (mittekasutaja on ühe põhjuse all), seepärast tohib neid ühte pilti panna
    def ruhmad(g):
        k, t, o = (andmed.leia(A, n, g, y)["vaartus"] for n in (IN, TOO, OS))
        if t > k or k + o > 100:
            raise AndmeViga(f"Sada inimest: rühmad ei sobi kokku ({g}: {k}, {t}, {o})")
        return k, {"tool": t, "kas": k - t, "oska": o, "muu": 100 - k - o}
    k_ee, r_ee = ruhmad("EE")
    k_eu, r_eu = ruhmad(EL)
    vah = lambda nimi, k, r: (f'<figure><figcaption><span class="gt">{nimi}</span></figcaption>'  # noqa: E731
                              f'{tt.vahvel([(x, r[x]) for x in ("tool", "kas", "oska")], f"{nimi} {y}: " + ", ".join(f"{pr(r[x], 0)} {tt.VAHVLI_RUHM[x]}" for x in tt.VAHVLI_RUHM))}'
                              f'{tt.vahvli_legend(r)}</figure>')
    sec_sada = f"""
<section class="jaotis" id="sada" aria-labelledby="h-sada">
  <header>
    <h2 id="h-sada"><span class="kys">Kui sada 16–74-aastast eestlast ritta panna?</span> <b>{pr(k_ee, 0)} kasutas tehisaru, ELis {pr(k_eu, 0)}</b></h2>
    <p class="alam">Üks ruut on 1% 16–74-aastastest, {y}, Eurostat. Kõik neli rühma on samast küsitlusest, seepärast saab need ühte pilti panna. Uusim Eesti number ({ee["aasta"]}: {tt.p1(ee["vaartus"])}%) on tahvlil.</p>
  </header>
  <div class="tt-wpaar">{vah("Eesti", k_ee, r_ee)}{vah("ELi keskmine", k_eu, r_eu)}</div>
  {allikarida([("Eurostat, isoc_ai_iaiu", EUROSTAT.format("isoc_ai_iaiu"), str(y)), ("Eurostat, isoc_ai_iaiuxr", EUROSTAT.format("isoc_ai_iaiuxr"), str(y))])}
  <p class="allikas">Mittekasutaja on ühe põhjuse all. Numbrid on ümardatud, seepärast võib summa olla 99 või 101.</p>
</section>"""
    pts = [(g, J_DS["v"][g], J_IN["v"][g]) for g in J_IN["v"] if g in J_DS["v"]]
    svg_sk, kaugus = tt.hajuvus(pts, J_DS["eu"], J_IN["eu"], "vähemalt baastaseme digioskused", "kasutas tehisaru", riik,
                                {"EE", "FI", "DK", "NL", "SE", "RO", "BG", "MT", "CY", "PL", "DE"})
    # Telefonis kitsam joonis (sama andmestik), et kiri jääks loetavaks; lai on telefonis peidus ja vastupidi
    svg_tel, _ = tt.hajuvus(pts, J_DS["eu"], J_IN["eu"], "digioskused", "kasutas tehisaru", riik, {"EE", "DK", "RO"}, w=360, h=320)
    vastus_sk = ("Eestis kasutatakse tehisaru rohkem, kui digioskuste põhjal võiks oodata" if kaugus >= 2 else
                 "Eestis kasutatakse tehisaru vähem, kui digioskuste põhjal võiks oodata" if kaugus <= -2 else
                 "Eesti kasutus vastab digioskuste tasemele")
    sec_sk = f"""
<section class="jaotis" id="kasutus-oskused" aria-labelledby="h-kasutus-oskused">
  <header>
    <h2 id="h-kasutus-oskused"><span class="kys">Kas kasutus käib oskustega kaasas?</span> <b>{vastus_sk}</b></h2>
    <p class="alam">ELi {len(pts)} riiki, {y}, % 16–74-aastastest. Kaks eri mõõdikut kahel teljel; neid ei liideta. Katkendjoon on riikide üldine seos:
      Eesti on sellest {pr(abs(kaugus), 0)} punkti {"kõrgemal" if kaugus >= 0 else "madalamal"}. Eesti digioskused on {pr(J_DS["ee"])}% (EL {pr(J_DS["eu"])}%), kasutus on ELis {koht}. kohal.</p>
  </header>
  <figure class="tt-scfig"><div class="tt-sc-lai">{svg_sk}</div><div class="tt-sc-kitsas" aria-hidden="true">{svg_tel}</div></figure>
  {allikarida([("Eurostat, isoc_ai_iaiu", EUROSTAT.format("isoc_ai_iaiu"), str(y)), ("Eurostat, isoc_sk_dskl_i21", EUROSTAT.format("isoc_sk_dskl_i21"), str(y))])}
  <p class="allikas">Seos riikide vahel ei näita põhjust.</p>
</section>"""
    uks = tt.uksikasjad([
        ("andmed", "Kus on Eesti ELis?", "kaart, järjestus, kasv aastaga, tööalane kasutus", sec_andmed),
        ("digi", "Kas digioskused paranevad?", "riigid 2023 → " + str(ds["aasta"]) + ", ELi siht", lisa_sihid(A, sec_digi, "digi", *SIHI_TEEMA["inimesed"])),
        ("ei-oska", "Kui paljusid takistab oskuste puudus?", "ELi riigid, lahknevus C6", sec_os),
        ("lopp", "Uuringud, väited, reeglid ja allikad", f'{len(vv)} {"väide" if len(vv) == 1 else "väidet"} · {len(reeglid)} reegel · 3 allikat',
         tm.teema_lopp(t_uuringud, t_vaited, t_reeglid, t_allikad)),
    ])
    # Kadri 14.11.2026 („Jah, kõigil teemadel“): alamleht Oskused on selle lehe plokid; kokkupandud plokk avaneb ankrult (sait.js avaAnkur)
    return jaga(A, vaade, lead, [], [
        ("tahvel", [("tahvel", "Ülevaade")], sec_tahvel),
        ("sada", [("sada", "Sada inimest")], sec_sada),
        ("kasutus-oskused", [("kasutus-oskused", "Kasutus ja oskused")], sec_sk),
        ("uksikasjad", [("andmed", "Kus ELis?"), ("digi", "Oskused"), ("ei-oska", "Oskuste puudus"), ("t-vaited", "Väited"), ("t-allikad", "Allikad")], uks),
    ])


# ---------------------------------------------------------------- Töö

def _muutus_arv(t):
    t = t.replace("−", "-").replace("%", "").strip()
    if "…" in t:
        a0, a1 = t.split("…")
        return (float(a0), -float(a1.lstrip("-")) if a0.startswith("-") else float(a1))
    return float(t)


def _tuh(n):
    """112713 → 112 713 (kitsas tühik)"""
    return f"{n:,}".replace(",", "\u202f")


def _toend(T, meetod):
    for tase, meetodid in T["kindlus"].items():
        if meetod in meetodid:
            return {"tugev": "tugev tõend", "keskmine": "keskmine tõend", "nork": "nõrk tõend", "prognoos": "prognoos"}[tase]
    raise AndmeViga(f"Meetodil {meetod} pole tõendi tugevust (tooelu-seire/leiud.json, kindlus)")


def toendi_silt(T, u):
    """Uuringu tõendi silt; uuringu enda silt (nt „tugev andmestik, nõrk tulemus“) läheb meetodist ette."""
    return u.get("silt") or _toend(T, u["meetod"])


def _alam(T, U, uid):
    u = U[uid]
    return f'{u["kus"]} · {u["aasta"]} · {toendi_silt(T, u)}'


def too(A, vaade, vaated=None):
    T, U = A["tooelu"], A["uuringud"]
    if not T:
        raise AndmeViga("Töö vaade vajab faili tooelu-seire/leiud.json")
    tk = T["tookohad"]
    can = next(r for r in tk if r["uuring"] == "canaries2026")
    hum = U["humlum2025"]
    tulevik = T["tulevik"]
    tootus = tulevik["tootus_ee"]["read"]
    t2030 = next(r for r in tootus if r["aasta"] == 2030)
    t_tegelik = max((r for r in tootus if r["tegelik"]), key=lambda r: r["aasta"])
    rm = U[tulevik["tootus_ee"]["uuring"]]
    if "Tehisaru mõju ei ole töötuse prognoosis" not in rm["leid"]:
        raise AndmeViga("Töötuse prognoosi juures puudub märge, et tehisaru mõju ei ole eraldi arvestatud")
    kontrolli(vaade, "Eesti andmetest", "USA noortel")
    if _muutus_arv(can["muutus"]) >= 0:
        raise AndmeViga("Noorte hõive langus ei ole enam andmetes")

    # 1. Mida maailmas leiti: muutus nullist, iga rida oma uuring
    read, fookus = [], None
    for i, r in enumerate(tk):
        if r["uuring"] == "canaries2026":
            fookus = i
        read.append((r["kes"], _alam(T, U, r["uuring"]), _muutus_arv(r["muutus"]),
                     "muutust pole" if r["muutus"] == "0" else r["muutus"]))
    vast = T["vastuolud"]
    noored = next(v for v in vast if "canaries2026" in v["uuringud"])
    ch = U["challenger2026"]
    koond = tulevik["koondamise_pohjused"]
    ai_teated = next(r for r in koond["read"] if r["nimi"] == "Tehisaru")["teateid"]
    bes = U["bessen2025"]
    allikad_maailm = [(f'{U[r["uuring"]]["autorid"]} {U[r["uuring"]]["aasta"]}', U[r["uuring"]]["url"], "") for r in tk]
    sec_maailm = f"""
<section class="jaotis" id="maailm" aria-labelledby="h-maailm">
  <header>
    <h2 id="h-maailm"><span class="kys">Kas tehisaru võtab töökohti?</span> Kogu tööturul pole mõju veel näha, <b>kitsastes rühmades</b> on tööd vähem ¦ nii näitavad USA ja Taani uuringud</h2>
  </header>
  <div class="kaks">
    <figure aria-labelledby="g-maailm">
      <figcaption><span class="gt" id="g-maailm">Hõive või tööpakkumiste muutus pärast ChatGPT tulekut, %</span>
        <span class="gs">Iga rida on eri uuring, eri rühm ja eri mõõt; ridu ei saa omavahel liita. Hele riba on vahemik.</span></figcaption>
      {muutus(read, -50, 10, 10, "%", fookus=fookus)}
      {allikarida(allikad_maailm)}
    </figure>
    <div class="kulg">
      {vastavus("osaliselt", "Tõendeid on veel vähe ja peaaegu kõik on USAst, Taanist või vabakutseliste platvormidelt. Eesti kohta sellist uuringut seire ei ole leidnud.")}
      {faktid([
          ("Kas vastuolu?", "", f'{e(noored["mis"])} {e(noored["miks"])}'),
          ("Teade, mitte koondamine", "risk", f'USAs nimetati {koond["periood"]} tehisaru {_tuh(ai_teated)} koondamisteates {_tuh(koond["kokku"])}-st, umbes {pr(ai_teated / koond["kokku"] * 100, 0)}%. Need on teated, mitte tegelikud koondamised ({a(ch["url"], ch["autorid"])}).'),
          ("Varasem automatiseerimine", "", f'Hollandis kaotasid automatiseerinud firmade töötajad viie aastaga umbes 8% ühe aasta palgast. See on automatiseerimine üldiselt, mitte tehisaru ({a(bes["url"], "Bessen jt " + str(bes["aasta"]))}).'),
      ])}
    </div>
  </div>
</section>"""

    # 2. Ülesannete kiirus
    kz = T["kiirus"]
    k_read = [(r["nimi"], _alam(T, U, r["uuring"]), r["kiiremini"],
               f'{"+" if r["kiiremini"] > 0 else "−"}{pr(abs(r["kiiremini"]), 0)}%') for r in kz]
    metr_i = next(i for i, r in enumerate(kz) if r["kiiremini"] < 0)
    prog = next(v for v in vast if "metr2025" in v["uuringud"])
    bryn, noy = U["brynjolfsson2023"], U["noy2023"]
    sec_kiirus = f"""
<section class="jaotis" id="ulesanded" aria-labelledby="h-ulesanded">
  <header>
    <h2 id="h-ulesanded"><span class="kys">Kas tehisaru teeb töö kiiremaks?</span> Katsetes kuni {pr(max(r["kiiremini"] for r in kz), 0)}% kiiremini, kogenud arendajad oma projektis aga <b>{pr(abs(kz[metr_i]["kiiremini"]), 0)}% aeglasemalt</b></h2>
  </header>
  <div class="kaks">
    <figure aria-labelledby="g-ulesanded">
      <figcaption><span class="gt" id="g-ulesanded">Kui palju kiiremini tehti ülesanne tehisaruga, %</span>
        <span class="gs">Juhuslikud katsed; iga rida on eri ülesanne ja eri inimesed. Miinus tähendab aeglasemat tööd.</span></figcaption>
      {muutus(k_read, -30, 60, 10, "%", fookus=metr_i)}
      {allikarida([(f'{U[r["uuring"]]["autorid"]} {U[r["uuring"]]["aasta"]}', U[r["uuring"]]["url"], "") for r in kz])}
    </figure>
    <div class="kulg">
      {vastavus("osaliselt", "Katse näitab põhjust, aga ülesanded on kitsad. Kiirem ülesanne ei tähenda veel kiiremat tööd ega rohkem tööd tervikuna.")}
      {faktid([
          ("Miks erinevad", "", e(prog["miks"])),
          ("Kes võidab", "", f'Klienditoes lahendati tunnis 14% rohkem pöördumisi, algajad 34% rohkem, kogenud töötajate tulemus peaaegu ei muutunud ({a(bryn["url"], "Brynjolfsson jt " + str(bryn["aasta"]))}). Kirjutamisülesannetes võitsid nõrgemad töötajad rohkem ({a(noy["url"], "Noy ja Zhang " + str(noy["aasta"]))}).'),
      ])}
    </div>
  </div>
</section>"""

    # 3. Mida Eestis leiti
    ee_u = [u for u in U.values() if u["kus"] == "Eesti" and u["meetod"] != "prognoos"]
    ee_u.sort(key=lambda u: -u["aasta"])
    e_read = [[f'{a(u["url"], u["autorid"].split(" (")[0])}<small>{u["aasta"]} · {e(toendi_silt(T, u))}</small>', e(u["leid"])] for u in ee_u]
    sec_eesti = f"""
<section class="jaotis" id="eesti" aria-labelledby="h-eesti">
  <header>
    <h2 id="h-eesti"><span class="kys">Mida Eesti uuringud mõõdavad?</span> Eesti uuringud ei mõõda veel <b>mõju töökohtadele</b> ¦ need mõõdavad tootlikkust ja takistusi</h2>
    <p class="alam">Seire kogus {len(ee_u)} Eesti uuringut tehisaru ja töö kohta (prognoosid allpool eraldi). Tootlikkuse leid on {link(vaated, "ettevotted", "vaates Ettevõtted", "tootlikkus")}.</p>
  </header>
  {vastavus("ei", "Eesti kohta pole seire leidnud uuringut, mis mõõdaks tehisaru mõju töökohtadele, palkadele või töötundidele. Taani registriandmete uuring on lähim võrdlus.")}
  {tabel(["Uuring", "Mida leiti"], e_read, numbrid=[], pealdis="Eesti uuringud tehisaru ja töö kohta")}
</section>"""

    # 4. Kokkupuude ametite kaupa: kui paljude Eesti töötajate ülesandeid tehisaru puudutab (mitte mõju)
    K = A["kokkupuude"]
    ilo = U["ilo2025"]
    ilo_korge = next(r["protsent"] for r in T["avatus"]["riigid"] if r["nimi"] == "Kõrge sissetulekuga riigid")
    k_read = [("Aste 3–4", K["korge"], None),
              ("Aste 1–2", K["osa"]["1"] + K["osa"]["2"], None),
              ("Minimaalne", K["osa"]["minimaalne"], None),
              ("Ei puutu kokku", K["osa"]["ei"], None)]
    k_tabel = [[e(r["nimi"]), _tuh(r["fte"]), r["aste"]] for r in K["ametid"]]
    # Kadri 9.11.2026: „see siin vajab normaalset visuaali“ – tabel tulpdiagrammiks, aste 4 fookusvärviga, tabel klõpsu taga
    ar = sorted(K["ametid"], key=lambda r: -r["fte"])
    ar_lopp = max(r["fte"] for r in ar)
    n4 = sum(1 for r in ar if str(r["aste"]) == "4")
    ar_read = "".join(
        f'<div class="ar-r{" a4" if str(r["aste"]) == "4" else ""}"><div class="ar-t"><span class="ar-n">{e(r["nimi"])}</span>'
        f'<span class="ar-v">{_tuh(r["fte"])}<small>aste {e(str(r["aste"]))}</small></span></div>'
        f'<span class="ar-rada"><span class="ar-tulp" style="width:{r["fte"] / ar_lopp * 100:.2f}%"></span></span></div>' for r in ar)
    ametiribad = f"""<figure class="plokk ar-fig" aria-labelledby="g-ametid">
        <figcaption><span class="gt" id="g-ametid">Kõige avatumad ametid Eestis: suurim rühm on {e(ar[0]["nimi"].lower())}; <b class="ar-hl">{n4} ametit on astmes 4</b></span>
          <span class="gs">Töötajad täistööajale taandatult, 2022; ametid astmetes 3 ja 4. Sinine = aste 4, hall = aste 3.</span></figcaption>
        <div class="ar" data-piir="12">{ar_read}</div>
        <details><summary>Näita andmetabelit</summary>
        {tabel(["Amet", "Töötajaid", "Aste"], k_tabel, piir=True, pealdis="Kõige avatumad ametid Eestis, töötajad täistööajale taandatult, 2022")}
        </details>
      </figure>"""
    ee_el, el_el = K["el"]["EE"], K["el"][EL]
    can_m = can["muutus"]
    sec_kokkupuude = f"""
<section class="jaotis" id="kokkupuude" aria-labelledby="h-kokkupuude">
  <header>
    <h2 id="h-kokkupuude"><span class="kys">Kui avatud need ametid on?</span> <b>{pr(K["korge"], 0)}% töötajatest on kõige avatumates ametites</b> ¦ kokku on avatud ametites {pr(K["avatud"], 0)}%; neis puudutab generatiivne tehisaru osa ülesandeid</h2>
  </header>
  <div class="kaks">
    <figure aria-labelledby="g-kokkupuude">
      <figcaption><span class="gt" id="g-kokkupuude">Eesti töötajad ameti kokkupuute astme järgi, % (2022)</span>
        <span class="gs">Aste näitab, kui suur osa ameti ülesannetest on generatiivsele tehisarule avatud; 4 on kõige avatum. Täistööajale taandatud; {pr(K["liigitamata"])}% on ametites, mida ILO indeksis pole.</span></figcaption>
      {lihtribad(k_read, 50, 10, "%", fookus=0)}
      {allikarida([(f"ILO {ilo['aasta']}, kokkupuute indeks", ilo["url"], ""), ("Statistikaamet, tabel PA633", andmed.PA633_URL, "oktoober 2022")])}
      {ametiribad}
    </figure>
    <div class="kulg">
      {vastavus("osaliselt", "Kokkupuude ei ole mõju: indeks ei ütle, kas töö kaob, muutub või jääb samaks.")}
      {faktid([
          ("Mida uuringud näitavad", "", f'USAs on 22–25-aastaste hõive avatud ametites {e(can_m)} võrreldes vähem avatud ametitega ({a(U["canaries2026"]["url"], "Brynjolfsson jt " + str(U["canaries2026"]["aasta"]))}). Taanis ei muutunud kogu tööturul tulu ega töötunnid ({a(hum["url"], "Humlum ja Vestergaard " + str(hum["aasta"]))}). Eesti kohta sellist uuringut pole.'),
          ("ELi võrdlus", "", f'Sama ligikaudne arvutus Eurostati 2025. aasta ametirühmade järgi annab Eestile {pr(ee_el["avatud"], 0)}% ja ELile {pr(el_el["avatud"], 0)}%. See on teine andmestik ja jämedam jaotus kui graafikul, seepärast eraldi. ILO enda hinnang kõrge sissetulekuga riikidele on {pr(ilo_korge, 0)}%.'),
          ("Tõlgendus", "s", f'Kõige avatumad on kontori-, raamatupidamise ja klienditeeninduse ametid ning tarkvaraarendus. ILO hinnangul on tõenäolisem, et töö muutub, kui et see kaob ({a(ilo["url"], "ILO " + str(ilo["aasta"]))}).'),
      ])}
    </div>
  </div>
  <details>
    <summary>Kuidas astmed on arvutatud ja mida number ei kata</summary>
    <div>
      <p>ILO hindas iga ameti ülesanded skaalal 0–1: kui suure osa ülesandest saab generatiivne tehisaru ära teha. Ameti aste tuleb ülesannete keskmisest ja hajuvusest: astmes 4 on keskmine vähemalt 0,6 ja ka madalamad hinnangud on kõrged. {K["ilo_avatud_ameteid"]} ametit {K["ilo_ameteid"]}-st on astmetes 1–4. Ülesanded on kirjeldatud Poola ametiklassifikaatori järgi; Eesti ametite sisu võib erineda (<a href="{andmed.ILO_SKOORID_URL}">ILO ametite skoorid</a>, CC BY 4.0).</p>
      <p>Eesti number on {_tuh(K["kokku"])} töötaja kohta, kes on taandatud täistööajale (Statistikaameti palgastruktuuri uuring, oktoober 2022). Ettevõtjad ja FIEd ei ole sees. Väikeste ametite numbrid on osaliselt avaldamata, seepärast on ametite summa rühmade summast kuni 5% väiksem.</p>
    </div>
  </details>
</section>"""

    # 5. Kas avatud ametites on hõive muutunud teisiti? Kirjeldus, mitte põhjus
    aeg = K["aeg"]
    A0, A1 = 2022, max(aeg[("EE", "T")])
    def mu(geo, sugu, osa_):
        g = K["aeg_uhtlane"][(geo, sugu)]
        return (g[A1][osa_] / g[A0][osa_] - 1) * 100
    def mt(x):
        return f'{"+" if x >= 0 else "−"}{pr(abs(x))}%'
    ee_av, ee_mu, el_av, el_mu = mu("EE", "T", "avatud"), mu("EE", "T", "muud"), mu(EL, "T", "avatud"), mu(EL, "T", "muud")
    if not ee_av < ee_mu:
        raise AndmeViga("Pealkiri ütleb, et Eestis kasvas hõive avatud ametites vähem kui teistes; andmed seda enam ei näita")
    m_read = [("Eesti, avatud ametid", "aste 1–4", ee_av, mt(ee_av)), ("Eesti, teised ametid", "minimaalne või ei puutu", ee_mu, mt(ee_mu)),
              ("EL, avatud ametid", "aste 1–4", el_av, mt(el_av)), ("EL, teised ametid", "minimaalne või ei puutu", el_mu, mt(el_mu))]
    def osa_pr(sugu, y, osa_="avatud"):
        g = aeg[("EE", sugu)][y]
        return g[osa_] / g["kokku"] * 100
    n_k0, m_k0 = mu("EE", "F", "korge"), mu("EE", "M", "korge")
    sugu_lause = f'{A1}. aastal töötas Eestis avatud ametites {pr(osa_pr("F", A1), 0)}% naistest ja {pr(osa_pr("M", A1), 0)}% meestest. Kõige avatumates ametites (aste 3–4) vähenes naiste hõive {A0}–{A1} {pr(abs(n_k0), 0)}% ja meeste oma kasvas {pr(m_k0, 0)}%.' if n_k0 < 0 < m_k0 else f'{A1}. aastal töötas Eestis avatud ametites {pr(osa_pr("F", A1), 0)}% naistest ja {pr(osa_pr("M", A1), 0)}% meestest.'
    sec_hoive = f"""
<section class="jaotis" id="hoive" aria-labelledby="h-hoive">
  <header>
    <h2 id="h-hoive"><span class="kys">Kuidas muutus hõive avatud ametites?</span> Eestis kasvas hõive avatud ametites <b>vähem kui teistes</b> ¦ see kehtib aastate {A0}–{A1} kohta. ELis oli vastupidi</h2>
  </header>
  <div class="kaks">
    <figure aria-labelledby="g-hoive">
      <figcaption><span class="gt" id="g-hoive">Hõivatute arvu muutus {A0}–{A1}, %</span>
        <span class="gs">ChatGPT tuli {A0}. aasta lõpus. Ametirühm on jagatud ILO astmete vahel; 15–74-aastased hõivatud, ka ettevõtjad.</span></figcaption>
      {muutus(m_read, -5, 10, 5, "%", fookus=0)}
      {allikarida([("Eurostat, lfsa_egai2d", EUROSTAT.format("lfsa_egai2d"), "uuendatud 30.10.2026"), (f"ILO {ilo['aasta']}", ilo["url"], "")])}
    </figure>
    <div class="kulg">
      {vastavus("osaliselt", "See on kirjeldus, mitte põhjus. Eesti majandus oli 2023–2024 langusel ja see mõjutas harusid eri moodi. Eesti tööjõu-uuringu valim on väike: mõne tuhande inimese muutus võib olla juhuslik.")}
      {faktid([
          ("Mida jälgida", "s", "Kui see erinevus püsib ka 2026. ja 2027. aastal ning on suurem noorte seas, on see märk, mida tasub uurida registriandmetega, nagu Taanis ja USAs tehti."),
      ])}
    </div>
  </div>
  <details>
    <summary>Naised ja mehed (lisa)</summary>
    <div>
      <p>{sugu_lause}</p>
      <p>Muutus on arvutatud ainult ametirühmadest, mille arv on avaldatud mõlemal aastal. Soo kaupa on avaldamata rühmi rohkem, seepärast on see number ebakindlam kui kogu hõive oma.</p>
    </div>
  </details>
</section>"""

    # 6. Mis ees ootab
    oska = U[tulevik["eesti_ametid"]["uuring"]]
    ced = U["cedefop2026"]
    bls = tulevik["ametid"]
    bls_u = U[bls["uuring"]]
    b_read = [(r["nimi"], "", r["muutus"], f'{"+" if r["muutus"] > 0 else "−" if r["muutus"] < 0 else ""}{pr(abs(r["muutus"]))}%')
              for r in bls["read"]]
    b_fookus = next(i for i, r in enumerate(bls["read"]) if r.get("kokku"))
    kasvab = "".join(f"<li>{e(x)}</li>" for x in tulevik["eesti_ametid"]["kasvab"])
    kahaneb = "".join(f"<li>{e(x)}</li>" for x in tulevik["eesti_ametid"]["kahaneb"])
    sec_tulevik = f"""
<section class="jaotis" id="tulevik" aria-labelledby="h-tulevik">
  <header>
    <h2 id="h-tulevik">Eesti töötus langeb prognoosi järgi 2030. aastaks <b>umbes {pr(t2030["protsent"], 0)}%-ni</b>, aga prognoos ei arvesta tehisaru mõju eraldi</h2>
  </header>
  <div class="kaks">
    <figure aria-labelledby="g-tulevik">
      <figcaption><span class="gt" id="g-tulevik">Töötuse määr Eestis, {t_tegelik["aasta"]}–2030, %</span>
        <span class="gs">{t_tegelik["aasta"]} on tegelik, edasi prognoos (hele tulp).</span></figcaption>
      {aastatulbad([(r["aasta"], r["protsent"], r["tegelik"]) for r in tootus], 10, 2)}
      {allikarida([(rm["pealkiri"], rm["url"], kp(rm["avaldatud"]))])}
    </figure>
    <div class="kulg">
      {vastavus("ei", "Ükski Eesti ametlik prognoos ei ütle eraldi, kui palju töökohti tehisaru tõttu kaob või tekib.")}
      <div class="plokk">
        <h3>OSKA prognoos: kus töökohti lisandub ja kus väheneb</h3>
        <div class="kaks vordne tihe">
          <div><p class="gt">Kasvab</p><ul class="loend">{kasvab}</ul></div>
          <div><p class="gt">Väheneb</p><ul class="loend">{kahaneb}</ul></div>
        </div>
        <p class="allikas">Allikas: {a(oska["url"], oska["pealkiri"])} ({kp(oska["avaldatud"])}). Prognoos on tehtud enne generatiivse tehisaru laia levikut.</p>
      </div>
      {faktid([("EL", "", f'{e(ced["leid"])} ({a(ced["url"], "Cedefop " + str(ced["aasta"]))})')])}
    </div>
  </div>
  <details>
    <summary>Näita USA prognoosi ametite kaupa</summary>
    <div>
      <p class="gt">Töökohtade muutus USAs {bls["yhik"]}</p>
      {muutus(b_read, -10, 15, 5, "%", fookus=b_fookus)}
      <p>{e(bls_u["leid"])}</p>
      {allikarida([(bls_u["autorid"], bls_u["url"], kp(bls_u["avaldatud"]))])}
    </div>
  </details>
</section>"""

    # Numbriplaadid too-* läksid 17.11.2026 ära: leht algab tahvliga (Kadri valis näidistest „A ja C koos“)
    lead = ("Mõnes ametis on vähenenud ka vabakutseliste tööd. "
            "Eesti kohta selliseid mõõtmisi veel ei ole.")
    from lehed_ulevaade import too_eesti, tootus_el, vabad_ametikohad
    from lehed_uudised import _arv, ai_kuulutused, palkamine, toopakkumised, uuringud_too
    sec_uuritakse = uuringud_too(A)
    sec_palk = palkamine(A)
    # Teemamall A (Kadri 8.11.2026): number → graafik sakkides → uuringud → väited → reeglid → allikad.
    import teemamall as tm
    from komponendid import KUUD
    from lehed_ulevaade import PAV_URL, UNE_URL, UNE_UUENDATUD, _loe, _kv, vaite_teema
    # Kadri 11.11.2026: koondamised olid liiga suure fookuse all; neid uudiseid on harva ja muu pole vähem tähtis.
    # Töötus, vabad kohad ja kuulutused on eespool; koondamised ja „Keda koondajad otsivad“ on ühes sakis prognoosi ees.
    sec_tootus, sec_koond = too_eesti(A)
    sec_andmed = tm.andmesakid("too", tm.kys("Mida näitavad Eesti tööturu andmed?", "Kas põhjus on tehisaru, kuunumbrid veel ei ütle"),
                               "Iga sakk on üks andmestik: töötus, vabad kohad, tööpakkumised, koondamised ja prognoos. "
                               "Põhjuse kohta on uuringud allpool.", [
        ("tootus", "Töötus", sec_tootus),
        ("tootus-el", "Töötus ELis", tootus_el()),
        ("vabad", "Vabad kohad", vabad_ametikohad()),
        ("portaalid", "Tööportaalid", toopakkumised(A)),
        ("ai-tood", "Tehisaru- ja andmetööd", ai_kuulutused(A)),
        ("koondamised", "Koondamised", sec_koond + sec_palk),
        ("prognoos", "Prognoos", sec_tulevik),
    ])
    t_uuringud = ""  # Kadri 11.11.2026: uuringud on ühes kohas, alamlehel Töö › Uuringud (teine rida)
    t_vaited = tm.vaidete_plokk(A, vaated, "too", vaite_teema)
    t_reeglid = tm.reeglite_plokk(A, vaated, ["ai-korge-risk-iii"])  # värbamine ja töötajate juhtimine
    vabad = [r for r in _loe("vabad-ametikohad.csv") if r["tabel"] == "PAV011"] if (Path(__file__).resolve().parent / "sisu" / "vabad-ametikohad.csv").exists() else []
    kv_v = max((r["periood"] for r in vabad), key=_kv) if vabad else None
    allikad = [
        ("Töötus kuu kaupa, Eurostat une_rt_m", UNE_URL, UNE_UUENDATUD, "sesoonselt tasandatud"),
        ("Koondamised, uudised", "", max(r["kuupaev"] for r in A["koondamised"]["juhtumid"]), "viimane teade; uudistest kogutud, nimekiri pole täielik"),
        ("Tööpakkumised, 3 portaali", "", A["toopakkumised"]["uuendatud"][:10], "kogutakse iga päev"),
        ("AI- ja andmetööde kuulutused, CV.ee", "https://www.cv.ee/et/search", A["ai_kuulutused"]["uuendatud"][:10], "kogutakse iga päev"),
        *([("Vabad ametikohad, Statistikaamet PAV011", PAV_URL, max(r["uuendatud"] for r in vabad), f"viimane kvartal: {kv_v}")] if vabad else []),
        ("Töötuse prognoos, Rahandusministeerium", rm["url"], rm["avaldatud"], "aasta keskmine, tehisaru mõju eraldi ei arvestata",
         f'{KUUD[int(rm["avaldatud"][5:7]) - 1]} {rm["avaldatud"][:4]}' if len(rm["avaldatud"]) == 7 else None),
    ]
    t_allikad = tm.allikate_plokk(allikad)
    P = A.get("publikatsioonid")
    if P:
        tais = [r for r in P["aastad"] if not r["poolik"]]
        p1 = tais[-1]
        p0 = next(r for r in tais if r["aasta"] == p1["aasta"] - 2)
        alam_h1(vaade, "too-kirjandus.html",
                f'Tehisarust ja tööst ilmus {p1["aasta"]}. aastal **{_arv(p1["koik"])} publikatsiooni** ¦ see on '
                f'{pr(p1["koik"] / p0["koik"])} korda rohkem kui {p0["aasta"]}. aastal.')
    # Töölaud (Kadri 17.11.2026 valis näidistest „A ja C koos“): tahvel, tõendikaart, hõive avatuse astme järgi,
    # siis praegused plokid kokkupandult. Kirjandus jääb kataloogina eraldi alamleheks (Kadri 14.11.2026).
    import teema_tahvel as tt
    import too_tahvel
    D = too_tahvel.Andmed(A)
    vv = [v for v in A["vaited"] if vaite_teema(v) == "too"]
    uusim = max(str(r[2])[:10] for r in allikad if r[2])
    uks = tt.uksikasjad([
        ("andmed", "Mida näitavad Eesti tööturu andmed?", "töötus, ELi järjestus, vabad kohad, tööportaalid, AI-tööd, koondamised, prognoos", sec_andmed),
        ("maailm", "Mida uuringud mujal leidsid?", "töökohad ja ülesannete kiirus", sec_maailm + sec_kiirus),
        ("eesti", "Mida Eesti uuringud mõõdavad?", "tootlikkus ja takistused", sec_eesti),
        ("ametid", "Kui avatud on Eesti ametid?", "ILO astmed, ametid, hõive muutus", sec_kokkupuude + sec_hoive),
        ("lopp", "Väited, reeglid ja allikad", f'{len(vv)} {"väide" if len(vv) == 1 else "väidet"} · 1 reegel · {len(allikad)} allikat',
         tm.teema_lopp(t_uuringud, t_vaited, t_reeglid, t_allikad)),
    ])
    return jaga(A, vaade, lead, [], [
        ("tahvel", [("tahvel", "Ülevaade")], too_tahvel.tahvel(D, vv, len(allikad), uusim)),
        ("toendid", [("toendid", "Kus on tõendeid?")], too_tahvel.sec_toendid(D)),
        ("astmed", [("astmed", "Avatud ametid")], too_tahvel.sec_astmed(D)),
        ("uksikasjad", [("andmed", "Tööturg"), ("maailm", "Uuringud"), ("t-vaited", "Väited"), ("t-allikad", "Allikad")], uks),
        ("uuritakse", [("uuritakse", "Mida uuritakse"), ("publikatsioonid", "Publikatsioonid"), ("eesti-allikad", "Eesti allikad")], sec_uuritakse),
    ])


# ---------------------------------------------------------------- Avalik sektor

OECD_URL = "https://doi.org/10.1787/c2c09a06-en"
OECD_NIMI = "OECD (2026), Strengthening the Innovative Capacity of the Public Sector of Estonia"


def _o(A, i):
    return A["avalik"][i]


def avalik_sektor(A, vaade, vaated=None):
    v = lambda i: float(_o(A, i)["vaartus"])  # noqa: E731
    # h1 (Kadri otsus 6.11.2026): „iga neljas“ = 25–30% innovaatoritest, „kolmandik“ = 30–36% laiendatakse
    kontrolli(vaade, "Iga neljas", "generatiivset tehisaru", "kolmandik")
    if not all(25 <= v(k) <= 30 for k in ("genai-kesk", "genai-kov")) or not 30 <= v("laiendati") <= 36:
        raise AndmeViga("Avaliku sektori h1 („iga neljas“, „kolmandik“) ei klapi enam OECD numbritega")
    gk, gl = _o(A, "genai-kesk"), _o(A, "genai-kov")
    if round(int(gk["lugeja"]) / int(gk["nimetaja"]) * 100) != int(gk["vaartus"]):
        raise AndmeViga("OECD 28% ei klapi arvudega 48/170")
    kl = [_o(A, k) for k in ("klaster-eesliin", "klaster-enamus", "klaster-vaikesed")]
    kokku = sum(int(k["vaartus"]) for k in kl)
    if any(int(k["nimetaja"]) != kokku for k in kl):
        raise AndmeViga("OECD rühmade summa ei ole 73")
    allikas = allikarida([(OECD_NIMI, OECD_URL, "avaldatud 3.11.2026, CC BY 4.0")])

    sec_lehter = f"""
<section class="jaotis" id="lehter" aria-labelledby="h-lehter">
  <header>
    <h2 id="h-lehter">Rakendamiseni jõuab {pr(v("rakendati"), 0)}%, <b>laiendatakse {pr(v("laiendati"), 0)}%</b> ¦ arvestatud on olulisimad uuendused</h2>
    <p class="alam">Avalikud teenistujad ja asutuste juhid nimetasid oma olulisima uuenduse ja etapi, kuhu see jõudis. Küsitlus oli detsember 2025 kuni veebruar 2026.</p>
  </header>
  <div class="kaks">
    <figure aria-labelledby="g-lehter">
      <figcaption><span class="gt" id="g-lehter">Kuhu olulisimad uuendused jõudsid, % uuendustest</span>
        <span class="gs">Avalik sektor kokku, keskvalitsus ja omavalitsused.</span></figcaption>
      {lihtribad([("Jõudis rakendamiseni", v("rakendati"), None), ("Laiendati", v("laiendati"), None)], 100, 25, "%", fookus=1)}
      {allikas}
    </figure>
    <div class="kulg">
      {vastavus("osaliselt", "Need on vastajate olulisimad uuendused, mitte kõik uuendused. Tehisaru projekte eraldi ei loendata.")}
      {faktid([
          ("Hindamine", "risk", e(_o(A, "hindamine-vfm-juhid")["markus"])),
          ("Uuendajad", "", f'Viimase 24 kuu jooksul tegi uuenduse {pr(v("uuendajad"), 0)}% vastanud avalikest teenistujatest. {e(_o(A, "uuendajad")["markus"])}'),
          ("Kes vastas", "", f'{int(v("vastajad-tootajad"))} teenistujat ja {int(v("vastajad-juhid"))} asutuse juhti vastasid täielikult. {e(_o(A, "vastajad-tootajad")["markus"])}'),
      ])}
    </div>
  </div>
</section>"""

    sec_genai = f"""
<section class="jaotis" id="tehisaru" aria-labelledby="h-tehisaru">
  <header>
    <h2 id="h-tehisaru">Generatiivset tehisaru kasutas oma uuenduses <b>{gk["vaartus"]}% keskvalitsuse</b> ja {gl["vaartus"]}% omavalitsuste innovaatoritest</h2>
  </header>
  <div class="kaks">
    <figure aria-labelledby="g-tehisaru">
      <figcaption><span class="gt" id="g-tehisaru">Innovaatorid, kelle uuendus kasutas generatiivset tehisaru, %</span>
        <span class="gs">Sulgudes vastajate arv.</span></figcaption>
      {lihtribad([("Keskvalitsus", float(gk["vaartus"]), f'{gk["vaartus"]}% ({gk["lugeja"]}/{gk["nimetaja"]})'),
                  ("Omavalitsused", float(gl["vaartus"]), f'{gl["vaartus"]}% ({gl["lugeja"]}/{gl["nimetaja"]})')], 50, 10, "%", fookus=0)}
      {allikarida([("OECD (2026)", OECD_URL, gk["koht"])])}
    </figure>
    <div class="kulg">
      {vastavus("osaliselt", f"{e(gk['markus'])} Riiklikku tehisaru kasutuse näitajat avalikus sektoris avalikus statistikas veel ei ole.")}
      {faktid([
          ("Oskused", "", "Alla 40-aastased hindavad oma tehisaru kirjaoskust kõrgemaks, üle 60-aastased madalamaks. Juhid on enesekindlamad kui spetsialistid, aga mitte selles, kuidas tehisaru asutuses tööle panna."),
          ("Takistused", "", "Andmete küpsus, arvutustaristu ja eesti keel tehisarumudelites; pilootprojektid jäävad sageli üksikuks katseks."),
      ])}
    </div>
  </div>
</section>"""

    # Etapid ja hindamismeetodid on teekonna joonisel tahvli all (avalik_tahvel.sec_teekond, Kadri 17.11.2026 „A ja C koos“)
    liigid = [("Olemasoleva parandamine", "liik-parandus"), ("Kohanemine muutustega", "liik-kohanemine"),
              ("Missioonipõhine", "liik-missioon"), ("Tulevikku ennetav", "liik-ennetav"), ("Muu", "liik-muu")]
    if not 60 <= v("liik-parandus") <= 70:
        raise AndmeViga("OECD uuenduse liigid: „kaks kolmandikku“ ei klapi enam")
    mootmed = [("Eesmärk", "eesmark"), ("Potentsiaal", "potentsiaal"), ("Võimekus", "voimekus"), ("Mõju", "moju")]
    ix = lambda m, k: f'{_o(A, f"indeks-{m}-{k}")["vaartus"].replace(".", ",")}'  # noqa: E731
    if max(v(f"indeks-moju-max"), 0) >= min(v(f"indeks-{m}-min") for _, m in mootmed[:3]):
        raise AndmeViga("OECD indeks: mõju ei ole enam kõigist teistest mõõtmetest madalam")
    m_read = [[f'<b>{n}</b><small>{e(_o(A, f"indeks-{m}-min")["markus"].split(". ")[0].rstrip("."))}.</small>', f"{ix(m, 'min')}–{ix(m, 'max')}"] for n, m in mootmed]
    sec_liigid = f"""
<section class="jaotis" id="liigid" aria-labelledby="h-liigid">
  <header>
    <h2 id="h-liigid">Kaks kolmandikku uuendustest parandab olemasolevat, <b>tulevikku ennetavaid on {pr(v("liik-ennetav"), 0)}%</b></h2>
    <p class="alam">Uuendajate osakaal uuenduse liigi järgi. Üks uuendus võib kuuluda mitmesse liiki, seega osad ei liitu 100%-ni.</p>
  </header>
  <div class="kaks">
    <figure aria-labelledby="g-liigid">
      <figcaption><span class="gt" id="g-liigid">Uuenduse liik, % uuendajatest</span></figcaption>
      {lihtribad([(n, v(k), None) for n, k in liigid], 100, 25, "%", fookus="Tulevikku ennetav")}
      {allikarida([("OECD (2026)", OECD_URL, _o(A, "liik-parandus")["koht"])])}
    </figure>
    <div class="kulg">
      {faktid([("Fakt", "", e(_o(A, "liik-parandus")["markus"].split(". ", 1)[1]))], koik_lahti=True)}
    </div>
  </div>
</section>
<section class="jaotis" id="moju" aria-labelledby="h-moju">
  <header>
    <h2 id="h-moju">Tahe ja oskused on olemas, aga uuenduste <b>mõju mõõdetakse vähe</b>: mõjuskoor on kõigis valitsemisalades {ix("moju", "min")}–{ix("moju", "max")}</h2>
    <p class="alam">OECD indeks 0–1 neljas mõõtmes, vastajate järgi valitsemisalas. Tabelis on madalaim ja kõrgeim valitsemisala.</p>
  </header>
  <div class="kaks">
    <div>{tabel(["Mõõde", "Vahemik valitsemisalade vahel"], m_read, fookus_rida=3, pealdis="OECD innovatsioonivõimekuse indeks valitsemisalade kaupa")}
      {allikarida([("OECD (2026)", OECD_URL, _o(A, "indeks-moju-min")["koht"])])}</div>
    <div class="kulg">
      {faktid([
          ("Tõlgendus · OECD", "s", "Omavalitsuste töötajad teevad uuendusi sama sageli kui keskvalitsuses, aga neil on vähem oma eelarvet ja struktuure, mis uuendusi toetaksid."),
          ("Pea meeles", "risk", e(_o(A, "indeks-moju-min")["markus"].split(". ", 1)[1])),
      ])}
    </div>
  </div>
</section>"""

    # Oskussoovid on asutuste ploki kõrval tahvli all (avalik_tahvel.sec_asutused)
    sec_kupsus = f"""
<section class="jaotis" id="kupsus" aria-labelledby="h-kupsus">
  <header>
    <h2 id="h-kupsus">OECD: enamikul asutustest <b>pole generatiivse tehisaru jaoks piisavat juhtimisraamistikku</b></h2>
    <p class="alam">Aruanne näitab asutusi joonistel 7.3 ja 7.4 ainult punktidena. Täpseid asutuste arve tekstis ei ole, seepärast neid siin ei ole.</p>
  </header>
  {faktid([
      ("Fakt · OECD", "", "Enamikul asutustest pole generatiivse tehisaru jaoks piisavat juhtimisraamistikku. Asutused peavad suurendama nii töötajate kasutusvõimekust kui ka juhtimise küpsust (OECD 2026, lk 156, joonis 7.4)."),
      ("Kuidas mõõdeti", "", "Juhtimise küpsus on asutuse juhi jah-vastuste osakaal küsimustele tehisaru poliitika, juhendi ja toe kohta. Kasutusvõimekus liidab töötajate generatiivse tehisaru kasutuse ja oskuste enesehinnangu. Joonisel on ainult asutused, kus vastas ka juht."),
      ("Tõlgendus · OECD", "", "Tehisaru kirjaoskus on OECD hinnangul generatiivse tehisaru kasutuse peamine tõukejõud kõigil valitsemistasanditel (lk 156, joonis 7.3)."),
      ("Usaldus", "risk", f'{pr(v("usaldus"), 0)}% {e(_o(A, "usaldus")["mida"])}. {e(_o(A, "usaldus")["markus"])} ({e(_o(A, "usaldus")["koht"])})'),
  ], koik_lahti=True)}
  {allikarida([("OECD (2026)", OECD_URL, "7. peatükk (lk 154–158)")])}
</section>"""

    hi = _o(A, "hanked-innovatsioon")
    hp = _o(A, "hanked-pole")
    fond = _o(A, "innovatsioonifond")
    r_read = [
        [f'<b>{pr(v("raha-el"), 0)}%</b>', e(_o(A, "raha-el")["mida"]) + f'<small>{e(_o(A, "raha-el")["markus"])}</small>', e(_o(A, "raha-el")["koht"])],
        [f'<b>{pr(v("hanked-innovatsioon"), 1)}%</b>', e(hi["mida"]) + f'<small>{e(hi["markus"])}</small>', e(hi["koht"])],
        [f'<b>{pr(v("hanked-pole"), 0)}%</b>', e(hp["mida"]) + f'<small>{e(hp["markus"])}</small>', e(hp["koht"])],
        [f'<b>{pr(v("innovatsioonifond"), 0)} mln €</b>', e(fond["mida"]), e(fond["koht"])],
    ]
    sec_raha = f"""
<section class="jaotis" id="rahastus" aria-labelledby="h-rahastus">
  <header>
    <h2 id="h-rahastus">Uuendusi rahastatakse projektidest: <b>{pr(v("raha-el"), 0)}% uuendusrahast tuli ELilt</b> ja innovatsioonihankeid tehakse vähe</h2>
    <p class="alam">Iga number loeb eri asja, seepärast on need tabelis, mitte ühel teljel.</p>
  </header>
  {tabel(["Number", "Mida see loeb", "Kus aruandes"], r_read, numbrid=[], pealdis="Avaliku sektori uuenduste rahastus")}
  {faktid([("Vastuolu aruandes", "risk", e(fond["markus"]))], koik_lahti=True)}
  {allikarida([("OECD (2026)", OECD_URL, "2. ja 6. peatükk")])}
</section>"""

    nimed = {"klaster-eesliin": ("Eestvedajad", "k-a"), "klaster-enamus": ("Piiratud enamus", "k-b"),
             "klaster-vaikesed": ("Väikesed katsetajad", "k-c")}
    o_read = [(nimed[k["id"]][0], int(k["vaartus"]), nimed[k["id"]][1],
               f'{e(k["mida"].split(" (")[0].replace("asutust on ", ""))}. {e(k["markus"])}') for k in kl]
    sec_kiirus = f"""
<section class="jaotis" id="kiirused" aria-labelledby="h-kiirused">
  <header>
    <h2 id="h-kiirused">OECD jagab {kokku} asutust kolme rühma: <b>{kl[1]["vaartus"]} kuulub rühma „piiratud enamus“</b>, {kl[0]["vaartus"]} eestvedajad ja {kl[2]["vaartus"]} väikesed katsetajad</h2>
    <p class="alam">Rühmad tulevad asutuste vastuste sarnasusest (k-keskmiste klasterdus). Iga rühm vajab OECD hinnangul eri tuge: eestvedajaid kasutada eeskujuna, väikeseid toetada ja piiratud enamusel avada võimalused.</p>
  </header>
  <figure aria-labelledby="g-kiirused">
    <figcaption><span class="gt" id="g-kiirused">Asutused OECD rühmade kaupa, asutuste arv</span></figcaption>
    {osad(o_read, f"{kokku} asutust")}
    {allikarida([("OECD (2026)", OECD_URL, kl[0]["koht"])])}
  </figure>
</section>"""

    s_read = [[str(r["nr"]), e(r["soovitus"]), e(r["kellele"])] for r in A["oecd_soovitused"]]
    sec_soov = f"""
<section class="jaotis" id="soovitused" aria-labelledby="h-soovitused">
  <header>
    <h2 id="h-soovitused">OECD soovitab tehisaru kasutuseks avalikus sektoris <b>{ARVSONAD[len(s_read)]} sammu</b>: juhtimine, oskused, rahastus ja hindamine</h2>
    <p class="alam">See on OECD soovitus, mitte seire hinnang. Kõik soovitused on raporti 7. peatükis.</p>
  </header>
  {tabel(["Nr", "OECD soovitus", "Kellele"], s_read, numbrid=[], pealdis="OECD tehisaru soovitused")}
  {allikarida([("OECD (2026)", OECD_URL, "7. peatükk")])}
</section>"""

    lead = "Kõik numbrid: OECD avalik raport (2026), küsitlus 2025–2026, ja Riigikontrolli asutuste küsitlus (2025)."
    # Numbriplaadid uuendus, laiendus ja genai läksid 17.11.2026 ära: leht algab tahvliga (Kadri valis näidistest „A ja C koos“)
    # Hanked on oma menüükoht; lehtede vahel on rida „Seotud“ (Kadri 6.11.2026 22:27, ettepanek 8)
    # Teemamall A (Kadri 8.11.2026): andmed sakkides, siis uuringud, väited, reeglid, allikad
    import teemamall as tm
    from lehed_ulevaade import vaite_teema
    U = A["uuringud"]
    sec_andmed = tm.andmesakid("avalik-sektor", tm.kys("Kus uuendused pidama jäävad?", "Hindamise ja otsuse ees"),
                               "Kõik numbrid on OECD avalikust raportist (2026), küsitlus detsember 2025 kuni veebruar 2026. "
                               "Sakkides on rakendamine, uuenduse liik, tehisaru, rahastus, asutuste rühmad ja OECD soovitused.", [
        ("lehter", "Rakendamine", sec_lehter),
        ("liigid", "Uuenduse liik ja mõju", sec_liigid),
        ("tehisaru", "Tehisaru", sec_genai + sec_kupsus),
        ("rahastus", "Rahastus", sec_raha),
        ("kiirused", "Kolm rühma", sec_kiirus),
        ("soovitused", "Soovitused", sec_soov),
    ])
    t_uuringud = tm.uuringute_plokk(vaated, [
        ("Eesti", "Alla 40-aastased hindavad oma tehisaru kirjaoskust kõrgemaks; juhid on enesekindlamad, aga mitte selles, kuidas tehisaru asutuses tööle panna (OECD 2026).", "avalik-sektor", "tehisaru"),
        ("Suurbritannia", f'{e(tm.esimene_lause(U["gds2025"]["leid"]))} (GDS {U["gds2025"]["aasta"]})', "too", "ulesanded"),
    ], [("hanked", "Hanked: mida riik ostab", "")])
    t_vaited = tm.vaidete_plokk(A, vaated, "avalik-sektor", vaite_teema)
    t_reeglid = tm.reeglite_plokk(A, vaated, ["ai-korge-risk-iii"])  # otsused avaliku teenuse saamise kohta
    rk = A["leiud"].get("rk-ai-kord")
    t_allikad = tm.allikate_plokk([
        (OECD_NIMI, OECD_URL, "2026-11-03", "CC BY 4.0; küsitlus 12.2025–02.2026"),
    ] + ([("Asutuste tehisaru kord, Riigikontroll", rk["url"], rk["avaldatud"], "2025, küsitlusele vastanud 48 asutust")] if rk else []))
    # Ametnike juhendid ja Riigikontrolli küsitlus tulid Ettevõtete lehelt (Kadri 14.11.2026: plokk oma küsimuse juurde)
    from lehed import ametnike_juhendid
    sec_ametnikud = ametnike_juhendid(A)
    # Töölaud (Kadri 17.11.2026 valis näidistest „A ja C koos“): tahvel, uuenduse teekond, 48 asutust, siis plokid kokkupandult.
    import avalik_tahvel as at
    import teema_tahvel as tt
    from lehed_usaldus import _raskus
    D = at.Andmed(A)
    vv = [x for x in A["vaited"] if vaite_teema(x) == "avalik-sektor"]
    kr3 = next(r for r in A["otsused"] if r["id"] == "ai-korge-risk-iii")
    n_all = 1 + (1 if rk else 0)
    uusim = max(["2026-11-03"] + ([rk["avaldatud"]] if rk else []))
    us = at.usaldus(len(vv), sum(_raskus(x) == 0 for x in vv), [(kr3["nimi"], kr3["kuupaev"] <= datetime.date.today().isoformat())], n_all, uusim)
    uks = tt.uksikasjad([
        ("andmed", "Kus uuendused pidama jäävad?", "rakendamine, uuenduse liik ja mõju, tehisaru, rahastus, kolm rühma, OECD soovitused", sec_andmed),
        ("ametnikud", "Mida ametnikud tohivad kasutada?", "neli riiki, Riigikontrolli küsitlus", sec_ametnikud),
        ("lopp", "Uuringud, reeglid ja allikad", f'2 uuringut · 1 reegel · {n_all} allikat', tm.teema_lopp(t_uuringud, t_vaited, t_reeglid, t_allikad)),
    ])
    # „Seotud“ rida jäi ära: Riigi alamlehtede rida viib samadele lehtedele (Kadri 11.11.2026, D)
    return jaga(A, vaade, lead, [], [
        ("tahvel", [("tahvel", "Ülevaade")], at.tahvel(D, us)),
        ("teekond", [("teekond", "Kus pidama jääb?")], at.sec_teekond(D)),
        ("asutused", [("asutused", "Asutuste kord")], at.sec_asutused(D)),
        ("uksikasjad", [("andmed", "Andmed"), ("ametnikud", "Ametnikud"), ("t-allikad", "Allikad")], uks),
    ])


# ---------------------------------------------------------------- Reeglid ja sihid

def _kp_otsus(r):
    if r["tapsus"] == "kuu":
        return kp(r["kuupaev"])
    return kp(r["kuupaev"])


def reeglid(A, vaade, vaated=None, tana=None):
    tana = tana or datetime.date.today().isoformat()
    O = A["otsused"]
    uld = next(r for r in O if r["id"] == "ai-uldkohaldamine")
    kr = next(r for r in O if r["id"] == "ai-korge-risk-iii")
    kontrolli(vaade, kp(uld["kuupaev"]), kp(kr["kuupaev"]))
    sundmused = [(r["kuupaev"] + ("-01" if r["tapsus"] == "kuu" else ""), _kp_otsus(r), r["nimi"],
                  f'{e(r["mida_tahendab"])}', r["kelle_jaoks"]) for r in O]
    moodas = [s for s in sundmused if s[0] < tana]
    ees = [s for s in sundmused if s[0] >= tana]
    jargmine = ees[0] if ees else None
    kontroll = max(r["kontrollitud"] for r in O)
    sec_aeg = f"""
<section class="jaotis" id="tahtajad" aria-labelledby="h-tahtajad">
  <header>
    <h2 id="h-tahtajad"><span class="kys">Millal määruse reeglid jõustuvad?</span> Tehisaru määruse {SEESTYTLEV.get(len(O), str(len(O)))} tähtajast <b>{ARVSONAD.get(len(moodas), str(len(moodas)))} on möödas</b>, {ARVSONAD.get(len(ees), str(len(ees)))} on veel ees</h2>
    {vastavus("jah", f"Määruse ametlik nimi on tehisintellekti määrus (EL) 2024/1689, siin nimetame seda lühidalt tehisaru määruseks. Tähtajad on kontrollitud Euroopa Komisjoni määruse lehelt {kp(kontroll)}.")}
  </header>
  <div class="kaks vordne">
    <div>
      <h3 class="veerg">Kehtib ({len(moodas)})</h3>
      {ajajoon(moodas, tana)}
    </div>
    <div>
      <h3 class="veerg">Ees ({len(ees)})</h3>
      {ajajoon(ees, tana)}
    </div>
  </div>
  {allikarida([(O[0]["allikas"], O[0]["url"], "kontrollitud " + kp(kontroll))])}
</section>"""

    from lehed_ulevaade import kpi_pais, kpi_plaat, kpi_riba
    def _kuud(kuup):
        if kuup < tana:
            return "kehtib juba"
        d0, d1 = datetime.date.fromisoformat(tana), datetime.date.fromisoformat(kuup)
        k = (d1.year - d0.year) * 12 + d1.month - d0.month
        return "sel kuul" if k <= 0 else f"{k} kuu pärast"
    pl1 = jargmine or moodas[-1]  # kui kõik tähtajad on möödas, näitab esimene plaat viimast
    aside = kpi_pais(
        kpi_plaat("ma-jargmine", "Järgmine tähtaeg" if jargmine else "Viimane tähtaeg", pl1[1], "",
                  {"muutus": (_kuud(pl1[0]), ""), "tekst": e(pl1[2])},
                  a(O[0]["url"], "Euroopa Komisjon"), fookus=True),
        kpi_plaat("ma-korge", "Suure riskiga kasutus", kp(kr["kuupaev"]), "",
                  {"muutus": (_kuud(kr["kuupaev"]), ""), "tekst": "nt <b>CVde sorteerimine</b>, hindamine koolis"},
                  a(kr["url"], "Euroopa Komisjon")),
        kpi_plaat("ma-osad", "Tähtajad 2024–2028", f"{len(moodas)}", f"/ {len(O)} möödas",
                  {"muutus": (f"{len(ees)} on veel ees", f"kehtib alates {kp(uld['kuupaev'])}"),
                   "riba": kpi_riba(len(moodas), len(O))},
                  a(uld["url"], "Euroopa Komisjon")),
    )
    j_tekst = f'Järgmine tähtaeg on {jargmine[1]}: {e(jargmine[2].lower())}.' if jargmine else ""
    lead = j_tekst
    sec_ee = eesti_otsused(A, vaade, vaated, tana)
    sec_st = riikide_strateegiad(A, vaade)
    # Kadri 14.11.2026 („Jah, kõigil teemadel“): Eesti otsused ja riikide strateegiad on selle lehe plokid.
    return jaga(A, vaade, lead, [], [
        ("tahtajad", [("tahtajad", "ELi tähtajad")], sec_aeg),
        ("eesti", [("eesti-otsused", "Eesti otsused")], sec_ee),
        ("strateegiad", [("strateegiad", "Teiste riikide sihid")], sec_st),
    ], aside=aside)


SIHI_JARJEKORD = ("kasutus", "oskused", "majandus", "avalik", "arvamus")  # peamised sihid: kasutus enne hoiakuid


def _sihi_rida(t):
    lk = f", lk {t['lk']}" if t.get("lk") else ""
    return f'<li><b>{e(t["vaartus"])}</b> {e(t.get("eesti") or t["siht"])} <span class="lk">({e(t.get("aasta") or "tähtajata")}{lk})</span></li>'


def riikide_strateegiad(A, vaade):
    """Teiste riikide ametlikud tehisarustrateegiad ja nende arvulised sihid (Kadri „jah kõik“ 12.11.2026, ettepanek sp-2026-11-11-1).

    Andmed: tooelu-uudised/strateegiad.json (hommikune kogumine) → sait/vota_kaasa.py → sisu/strateegiad.json.
    Sihid on riikide poliitilised eesmärgid ja mõõdetakse erinevalt: ainult tabel, ei ühist graafikut ega järjestust."""
    S = list(((A.get("strateegiad") or {}).get("strateegiad")) or [])
    if not S:
        return """
<section class="jaotis" id="strateegiad" aria-labelledby="h-strateegiad">
  <header>
    <h2 id="h-strateegiad"><span class="kys">Mida teised riigid sihivad?</span> Riikide strateegiaid pole kogumine veel siia toonud</h2>
    <p class="alam">Hommikune kogumine lisab riikide ametlikke tehisarustrateegiaid koos sihtidega algdokumendist.</p>
  </header>
</section>"""
    S.sort(key=lambda s: s.get("kuupaev") or "", reverse=True)
    read = []
    for s in S:
        sihid = sorted(s.get("sihid") or [], key=lambda t: SIHI_JARJEKORD.index(t["liik"]) if t.get("liik") in SIHI_JARJEKORD else 9)
        peamised = "".join(_sihi_rida(t) for t in sihid[:3])
        rohkem = (f'<details class="strat-koik"><summary>Veel {len(sihid) - 3} sihti</summary><ul class="strat-sihid">'
                  f'{"".join(_sihi_rida(t) for t in sihid[3:])}</ul></details>') if len(sihid) > 3 else ""
        read.append([
            f'<b>{e(s["riik"])}</b><small>{e(kp(s["kuupaev"]))}</small>',
            f'{a(s["url"], s["pealkiri"])}<small>{e(s.get("asutus", ""))}</small>',
            e(s.get("tahtaeg") or "puudub"),
            f'<ul class="strat-sihid">{peamised}</ul>{rohkem}' if peamised else "arvulisi sihte pole",
            e(s.get("markus", "")),
        ])
    ee = (A.get("sihid") or {}).get("ee-ettevotted-75")
    if ee:
        read.append([
            '<b>Eesti</b><small>võrdluseks</small>',
            f'{a(ee["url"], ee["allikas"])}<small>Vabariigi Valitsus</small>',
            e(ee["aasta"]),
            f'<ul class="strat-sihid"><li><b>{e(ee["siht"])}%</b> {e(ee["nimi"].lower())} <span class="lk">({e(ee["aasta"])})</span></li></ul>',
            e(ee.get("markus", "")),
        ])
    n = len(S)
    sihte = sum(len(s.get("sihid") or []) for s in S)
    riike = ", ".join(s["riik"] for s in S)
    uusim = max(s.get("kontrollitud") or s.get("lisatud") or "" for s in S)
    return f"""
<section class="jaotis" id="strateegiad" aria-labelledby="h-strateegiad">
  <header>
    <h2 id="h-strateegiad"><span class="kys">Mida teised riigid sihivad?</span> <b>{sihte} arvulist sihti</b> ¦ {e(riike)}</h2>
    <p class="alam">Iga rida on riigi ametlik strateegia. Sihid on võetud algdokumendist koos leheküljega. Uusim dokument on eespool.</p>
    {vastavus("osaliselt", "Riigid mõõdavad sarnaseid sihte erinevalt (riigi statistika, küsitlus või määramata). Seepärast ei ole siin ühist graafikut ega järjestust ning sihte ei võrrelda omavahel.")}
  </header>
  {tabel(["Riik", "Strateegia", "Tähtaeg", "Peamised sihid", "Kuidas mõõdetakse"], read, piir=True, numbrid=set(), pealdis="Riikide tehisarustrateegiad ja nende arvulised sihid")}
  <p class="allikas">Allikas: iga riigi strateegiadokument (link tabelis); kogumine kontrollis viimati {e(kp(uusim)) if uusim else "–"}.</p>
</section>"""


def eesti_otsused(A, vaade, vaated, tana):
    """Eesti riigi otsused, eelnõud, hanked ja tähtajad igapäevasest uudistekogumisest (teema „riik“, alates 9.11.2026).

    Kirjeid ei kanta käsitsi (Kadri 8.11.2026 23:02: kogumine peab need ise leidma)."""
    from lehed_uudised import RIIGI_LIIK, _uudis
    U = [r for r in (A.get("uudised") or []) if r.get("teema") == "riik"]
    U.sort(key=lambda r: r["kuupaev"], reverse=True)
    ees = sorted((r for r in U if r.get("tahtaeg") and r["tahtaeg"] >= tana), key=lambda r: r["tahtaeg"])
    if not U:
        return f"""
<section class="jaotis" id="eesti-otsused" aria-labelledby="h-eesti-otsused">
  <header>
    <h2 id="h-eesti-otsused"><span class="kys">Mida Eesti on otsustanud?</span> Riigi otsuseid ja tähtaegu pole kogumine veel leidnud</h2>
    <p class="alam">Kogumine otsib kaks korda päevas riigi otsuseid, eelnõusid, riigihankeid, tähtaegu, üritusi ja aruandeid. Kirjeid ei kanta siia käsitsi.</p>
  </header>
</section>"""
    loend = lambda rr: f'<ul class="u-voog" data-piir-li="12">{"".join(_uudis(r) for r in rr)}</ul>'  # noqa: E731
    liigid = {}
    for r in U:
        liigid[r.get("riigi_liik") or "muu"] = liigid.get(r.get("riigi_liik") or "muu", 0) + 1
    kokku = ", ".join(f'{n} {RIIGI_LIIK.get(k, k)}' for k, n in sorted(liigid.items(), key=lambda x: -x[1]))
    ees_html = (f'<h3 class="veerg">Ees olevad tähtajad ({len(ees)})</h3>' + loend(ees)) if ees else ""
    return f"""
<section class="jaotis" id="eesti-otsused" aria-labelledby="h-eesti-otsused">
  <header>
    <h2 id="h-eesti-otsused"><span class="kys">Mida Eesti on otsustanud?</span> Riigi otsused, eelnõud ja tähtajad: <b>{len(U)} kirjet</b> ¦ {e(kokku)}</h2>
    <p class="alam">Kirjed tulevad igapäevasest uudistekogumisest (riigi asutuste lehed ja uudisteotsing), mitte käsitsi. Iga kirje juures on algallika link.</p>
    {vastavus("osaliselt", "Kogumine leiab avalikult teatatud otsuseid. Eelnõude infosüsteemi kogumine ei loe, nii et kõik eelnõud ei pruugi siia jõuda.")}
  </header>
  {ees_html}
  <details class="kokku"><summary>Näita kõiki {len(U)} kirjet, uusimad eespool</summary>{loend(U)}</details>
  <p class="lingid">{link(vaated, "uudised", "Kõik uudised")}</p>
</section>"""


SIHI_TEEMA = {"inimesed": ("el-digioskused-80",), "ettevotted": ("ee-ettevotted-75",),
              "ettevotted-voimekus": ("el-digiintensiivsus-90", "el-ta-3")}


def siht_rida(A, sid):
    """Üks siht ühe reana näitaja enda plokis (Kadri 6.11.2026 22:27, paigutuse ettepanek 4): oma telg, sihte ei võrrelda."""
    s = A["sihid"][sid]
    nid, siht = s["naitaja"], float(s["siht"])
    ta = nid == "ta-kulud"
    u, k, lopp = ("% SKPst", 2, 4) if ta else ("%", 1, 100)
    kes = a(s["url"], s["allikas"].split(",")[0])
    if s["tase"] == "EE":
        p = andmed.leia(A, nid, "EE", "uusim")
        tekst = (f'<b>Eesti {pr(siht, 0)}{u}</b> aastaks {e(s["aasta"])} ({kes}). Praegu {pr(p["vaartus"], k)}{u} '
                 f'(Eesti {p["aasta"]}, {e(p["allikas"])}). Vahet ei arvuta: {e(s["markus"].split(". ")[0].rstrip("."))}.')
    else:
        p = andmed.leia(A, nid, EL, "uusim:alus")
        ee = andmed.leia(A, nid, "EE", p["aasta"])
        aastaks = f' aastaks {e(s["aasta"])}' if s["aasta"] else ""
        tekst = (f'<b>EL {pr(siht, 0)}{u}</b>{aastaks} ({kes}). '
                 f'EL tervikuna {pr(p["vaartus"], k)}{u}, Eesti {pr(ee["vaartus"], k)}{u} ({p["aasta"]}); ELil puudu {pr(siht - p["vaartus"], k)} protsendipunkti.')
    return (f'<div class="siht-rida"><p><span class="siht-silt">Siht</span> {tekst}</p>'
            f'{sihiriba(p["vaartus"], siht, lopp, "", fookus=(s["tase"] == "EE"))}</div>')


def lisa_sihid(A, html, jaotis, *sid):
    """Paneb sihi read jaotise lõppu (enne selle </section>)."""
    i = html.index(f'id="{jaotis}"')
    j = html.index("</section>", i)
    return html[:j] + "".join(siht_rida(A, x) for x in sid) + html[j:]


