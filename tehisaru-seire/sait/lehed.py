"""Vaadete sisu. Iga funktsioon saab andmeobjekti ja vaate kirje ning tagastab lehe sisu (ilma kestata).

Iga vaate järjekord (sisuloogika hinnang): vastus, peamine tõend koos võrdlusega, mida see ei näita,
mida see tähendab, siis üksikasjad ja allikad.
"""
import andmekiht as andmed
from andmekiht import EL
from komponendid import (allikarida, e, ei_naita, faktid, hantlid, jaga_klassid, kaart, kp, leiu_ribad, margend, pr,
                         riik, tabel, telg, vastavus)
from pealkiri import taida

POHJAMAAD = ["FI", "SE", "DK"]  # ELi Põhjamaad; Norra ei ole ELi skaalal
EB = "ettevotete-tehisaru-kasutus"


# ---------------------------------------------------------------- Ettevõtted

def _kasutus(A):
    n = A["naitajad"][EB]
    m = A["meta"][EB]
    ee = andmed.leia(A, EB, "EE", "uusim:alus")
    y = ee["aasta"]
    eu = andmed.leia(A, EB, EL, y)
    el = andmed.el27_aasta(A, EB, y)
    koht = andmed.koht(A, EB, "EE", y)
    pm = [andmed.leia(A, EB, g, y)["vaartus"] for g in POHJAMAAD]
    pm23 = [andmed.leia(A, EB, g, 2023)["vaartus"] for g in POHJAMAAD]
    ee23, eu23 = andmed.leia(A, EB, "EE", 2023)["vaartus"], andmed.leia(A, EB, EL, 2023)["vaartus"]
    vahe23, vahe = sum(pm23) / 3 - ee23, sum(pm) / 3 - ee["vaartus"]

    # Kaart tulpade asemel (Kadri kommentaar eelvaatel 4.11.2026); täpne järjestus on andmetabelis
    graafik = kaart(list(el.values()), (0, 10, 20, 30, 40), viide=eu["vaartus"], viite_nimi=f"EL keskmine {pr(eu['vaartus'])}%")

    # Kõik uusimad riiklikud numbrid; skaalal ainult võrdlusalus (Kadri otsus 4.11.2026)
    koik_uued = [v for v in A["vaatlused"] if v["naitaja"].startswith(EB) and v["aasta"] > y]
    skaalal, muud = jaga_klassid(koik_uued)
    assert not skaalal, "Uuemat Eurostati aastat pole; kui tuleb, läheb see skaalale ja leht tuleb üle vaadata"
    muud.sort(key=lambda v: (v["geo"] != "EE", -v["vaartus"]))
    t_read = [[f'{e(riik(v["geo"]))}<small>{e(v["kogum"])}</small>', pr(v["vaartus"]),
               f'<span class="vrd">ei ole otse võrreldav:</span> {e(v.get("miks", ""))}'
               f'<small><a href="{e(v["url"])}">{e(v["allikas"])}</a>, {e(kp(v["avaldatud"]))}</small>'] for v in muud]
    uued_tbl = tabel(["Riik ja kogum", f"{muud[0]['aasta']}, %", "Miks mitte skaalal ja allikas"], t_read, fookus_rida=0, numbrid=[1],
                     pealdis="Riikide uusimad numbrid, mis ei ole ELi skaalaga võrreldavad")

    lahk = next(l for l in A["lahknevused"] if l["kood"] == "C5")
    sa25 = next(t for t in n["teised_allikad"] if t["allikas"].startswith("Statistikaamet, tabel IT149"))
    piirang = next(r for r in A["riskid"] if r["liik"] == "piirang" and r["naitaja"] == EB)
    vaide = next(v for v in A["vaited"] if v["naitaja"] == EB and "1,5 korda" in v["vaide"])
    usaldus = faktid([
        ("Lahknevus C5", "risk",
         f'Sama {y}. aasta küsitluse kohta annab Statistikaamet {pr(sa25["vaartus"])}% '
         f'(<a href="{e(sa25["url"])}">IT149</a>) ja Eurostat {pr(ee["vaartus"])}%. Põhjus on {e(lahk["staatus"])}. <a href="kas-see-on-tosi.html#lahknevused">Kõik lahknevused</a>.'),
        ("Piirang", "",
         f'Osa 2024–2025 kasvust tuleb sellest, et küsimustikku lisandus piltide, video ja heli genereerimine '
         f'(<a href="{e(piirang["url"])}">Eurostat, {e(kp(piirang["kuupaev"]))}</a>).'),
        ("Väide", "risk",
         f'Statistikaameti uudis ütles, et kasutus kasvas aastaga 1,5 korda. Suurus on ebakindel, sest 2025 ja 2026 '
         f'on eri klassifikaatoriga (<a href="{e(vaide["url"])}">Statistikaamet, {e(kp(vaide["kuupaev"]))}</a>).'),
    ])

    aastad = sorted({v["aasta"] for v in andmed.vali(A, EB, "EE", klass="alus")})
    d_read = []
    for g in ["EE", "FI", "SE", "DK", "NO", "DE", "NL", EL]:
        rida = [e(riik(g))]
        for a in aastad:
            v = andmed.vali(A, EB, g, a, klass="alus")
            rida.append(pr(v[0]["vaartus"]) + margend(v[0]["margend"]) if v else "–")
        d_read.append(rida)
    jarjest = sorted(el.values(), key=lambda v: -v["vaartus"])
    el_read = [[e(riik(v["geo"])), pr(v["vaartus"]) + margend(v["margend"])] for v in jarjest]

    return f"""
<section class="jaotis" id="kasutus" aria-labelledby="h-kasutus">
  <header>
    <h2 id="h-kasutus">ELi skaalal on Eesti {len(el)} riigi seas <b>{koht}. kohal</b>: {pr(ee["vaartus"])}% ettevõtetest, EL {pr(eu["vaartus"])}%, Soome, Rootsi ja Taani {pr(min(pm), 0)}–{pr(max(pm), 0)}% ({y})</h2>
  </header>
  <div class="ruut3">
    <figure aria-labelledby="g-kasutus">
      <figcaption><span class="gt" id="g-kasutus">Tehisaru kasutavad ettevõtted ELi riikides, {y}, % ettevõtetest</span>
        <span class="gs">Vähemalt 10 hõivatuga ettevõtted, ilma põllumajanduse, kaevandamise ja finantssektorita.</span></figcaption>
      {graafik}
      <p class="peidus">Eesti on {koht}. kohal {pr(ee["vaartus"])}%-ga. Eespool on {", ".join(riik(v["geo"]) for v in jarjest[:koht - 1])}.</p>
      {allikarida([("Eurostat, isoc_eb_ai", "https://ec.europa.eu/eurostat/databrowser/view/isoc_eb_ai/default/table", "uuendatud " + kp(m["allikas_uuendas"]))])}
    </figure>
    <div class="kulg">
      {vastavus("osaliselt", "Suund on kindel, aga osa 2025. aasta tõusust tuleb küsimustiku muutusest ja Eesti uusim number on uue klassifikaatoriga.")}
      <div class="plokk">
        <h3>Vahe Soome, Rootsi ja Taaniga kasvas {pr(vahe23)} punktilt {pr(vahe)} punktini</h3>
        <div class="vahe">
          <div><span class="big s">{pr(ee23)} → {pr(ee["vaartus"])}%</span><p>Eesti, 2023 → {y}</p></div>
          <div><span class="big">{pr(eu23)} → {pr(eu["vaartus"])}%</span><p>ELi keskmine, 2023 → {y}</p></div>
        </div>
        <p class="gs">Eesti kasvab suhtes kiiremini, aga punktides aeglasemalt kui Põhjamaad.</p>
      </div>
      <div class="plokk">
        <h3>{muud[0]["aasta"]}. aasta numbrid on olemas, aga ELi skaalale need ei sobi</h3>
        {uued_tbl}
      </div>
    </div>
    <div class="usaldus3">{usaldus}</div>
  </div>
  <details>
    <summary>Näita andmetabelit ja määratlust</summary>
    <div>
      <p class="gt">Kõik ELi riigid, {y}, %</p>
      {tabel(["Riik", f"{y}, %"], el_read, fookus_rida=[v["geo"] for v in jarjest].index("EE"), piir=True, pealdis=f"ELi riigid {y}")}
      <p class="gt">Võrdlusriigid aastate kaupa, %</p>
      {tabel(["Riik"] + [str(a) for a in aastad], d_read, fookus_rida=0, pealdis="Võrdlusriigid aastate kaupa")}
      <p>2022. aasta andmeid ei ole: Eurostat seda küsimust 2022. aastal ei küsinud.</p>
      <p class="gt">Mida see number ei näita</p>
      {ei_naita(n["piirangud"])}
      {allikarida([("Eurostat, isoc_eb_ai", m["url"].split("?")[0], "kontrollitud " + kp(m["kontrollitud"]))])}
    </div>
  </details>
</section>"""


