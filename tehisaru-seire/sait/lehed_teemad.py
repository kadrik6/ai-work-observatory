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
    kontrolli(vaade, f"tööl kasutab {pr(too['vaartus'])}%")

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
        ("Ümardus", "", f'Rootsi {y + 1}. aasta number on täisarvuni ümardatud ja SCB veapiir on ±2 punkti '
                        f'({a(se["url"], "SCB, TAB6388")}).' if se else "Teiste riikide uued numbrid on riiklikest tabelitest."),
    ])
    sec_kasutus = f"""
<section class="jaotis" id="kasutus" aria-labelledby="h-kasutus">
  <header>
    <h2 id="h-kasutus">ELi skaalal oli Eesti {y}. aastal {len(el)} riigi seas <b>{koht}. kohal</b>: {pr(ee25["vaartus"])}% inimestest, EL {pr(eu["vaartus"])}%</h2>
  </header>
  <div class="ruut3">
    <figure aria-labelledby="g-kasutus">
      <figcaption><span class="gt" id="g-kasutus">Tehisaru kasutanud inimesed ELi riikides, {y}, % 16–74-aastastest</span>
        <span class="gs">Generatiivse tehisaru tööriistad viimase 3 kuu jooksul, inimeste enda vastused.</span></figcaption>
      {kaart(list(el.values()), (0, 10, 20, 30, 40), viide=eu["vaartus"], viite_nimi=f"EL keskmine {pr(eu['vaartus'])}%")}
      <p class="peidus">Eesti on {koht}. kohal. Eespool on {", ".join(riik(v["geo"]) for v in jarjest[:koht - 1])}.</p>
      {allikarida([("Eurostat, isoc_ai_iaiu", EUROSTAT.format("isoc_ai_iaiu"), "uuendatud " + kp(m_in["allikas_uuendas"]))])}
    </figure>
    <div class="kulg">
      {vastavus("osaliselt", f"Eurostati uusim aasta on {y}. Eesti, Norra ja Rootsi {y + 1}. aasta numbrid on riiklikest tabelitest, aga sama küsimustikuga; ELi keskmist {y + 1}. aasta kohta veel pole.")}
      <figure class="plokk" aria-labelledby="g-aasta">
        <figcaption><span class="gt" id="g-aasta">Kasv aastaga, {y} → {y + 1}, % 16–74-aastastest</span>
          <span class="gs">{y} Eurostat, {y + 1} riiklik statistikaamet. Punkte juurde: {kasvud}.</span></figcaption>
        {g_aasta}
        {allikarida([(sa_m["nimi"], sa_m["url"], kp(ee["avaldatud"]))] + [(v1["allikas"], v1["url"], "") for _, v1 in paarid if v1["geo"] != "EE"])}
      </figure>
      <figure class="plokk" aria-labelledby="g-jrj">
        <figcaption><span class="gt" id="g-jrj">{gt_jrj}</span>
          <span class="gs">{gs_jrj}</span></figcaption>
        {g_jrj}
        {allikarida([("Eurostat, isoc_ai_iaiu", EUROSTAT.format("isoc_ai_iaiu"), "uuendatud " + kp(m_in["allikas_uuendas"]))])}
      </figure>
      {usaldus}
    </div>
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
    <h2 id="h-digi">Vähemalt baastaseme digioskused on <b>{pr(ds["vaartus"])}% Eesti inimestest</b>, sama palju kui 2023; ELi 2030. aasta siht on {siht["siht"]}%</h2>
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
    <h2 id="h-ei-oska">Oskuse puudusel jätab tehisaru kasutamata <b>{pr(os_ee["vaartus"])}% Eesti inimestest</b>, ELis {pr(os_eu["vaartus"])}% ({y})</h2>
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

    # Päise plaadid käsitsi valitud kontekstiga (ver1 laiendus, Kadri 8.11.2026)
    from lehed_ulevaade import _p, kpi_pais, kpi_plaat, kpi_riba
    if too["aasta"] != too25["aasta"] + 1:
        raise AndmeViga("Tööalase kasutuse plaadi muutus eeldab kahte järjestikust võrreldavat aastat")
    aside = kpi_pais(
        kpi_plaat("in-kasutus", "Kasutas tehisaru (16–74)", f'{pr(ee["vaartus"])}%', str(ee["aasta"]),
                  {"muutus": (f"{_p(kasv)} punkti aastaga", f'{y}: {pr(ee25["vaartus"])}% · küsimus võib erineda'),
                   "riba": kpi_riba(ee["vaartus"], 100, fookus=True)},
                  a(ee["url"], "Statistikaamet " + ee["allikas"].split("tabel ")[-1]), fookus=True),
        kpi_plaat("in-koht", "Koht ELis", f"{koht}.", f"/ {len(el)} · {y}",
                  {"tekst": f'Eesti <b>{pr(ee25["vaartus"])}%</b>',
                   "riba": kpi_riba(ee25["vaartus"], 100, vrd=eu["vaartus"])},
                  a(EUROSTAT.format("isoc_ai_iaiu"), "Eurostat isoc_ai_iaiu")),
        kpi_plaat("in-tool", "Kasutas tehisaru tööl", f'{pr(too["vaartus"])}%', str(too["aasta"]),
                  {"muutus": (f'{_p(too["vaartus"] - too25["vaartus"])} punkti aastaga', f'{too25["aasta"]}: {pr(too25["vaartus"])}% · küsimus võib erineda'),
                   "tekst": "<b>kõigist</b> 16–74-aastastest"},
                  a(too["url"], "Statistikaamet " + too["allikas"].split("tabel ")[-1])),
    )
    lead = (f"Kasutajaid on aastaga {pr(kasv / ee25['vaartus'] * 100, 0)}% rohkem, kui {ee['aasta']}. aasta küsimus on sama mis {y}. aastal; seda pole veel kontrollitud.")
    # Teemamall A (Kadri 8.11.2026, Töö järel teine teema)
    import teemamall as tm
    from lehed_ulevaade import vaite_teema
    U = A["uuringud"]
    sec_andmed = tm.andmesakid("inimesed", "Uuri andmeid: kasutus ELis ja tööl",
                               "Iga sakk on üks andmestik. ELi võrdlus on Eurostati aasta, uusim Eesti number Statistikaameti oma.", [
        ("kasutus", "Kasutus ELis", sec_kasutus),
        ("tool", "Tööl", sec_too),
    ])
    lyh = lambda k: e(tm.esimene_lause(U[k]["leid"]))  # noqa: E731
    t_uuringud = tm.uuringute_plokk(vaated, [
        ("USA", f'{lyh("bick2024")} ({e(U["bick2024"]["autorid"].split(",")[0])} jt {U["bick2024"]["aasta"]})', "too", "ulesanded"),
        ("Suurbritannia", f'Avalikus sektoris hindasid kasutajad, et säästsid umbes 26 minutit päevas; seda, milleks aega kasutati, ei mõõdetud (GDS {U["gds2025"]["aasta"]}).', "too", "ulesanded"),
        ("Eesti", "Inimeste kasutust mõõdab Statistikaamet; uuringut selle kohta, mida kasutus inimestele annab, Eestis veel pole.", "inimesed", "tool"),
    ], [("inimesed", "Oskused", "digi"), ("too", "Uuringud töö kohta", "maailm")])
    t_vaited = tm.vaidete_plokk(A, vaated, "inimesed", vaite_teema)
    t_reeglid = tm.reeglite_plokk(A, vaated, ["ai-keelud-kirjaoskus", "ai-uldkohaldamine"])
    t_allikad = tm.allikate_plokk([
        (f"Kasutus, {ee['allikas']}", ee["url"], ee["avaldatud"], f"{ee['aasta']}, 16–74-aastased"),
        (f"Tööl, {too['allikas']}", too["url"], too["avaldatud"], f"{too['aasta']}, kõigist 16–74-aastastest"),
        ("ELi võrdlus, Eurostat isoc_ai_iaiu", EUROSTAT.format("isoc_ai_iaiu"), eu.get("avaldatud") or None, f"{y}, ELi riigid"),
    ])
    alam_h1(vaade, "inimesed-oskused.html",
            f'Vähemalt baastaseme digioskused on **{pr(ds["vaartus"])}% Eesti inimestest**, ELi {siht["aasta"]}. aasta siht on {siht["siht"]}%; '
            f'oskuse puudusel jätab tehisaru kasutamata {pr(os_ee["vaartus"])}%.')
    return jaga(A, vaade, lead, [], [
        ("andmed", [("andmed", "Andmed")], sec_andmed),
        ("teema-lopp", [("t-uuringud", "Uuringud"), ("t-vaited", "Väited"), ("t-reeglid", "Reeglid"), ("t-allikad", "Allikad")],
         tm.teema_lopp(t_uuringud, t_vaited, t_reeglid, t_allikad)),
        ("digi", [("digi", "Digioskused")], lisa_sihid(A, sec_digi, "digi", *SIHI_TEEMA["inimesed"])),
        ("ei-oska", [("ei-oska", "„Ei oska“")], sec_os),
    ], aside=aside)


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
    <h2 id="h-maailm">Kogu tööturul pole tehisaru mõju veel näha, <b>kitsastes rühmades</b> on tööd aga vähem</h2>
  </header>
  <div class="kaks">
    <figure aria-labelledby="g-maailm">
      <figcaption><span class="gt" id="g-maailm">Hõive või tööpakkumiste muutus pärast ChatGPT tulekut, %</span>
        <span class="gs">Iga rida on eri uuring, eri rühm ja eri mõõt; ridu ei saa omavahel liita. Hele riba on vahemik.</span></figcaption>
      {muutus(read, -50, 10, 10, "%", fookus=fookus)}
      {allikarida(allikad_maailm)}
    </figure>
    <div class="kulg">
      {vastavus("osaliselt", "Tõendeid on veel vähe ja peaaegu kõik on USA-st, Taanist või vabakutseliste platvormidelt. Eesti kohta sellist uuringut seire ei ole leidnud.")}
      {faktid([
          ("Kas vastuolu?", "", f'{e(noored["mis"])} {e(noored["miks"])}'),
          ("Teade, mitte koondamine", "risk", f'USA-s nimetati {koond["periood"]} tehisaru {_tuh(ai_teated)} koondamisteates {_tuh(koond["kokku"])}-st, umbes {pr(ai_teated / koond["kokku"] * 100, 0)}%. Need on teated, mitte tegelikud koondamised ({a(ch["url"], ch["autorid"])}).'),
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
    <h2 id="h-ulesanded">Katsetes tegi tehisaru ülesanded kuni {pr(max(r["kiiremini"] for r in kz), 0)}% kiiremaks, aga kogenud arendajad olid oma projektis <b>{pr(abs(kz[metr_i]["kiiremini"]), 0)}% aeglasemad</b></h2>
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
    <h2 id="h-eesti">Eesti uuringud mõõdavad tootlikkust ja takistusi; <b>mõju töökohtadele</b> neis veel ei mõõdeta</h2>
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
    ee_el, el_el = K["el"]["EE"], K["el"][EL]
    can_m = can["muutus"]
    sec_kokkupuude = f"""
