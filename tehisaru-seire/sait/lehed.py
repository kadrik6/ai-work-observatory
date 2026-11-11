"""Vaadete sisu. Iga funktsioon saab andmeobjekti ja vaate kirje ning tagastab lehe sisu (ilma kestata).

Iga vaate järjekord (sisuloogika hinnang): vastus, peamine tõend koos võrdlusega, mida see ei näita,
mida see tähendab, siis üksikasjad ja allikad.
"""
import andmekiht as andmed
from andmekiht import EL, AndmeViga
from komponendid import (allikarida, e, ei_naita, faktid, hantlid, jaga_klassid, kaart, kp, leiu_ribad, margend, pr,
                         riik, tabel, telg, vastavus)
from pealkiri import taida
from abi import sonaga

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
               f'{e(v.get("miks", ""))}'
               f'<small><a href="{e(v["url"])}">{e(v["allikas"])}</a>, {e(kp(v["avaldatud"]))}</small>'] for v in muud]
    uued_tbl = tabel(["Riik ja kogum", f"{muud[0]['aasta']}, %", "Miks ei ole otse võrreldav; allikas"], t_read, fookus_rida=0, numbrid=[1],
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

    # Koha muutus ELis aastate kaupa, sama graafik nagu avalehel (Kadri 9.11.2026: „I really like these visuals“)
    from lehed_ulevaade import el_jarjestus
    j_ev = el_jarjestus(EB, koht_praegu=koht, aasta_praegu=y, lai=(640, 130, 140), min_aastaid=2)
    jrj_fig = ""
    if j_ev:
        b_g, b_k, b_a, _, b_uuend = j_ev
        jrj_fig = f"""<figure aria-labelledby="g-jrj">
      <figcaption><span class="gt" id="g-jrj">Eesti koht ELis aastate kaupa, {b_a[0]}–{b_a[-1]}: {b_k[b_a[0]]}. → {b_k[b_a[-1]]}.</span>
        <span class="gs">Tehisaru kasutavad ettevõtted, % vähemalt 10 hõivatuga ettevõtetest. Klõpsa real, et see esile tõsta.</span></figcaption>
      <div class="kp-sisu"><div class="el-bump">{b_g}</div>
      {allikarida([("Eurostat, isoc_eb_ai", "https://ec.europa.eu/eurostat/databrowser/view/isoc_eb_ai/default/table", "uuendatud " + kp(b_uuend))])}</div>
    </figure>"""
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
    <h2 id="h-kasutus">ELi skaalal on Eesti {len(el)} riigi seas <b>{koht}. kohal</b> ¦ {pr(ee["vaartus"])}% ettevõtetest, EL {pr(eu["vaartus"])}%, Soome, Rootsi ja Taani {pr(min(pm), 0)}–{pr(max(pm), 0)}% ({y})</h2>
  </header>
  <div class="ruut3 kaart-paar">
    <figure aria-labelledby="g-kasutus">
      <figcaption><span class="gt" id="g-kasutus">Tehisaru kasutavad ettevõtted ELi riikides, {y}, % ettevõtetest</span>
        <span class="gs">Vähemalt 10 hõivatuga ettevõtted, ilma põllumajanduse, kaevandamise ja finantssektorita.</span></figcaption>
      <div class="kp-sisu">{graafik}
      <p class="peidus">Eesti on {koht}. kohal {pr(ee["vaartus"])}%-ga. Eespool on {", ".join(riik(v["geo"]) for v in jarjest[:koht - 1])}.</p>
      {allikarida([("Eurostat, isoc_eb_ai", "https://ec.europa.eu/eurostat/databrowser/view/isoc_eb_ai/default/table", "uuendatud " + kp(m["allikas_uuendas"]))])}</div>
    </figure>
    {jrj_fig}
  </div>
  <div class="kulg-all">
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
    </div>
    {usaldus}
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
</section>
<section class="jaotis" id="kasutus-uued" aria-labelledby="h-kasutus-uued">
  <header>
    <h2 id="h-kasutus-uued">{muud[0]["aasta"]}. aasta numbrid on olemas {sonaga(len(muud), "alaleytlev")} riigil, aga <b>ELi skaalale need ei sobi</b></h2>
    <p class="alam">Riikide statistikaametid avaldasid need enne Eurostati. Küsimustik või ettevõtete kogum erineb, seepärast ei ole need kaardil.</p>
  </header>
  {uued_tbl}
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
                          "„Ei olnud oluline“ tähendab, et mõju ei leitud, mitte seda, et see oli null."),
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
    <h2 id="h-tootlikkus">Tootlikkus oli suurem, kui tehisaruga <b>muutus ka töökorraldus</b></h2>
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
    <h2 id="h-digi">Vähemalt baastaseme digiintensiivsusega on <b>{pr(ee_d)}% Eesti VKEdest</b> ¦ see on veidi alla ELi keskmise {pr(eu_d)}% (2024)</h2>
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
    <h2 id="h-ta">Eesti teadus- ja arendustegevuse kulu kasvab, aga jääb <b>ELi keskmisest alla</b> ¦ vahe oli {pr(eu_t - ee_t, 2)} protsendipunkti (2024)</h2>
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


# ---------------------------------------------------------------- Põhjamaade võrdlus (100 = Põhjamaade keskmine)