def _tootlikkus(A):
    L = A["leiud"]["ars-tootlikkus"]
    arvud = [r for r in A["leiud_arvud"] if r["leid"] == L["id"]]
    ruhmad = []
    for r in arvud:
        if r["ruhm"] not in ruhmad:
            ruhmad.append(r["ruhm"])
    fig = []
    for g in ruhmad:
        read = [(r["silt"], float(r["vaartus"]) if r["vaartus"] else None, r["olulisus"]) for r in arvud if r["ruhm"] == g]
        fig.append(f'<p class="ruhm">{e(g)}</p>' + leiu_ribad(read, 30, "Tehisaru + töökorralduse muutus"))
    fig = ['<div class="ribad leiud" aria-hidden="true">'] + fig + [telg(0, 30, 10, "%"), "</div>"]
    U = A["uuringud"]
    calvino, bbh, vahter = U.get("calvino2023", {}), U.get("bbh2002", {}), U.get("vahter2026", {})
    pwc = next((v for v in A["vaited"] if v["id"] == "pwc-2026-tootlikkus-40"), None)
    palk = A["leiud"]["ars-oskused-palk"]
    fk = [
        ("Kui kindel", "", "Uuring, mitte statistika. 19% ja 23% on nõrga statistilise olulisusega (tärn). "
                          "„Ei olnud oluline“ tähendab, et mõju ei leitud, mitte et see oli null."),
        ("Sama muster", "",
         f'OECD 11 riigi andmetel jääb tehisaru kasutajate eelis väiksemaks või kaob, kui arvestada IT-oskusi ja muid '
         f'digitehnoloogiaid (<a href="{e(calvino.get("url", ""))}">Calvino ja Fontanelli 2023</a>). Arvutiajastul leiti '
         f'sama: kasu tuleb, kui IT, töökorraldus ja oskused muutuvad koos (<a href="{e(bbh.get("url", ""))}">Bresnahan jt 2002</a>).'),
    ]
    kim = U.get("kim2026")
    if kim:  # sisuloogika 6.11.2026: ainus juhuslik katse, mis testib „töökorraldus enne tööriista“
        fk.append(("Katse", "s",
                   f'{e(kim["valim"].capitalize())} said samad tehisaru tööriistad. Need, kellele näidati, kuidas töövoogu '
                   f'ümber korraldada, leidsid 44% rohkem kasutusviise ja teenisid 1,9 korda rohkem tulu '
                   f'(<a href="{e(kim["url"])}">Kim jt {kim["aasta"]}, INSEAD</a>; töödokument, retsenseerimata).'))
    if pwc:
        fk.append(("Väide", "risk",
                   f'PwC pressiteade ütles, et tehisaruga enim kokkupuutuvates ettevõtetes on tootlikkuse kasv 40% kõrgem. '
                   f'See on seos tegevusalade vahel, mitte tehisaru kasutamise mõju '
                   f'(<a href="{e(pwc["url"])}">PwC Eesti, {e(kp(pwc["kuupaev"]))}</a>).'))
    andmetabel = tabel(["Rühm ja tegevus", "Tootlikkuse muutus, %"],
                       [[f'{e(r["ruhm"])}<small>{e(r["silt"])}</small>',
                         ("ei olnud oluline" if not r["vaartus"] else "+" + pr(float(r["vaartus"])))
                         + (" (nõrk olulisus)" if r["olulisus"] == "nõrk" else "")] for r in arvud],
                       pealdis="Tootlikkuse muutus tehnoloogia ja töökorralduse järgi", numbrid=[])
    return f"""
<section class="jaotis" id="tootlikkus" aria-labelledby="h-tootlikkus">
  <header>
    <h2 id="h-tootlikkus">Tehisaru kasutus oli seotud suurema tootlikkusega <b>ainult koos töökorralduse muutusega</b></h2>
    {f'<p class="alam">Tõend: {e(vahter["silt"])}. Ettevõtete registriandmed on ulatuslikud, aga tulemus on nõrga statistilise olulisusega ja retsenseerimata.</p>' if vahter.get("silt") else ""}
    {vastavus("osaliselt", "Uuring kasutab Eesti ettevõtete andmeid kuni 2023. aastani, enne generatiivse tehisaru laia levikut.")}
  </header>
  <div class="kaks">
    <figure aria-labelledby="g-tootlikkus">
      <figcaption><span class="gt" id="g-tootlikkus">Tootlikkuse muutus pärast tehnoloogia kasutuselevõttu, %</span>
        <span class="gs">Eesti ettevõtted 2000–2023. Töökorralduse muutus = uued tööviisid, juhtimispraktikad ja otsustusprotsessid. * nõrk statistiline olulisus.</span></figcaption>
      {"".join(fig)}
      {allikarida([(L["allikas"], L["url"], kp(L["avaldatud"]) + ", " + L["koht"])])}
    </figure>
    <div class="kulg">{faktid(fk)}</div>
  </div>
  <details>
    <summary>Näita andmetabelit ja meetodit</summary>
    <div>
      {andmetabel}
      <p>{e(vahter.get("valim", L["markus"]))}. Autorid: {e(vahter.get("autorid", ""))}. Uuring ei ole eelretsenseeritud.</p>
      <p>{e(palk["leid"])} ({e(palk["koht"])}; {e(palk["markus"])})</p>
      <p class="allikas">Numbrid on {e(L["kontrollitud"])}.</p>
    </div>
  </details>
</section>"""