<section class="jaotis" id="kokkupuude" aria-labelledby="h-kokkupuude">
  <header>
    <h2 id="h-kokkupuude">Eesti töötajatest {pr(K["avatud"], 0)}% on ametites, kus generatiivne tehisaru puudutab osa ülesandeid; <b>{pr(K["korge"], 0)}% kõige avatumates</b></h2>
  </header>
  <div class="kaks">
    <figure aria-labelledby="g-kokkupuude">
      <figcaption><span class="gt" id="g-kokkupuude">Eesti töötajad ameti kokkupuute astme järgi, % (2022)</span>
        <span class="gs">Aste näitab, kui suur osa ameti ülesannetest on generatiivsele tehisarule avatud; 4 on kõige avatum. Täistööajale taandatud; {pr(K["liigitamata"])}% on ametites, mida ILO indeksis pole.</span></figcaption>
      {lihtribad(k_read, 50, 10, "%", fookus=0)}
      {allikarida([(f"ILO {ilo['aasta']}, kokkupuute indeks", ilo["url"], ""), ("Statistikaamet, tabel PA633", andmed.PA633_URL, "oktoober 2022")])}
      <h3 class="tabeli-pealkiri">Kõige avatumad ametid Eestis</h3>
      {tabel(["Amet", "Töötajaid", "Aste"], k_tabel, piir=True, pealdis="Kõige avatumad ametid Eestis, töötajad täistööajale taandatult, 2022")}
    </figure>
    <div class="kulg">
      {vastavus("osaliselt", "Kokkupuude ei ole mõju: indeks ei ütle, kas töö kaob, muutub või jääb samaks.")}
      {faktid([
          ("Mida uuringud näitavad", "", f'USA-s on 22–25-aastaste hõive avatud ametites {e(can_m)} võrreldes vähem avatud ametitega ({a(U["canaries2026"]["url"], "Brynjolfsson jt " + str(U["canaries2026"]["aasta"]))}). Taanis ei muutunud kogu tööturul tulu ega töötunnid ({a(hum["url"], "Humlum ja Vestergaard " + str(hum["aasta"]))}). Eesti kohta sellist uuringut pole.'),
          ("ELi võrdlus", "", f'Sama ligikaudne arvutus Eurostati 2025. aasta ametirühmade järgi annab Eestile {pr(ee_el["avatud"], 0)}% ja ELile {pr(el_el["avatud"], 0)}%. See on teine andmestik ja jämedam jaotus kui graafikul, seepärast eraldi. ILO enda hinnang kõrge sissetulekuga riikidele on {pr(ilo_korge, 0)}%.'),
          ("Tõlgendus", "s", f'Kõige avatumad on kontori-, raamatupidamise ja klienditeeninduse ametid ning tarkvaraarendus. ILO hinnangul on tõenäolisem, et töö muutub, kui et see kaob ({a(ilo["url"], "ILO " + str(ilo["aasta"]))}).'),
      ])}
    </div>
  </div>
  <details>
    <summary>Kuidas astmed on arvutatud ja mida number ei kata</summary>
    <div>
      <p>ILO hindas iga ameti ülesanded skaalal 0–1: kui suure osa ülesandest saab generatiivne tehisaru ära teha. Ameti aste tuleb ülesannete keskmisest ja hajuvusest: astmes 4 on keskmine vähemalt 0,6 ja ka madalamad hinnangud on kõrged. {K["ilo_avatud_ameteid"]} ametit {K["ilo_ameteid"]}-st on astmetes 1–4. Ülesanded on kirjeldatud Poola ametiklassifikaatori järgi; Eesti ametite sisu võib erineda (<a href="{andmed.ILO_SKOORID_URL}">ILO ametite skoorid</a>, CC BY 4.0).</p>
      <p>Eesti number on {_tuh(K["kokku"])} töötaja kohta, kes on taandatud täistööajale (Statistikaameti palgastruktuuri uuring, oktoober 2022). Ettevõtjad ja FIE-d ei ole sees. Väikeste ametite numbrid on osaliselt avaldamata, seepärast on ametite summa rühmade summast kuni 5% väiksem.</p>
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
    <h2 id="h-hoive">Aastatel {A0}–{A1} kasvas Eestis hõive tehisarule avatud ametites <b>vähem kui teistes ametites</b>; ELis oli vastupidi</h2>
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
          ("Mida jälgida", "s", "Kui see erinevus püsib ka 2026. ja 2027. aastal ning on suurem noorte seas, on see märk, mida tasub uurida registriandmetega, nagu Taanis ja USA-s tehti."),
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
      <p class="gt">Töökohtade muutus USA-s {bls["yhik"]}</p>
      {muutus(b_read, -10, 15, 5, "%", fookus=b_fookus)}
      <p>{e(bls_u["leid"])}</p>
      {allikarida([(bls_u["autorid"], bls_u["url"], kp(bls_u["avaldatud"]))])}
    </div>
  </details>