RIIGID7 = ["EE", "FI", "SE", "DK", "NO", "DE", "NL"]
POHJA4 = ["FI", "SE", "DK", "NO"]  # Põhjamaad koos Norraga (ELi skaalal on ainult 3)
# (kataloogi mõõdik, seire näitaja või None, lühinimi, ühik, komakohti, väiksem on parem)
PROFIIL = [
    ("eurostat-isoc-ai-iaiu", "inimeste-tehisaru-kasutus", "Inimesed kasutavad generatiivset tehisaru", "% 16–74-aastastest", 1, False),
    ("eurostat-isoc-ai-iaiu-too", "tooalane-tehisaru-kasutus", "Inimesed kasutavad seda tööl", "% 16–74-aastastest", 1, False),
    ("eurostat-isoc-eb-ai", EB, "Ettevõtted kasutavad tehisaru", "% vähemalt 10 hõivatuga ettevõtetest", 1, False),
    ("eurostat-isoc-ai-iaiuxr-oskus", "tehisaru-oskuse-puudus", "Ei kasuta tehisaru, sest ei oska", "% 16–74-aastastest, väiksem on parem", 1, True),
    ("eurostat-isoc-sk-dskl-i21", "inimeste-digioskused", "Vähemalt baastasemel digioskused", "% 16–74-aastastest", 1, False),
    ("eurostat-isoc-sks-itspt", None, "IKT-spetsialistid hõivatute seas", "% hõivatutest", 1, False),
    ("uis-ikt-lopetajad", None, "IKT eriala lõpetajad", "% kõrgkoolide lõpetajatest", 1, False),
    ("eurostat-rd-e-gerdtot", "ta-kulud", "Teadus- ja arendustegevuse kulu", "% SKPst", 2, False),
    ("uis-teadlased", None, "Teadlased", "miljoni elaniku kohta", 0, False),
]
PP_HINNANG = {"yle": "üle kõigi Põhjamaade", "vahemik": "Põhjamaade vahemikus", "maas": "Põhjamaadest maas, EList eespool",
              "alla_el": "ELi keskmisest maas", "alla_pohja": "alla kõigi Põhjamaade"}
PP_NIMI = {"EE": "Eesti", "FI": "Soome", "SE": "Rootsi", "DK": "Taani", "NO": "Norra", "DE": "Saksamaa", "NL": "Holland"}


def pohjamaade_profiil(A):
    """Üheksa näitajat seitsmes riigis. Seire andmed, kui näitaja on seires; muidu kataloogi välisvaatlused
    (kataloog/vaatlused-valis.csv), mida kataloog/lae_valis.py laeb iga päev otse Eurostati ja UNESCO UISi API-st."""
    from statistics import mean
    S = {}
    for r in A["valis_vaatlused"]:
        if r["vaartus"]:
            S.setdefault(r["moodik"], {}).setdefault(r["riik"], {})[int(r["aasta"])] = float(r["vaartus"])
    out = []
    for mid, nid, nimi, uhik, k, vp in PROFIIL:
        if nid:  # seire enda Eurostati aegrida (uueneb iga päev)
            s = {}
            for v in A["vaatlused"]:
                if v["naitaja"] == nid and v["klass"] == "alus" and v["geo"] in RIIGID7 + [EL]:
                    s.setdefault(v["geo"], {})[v["aasta"]] = v["vaartus"]
            m = A["meta"][nid]
            allikas = (A["naitajad"][nid]["allikas"], A["naitajad"][nid]["andmestik"],
                       A["moodikud"].get(next((x for x in A["moodikud"] if A["moodikud"][x]["naitaja"] == nid
                                               and A["moodikud"][x]["vorreldavus"] == "alus"), ""), {}).get("url") or m["url"])
        else:
            m = A["moodikud"].get(mid)
            s = S.get(mid, {})
            if not s or m is None:
                raise AndmeViga(f"Põhjamaade võrdlus: mõõdik {mid} puudub kataloogis (moodikud.csv või vaatlused-valis.csv)")
            allikas = (m["allikas"].replace("INT-", "").replace("EUROSTAT", "Eurostat"), m["andmestik"], m["url"])
        aastad = sorted({y for g in RIIGID7 for y in s.get(g, {})}, reverse=True)
        a = next((y for y in aastad if y in s.get("EE", {}) and sum(1 for g in RIIGID7[1:] if y in s.get(g, {})) >= 5), None)
        if a is None:
            raise AndmeViga(f"Põhjamaade võrdlus: mõõdikul {mid} pole aastat, kus on Eesti ja vähemalt 5 riiki")
        v = {g: s[g][a] for g in RIIGID7 + [EL] if a in s.get(g, {})}
        ee, el = v["EE"], v.get(EL)
        po = [v[g] for g in POHJA4 if g in v]
        pk = mean(po)
        parem = (lambda x, y: x < y) if vp else (lambda x, y: x > y)
        jrk = sorted((g for g in RIIGID7 if g in v), key=lambda g: v[g] if vp else -v[g])
        if el is not None and parem(el, ee):
            h = "alla_el"
        elif all(parem(ee, x) for x in po):
            h = "yle"
        elif all(parem(x, ee) for x in po):
            h = "maas" if el is not None else "alla_pohja"
        else:
            h = "vahemik"
        out.append(dict(mid=mid, nimi=nimi, uhik=uhik, k=k, vp=vp, a=a, v=v, ee=ee, el=el, pk=pk, po=po, n_po=len(po),
                        koht=jrk.index("EE") + 1, n=len(jrk), hinnang=h, indeks=(pk / ee if vp else ee / pk) * 100,
                        allikas=allikas, seirest=bool(nid)))
    return out