def _digi_ja_ta(A):
    DI, TA = "ettevotete-digiintensiivsus", "ta-kulud"
    nd, nt = A["naitajad"][DI], A["naitajad"][TA]
    md, mt = A["meta"][DI], A["meta"][TA]
    siht_d, siht_t = A["sihid"]["el-digiintensiivsus-90"], A["sihid"]["el-ta-3"]

    def paarid(nid, riigid, a0, a1):
        p = []
        for g in riigid:
            v0, v1 = andmed.vali(A, nid, g, a0, klass="alus"), andmed.vali(A, nid, g, a1, klass="alus")
            if v0 and v1:
                p.append((v0[0], v1[0]))
        return p

    d_riigid = ["EE", "FI", "SE", "DK", "NO", "DE", "NL", EL]
    pd = paarid(DI, d_riigid, 2022, 2024)
    ee_d, eu_d = andmed.leia(A, DI, "EE", 2024)["vaartus"], andmed.leia(A, DI, EL, 2024)["vaartus"]
    g_d = hantlid(pd, 60, 100, 10, "%", viide=float(siht_d["siht"]),
                  viite_nimi=f"ELi siht {siht_d['aasta']}: {siht_d['siht']}% VKEdest")
    pt = paarid(TA, d_riigid, 2022, 2024)
    ee_t, eu_t = andmed.leia(A, TA, "EE", 2024)["vaartus"], andmed.leia(A, TA, EL, 2024)["vaartus"]
    ee_t_uus = andmed.leia(A, TA, "EE", "uusim:alus")
    lisa = {"EE": ee_t_uus} if ee_t_uus["aasta"] > 2024 else None
    g_t = hantlid(pt, 1, 4, 0.5, "% SKPst", k=2, viide=float(siht_t["siht"]),
                  viite_nimi=f"ELi ühine siht: {siht_t['siht']}% SKPst", lisa=lisa)
    uus_tekst = (f'Eesti {ee_t_uus["aasta"]}. aasta number {pr(ee_t_uus["vaartus"], 2)}% on '
                 f'{e(ee_t_uus["margend"] and "esialgne" or "lõplik")} (katkendring).'
                 if lisa else "")
    return f"""
<div class="kaks vordne paar">
<section class="jaotis" id="digi" aria-labelledby="h-digi">
  <header>
    <h2 id="h-digi">Vähemalt baastaseme digiintensiivsusega on <b>{pr(ee_d)}% Eesti VKEdest</b>, veidi alla ELi keskmise {pr(eu_d)}% (2024)</h2>
    <p class="alam">10–249 hõivatuga ettevõtted, mis täidavad vähemalt 4 tunnust 12-st (indeksi 4. versioon). Tehisaru on üks tunnustest.</p>
  </header>
  <figure aria-labelledby="g-digi">
    <figcaption><span class="gt" id="g-digi">Vähemalt baastasemel VKEd, % ettevõtetest, 2022 → 2024</span>
</figcaption>
    {g_d}
    {allikarida([("Eurostat, isoc_e_dii", "https://ec.europa.eu/eurostat/databrowser/view/isoc_e_dii/default/table", "uuendatud " + kp(md["allikas_uuendas"])), ("ELi siht", siht_d["url"], siht_d["allikas"])])}
  </figure>
  <details>
    <summary>Mida see number ei näita</summary>
    <div>{ei_naita(nd["piirangud"], '<p class="vaikne">Teine mõõt, kõrge ja väga kõrge digiintensiivsusega ettevõtete osakaal, annab teised numbrid. See leht kasutab ainult baastaset.</p>')}</div>
  </details>
</section>
<section class="jaotis" id="ta" aria-labelledby="h-ta">
  <header>
    <h2 id="h-ta">Eesti teadus- ja arendustegevuse kulu kasvab, aga jääb <b>ELi keskmisest {pr(eu_t - ee_t, 2)} punkti alla</b> (2024)</h2>
    <p class="alam">Kõigi sektorite kulu kokku, % SKPst: ettevõtted, riik, kõrgharidus ja mittetulundussektor. Ei näita, kui palju läheb tehisarule.</p>
  </header>
  <figure aria-labelledby="g-ta">
    <figcaption><span class="gt" id="g-ta">T&amp;A kulu, % SKPst, 2022 → 2024</span>
      {f'<span class="gs">{uus_tekst}</span>' if uus_tekst else ""}</figcaption>
    {g_t}
    {allikarida([("Eurostat, rd_e_gerdtot", "https://ec.europa.eu/eurostat/databrowser/view/rd_e_gerdtot/default/table", "uuendatud " + kp(mt["allikas_uuendas"])), ("ELi siht", siht_t["url"], siht_t["allikas"])])}
  </figure>
  <details>
    <summary>Mida see number ei näita</summary>
    <div>{ei_naita(nt["piirangud"])}</div>
  </details>
</section>
</div>"""