</section>"""

    from lehed_ulevaade import _p, kpi_pais, kpi_plaat
    aside = kpi_pais(
        kpi_plaat("too-noored", "Noorte (22–25) hõive tehisarule avatud ametites, USA", e(can["muutus"]), "",
                  {"tekst": "vs vähem avatud ametid · <b>laialdast kadu pole</b>"},
                  a(U["canaries2026"]["url"], f'Brynjolfsson jt {U["canaries2026"]["aasta"]}'), fookus=True),
        kpi_plaat("too-taani", "Mõju tulule ja töötundidele, Taani", "&lt; 2%", "",
                  {"tekst": "<b>muutust ei leitud</b> 2 aastat pärast ChatGPT-d"},
                  a(hum["url"], f'Humlum ja Vestergaard {hum["aasta"]}')),
        kpi_plaat("too-prognoos", "Eesti töötuse prognoos", f'{pr(t2030["protsent"])}%', "2030",
                  {"muutus": (f'{_p(t2030["protsent"] - t_tegelik["protsent"])} punkti {t_tegelik["aasta"]}. aastast',
                              f'{t_tegelik["aasta"]}: {pr(t_tegelik["protsent"])}% · <b>tehisaru mõjuta</b>')},
                  a(rm["url"], f'Rahandusministeerium, {kp(rm["avaldatud"])}')),
    )
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
    sec_andmed = tm.andmesakid("too", "Uuri andmeid: töötus, koondamised, palkamine ja tööpakkumised Eestis",
                               "Iga sakk on üks andmestik. Kuunumbrid ja kuulutused ei ütle, kas põhjus on tehisaru; põhjuse kohta on uuringud allpool.", [
        ("tootus", "Töötus ja koondamised", too_eesti(A)),
        ("tootus-el", "Töötus ELis", tootus_el()),
        ("palkamine", "Keda koondajad otsivad", sec_palk),
        ("vabad", "Vabad kohad", vabad_ametikohad()),
        ("portaalid", "Tööportaalid", toopakkumised(A)),
        ("ai-tood", "AI-tööd", ai_kuulutused(A)),
        ("prognoos", "Prognoos", sec_tulevik),
    ])
    lyh = lambda k: e(tm.esimene_lause(U[k]["leid"]))  # noqa: E731
    t_uuringud = tm.uuringute_plokk(vaated, [
        ("USA", f'{lyh("canaries2026")} ({e(U["canaries2026"]["autorid"].split(",")[0])} {U["canaries2026"]["aasta"]})', "too", "maailm"),
        ("Taani", f'{lyh("humlum2025")} ({e(U["humlum2025"]["autorid"].split(",")[0])} {U["humlum2025"]["aasta"]})', "too", "maailm"),
        ("Katsed", f'Katsetes kulus ülesandele kuni 40% vähem aega, aga kogenud arendajatel oma projektis 19% rohkem aega (Noy ja Zhang {U["noy2023"]["aasta"]}; METR {U["metr2025"]["aasta"]}).', "too", "ulesanded"),
        ("Eesti", "Eesti uuringud mõõdavad kasutust, tootlikkust ja takistusi; mõju töökohtadele pole veel mõõdetud.", "too", "eesti"),
    ], [("too", "Uuringud", "maailm"), ("too", "Kirjandus", "uuritakse"), ("too", "Ametid ja hõive", "kokkupuude")])
    t_vaited = tm.vaidete_plokk(A, vaated, "too", vaite_teema)
    t_reeglid = tm.reeglite_plokk(A, vaated, ["ai-keelud-kirjaoskus", "ai-korge-risk-iii"])
    vabad = [r for r in _loe("vabad-ametikohad.csv") if r["tabel"] == "PAV011"] if (Path(__file__).resolve().parent / "sisu" / "vabad-ametikohad.csv").exists() else []
    kv_v = max((r["periood"] for r in vabad), key=_kv) if vabad else None
    t_allikad = tm.allikate_plokk([
        ("Töötus kuu kaupa, Eurostat une_rt_m", UNE_URL, UNE_UUENDATUD, "sesoonselt tasandatud"),
        ("Koondamised, uudised", "", A["koondamised"]["kontrollitud"], "käsitsi kogutud, nimekiri pole täielik"),
        ("Tööpakkumised, 3 portaali", "", A["toopakkumised"]["uuendatud"][:10], "kogutakse iga päev"),
        ("AI- ja andmetööde kuulutused, CV.ee", "https://www.cv.ee/et/search", A["ai_kuulutused"]["uuendatud"][:10], "kogutakse iga päev"),
        *([("Vabad ametikohad, Statistikaamet PAV011", PAV_URL, max(r["uuendatud"] for r in vabad), f"viimane kvartal: {kv_v}")] if vabad else []),
        ("Töötuse prognoos, Rahandusministeerium", rm["url"], rm["avaldatud"], "aasta keskmine, tehisaru mõju eraldi ei arvestata",
         f'{KUUD[int(rm["avaldatud"][5:7]) - 1]} {rm["avaldatud"][:4]}' if len(rm["avaldatud"]) == 7 else None),
    ])
    alam_h1(vaade, "too-ametid.html",
            f'Eesti töötajatest **{pr(K["avatud"], 0)}% on ametites**, mida generatiivne tehisaru puudutab; '
            f'nende hõive kasvas {A0}–{A1} vähem kui teistes ametites.')
    P = A.get("publikatsioonid")
    if P:
        tais = [r for r in P["aastad"] if not r["poolik"]]
        p1 = tais[-1]
        p0 = next(r for r in tais if r["aasta"] == p1["aasta"] - 2)
        alam_h1(vaade, "too-kirjandus.html",
                f'Tehisarust ja tööst ilmus {p1["aasta"]}. aastal **{_arv(p1["koik"])} publikatsiooni**, '
                f'{pr(p1["koik"] / p0["koik"])} korda rohkem kui {p0["aasta"]}.')
    return jaga(A, vaade, lead, [], [
        ("andmed", [("andmed", "Andmed")], sec_andmed),
        ("teema-lopp", [("t-uuringud", "Uuringud"), ("t-vaited", "Väited"), ("t-reeglid", "Reeglid"), ("t-allikad", "Allikad")],
         tm.teema_lopp(t_uuringud, t_vaited, t_reeglid, t_allikad)),
        ("maailm", [("maailm", "Mida maailmas leiti")], sec_maailm),
        ("ulesanded", [("ulesanded", "Ülesanded")], sec_kiirus),
        ("eesti", [("eesti", "Eestis")], sec_eesti),
        ("uuritakse", [("uuritakse", "Mida uuritakse"), ("publikatsioonid", "Publikatsioonid"), ("eesti-allikad", "Eesti allikad")], sec_uuritakse),
        ("kokkupuude", [("kokkupuude", "Ametid")], sec_kokkupuude),
        ("hoive", [("hoive", "Hõive muutus")], sec_hoive),
    ], aside=aside)


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
    src = lambda i: f'{OECD_NIMI.split(",")[0]}, {_o(A, i)["koht"]}'  # noqa: E731
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
    <h2 id="h-lehter">Olulisimatest uuendustest jõuab rakendamiseni {pr(v("rakendati"), 0)}%, aga <b>laiendatakse {pr(v("laiendati"), 0)}%</b></h2>
    <p class="alam">Avalikud teenistujad ja asutuste juhid nimetasid oma olulisima uuenduse ja etapi, kuhu see jõudis. Küsitlus oli detsember 2025 kuni veebruar 2026.</p>
  </header>
  <div class="kaks">
    <div class="pinu">
    <figure aria-labelledby="g-lehter">
      <figcaption><span class="gt" id="g-lehter">Kuhu olulisimad uuendused jõudsid, % uuendustest</span>
        <span class="gs">Avalik sektor kokku, keskvalitsus ja omavalitsused.</span></figcaption>
      {lihtribad([("Jõudis rakendamiseni", v("rakendati"), None), ("Laiendati", v("laiendati"), None)], 100, 25, "%", fookus=1)}
      {allikas}
    </figure>
    <figure aria-labelledby="g-hindamine">
      <figcaption><span class="gt" id="g-hindamine">Hindamismeetod, % töötajate kirjeldatud hindamistest</span>
        <span class="gs">Üks hindamine võib kasutada mitut meetodit. Juhtide järgi oli tasuvuse hindamine {pr(v("hindamine-vfm-juhid"), 0)}%.</span></figcaption>
      {lihtribad([("Protsess", v("hindamine-protsess-tootajad"), None), ("Tasuvus", v("hindamine-vfm-tootajad"), None),
                  ("Teooriapõhine", v("hindamine-teooria-tootajad"), None), ("Kulude ja tulude analüüs", v("hindamine-cba-tootajad"), None),
                  ("Katse (RCT)", v("hindamine-rct-tootajad"), None), ("Kvaasikatse", v("hindamine-kvaasi-tootajad"), None)], 100, 25, "%")}
      {allikarida([("OECD (2026)", OECD_URL, "joonised 6.3 ja 6.4 (lk 132–133)")])}
    </figure>
    </div>
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

    # OECD lisatulemused otse aruandest (Kadri 8.11.2026: kõik ühes kohas, otse allikast; kontrollitud aruande PDF-ist)
    et = [("Uurimine", "etapp-uurimine"), ("Ideed", "etapp-ideed"), ("Prototüüp", "etapp-prototyyp"),
          ("Hindamine", "etapp-hindamine"), ("Otsus", "etapp-otsus")]
    langus = round(v("etapp-prototyyp") - v("etapp-hindamine"))
    if max(round(v(et[i][1]) - v(et[i + 1][1])) for i in range(len(et) - 1)) != langus:
        raise AndmeViga("OECD etapid: suurim langus ei ole enam prototüübist hindamiseni")
    sec_etapid = f"""