def _arvt(x, k):
    """Arv koos tuhandete tühikuga (4 800)."""
    t = pr(x, k)
    t_int, _, frac = t.partition(",")
    if len(t_int) > 4:
        t_int = f"{int(t_int):,}".replace(",", " ")
    return t_int + ("," + frac if frac else "")


def _pohjamaad(A):
    P = pohjamaade_profiil(A)
    tasemel = [p for p in P if p["hinnang"] in ("yle", "vahemik")]
    maas = [p for p in P if p["hinnang"] not in ("yle", "vahemik")]
    from abi import OMASTAV
    arv = lambda n: OMASTAV[n] if n in OMASTAV else "mitte ühe"  # noqa: E731  omastav: kolme puhul (keeletoimetus 10.11.2026)
    read = []
    for p in P:
        vv = list(p["v"].values())
        lo, hi = min(vv), max(vv)
        pad = (hi - lo) * 0.08 or 1
        lo, hi = max(0, lo - pad), hi + pad
        x = lambda z: (z - lo) / (hi - lo) * 100  # noqa: E731
        punktid = "".join(f'<i class="pp-p" style="left:{x(z):.2f}%" title="{e(PP_NIMI[g])} {pr(z, p["k"])}"></i>'
                          for g, z in p["v"].items() if g not in ("EE", EL))
        ala = f'<span class="pp-ala" style="left:{x(min(p["po"])):.2f}%;width:{x(max(p["po"])) - x(min(p["po"])):.2f}%"></span>'
        el = f'<i class="pp-el" style="left:{x(p["el"]):.2f}%" title="EL {pr(p["el"], p["k"])}"></i>' if p["el"] is not None else ""
        ee = f'<i class="pp-ee" style="left:{x(p["ee"]):.2f}%"></i>'
        u = "%" if p["uhik"].startswith("%") else ""
        read.append(f'<div class="pp-rida"><span class="n">{e(p["nimi"])}<small>{e(p["uhik"])} · {p["a"]}</small></span>'
                    f'<span class="pp-rada" aria-hidden="true">{ala}{punktid}{el}{ee}</span>'
                    f'<span class="v"><b>{_arvt(p["ee"], p["k"])}{u}</b> {p["koht"]}./{p["n"]}</span></div>')
    t_read = [[f'<b>{e(p["nimi"])}</b><small>{e(p["uhik"])}, {p["a"]}</small>', _arvt(p["ee"], p["k"]),
               _arvt(p["pk"], p["k"]), f'{pr(p["indeks"], 0)}', e(PP_HINNANG[p["hinnang"]]),
               f'{p["koht"]}./{p["n"]}'] for p in P]
    allikad = []
    for p in P:
        nm = f'{p["allikas"][0]}, {p["allikas"][1]}'
        if all(nm != x[0] for x in allikad):
            allikad.append((nm, p["allikas"][2], ""))
    ettev = next(p for p in P if p["mid"] == "eurostat-isoc-eb-ai")
    vaike = lambda t: t if t[1:2].isupper() else t[:1].lower() + t[1:]  # noqa: E731  „IKT“ jääb suurtähtedega
    nimed = lambda pp: ", ".join(vaike(p["nimi"]) for p in pp)  # noqa: E731
    return f"""
<section class="jaotis" id="pohjamaad" aria-labelledby="h-pohjamaad">
  <header>
    <h2 id="h-pohjamaad">Üheksast näitajast on Eesti {arv(len(tasemel))} puhul Põhjamaade tasemel ¦ <b>{arv(len(maas))} puhul jääb Põhjamaadest maha</b></h2>
    <p class="alam">Seitse riiki igal näitajal: Eesti, Soome, Rootsi, Taani, Norra, Saksamaa ja Holland. Iga rida on oma skaalal, ridu omavahel ei võrrelda.</p>
    {vastavus("osaliselt", "Näitajad on samast küsimustikust kõigis riikides, aga need mõõdavad eri asju (inimesed, ettevõtted, kulud). Ühte koondnumbrit neist ei arvutata.")}
  </header>
  <figure aria-labelledby="g-pohjamaad">
    <figcaption><span class="gt" id="g-pohjamaad">Eesti seitsme riigi seas, iga näitaja oma skaalal</span>
      <span class="gs"><i class="pp-leg ala"></i> Põhjamaade vahemik (Soome, Rootsi, Taani, Norra) · <i class="pp-leg el"></i> ELi keskmine · <i class="pp-leg ee"></i> Eesti · paremal Eesti väärtus ja koht.</span></figcaption>
    <div class="pp">{"".join(read)}</div>
    {allikarida(allikad)}
  </figure>
  <div class="kulg">{faktid([
      ("Maas", "risk", f'Põhjamaadest maas: {e(nimed(maas))}.' if maas else "Eesti ei jää üheski näitajas Põhjamaadest maha."),
      ("Põhjamaade tasemel", "s", f'{e(nimed(tasemel)[:1].upper() + nimed(tasemel)[1:])}.' if tasemel else "Mitte üheski näitajas."),
      ("Kuidas arvutatud", "", "Arvutatud: indeks = Eesti väärtus / Põhjamaade keskmine × 100 (näitajal „ei oska“ vastupidi, sest väiksem on parem). "
                               "Aasta on uusim, kus on olemas Eesti ja vähemalt viis teist riiki."),
      ("Erinev keskmine", "", f'Siin on Põhjamaade keskmine neli riiki koos Norraga. Lehe Kasutus vahe Põhjamaadega arvutab ainult kolm ELi Põhjamaad, '
                              f'seepärast on ettevõtete vahe seal teine number (siin Eesti {pr(ettev["ee"])}% ja Põhjamaade keskmine {pr(ettev["pk"])}%, {ettev["a"]}).'),
  ])}</div>
  <details>
    <summary>Näita andmetabelit ja indeksit</summary>
    <div>{tabel(["Näitaja", "Eesti", "Põhjamaade keskmine", "Indeks (100 = Põhjamaad), arvutatud", "Hinnang", "Koht"], t_read,
                pealdis="Eesti ja Põhjamaade keskmine üheksas näitajas")}
      <p>Kuus näitajat tulevad seire enda Eurostati andmetest ja uuenevad iga päev. IKT-spetsialistid tulevad Eurostatist ning IKT lõpetajad ja teadlased UNESCO UISist. Seire laeb need iga päev otse allika API-st.</p></div>
  </details>
</section>"""