def ettevotted(A, vaade, vaated=None):
    """Kaks alamlehte (sisuloogika 6.11.2026, Kadri otsus 6): Kasutus | Tootlikkus ja võimekus."""
    from abi import jaga
    from lehed_teemad import lisa_sihid
    ee = andmed.leia(A, EB, "EE", "uusim")
    ee_el = andmed.leia(A, EB, "EE", "uusim:alus")
    eu = andmed.leia(A, EB, EL, ee_el["aasta"])
    koht = andmed.koht(A, EB, "EE", ee_el["aasta"])
    n_el = len(A["el_riigid"])
    siht = A["sihid"]["ee-ettevotted-75"]
    ree = [
        (f'{pr(ee["vaartus"])}%', f'Eesti ettevõtetest kasutas tehisaru {ee["aasta"]}. aastal (10+ hõivatut, uus klassifikaator).',
         f'<a href="{e(ee["url"])}">{e(ee["allikas"])}</a>, {kp(ee["avaldatud"])}'),
        (f'{koht}. <small>/ {n_el} ELi riigist</small>', f'{ee_el["aasta"]}: Eesti {pr(ee_el["vaartus"])}%, EL {pr(eu["vaartus"])}%. Uusim aasta, mida saab ELiga võrrelda.',
         e(ee_el["allikas"])),
        (f'{siht["siht"]}% <small>aastaks {siht["aasta"]}</small>', 'Eesti siht Statistikaameti numbril; klassifikaator kontrollimata.',
         f'<a href="{e(siht["url"])}">{e(siht["allikas"])}</a>'),
    ]
    lead = ("Kasutus kasvab kiiresti, aga vahe Põhjamaadega on punktides suurenenud. "
            "Eesti andmetel on tehisaru seotud suurema tootlikkusega alles siis, kui muutub ka töökorraldus.")
    return jaga(A, vaade, lead, ree, [
        ("kasutus", [("kasutus", "Kasutus")], lisa_sihid(A, _kasutus(A), "kasutus", "ee-ettevotted-75")),
        ("tootlikkus", [("tootlikkus", "Tootlikkus")], _tootlikkus(A)),
        ("voimekus", [("digi", "Digiintensiivsus"), ("ta", "Teadus ja arendus")],
         lisa_sihid(A, lisa_sihid(A, _digi_ja_ta(A), "digi", "el-digiintensiivsus-90"), "ta", "el-ta-3")),
    ])