<section class="jaotis" id="etapid" aria-labelledby="h-etapid">
  <header>
    <h2 id="h-etapid">Uuendused jäävad toppama hindamise ja otsuse ees: prototüübist hindamiseni jõuab <b>{langus} punkti vähem</b> projekte</h2>
    <p class="alam">Uuendusprojektide osakaal, mis jõudis etapini (projekte {", ".join(_o(A, k)["lugeja"] for _, k in et)}).</p>
  </header>
  <div class="kaks">
    <figure aria-labelledby="g-etapid">
      <figcaption><span class="gt" id="g-etapid">Etapini jõudnud uuendusprojektid, %</span></figcaption>
      {lihtribad([(n, v(k), None) for n, k in et], 100, 25, "%", fookus="Hindamine")}
      {allikarida([("OECD (2026)", OECD_URL, _o(A, "etapp-uurimine")["koht"])])}
    </figure>
    <div class="kulg">
      {vastavus("osaliselt", "Vastajad kirjeldasid oma projekte. Tehisaru projekte eraldi ei loendata.")}
      {faktid([
          ("Fakt", "", f'Kõige olulisematest uuendustest jõuab rakendamiseni {pr(v("rakendati"), 0)}%, laiendatakse {pr(v("laiendati"), 0)}%. {e(_o(A, "etapp-otsus")["markus"])}'),
          ("Tõlgendus · OECD", "s", "Hinnatakse peamiselt protsessi; mõju ja tasuvust hinnatakse harvem, nii et otsustajal on vähe tõendeid laiendamiseks."),
      ], koik_lahti=True)}
    </div>
  </div>