def _arenguseire(A):
    L = A["leiud"]
    j = [L["ars-jareldus-digi"], L["ars-jareldus-juhtimine"], L["ars-jareldus-koostoo"]]
    risk = L["ars-risk-lohe"]
    li = "".join(f'<li><span class="nr">{i}</span><div><h3>{e(r["leid"].split(":")[0])}</h3><p>{e(r["leid"].split(": ", 1)[1][:1].upper() + r["leid"].split(": ", 1)[1][1:])}</p></div></li>'
                 for i, r in enumerate(j, 1))
    return f"""
<section class="jaotis" id="arenguseire" aria-labelledby="h-arenguseire">
  <header>
    <h2 id="h-arenguseire">Ettevõtteid tuleb toetada tervikuna, <b>mitte ainult tööriistade katsetamisel</b> ¦ nii järeldas Arenguseire Keskus</h2>
    <p class="alam">Soovitus · Arenguseire Keskus. {e(j[0]["markus"])}</p>
  </header>
  <ol class="sammud">{li}</ol>
  {faktid([("Risk · Arenguseire Keskus", "risk", e(risk["leid"]))], koik_lahti=True)}
  {allikarida([(j[0]["allikas"], j[0]["url"], kp(j[0]["avaldatud"]) + "; " + j[0]["kontrollitud"])])}
</section>"""


def _gem(A, ee_el):
    """Kadri 9.11.2026 („lisa“, kolleegi soovitus): GEMi ekspertide hinnang Eurostati mõõdetud kasutuse kõrvale.
    Eraldi sakk ja oma 0–10 skaala: hinnang ja ettevõtete osa ei ole võrreldavad, seega ei ole nad samal teljel."""
    L = A["leiud"]["gem-ai-teadlikkus"]
    v = float(next(r for r in A["leiud_arvud"] if r["leid"] == L["id"])["vaartus"])
    if not 0 <= v <= 10:
        raise AndmeViga("GEMi ekspertide hinnang peab olema skaalal 0–10")
    tase = "suurepärane" if v >= 7 else "piisav" if v >= 5 else "ebapiisav"
    x = lambda t: f"{t * 10:g}%"  # noqa: E731
    tsoonid = "".join(f'<span class="gem-tsoon {k}" style="left:{x(a)};width:{x(b - a)}"><small>{e(n)}</small></span>'
                      for a, b, k, n in [(0, 5, "alla", "ebapiisav"), (5, 7, "piisav", "piisav"), (7, 10, "hea", "suurepärane")])
    return f"""
<section class="jaotis" id="gem" aria-labelledby="h-gem">
  <header>
    <h2 id="h-gem">Eesti eksperdid hindavad uute ettevõtjate tehisaruteadlikkust <b>{pr(v)} punktiga 10-st</b>, mis on GEM&#8209;i skaalal {tase}</h2>
    <p class="alam"><b>Eksperthinnang, mitte mõõtmine.</b> Global Entrepreneurship Monitor (GEM) küsis {L["aasta"]}. aastal igas riigis ekspertidelt,
      kui teadlikud on uued ettevõtjad vajadusest tehisarulahendusi arendada ja kasutada. Skaala 0–10.</p>
  </header>
  <figure class="gem-fig" aria-labelledby="g-gem">
    <figcaption><span class="gt" id="g-gem">Ekspertide hinnang: uute ettevõtjate teadlikkus tehisaru vajadusest, Eesti {L["aasta"]}, 0–10</span></figcaption>
    <div class="gem-skaala" role="img" aria-label="Eesti {pr(v)} punkti 10-st; alla 5 ebapiisav, 5–7 piisav, 7 või rohkem suurepärane">
      {tsoonid}
      <span class="gem-mark" style="left:{x(v)}"><b>Eesti {pr(v)}</b></span>
    </div>
    <div class="gem-telg" aria-hidden="true">{"".join(f'<span style="left:{x(t)}">{t}</span>' for t in (0, 5, 7, 10))}</div>
  </figure>
  {faktid([
      ("Mida see ei näita", "risk",
       "See ei ütle, kui paljud ettevõtted tehisaru kasutavad. Kasutust mõõdab Eurostat (saki „Kasutus ELis“ all: "
       f"Eestis {pr(ee_el['vaartus'])}% vähemalt 10 hõivatuga ettevõtetest, {ee_el['aasta']}). Need kaks numbrit ei ole võrreldavad: "
       "üks on ekspertide hinnang uutele ettevõtjatele, teine ettevõtete osa."),
      ("Teised riigid", "", "GEM küsis sama 53 riigis. Ebapiisavaks (alla 5) hinnati neist kuus: Ungari, Angola, Lõuna-Aafrika, "
       "Maroko, Alžeeria ja El Salvador."),
      ("Mida GEM ei avalda", "", "GEM küsis ka uutelt ettevõtjatelt, kas tehisaru muutub nende ärile lähema kolme aasta jooksul väga "
       "oluliseks. Eesti number on raportis ainult joonisel (7.4), mitte tekstis, seepärast seda siin ei ole."),
  ])}
  {allikarida([("GEM 2025/2026 Global Report", L["url"], kp(L["avaldatud"]) + "; " + L["koht"] + "; " + L["kontrollitud"])])}
</section>"""