# ---------------------------------------------------------------- Saidikaart

def saidikaart(A, vaade, vaated):
    read = []
    for v in vaated:
        nimi = v["menuu"] or {"avaleht": "Avaleht", "kuidas": "Kuidas lugeda", "saidikaart": "Saidikaart"}[v["id"]]
        link = f'<a href="{v["fail"]}">{e(nimi)}</a>' if v["olek"] == "valmis" else e(nimi)
        if v.get("alamlehed") and v["olek"] == "valmis":
            link += "<small>alamlehed: " + ", ".join(f'<a href="{s["fail"]}">{e(s["nimi"])}</a>' for s in v["alamlehed"]) + "</small>"
        read.append(f'<tr><td>{link}<small>{e(v["koht"])} · {e(v["kusimused"])}</small></td><td>{e(v["kusimus"])}</td>'
                    f'<td class="h1">{taida(v["h1"], A)}</td><td>{e(v["osad"])}</td>'
                    f'<td><span class="olek {v["olek"]}">{v["olek"]}</span></td></tr>')
    pais = "".join(f'<th scope="col">{t}</th>' for t in ["Vaade", "Lugeja küsimus", "Pealkiri (vastus)", "Mis vaates on", "Olek"])
    return f"""
<div class="pea yks">
  <div class="pea-tekst">
    <h1>{taida(vaade["h1"], A)}</h1>
    <p class="lead">Valmis on {sum(v["olek"] == "valmis" for v in vaated)} vaadet {len(vaated)}-st; iga rea pealkiri on sama, mis vaate lehel.</p>
    <p class="meta">Iga vaate järjekord: vastus, peamine tõend koos võrdlusega, mida see ei näita, mida see tähendab, siis üksikasjad ja allikad. Pealkirjade numbrid tulevad andmefailidest.</p>
  </div>
</div>
<section class="jaotis" aria-label="Vaated">
  <div class="tbl kaart"><table><thead><tr>{pais}</tr></thead><tbody>{"".join(read)}</tbody></table></div>
</section>"""


import lehed_teemad as _t  # noqa: E402
import lehed_usaldus as _u  # noqa: E402
import lehed_ulevaade as _o  # noqa: E402
import lehed_uudised as _n  # noqa: E402

EHITAJAD = {"avaleht": _o.avaleht, "inimesed": _t.inimesed, "ettevotted": ettevotted, "too": _t.too,
            "avalik-sektor": _t.avalik_sektor, "reeglid": _t.reeglid, "kas-tosi": _u.kas_tosi, "kuidas": _u.kuidas,
            "hanked": _n.hanked, "uudised": _n.uudised}