</section>"""

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
    <h2 id="h-moju">Tahe ja oskused on olemas, aga uuenduste <b>mõju mõõdetakse vähe</b>: mõju skoor on kõigis valitsemisalades {ix("moju", "min")}–{ix("moju", "max")}</h2>
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

    osk = [("Tehisaru kasutuselevõtt", "oskus-kasutuselevott"), ("Strateegiline juhtimine ja teenused", "oskus-strateegia"),
           ("Suhtlus ja mõjutamine", "oskus-suhtlus"), ("Digi- ja andmeoskused", "oskus-digi"),
           ("Andmepõhised otsused", "oskus-andmeotsused"), ("Tehisaruoskuste arendamine", "oskus-arendus")]
    if max(osk, key=lambda x: v(x[1]))[1] != "oskus-kasutuselevott":
        raise AndmeViga("OECD oskused: tehisaru kasutuselevõtt ei ole enam kõige soovitum oskus")
    sec_oskused = f"""
<section class="jaotis" id="oskused" aria-labelledby="h-oskused">
  <header>
    <h2 id="h-oskused">Töötajad tahavad kõige rohkem arendada <b>tehisaru kasutuselevõtu</b> oskusi</h2>
    <p class="alam">Vastused küsimusele „Milliseid oskusi tahaksid kõige rohkem arendada?“, kokku {_o(A, "oskus-kasutuselevott")["nimetaja"]} vastust.</p>
  </header>
  <div class="kaks">
    <figure aria-labelledby="g-oskused">
      <figcaption><span class="gt" id="g-oskused">Soovitud oskus, % vastustest</span></figcaption>
      {lihtribad([(n, v(k), None) for n, k in osk], 50, 10, "%", fookus=0)}
      {allikarida([("OECD (2026)", OECD_URL, _o(A, "oskus-kasutuselevott")["koht"])])}
    </figure>
    <div class="kulg">
      {faktid([
          ("Hoiatus · OECD", "risk", e(_o(A, "oskus-arendus")["markus"])),
          ("Kuidas mõõdeti", "", e(_o(A, "oskus-kasutuselevott")["markus"])),
      ])}
    </div>
  </div>