LIGIPAAS_NIMI = {"avab_koigile": "Avab kõigile", "avab_ehitamise_piirab_avaldamise": "Lubab ehitada, piirab avaldamist",
                 "piirab_rolliga": "Piirab rolliga", "keelab": "Keelab"}
LIGIPAAS_TEGU = {"avab_koigile": "avas tööriistad kõigile", "avab_ehitamise_piirab_avaldamise": "lubas ehitada, aga piiras avaldamist",
                 "piirab_rolliga": "piiras neid rolliga", "keelab": "keelas need"}


def _ligipaas(A):
    """Kes tohib tehisaru tööriistu ja agente kasutada (Kadri 9.11.2026 12:32: saidile kohe, märkega „töös, kogumine käib“).
    Andmed sisu/ligipaas.json (sait/vota_kaasa.py). Valim on uudistepõhine, seega näitame arve, mitte osakaale."""
    from abi import a as a_
    from komponendid import tabel
    S = (A.get("ligipaas") or {}).get("sundmused") or []
    if not S:
        return ""
    for r in S:
        if r["ligipaas"] not in LIGIPAAS_NIMI:
            raise AndmeViga(f"ligipaas.json: tundmatu rühm {r['ligipaas']!r} ({r['ettevote']})")
        if not r.get("url"):
            raise AndmeViga(f"ligipaas.json: otsusel puudub link ({r['ettevote']})")

    def avab(r):
        return r["ligipaas"].startswith("avab")

    def lyh(n):
        return n.split()[0] if len(n) > 12 else n

    def aastad(rr):
        a = sorted({r["kuupaev"][:4] for r in rr})
        return a[0] if len(a) == 1 else f"{a[0]}–{a[-1]}"

    def kiip(r):
        eesti = " · Eesti" if r["piirkond"] == "EE" else ""
        return (f'<li class="lp-kiip{" ava" if avab(r) else ""}"><b>{e(lyh(r["ettevote"]))}</b> '
                f'<small>{r["kuupaev"][5:7]}.{r["kuupaev"][:4]}{eesti}</small></li>')

    def lahter(rr):
        if not rr:
            return '<span class="lp-tyhi">–</span>'
        return "<ul>" + "".join(kiip(r) for r in sorted(rr, key=lambda r: r["kuupaev"])) + "</ul>"

    osad = [f"{sonaga(len(rr))} {LIGIPAAS_TEGU[k]} ({aastad(rr)})" for k in LIGIPAAS_NIMI
            for rr in [[r for r in S if r["ligipaas"] == k]] if rr]
    pealkiri = f"{sonaga(len(S), 'seestytlev').capitalize()} kogutud otsusest " + osad[0] + (" ¦ " + (", ".join(osad[1:-1]) + " ja " if len(osad) > 2 else "") + osad[-1] if len(osad) > 1 else "")
    a0, a1 = int(min(r["kuupaev"] for r in S)[:4]), int(max(r["kuupaev"] for r in S)[:4])
    read_aastad = []
    for y in range(a1, a0 - 1, -1):
        yy = [r for r in S if r["kuupaev"][:4] == str(y)]
        read_aastad.append(f'<div class="lp-rida" role="listitem"><span class="lp-aasta">{y}</span>'
                           f'<div>{lahter([r for r in yy if avab(r)])}</div><div>{lahter([r for r in yy if not avab(r)])}</div></div>')
    # Eesti avaliku sektori number otse Riigikontrolli ülevaatest (TOOELU ligipääsu lõime tekst 9.11.2026, algallikast kontrollitud)
    rk = A["leiud"].get("rk-ai-kord")
    eesti = []
    if rk:
        n = {r["ruhm"]: int(r["vaartus"]) for r in A["leiud_arvud"] if r["leid"] == "rk-ai-kord"}
        eesti = [("Eesti asutused", "s", f'Riigikontrolli küsitluses ({rk["aasta"]}) kasutas {n["kasutab"]} vastanud asutust {n["vastas"]}-st '
                  f'välismaiseid tehisaru valmislahendusi, aga <b>{n["korrata"]} asutusel puudus asutusesisene kord</b>, kuidas neid '
                  f'korrektselt ja turvaliselt kasutada ({a_(rk["url"], "Riigikontroll " + kp(rk["avaldatud"]))}, {e(rk["koht"].split(";")[0])}). '
                  "See on avalik sektor, mitte ettevõtted, ja ainult küsitlusele vastanud asutused.")]
    tabel_read = []
    for r in S:
        kus = "Eesti" if r["piirkond"] == "EE" else "maailm"
        # „jaanuar 2026 (juurutamise algus)“: täpse kuupäeva asemel allika enda täpsus
        tabel_read.append([e(r["kuupaev_tapsus"]) if r.get("kuupaev_tapsus") else kp(r["kuupaev"]),
                           f'<b>{e(r["ettevote"])}</b><small>{e(r["sektor"])} · {kus}</small>',
                           f'<span class="lp-kiip{" ava" if avab(r) else ""}">{e(LIGIPAAS_NIMI[r["ligipaas"]])}</span>',
                           e(r["tekst"]), e(r["pohjus"]) or "ettevõte ei kommenteerinud",
                           f'<a href="{e(r["url"])}">{e(r["allikas"] or "allikas")}</a>'])
    K = A.get("ligipaas_kontekst") or {}
    for r in (K.get("riigid") or []) + (K.get("uuringud") or []):
        if not str(r.get("url", "")).startswith("https://"):
            raise AndmeViga(f"ligipaas-kontekst.json: real puudub https-link ({r.get('riik') or r.get('uuring')})")
    kontekst = ""
    if K.get("riigid"):
        # Kadri „jah, avalda“ 9.11.2026 19:59 (ligipääsu lõime LISA 9.11 õhtu); read algallikast üle kontrollitud
        kontekst += f"""
  <div class="lp-lisa" id="ligipaas-riigid">
    <h3>Soome, Holland, Ühendkuningriik ja USA lubavad ametnikel tehisaru kasutada tingimustega</h3>
    <p>Piirid tulevad peamiselt andmetest ja mõjust. Üksikuid tööriistu on keelatud turvariski tõttu: näiteks Austraalia keelas 4.02.2025 DeepSeeki kõigis riigiasutuste süsteemides ja seadmetes (<a href="https://www.protectivesecurity.gov.au/publications-library/direction-001-2025-deepseek-products-applications-and-web-services">PSPF Direction 001-2025</a>).</p>
    {tabel(["Riik", "Mida juhend ütleb", "Allikas"],
           [[f"<b>{e(r['riik'])}</b>", e(r["tekst"]), f'<a href="{e(r["url"])}">{e(r["allikas"])}</a>'] for r in K["riigid"]],
           pealdis="Kuidas teised riigid ametnike tehisaru kasutust korraldavad", numbrid=[])}
    {faktid([("Kuidas lugeda", "", "Neli riiki on valik, mitte kõigi riikide ülevaade. Juhendid on võrdlusmaterjal, Eestile mitte siduvad. "
              "Soome juhendi lehte ei saanud otse avada, rida põhineb OECD.AI kirjeldusel.")])}
  </div>"""
    if K.get("uuringud"):
        kontekst += f"""
  <div class="lp-lisa" id="ligipaas-uuringud">
    <h3>Kasu on päris, aga mitte igas ülesandes, ja kasutaja hinnang võib eksida</h3>
    <p>Katsetes tegid tehisaru kasutajad tööd rohkem ja kiiremini. Ühes katses said nad tehisarule sobimatus ülesandes vähem õigeid lahendusi, teises hindasid kogenud arendajad oma kiirust valesti.</p>
    {tabel(["Leid", "Uuring", "Tõendi liik"],
           [[e(r["leid"]), f'<a href="{e(r["url"])}">{e(r["uuring"])}</a>', e(r["liik"])] for r in K["uuringud"]],
           pealdis="Uuringud tehisaru mõjust töö tulemusele", numbrid=[])}
    {faktid([("Mida see ei näita", "risk", "Neli uuringut on valik, mitte süstemaatiline ülevaade. Need kasutasid 2022–2025 tööriistu ja erasektori töötajaid, mitte riigiametnikke ega tänaseid agente.")])}
  </div>"""
    return f"""
<section class="jaotis" id="ligipaas" aria-labelledby="h-ligipaas">
  <header>
    <h2 id="h-ligipaas">{e(pealkiri)}</h2>
    <p class="alam"><span class="lp-toos">Töös: kogumine käib</span> Kes tohib ettevõttes tehisaru tööriistu ja agente kasutada?
      Kogume ettevõtete otsuseid uudistest ja ettevõtete endi teadetest iga päev. Põhjus on ettevõtte enda sõnadega, mitte seire hinnang.</p>
  </header>
  <figure aria-labelledby="g-ligipaas">
    <figcaption><span class="gt" id="g-ligipaas">Otsused aastate kaupa: vasakul avamised, paremal piiramised ja keelud</span>
      <span class="gs">Iga kiip on üks otsus (kuu/aasta). Sama ettevõte võib olla mitu korda.</span></figcaption>
    <div class="lp-ajajoon" role="list" aria-label="Otsused aastate kaupa">
      <div class="lp-rida lp-pais" aria-hidden="true"><span></span><span>Avab</span><span>Piirab või keelab</span></div>
      {"".join(read_aastad)}
    </div>
  </figure>
  {faktid(eesti + [("Valim on kallutatud", "risk", "Otsused tulevad uudistest, seepärast on neis rohkem suuri ja tuntud ettevõtteid. "
            "Näitame arve, mitte osakaale: see ei ütle, kui suur osa ettevõtetest tööriistu lubab või keelab.")])}
  {tabel(["Kuupäev", "Ettevõte", "Otsus", "Mida otsustati", "Põhjus ettevõtte sõnul", "Allikas"], tabel_read,
         pealdis="Ettevõtete otsused tehisaru tööriistade kasutamise kohta, uuemad eespool", numbrid=[])}
  {kontekst}
</section>"""


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
    # Päise plaadid käsitsi valitud kontekstiga (ver1 laiendus, Kadri 8.11.2026). Siht on esimese plaadi ribal,
    # kolmas plaat näitab vahet Põhjamaadega, millest räägib ka lead.
    from abi import a
    from lehed_ulevaade import _p, el_jarjestus, kpi_pais, kpi_plaat, kpi_riba
    y = ee_el["aasta"]
    j = el_jarjestus(EB, koht_praegu=koht, aasta_praegu=y)
    if not j:
        raise AndmeViga("Ettevõtete koha muutus vajab faili sisu/el-jarjestus.csv")
    k_ee = j[1]
    y0 = min(k_ee)
    pm = sum(andmed.leia(A, EB, g, y)["vaartus"] for g in POHJAMAAD) / len(POHJAMAAD)
    pm0 = sum(andmed.leia(A, EB, g, 2023)["vaartus"] for g in POHJAMAAD) / len(POHJAMAAD)
    vahe, vahe0 = pm - ee_el["vaartus"], pm0 - andmed.leia(A, EB, "EE", 2023)["vaartus"]
    sv = float(siht["siht"])
    aside = kpi_pais(
        kpi_plaat("ev-kasutus", "Kasutab tehisaru (10+ hõivatut)", f'{pr(ee["vaartus"])}%', f'{ee["aasta"]} · siht {pr(sv, 0)}%',
                  {"muutus": (f'{ee["aasta"] - 1}. aastaga ei võrrelda', "uus tegevusalade klassifikaator (EMTAK 2025)"),
                   "riba": kpi_riba(ee["vaartus"], 100, siht=sv, fookus=True, siht_tekst=f'siht {pr(sv, 0)}% ({siht["aasta"]})')},
                  a(ee["url"], "Statistikaamet " + ee["allikas"].split("tabel ")[-1]), fookus=True),
        kpi_plaat("ev-koht", "Koht ELis", f"{koht}.", f"/ {n_el} · {y}",
                  {"muutus": (f"{k_ee[y0] - koht} kohta üles", f'{y0}: {k_ee[y0]}. koht · Eesti {pr(ee_el["vaartus"])}%'),
                   "riba": kpi_riba(ee_el["vaartus"], 100, vrd=eu["vaartus"])},
                  a("https://ec.europa.eu/eurostat/databrowser/view/isoc_eb_ai/default/table", "Eurostat isoc_eb_ai")),
        kpi_plaat("ev-pohja", "Vahe Põhjamaade keskmisega", f"{pr(vahe)}", f"protsendipunkti · {y}",
                  {"muutus": (f"{_p(vahe - vahe0)} protsendipunkti 2023. aastast", f"2023: {pr(vahe0)} · Soome, Rootsi, Taani")},
                  a("https://ec.europa.eu/eurostat/databrowser/view/isoc_eb_ai/default/table", "Eurostat isoc_eb_ai")),
    )
    lead = ("Kasutus kasvab kiiresti, aga vahe Põhjamaadega on protsendipunktides suurenenud. "
            "Eesti andmetel on tehisaru seotud suurema tootlikkusega alles siis, kui muutub ka töökorraldus.")
    # Teemamall A (Kadri 8.11.2026): andmed sakkides, siis uuringud, väited, reeglid, allikad
    import teemamall as tm
    from lehed_ulevaade import vaite_teema
    U = A["uuringud"]
    kas = lisa_sihid(A, _kasutus(A), "kasutus", "ee-ettevotted-75")
    jagu = kas.index('<section class="jaotis" id="kasutus-uued"')
    sec_andmed = tm.andmesakid("ettevotted", "Uuri andmeid: kasutus ELis ja teiste riikide 2026. aasta numbrid",
                               "ELi võrdlus on Eurostati aasta; riikide uued numbrid ja ekspertide hinnang on eraldi, sest need ei sobi ELi skaalale.", [
        ("kasutus", "Kasutus ELis", kas[:jagu]),
        ("uued", "Riikide 2026. aasta numbrid", kas[jagu:]),
        ("gem", "Ekspertide hinnang (GEM)", _gem(A, ee_el)),
    ])
    lyh = lambda k: e(tm.esimene_lause(U[k]["leid"]))  # noqa: E731
    t_uuringud = tm.uuringute_plokk(vaated, [
        ("Eesti", f'{lyh("vahter2026")} ({e(U["vahter2026"]["autorid"].split(",")[0])} {U["vahter2026"]["aasta"]})', "ettevotted", "tootlikkus"),
        ("Eesti", f'{lyh("oska2025")} (OSKA {U["oska2025"]["aasta"]})', "ettevotted", "tootlikkus"),
        ("OECD", f'{lyh("calvino2023")} (Calvino ja Fontanelli {U["calvino2023"]["aasta"]})', "ettevotted", "tootlikkus"),
        ("Katse", f'Firmad, kes nägid teiste ümberkorraldatud töövooge, leidsid 44% rohkem kasutusviise ja teenisid 1,9 korda rohkem tulu (Kim jt {U["kim2026"]["aasta"]}).', "too", "ulesanded"),
    ], [("ettevotted", "Tootlikkus ja võimekus", "tootlikkus")])
    t_vaited = tm.vaidete_plokk(A, vaated, "ettevotted", vaite_teema)
    t_reeglid = tm.reeglite_plokk(A, vaated, ["ai-uldkohaldamine"])  # läbipaistvus, nt klienditeeninduse vestlusrobot
    t_allikad = tm.allikate_plokk([
        (f"Kasutus, {ee['allikas']}", ee["url"], ee["avaldatud"], f"{ee['aasta']}, vähemalt 10 hõivatuga ettevõtted"),
        ("ELi võrdlus, Eurostat isoc_eb_ai", "https://ec.europa.eu/eurostat/databrowser/view/isoc_eb_ai/default/table",
         ee_el.get("avaldatud") or None, f"{y}, ELi riigid"),
        ("Ekspertide hinnang, GEM 2025/2026 Global Report", A["leiud"]["gem-ai-teadlikkus"]["url"],
         A["leiud"]["gem-ai-teadlikkus"]["avaldatud"], "2025, eksperthinnang 0–10, mitte mõõtmine",
         kp(A["leiud"]["gem-ai-teadlikkus"]["avaldatud"])),
        (f"Siht, {siht['allikas']}", siht["url"], siht["kontrollitud"], f"{pr(sv, 0)}% aastaks {siht['aasta']}; kontrollitud"),
        ("Asutuste tehisaru kord, Riigikontroll", A["leiud"]["rk-ai-kord"]["url"], A["leiud"]["rk-ai-kord"]["avaldatud"],
         "2025, küsitlusele vastanud 48 asutust"),
    ])
    return jaga(A, vaade, lead, [], [
        ("andmed", [("andmed", "Andmed")], sec_andmed),
        ("ligipaas", [("ligipaas", "Kes tohib tööriistu kasutada")], _ligipaas(A)),
        ("teema-lopp", [("t-uuringud", "Uuringud"), ("t-vaited", "Väited"), ("t-reeglid", "Reeglid"), ("t-allikad", "Allikad")],
         tm.teema_lopp(t_uuringud, t_vaited, t_reeglid, t_allikad)),
        ("tootlikkus", [("tootlikkus", "Tootlikkus")], _tootlikkus(A)),
        ("voimekus", [("digi", "Digiintensiivsus"), ("ta", "Teadus ja arendus")],
         lisa_sihid(A, lisa_sihid(A, _digi_ja_ta(A), "digi", "el-digiintensiivsus-90"), "ta", "el-ta-3")),
        ("arenguseire", [("arenguseire", "Arenguseire järeldused")], _arenguseire(A)),
        ("pohjamaad", [("pohjamaad", "Põhjamaade võrdlus")], _pohjamaad(A)),
    ], aside=aside)