</section>
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
    <h2 id="h-kiirused">OECD jagab {kokku} asutust kolme rühma: <b>{kl[1]["vaartus"]} on piiratud enamuses</b>, {kl[0]["vaartus"]} eestvedajad ja {kl[2]["vaartus"]} väikesed katsetajad</h2>
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

    ree = [
        (f'{pr(v("uuendajad"), 0)}%', f'vastanud avalikest teenistujatest tegi viimase 24 kuu jooksul uuenduse.', e(src("uuendajad"))),
        (f'{pr(v("rakendati"), 0)} → {pr(v("laiendati"), 0)}%', 'olulisimatest uuendustest jõudis rakendamiseni → laiendati.', e(src("rakendati"))),
        (f'{gk["vaartus"]}% <small>({gk["lugeja"]}/{gk["nimetaja"]})</small>', 'keskvalitsuse innovaatoritest kasutas oma uuenduses generatiivset tehisaru.', e(src("genai-kesk"))),
    ]
    lead = "Kõik numbrid: OECD avalik raport (2026), küsitlus 2025–2026."
    # Päise numbrid lukustatud KPI valiku ver1 järgi (Kadri 7.11.2026 21:46): silt üleval, muutus/tekst ja võrdlusriba
    import re
    from lehed_ulevaade import kpi_plaat, kpi_riba
    uu = _o(A, "uuendajad")
    m = re.search(r"Juhtidest (\d+)%, haldustöötajatest (\d+)%", uu["markus"])
    if not m:
        raise AndmeViga("avalik-sektor.csv: uuendajate märkuses puudub juhtide ja haldustöötajate osa")
    oecd = lambda i: a(OECD_URL, f'OECD 2026, {_o(A, i)["koht"].split(", ")[-1]}')  # noqa: E731
    aside = ('<aside class="vastus kpi-pais" aria-label="Peamised numbrid">' + "".join([
        kpi_plaat("uuendus", "Tegi uuenduse (avalikud teenistujad, 24 kuud)", f'{pr(v("uuendajad"), 0)}%', "2025–2026",
                  {"muutus": (f"juhid {m.group(1)}% · haldustöötajad {m.group(2)}%", ""), "riba": kpi_riba(v("uuendajad"), 100, fookus=True)},
                  oecd("uuendajad"), fookus=True),
        kpi_plaat("laiendus", "Uuendus rakendati → laiendati", f'{pr(v("rakendati"), 0)} → {pr(v("laiendati"), 0)}%', "",
                  {"tekst": "<b>kolmandik</b> jõuab laiendamiseni", "riba": kpi_riba(v("laiendati"), 100, vrd=v("rakendati"), vrd_nimi="rakendati")},
                  oecd("rakendati")),
        kpi_plaat("genai", "Kasutab generatiivset tehisaru (keskvalitsuse uuendajad)", f'{gk["vaartus"]}%', f'{gk["lugeja"]}/{gk["nimetaja"]}',
                  {"tekst": "omavalitsustes " + ("<b>peaaegu sama</b>" if abs(float(gk["vaartus"]) - float(gl["vaartus"])) < 3 else f'<b>{gl["vaartus"]}%</b>'), "riba": kpi_riba(v("genai-kesk"), 100, vrd=v("genai-kov"), vrd_nimi="omavalitsused")},
                  oecd("genai-kesk")),
    ]) + "</aside>")
    # Hanked on oma menüükoht; lehtede vahel on rida „Seotud“ (Kadri 6.11.2026 22:27, ettepanek 8)
    # Teemamall A (Kadri 8.11.2026): andmed sakkides, siis uuringud, väited, reeglid, allikad
    import teemamall as tm
    from lehed_ulevaade import vaite_teema
    U = A["uuringud"]
    sec_andmed = tm.andmesakid("avalik-sektor", "Uuri andmeid: uuendused, tehisaru, rahastus, asutuste rühmad ja OECD soovitused",
                               "Kõik numbrid on OECD avalikust raportist (2026), küsitlus detsember 2025 kuni veebruar 2026.", [
        ("lehter", "Rakendamine", sec_lehter + sec_etapid),
        ("liigid", "Uuenduse liik ja mõju", sec_liigid),
        ("tehisaru", "Tehisaru", sec_genai + sec_oskused),
        ("rahastus", "Rahastus", sec_raha),
        ("kiirused", "Kolm rühma", sec_kiirus),
        ("soovitused", "Soovitused", sec_soov),
    ])
    t_uuringud = tm.uuringute_plokk(vaated, [
        ("Eesti", "Alla 40-aastased hindavad oma tehisaru kirjaoskust kõrgemaks; juhid on enesekindlamad, aga mitte selles, kuidas tehisaru asutuses tööle panna (OECD 2026).", "avalik-sektor", "tehisaru"),
        ("Suurbritannia", f'{e(tm.esimene_lause(U["gds2025"]["leid"]))} (GDS {U["gds2025"]["aasta"]})', "too", "ulesanded"),
    ], [("hanked", "Hanked: mida riik ostab", "")])
    t_vaited = tm.vaidete_plokk(A, vaated, "avalik-sektor", vaite_teema)
    t_reeglid = tm.reeglite_plokk(A, vaated, ["ai-keelud-kirjaoskus", "ai-uldkohaldamine", "ai-korge-risk-iii"])
    t_allikad = tm.allikate_plokk([
        (OECD_NIMI, OECD_URL, "2026-11-03", "CC BY 4.0; küsitlus 12.2025–02.2026"),
    ])
    return (pea(A, vaade, lead, [("andmed", "Andmed"), ("t-uuringud", "Uuringud"), ("t-vaited", "Väited"), ("t-reeglid", "Reeglid"), ("t-allikad", "Allikad")], ree, aside=aside)
            + sec_andmed + tm.teema_lopp(t_uuringud, t_vaited, t_reeglid, t_allikad)
            + seotud(vaated, [("hanked", "Hanked: mida riik tehisaru ja andmete kohta ostab"), ("reeglid", "Tehisaru määrus: tähtajad")]))


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
    <h2 id="h-tahtajad">Tehisaru määruse {SEESTYTLEV.get(len(O), str(len(O)))} tähtajast <b>{ARVSONAD.get(len(moodas), str(len(moodas)))} on kehtima hakanud</b>, {ARVSONAD.get(len(ees), str(len(ees)))} on veel ees</h2>
    {vastavus("jah", f"Tähtajad on kontrollitud Euroopa Komisjoni tehisintellekti määruse lehelt {kp(kontroll)}.")}
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
        kpi_plaat("ma-korge", "Kõrge riskiga kasutus", kp(kr["kuupaev"]), "",
                  {"muutus": (_kuud(kr["kuupaev"]), ""), "tekst": "nt <b>CV-de sorteerimine</b>, hindamine koolis"},
                  a(kr["url"], "Euroopa Komisjon")),
        kpi_plaat("ma-osad", "Tähtajad 2024–2028", f"{len(moodas)}", f"/ {len(O)} möödas",
                  {"muutus": (f"{len(ees)} on veel ees", f"kehtib alates {kp(uld['kuupaev'])}"),
                   "riba": kpi_riba(len(moodas), len(O))},
                  a(uld["url"], "Euroopa Komisjon")),
    )
    j_tekst = f'Järgmine tähtaeg on {jargmine[1]}: {e(jargmine[2].lower())}.' if jargmine else ""
    lead = j_tekst
    sec_ee = eesti_otsused(A, vaade, vaated, tana)
    return jaga(A, vaade, lead, [], [
        ("tahtajad", [("tahtajad", "ELi tähtajad")], sec_aeg),
        ("eesti", [("eesti-otsused", "Eesti otsused")], sec_ee),
    ], aside=aside)