# ---------------------------------------------------------------- Saidikaart

def saidikaart(A, vaade, vaated):
    read = []
    for v in vaated:
        nimi = v["menuu"] or {"avaleht": "Avaleht", "saidist": "Mis see sait on", "kuidas": "Kuidas lugeda", "saidikaart": "Saidikaart"}[v["id"]]
        link = f'<a href="{v["fail"]}">{e(nimi)}</a>' if v["olek"] == "valmis" else e(nimi)
        if v.get("alamlehed") and v["olek"] == "valmis":
            link += "<small>alamlehed: " + ", ".join(f'<a href="{s["fail"]}">{e(s["nimi"])}</a>' for s in v["alamlehed"]) + "</small>"
        read.append(f'<tr><td>{link}<small>{e(v["koht"])} · {e(v["kusimused"])}</small></td><td>{e(v["kusimus"])}</td>'
                    f'<td class="h1">{taida(v["h1"], A).split(" ¦ ")[0]}</td><td>{e(v["osad"])}</td></tr>')
    pais = "".join(f'<th scope="col">{t}</th>' for t in ["Vaade", "Lugeja küsimus", "Pealkiri (vastus)", "Mis vaates on"])
    return f"""
<div class="pea yks">
  <div class="pea-tekst">
    <h1>{taida(vaade["h1"], A)}</h1>
    <p class="lead">Saidil on {sum(v["olek"] == "valmis" for v in vaated)} vaadet; iga rea pealkiri on sama, mis vaate lehel.</p>
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
            "avalik-sektor": _t.avalik_sektor, "reeglid": _t.reeglid, "kas-tosi": _u.kas_tosi, "kuidas": _u.kuidas, "saidist": _u.saidist,
            "hanked": _n.hanked, "uudised": _n.uudised}