def eesti_otsused(A, vaade, vaated, tana):
    """Eesti riigi otsused, eelnõud, hanked ja tähtajad igapäevasest uudistekogumisest (teema „riik“, alates 9.11.2026).

    Kirjeid ei kanta käsitsi (Kadri 8.11.2026 23:02: kogumine peab need ise leidma)."""
    from lehed_uudised import RIIGI_LIIK, _uudis
    U = [r for r in (A.get("uudised") or []) if r.get("teema") == "riik"]
    U.sort(key=lambda r: r["kuupaev"], reverse=True)
    ees = sorted((r for r in U if r.get("tahtaeg") and r["tahtaeg"] >= tana), key=lambda r: r["tahtaeg"])
    fail = "eesti-otsused.html"
    if not U:
        alam_h1(vaade, fail, "Eesti riigi otsused, eelnõud ja tähtajad tulevad siia **igapäevasest uudistekogumisest**.")
        return f"""
<section class="jaotis" id="eesti-otsused" aria-labelledby="h-eesti-otsused">
  <header>
    <h2 id="h-eesti-otsused">Riigi otsuseid ja tähtaegu pole kogumine veel leidnud</h2>
    <p class="alam">Kogumine otsib kaks korda päevas riigi otsuseid, eelnõusid, riigihankeid, tähtaegu, üritusi ja aruandeid. Kirjeid ei kanta siia käsitsi.</p>
  </header>
</section>"""
    loend = lambda rr: f'<ul class="u-voog" data-piir-li="12">{"".join(_uudis(r) for r in rr)}</ul>'  # noqa: E731
    if ees:
        j = ees[0]
        alam_h1(vaade, fail, f'Kogumine on leidnud {len(U)} Eesti riigi otsust, eelnõu või tähtaega; '
                             f'**järgmine tähtaeg on {kp(j["tahtaeg"])}**.')
    else:
        alam_h1(vaade, fail, f'Kogumine on leidnud {len(U)} Eesti riigi otsust või eelnõu; **eesolevaid tähtaegu neis pole**.')
    liigid = {}
    for r in U:
        liigid[r.get("riigi_liik") or "muu"] = liigid.get(r.get("riigi_liik") or "muu", 0) + 1
    kokku = ", ".join(f'{n} {RIIGI_LIIK.get(k, k)}' for k, n in sorted(liigid.items(), key=lambda x: -x[1]))
    ees_html = (f'<h3 class="veerg">Ees olevad tähtajad ({len(ees)})</h3>' + loend(ees)) if ees else ""
    return f"""
<section class="jaotis" id="eesti-otsused" aria-labelledby="h-eesti-otsused">
  <header>
    <h2 id="h-eesti-otsused">Riigi otsused, eelnõud ja tähtajad: <b>{len(U)} kirjet</b> ({e(kokku)})</h2>
    <p class="alam">Kirjed tulevad igapäevasest uudistekogumisest (riigi asutuste lehed ja uudisteotsing), mitte käsitsi. Iga kirje juures on algallika link.</p>
    {vastavus("osaliselt", "Kogumine leiab avalikult teatatud otsuseid. Eelnõude infosüsteemi kogumine ei loe, nii et kõik eelnõud ei pruugi siia jõuda.")}
  </header>
  {ees_html}
  <h3 class="veerg">Kõik kirjed, uusimad eespool</h3>
  {loend(U)}
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
                 f'EL tervikuna {pr(p["vaartus"], k)}{u}, Eesti {pr(ee["vaartus"], k)}{u} ({p["aasta"]}); ELil puudu {pr(siht - p["vaartus"], k)} punkti.')
    return (f'<div class="siht-rida"><p><span class="siht-silt">Siht</span> {tekst}</p>'
            f'{sihiriba(p["vaartus"], siht, lopp, "", fookus=(s["tase"] == "EE"))}</div>')


def lisa_sihid(A, html, jaotis, *sid):
    """Paneb sihi read jaotise lõppu (enne selle </section>)."""
    i = html.index(f'id="{jaotis}"')
    j = html.index("</section>", i)
    return html[:j] + "".join(siht_rida(A, x) for x in sid) + html[j:]


