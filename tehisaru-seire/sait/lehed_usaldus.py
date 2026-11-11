"""Usalduse vaated ja sisenemine: Kas see on tõsi?, Avaleht, Kuidas lugeda (5.11.2026)."""
import re
import andmekiht as andmed
from abi import ARVSONAD, OMASTAV, SEESTYTLEV, a, jaga, kontrolli, link, pea, sonaga
from andmekiht import EL, AndmeViga
from komponendid import (allikarida, e, faktid, kohariba, kp, lihtribad, osad, pr, riik, tabel, vastavus)
from pealkiri import taida
from kest import AUTOR, autori_aastad

# Väidete hinnangud ja nende raskus; sama loend on vanas raportis (raportid/koosta.py HINNANGUD)
HINNANGUD = {
    "Vale tõlgendus": (0, "Lause ütleb allikast midagi muud, kui allikas ütles."),
    "Nimetaja vale": (0, "Protsent on arvutatud teisest rühmast, kui lause ütleb."),
    "Sõnastus liialdab": (0, "Lause ütleb rohkem, kui allikas ütles, näiteks „kaob“, kui allikas ütles „puudutab“."),
    "Suurus ebakindel": (1, "Suund on tõenäoliselt õige, täpne suurus mitte."),
    "Vale": (0, "Väide on algallikaga vastuolus, näiteks vale aasta number."),
    "Osaliselt tõsi": (1, "Osa väitest vastab tõenditele, osa on mõõtmata või ütleb rohkem."),
    "Täpsustus puudu": (1, "Number vastab allikale, aga lausest puudub, keda või mida see kirjeldab."),
    "Vastab allikale": (2, "Lause ütleb sama, mida allikas."),
}
RASKUS = {0: ("Ütleb muud kui allikas", "risk"), 1: ("Vajab täpsustust", "warn"), 2: ("Vastab allikale", "ok")}
NAITAJA_NIMI = {
    "ettevotete-tehisaru-kasutus": "Ettevõtete tehisaru kasutus", "inimeste-tehisaru-kasutus": "Inimeste tehisaru kasutus",
    "tooalane-tehisaru-kasutus": "Tööalane kasutus", "tehisaru-oskuse-puudus": "„Ei oska“",
    "inimeste-digioskused": "Digioskused", "ettevotete-digiintensiivsus": "Ettevõtete digiintensiivsus",
    "ta-kulud": "Teadus- ja arendustegevuse kulu",
}
NAITAJA_VAADE = {"ettevotete-tehisaru-kasutus": "ettevotted", "ettevotete-digiintensiivsus": "ettevotted", "ta-kulud": "ettevotted",
                 "inimeste-tehisaru-kasutus": "inimesed", "tooalane-tehisaru-kasutus": "inimesed",
                 "tehisaru-oskuse-puudus": "inimesed", "inimeste-digioskused": "inimesed"}


def _raskus(v):
    if v["hinnang"] not in HINNANGUD:
        raise AndmeViga(f"Väitel {v['id']} on tundmatu hinnang {v['hinnang']!r}")
    return HINNANGUD[v["hinnang"]][0]


# ---------------------------------------------------------------- Kas see on tõsi?

PEAMINE_LEID = ("worthynews-2024-imf-40", "247wallst-2025-goldman-300m")


def kas_tosi_h1(A):
    """Pealkiri on konkreetne leid, mitte suhe (Kadri otsus 6.11.2026): väited valis seire ise,
    suhe „neli kaheksast“ kutsuks üldistama, et pool avalikest väidetest on vale."""
    ids = {v["id"] for v in A["vaited"]}
    if not all(i in ids for i in PEAMINE_LEID):
        raise AndmeViga("Väidete pealkiri räägib IMFi ja Goldman Sachsi pealkirjadest, aga neid väiteid pole enam loendis")
    lahti = sum(1 for l in A["lahknevused"] if l["staatus"] == "selgitamata")
    return (f"IMFi ja Goldman Sachsi **„puudutab“ on pealkirjades muutunud sõnaks „kaob“** ¦ "
            f"{ARVSONAD[lahti]} Eurostati ja Statistikaameti lahknevust on selgitamata.")


def kas_tosi(A, vaade, vaated=None):
    V = sorted(A["vaited"], key=lambda v: (_raskus(v), v["kuupaev"]))
    n = len(V)
    loend = {k: sum(1 for v in V if _raskus(v) == k) for k in RASKUS}
    L = A["lahknevused"]
    lahti = [l for l in L if l["staatus"] == "selgitamata"]
    kontrolli(vaade, "IMFi ja Goldman Sachsi", f"{ARVSONAD[len(lahti)]} Eurostati ja Statistikaameti lahknevust")

    o_read = [(RASKUS[k][0], loend[k], RASKUS[k][1], e({0: "Lause ütleb midagi muud või rohkem, kui allikas ütles.",
                                                       1: "Number on õige, aga lausest puudub, keda see kirjeldab, või suurus on ebakindel.",
                                                       2: "Lause ütleb sama mida allikas."}[k])) for k in RASKUS if loend[k]]
    kaardid, lisa = [], []
    for v in V:
        k = _raskus(v)
        alg = (f'<p class="alg"><span>Algallikas:</span> {a(v["algallika_url"], v["algallikas"]) if v.get("algallika_url") else e(v["algallikas"])}'
               f'{": " + e(v["algallikas_utleb"]) if v["algallikas_utleb"] else ""}</p>') if v["algallikas"] else ""
        # Üks rida väite kohta: hinnang | väide ja kes ütles | õige lause ja „Miks“ klõpsu taga (kaarte ei ole)
        (kaardid if k == 0 else lisa).append(f"""<li class="vaide {RASKUS[k][1]}">
  <p class="hinnang"><span class="mark-l {"risk" if k == 0 else ""}">{e(v["hinnang"])}</span><small>{e(RASKUS[k][0].lower())}</small></p>
  <div><blockquote>{e(v["vaide"])}</blockquote>
  <p class="kes">{a(v["url"], v["valjaanne"])}, {kp(v["kuupaev"])}</p></div>
  <div>{f'<p class="oige"><span>Õige lause:</span> {e(v["oige_lause"])}</p>' if v["oige_lause"] else ""}
  <details><summary>Miks</summary><div>{alg}<p>{e(v["selgitus"])}</p></div></details></div>
</li>""")
    sec_v = f"""
<section class="jaotis" id="vaited" aria-labelledby="h-vaited">
  <header>
    <h2 id="h-vaited">{SEESTYTLEV[n].capitalize()} väitest <b>{ARVSONAD[loend[0]]} ütleb muud kui allikas</b>, {ARVSONAD[loend[1]]} vajab täpsustust</h2>
    <p class="alam">Seire kontrollis avalikke väiteid, mis tundusid kahtlased, ja võrdles neid algallikaga. See ei näita, kui täpne on meedia keskmiselt. Väide kuulub väljaandele, mitte üksikule ajakirjanikule.</p>
  </header>
  <figure aria-labelledby="g-vaited">
    <figcaption><span class="gt" id="g-vaited">Kontrollitud väited hinnangu järgi, väidete arv</span></figcaption>
    {osad(o_read, f"{n} väidet")}
  </figure>
  <ul class="vaited">{"".join(kaardid)}</ul>
  {f'<details class="lisa"><summary>Näita veel {len(lisa)} väidet{", mis vajavad täpsustust" if not loend[2] else ""}</summary><ul class="vaited">{"".join(lisa)}</ul></details>' if lisa else ""}
</section>"""

    # Lahknevused
    l_kaardid = []
    for l in L:
        nid = l["naitaja"]
        y = int(l["aasta"])
        eu = andmed.leia(A, nid, "EE", y)
        if l["kood"] == "C5":
            teine = next(t for t in A["naitajad"][nid]["teised_allikad"] if "IT149" in t["allikas"])
            t_nimi, t_v, t_url = "Statistikaamet, IT149", float(teine["vaartus"]), teine["url"]
        else:
            t = andmed.kataloogist(A, "sa-it72-oskus", "EE", y)
            t_nimi, t_v, t_url = "Statistikaamet, IT72", t["vaartus"], t["url"]
        hup = next((r for r in A["riskid"] if r["liik"] == "hupotees" and r["naitaja"] == nid), None)
        lopp = max(eu["vaartus"], t_v) * 1.25
        l_kaardid.append(f"""<div class="lahk">
  <h3>{e(l["kood"])}: {e(NAITAJA_NIMI[nid])}, Eesti {y}</h3>
  {lihtribad([("Eurostat", eu["vaartus"], None), (t_nimi, t_v, None)], lopp, 10 if lopp > 20 else 5, "%", fookus=0, k=1)}
  <p class="allikas">Allikad: {a(eu["url"], eu["allikas"])}; {a(t_url, t_nimi)}.</p>
  {faktid([("Staatus", "risk", e(l["staatus"])), ("Järgmine samm", "s", e(l["jargmine_samm"]))])}
  {f'<details><summary>Miks numbrid võivad erineda (kontrollimata)</summary><p>{e(hup["selgitus"])}</p></details>' if hup else ""}
  <p>{link(vaated, NAITAJA_VAADE[nid], "Number vaates " + {"ettevotted": "Ettevõtted", "inimesed": "Inimesed"}[NAITAJA_VAADE[nid]])}</p>
</div>""")
    sec_l = f"""
<section class="jaotis" id="lahknevused" aria-labelledby="h-lahknevused">
  <header>
    <h2 id="h-lahknevused">{ARVSONAD[len(lahti)].capitalize()} lahknevust on <b>selgitamata</b> ¦ sama küsitluse kohta annavad Eurostat ja Statistikaamet eri numbri</h2>
    <p class="alam">Lahknevus tähendab, et kaks allikat mõõdavad kataloogi järgi sama asja, aga numbrid erinevad rohkem kui ümardus. Kuni põhjus selgub, kasutab seire riikide võrdluseks Eurostati numbrit.</p>
  </header>
  <div class="kaks vordne">{"".join(l_kaardid)}</div>
</section>"""

    from lehed_ulevaade import kpi_pais, kpi_plaat, kpi_riba
    LNIMI = {"ettevotete-tehisaru-kasutus": "ettevõtted", "tehisaru-oskuse-puudus": "„ei oska“"}
    n_uud = sum(1 for v in V if v.get("uudisest"))
    aside = kpi_pais(
        kpi_plaat("us-muud", "Väide ütleb muud kui allikas", str(loend[0]), f"/ {n} väitest",
                  {"tekst": f"<b>{loend[1]}</b> vajab täpsustust",
                   "riba": kpi_riba(loend[0], n, fookus=True)},
                  "Seire väidete kontroll", fookus=True),
        kpi_plaat("us-lahk", "Selgitamata lahknevused", str(len(lahti)), "",
                  {"tekst": "Eurostat vs Statistikaamet: <b>"
                            + ", ".join(f'{l["kood"]} {LNIMI.get(l["naitaja"], l["naitaja"])}' for l in lahti) + "</b>"},
                  "Seire allikate võrdlus"),
        kpi_plaat("us-uudis", "Väited uudistest", str(n_uud), f"/ {n} väitest",
                  {"tekst": "kontrollitud <b>algallika järgi</b>"},
                  "Seire uudiste kontroll"),
    )
    # Kadri 11.11.2026 (ülesehituse kontroll E): menüüpunkt „Usaldus“ avab selle lehe, seega ütleb lead, mida osa tervikuna näitab
    lead = (f"Usaldus kontrollib kolme asja: kas väide vastab allikale ({sonaga(n)} väidet), kus Eurostat ja Statistikaamet "
            f"annavad eri numbri ja kui värsked on numbrid. Väited on kontrollitud algallika järgi ühel skaalal.")
    # Usaldus (Kadri 6.11.2026 22:27): väited, lahknevused ja värskus on üks teema kolmel alamlehel
    return jaga(A, vaade, lead, [], [
        ("vaited", [("vaited", "Väited")], sec_v),
        ("lahknevused", [("lahknevused", "Lahknevused")], sec_l),
        ("varskus", [("varskus", "Värskus"), ("muutused", "Mis muutus")], varskus_ja_muutused(A, vaated)),
    ], aside=aside)


ALLIKA_NIMED = {"ec.europa.eu": "Eurostat", "stat.ee": "Statistikaamet", "scb.se": "SCB (Rootsi)", "statistikbanken.dk": "Danmarks Statistik",
                "dst.dk": "Danmarks Statistik", "ssb.no": "SSB (Norra)", "stat.fi": "Statistikaamet Soome", "oecd.org": "OECD", "ilo.org": "ILO"}


def _allika_nimi(url):
    """Lingi tekst ütleb, kuhu see viib (oskus andmesaidi-ulesehitus): „Allikas“ asemel allika nimi."""
    host = re.sub(r"^https?://([^/]+).*", r"\1", url)
    return next((n for d, n in ALLIKA_NIMED.items() if host == d or host.endswith("." + d)), host.removeprefix("www."))


def varskus_ja_muutused(A, vaated):
    """Näitajate värskus ja allikate muutuste logi: Usaldus › Värskus (Kadri 6.11.2026 22:27)."""
    v_read, uuem = [], 0
    for nid in A["naitajad"]:
        m = A["meta"][nid]
        ua = m.get("uuem_allikas")
        uuem += bool(ua)
        v_read.append([f'{link(vaated, NAITAJA_VAADE[nid], NAITAJA_NIMI[nid])}<small>{e(A["naitajad"][nid]["allikas"])}, {e(A["naitajad"][nid]["andmestik"])}</small>',
                       kp(m["allikas_uuendas"]), kp(m["varskus"]["jargmine_oodatav"]), e(m["varskus"]["staatus"]),
                       (f'{pr(ua["vaartus"])}% ({ua["aasta"]}), {a(ua["url"], ua["allikas"].split(" (")[0])}' if ua else "–")])
    koik_ajakohased = all(A["meta"][nid]["varskus"]["staatus"] == "ajakohane" for nid in A["naitajad"])
    sec_varskus = f"""
<section class="jaotis" id="varskus" aria-labelledby="h-varskus">
  <header>
    <h2 id="h-varskus">{("Kõik " + ARVSONAD[len(v_read)] + " näitajat <b>on Eurostatis ajakohased</b>") if koik_ajakohased else (SEESTYTLEV[len(v_read)].capitalize() + " näitajast <b>mõni on vananenud</b>")} ¦ {f"{OMASTAV[uuem]} puhul on riiklikul statistikaametil juba uuem number" if uuem else "riiklikel statistikaametitel uuemat numbrit pole"}</h2>
    <p class="alam">Ajakohane tähendab, et allikas pole avaldanud uuemat aastat, kui seire näitab. Uuem riiklik number on lehel eraldi märgitud.</p>
  </header>
  {tabel(["Näitaja", "Allikas uuendas", "Järgmine oodatav", "Seis", "Uuem number"], v_read, numbrid=[], pealdis="Näitajate värskus")}
</section>"""

    S = sorted([s for s in A["sundmused"] if s["liik"] in ("allikas", "lahknevus")], key=lambda s: s["kuupaev"], reverse=True)
    s_read = [[kp(s["kuupaev"]), e({"allikas": "uus number", "lahknevus": "lahknevus"}[s["liik"]]),
               e(s["tekst"]) + (f' {a(s["url"], _allika_nimi(s["url"]))}.' if s["url"].startswith("http") else "")] for s in S]
    sec_muut = f"""
<section class="jaotis" id="muutused" aria-labelledby="h-muutused">
  <header>
    <h2 id="h-muutused">Allikate ja lahknevuste logis on viimane kanne <b>{kp(S[0]["kuupaev"])}</b></h2>
    <p class="alam">Logis on allikate uued numbrid ja leitud lahknevused, uuemad üleval.</p>
  </header>
  {tabel(["Kuupäev", "Liik", "Mis muutus"], s_read, numbrid=[], piir=True, pealdis="Muutuste logi")}
</section>"""

    return sec_varskus + sec_muut



# ---------------------------------------------------------------- Avaleht

KOHA_NAITAJAD = [
    ("inimeste-tehisaru-kasutus", "Inimeste tehisaru kasutus", False),
    ("tooalane-tehisaru-kasutus", "Tööalane tehisaru kasutus", False),
    ("ettevotete-tehisaru-kasutus", "Ettevõtete tehisaru kasutus", False),
    ("tehisaru-oskuse-puudus", "„Ei oska“ (väiksem on parem)", True),
    ("inimeste-digioskused", "Inimeste digioskused", False),
    ("ettevotete-digiintensiivsus", "VKEde digiintensiivsus", False),
]


def avaleht(A, vaade, vaated):
    IN, EB, DS = "inimeste-tehisaru-kasutus", "ettevotete-tehisaru-kasutus", "inimeste-digioskused"
    ds, ds23 = andmed.leia(A, DS, "EE", "uusim:alus"), andmed.leia(A, DS, "EE", 2023)
    if abs(ds["vaartus"] - ds23["vaartus"]) >= 0.5:
        raise AndmeViga("Digioskused ei ole enam 2023. aastast „paigal“: avalehe pealkiri tuleb üle vaadata")
    kontrolli(vaade, "2023. aastast paigal")
    k_read, kohad = [], {}
    for nid, nimi, vaiksem in KOHA_NAITAJAD:
        y = andmed.leia(A, nid, "EE", "uusim:alus")["aasta"]
        k = andmed.koht(A, nid, "EE", y)
        if vaiksem:
            k = len(A["el_riigid"]) + 1 - k
        kohad[nid] = (k, y)
        ee, eu = andmed.leia(A, nid, "EE", y), andmed.leia(A, nid, EL, y)
        vf = next(v for v in vaated if v["id"] == ("inimesed" if nid in (IN, "tooalane-tehisaru-kasutus", "tehisaru-oskuse-puudus", DS) else "ettevotted"))
        k_read.append((nimi, k, f'{y}: Eesti {pr(ee["vaartus"])}%, EL {pr(eu["vaartus"])}%', vf["fail"] if vf["olek"] == "valmis" else ""))
    ki, ke = kohad[IN], kohad[EB]
    if ki[1] != ke[1]:
        raise AndmeViga("Avalehe kohtade pealkiri eeldab sama aastat")
    sec_kohad = f"""
<section class="jaotis" id="kohad" aria-labelledby="h-kohad">
  <header>
    <h2 id="h-kohad">ELi 27 riigi seas on Eesti inimeste tehisaru kasutuses <b>{ki[0]}. ja ettevõtetes {ke[0]}. kohal</b> ({ki[1]})</h2>
  </header>
  <div class="kaks">
    <figure aria-labelledby="g-kohad">
      <figcaption><span class="gt" id="g-kohad">Eesti koht ELi 27 riigi seas, Eurostati uusim aasta</span>
        <span class="gs">1 on suurim osakaal; „ei oska“ puhul väikseim. Peen joon on keskmine koht. Koht ei näita vahe suurust.</span></figcaption>
      {kohariba(k_read)}
      {allikarida([("Eurostat", "https://ec.europa.eu/eurostat/databrowser/", "uusim võrreldav aasta igal näitajal")])}
    </figure>
    <div class="kulg">
      {vastavus("osaliselt", "Koht ELi skaalal on võrreldav, sest kõik riigid vastavad samale küsimustikule. Riikide 2026. aasta numbrid ei ole veel kõigil olemas, seepärast on kohad 2024. ja 2025. aasta järgi.")}
      {faktid([("Tõlgendus", "s", "ELi võrdluses on Eesti inimesed tehisaru kasutuses eespool kui ettevõtted ja eespool kui oma üldiste digioskuste poolest. Põhjust kohad ei näita."),
               ("Lugemise abi", "", link(vaated, "kuidas", "Kuidas lugeda") + ": kust numbrid tulevad ja mida saab võrrelda.")])}
    </div>
  </div>
</section>"""

    teemad = []
    for v in vaated:
        if not v["menuu"] or v["id"] == "avaleht":
            continue
        nimi = f'<a href="{v["fail"]}">{e(v["menuu"])}</a>' if v["olek"] == "valmis" else e(v["menuu"])
        teemad.append(f'<li><h3>{nimi}</h3><p>{taida(v["h1"], A).split(" ¦ ")[0]}</p></li>')
    sec_teemad = f"""
<section class="jaotis" id="teemad" aria-labelledby="h-teemad">
  <header>
    <h2 id="h-teemad">Kuus teemat, igaühel <b>üks küsimus ja vastus</b></h2>
  </header>
  <ul class="teemad">{"".join(teemad)}</ul>
</section>"""

    sec_ei = f"""
<section class="jaotis" id="ei-naita" aria-labelledby="h-ei-naita">
  <header><h2 id="h-ei-naita">Mida sait <b>ei näita</b></h2></header>
  {faktid([
      ("Ainult avalik", "", "Iga number on avalikust allikast koos lingi ja kuupäevaga. Sait ei kogu ise andmeid ega kasuta asutuste siseseid materjale."),
      ("Kasutus, mitte mõju", "", "Statistika näitab, kui paljud tehisaru kasutavad. Mõju tööle ja tootlikkusele näitavad üksikud uuringud, mis on eraldi märgitud."),
      ("Ei liideta", "", "Eri küsimustikuga numbreid ei panda samale teljele. Inimeste ja ettevõtete numbrid ei ole omavahel võrreldavad."),
  ])}
</section>"""

    ein, eeb = andmed.leia(A, IN, "EE", "uusim"), andmed.leia(A, EB, "EE", "uusim")
    ree = [
        (f'{pr(ein["vaartus"])}%', f'Eesti 16–74-aastastest kasutas tehisaru {ein["aasta"]}. aastal.', f'{a(ein["url"], ein["allikas"])}, {kp(ein["avaldatud"])}'),
        (f'{pr(eeb["vaartus"])}%', f'Eesti ettevõtetest (10+ hõivatut) kasutas tehisaru {eeb["aasta"]}. aastal.', f'{a(eeb["url"], eeb["allikas"])}, {kp(eeb["avaldatud"])}'),
        (f'{pr(ds["vaartus"])}%', f'Eesti inimestest on vähemalt baastaseme digioskused ({ds["aasta"]}; 2023: {pr(ds23["vaartus"])}%).', e(ds["allikas"])),
    ]
    lead = ("Tehisaru seire koondab avalikku statistikat ja uuringuid tehisaru kasutusest Eestis ja Euroopas. "
            "Iga numbri juures on allikas, kuupäev ja see, mida number ei näita.")
    return (pea(A, vaade, lead, [("kohad", "Eesti ELis"), ("teemad", "Teemad"), ("ei-naita", "Mida ei näita")], ree)
            + sec_kohad + sec_teemad + sec_ei)


# ---------------------------------------------------------------- Kuidas lugeda

KLASSI_SELGITUS = [
    ("alus", "Võrdlusalus", "Tavaliselt Eurostat, sest see on kõigi ELi riikide kohta sama meetodiga."),
    ("sama", "Sama", "Sama küsitlus ja määratlus. Number peab klappima ümardamise täpsusega; kui ei klapi, on see lahknevus."),
    ("osaliselt", "Osaliselt", "Sama küsitlus, aga teine kogum, klassifikaator või nimetaja. Näidatakse eraldi, kasvu ei arvutata."),
    ("erinev", "Erinev", "Teine küsitlus või määratlus. Näidatakse eraldi tabelis, samasse ritta ei panda."),
    ("kontrollimata", "Kontrollimata", "Määratlust pole metaandmetest kontrollitud. Käsitletakse nagu „erinev“."),
]


# Metoodika: mõisted ja avaliku sektori numbrid (Kadri 8.11.2026: kõik ühes kohas, otse allikast). Ainult avalikud allikad.
DYAK_URL = "https://valitsus.ee/sites/default/files/documents/2026-06/DYAK%202035%20arengukava.pdf"
PROG_URL = "https://www.justdigi.ee/sites/default/files/documents/2026-06/Digi%C3%BChiskonna%20programm%202027-2030%20eeln%C3%B5u.pdf"
ARS_URL = "https://arenguseire.ee/raportid/tehnoloogilise-arenguga-seotud-trendid-eesti-ettevotluses/"
MOISTED = [
    ("Inimeste tehisaru kasutus", "Eurostat, Statistikaamet", "Generatiivse tehisaru tööriistade kasutamine, 16–74-aastased.", "inimesed"),
    ("Ettevõtete tehisaru kasutus", "Eurostat, Statistikaamet", "Ettevõte kasutab vähemalt üht tehisaru tehnoloogiat. Vähemalt 10 hõivatuga ettevõtted, finantssektorita.", "ettevotted"),
    ("Digioskused", "Eurostat", "Inimese vähemalt baastasemel digioskused. Arvutatakse tegevuste põhjal, mida inimene on teinud, mitte testiga.", "inimesed"),
    ("Digiintensiivsus", "Eurostat, Arenguseire Keskus", "Kui paljusid digitehnoloogiaid ettevõte kasutab (12 tunnusest). Seire näitab vähemalt baastaset; Arenguseire raport kasutab kõrget ja väga kõrget taset.", "ettevotted"),
    ("OECD vastajad", "OECD", "Vabatahtlikult vastanud avaliku sektori juhid ja töötajad, mitte kõik töötajad. Kas nad esindavad kõiki, aruanne ei hinda.", "avalik-sektor"),
]
EI_NAITA = [
    ("Kasutus ei ole sama mis kasu", f'Eurostat ja Statistikaamet küsivad, kas inimene või ettevõte kasutab tehisaru. Kas see tõstab tootlikkust, need andmed ei ütle. '
                                      f'<a href="{ARS_URL}">Arenguseire Keskus</a> leidis seose alles koos töökorralduse muutusega.'),
    ("Uuendus ei ole sama mis kogu töö", "OECD 28% loeb innovaatorite uuendusi, mitte kõiki töötajaid ega asutusi. Küsimus esitati ainult neile, kes olid viimase kahe aasta jooksul midagi uuendanud."),
    ("Mõõdik ei ole sama mis avaldatud arvutus", f'Avaliku sektori tehisaru kasutust mõõdab <a href="{DYAK_URL}">arengukava</a> mõõdik 7 (50,8%), '
                                                 "aga selle arvutuskäik pole avaldatud. Statistikaamet ja Eurostat sellist näitajat ei avalda."),
    ("Puuduv number ei ole null", "Tehisaru investeeringute kohta avalikku allikat ei leitud. Kui number puudub, ei tähenda see, et kulu või mõju oleks null."),
    ("Tegevused ei ole oskuste test", "Digioskuste näitaja liidab tegevused, mida inimene on teinud. Inimese oskusi ei testita."),
    ("Kõik 16–74-aastased ei ole töötajad", "Tööalase kasutuse osakaal on arvutatud kõigist 16–74-aastastest, ka töötutest ja õpilastest."),
    ("Statistikaameti 2026. aasta number ei ole sama mis Eurostati 2025. aasta number", "Riiklikud 2026. aasta numbrid ei ole Eurostati omadega täielikult võrreldavad, näiteks Eesti kasutab uut tegevusalade klassifikaatorit."),
]


def _metoodika(A, vaated):
    from abi import link
    gk = A["avalik"]["genai-kesk"]
    m_read = [[f'<b>{e(n)}</b><small>{e(k)}</small>', e(t), link(vaated, v, next((x["menuu"] for x in vaated or [] if x["id"] == v), v) or v)]
              for n, k, t, v in MOISTED]
    a_read = [
        ["<b>50,8%</b><small>arengukavas aasta 2024, programmis 2025</small>", "Asutused ja omavalitsused, kes on kasutanud vähemalt üht tehisaru tehnoloogiat",
         f'<a href="{DYAK_URL}">Digiühiskonna arengukava 2035</a>, mõõdik 7 (lk 17, allikas JDM)',
         "Lähtetase. Arengukava märgib selle aastaks 2024, programmi eelnõu (tabel 3) aastaks 2025. Arvutuskäik (küsimus, nimetaja) on avaldamata."],
        ["<b>55%, 75%, 90%</b><small>2027, 2030, 2035</small>", "Sama mõõdiku sihid: asutuste ja omavalitsuste osakaal",
         f'<a href="{PROG_URL}">Digiühiskonna programm 2027–2030</a> (eelnõu, tabel 3: 55% 2027, 65% 2028, 70% 2029, 75% 2030); <a href="{DYAK_URL}">arengukava</a> (75% 2030, 90% 2035)',
         "Siht. Vahesiht 55% kehtib juba 2027. aastal."],
        [f'<b>{gk["vaartus"]}%</b><small>2026; omavalitsustes {A["avalik"]["genai-kov"]["vaartus"]}%</small>',
         f'Innovaatorite uuendused: keskvalitsuse innovaatoritest {gk["lugeja"]} {gk["nimetaja"]}-st kasutas uuenduses generatiivset tehisaru',
         '<a href="https://doi.org/10.1787/c2c09a06-en">OECD 2026</a>, joonis 7.2',
         "Ainult taust. Küsiti ainult neilt, kes olid 24 kuu jooksul midagi uuendanud; kõigi töötajate kasutust ei näita."],
    ]
    ei = "".join(f'<li><h3>{e(p)}</h3><p>{t}</p></li>' for p, t in EI_NAITA)
    return f"""
<section class="jaotis" id="moisted" aria-labelledby="h-moisted">
  <header>
    <h2 id="h-moisted">Viis mõistet kõlavad sarnaselt, aga <b>mõõdavad eri asju</b></h2>
    <p class="alam">Kui kaks numbrit kasutavad eri mõistet, ei panda neid samale teljele.</p>
  </header>
  {tabel(["Mõiste", "Mida see tähendab", "Kus saidil"], m_read, numbrid=[], piir=True, pealdis="Sarnased mõisted")}
</section>
<section class="jaotis" id="avaliku-numbrid" aria-labelledby="h-avaliku-numbrid">
  <header>
    <h2 id="h-avaliku-numbrid">Avaliku sektori tehisaru numbrid <b>ei ole omavahel võrreldavad</b> ¦ üks loeb asutusi, teine innovaatorite uuendusi</h2>
    <p class="alam">„Kasutamine“ on eri allikates määratletud eri moodi. Siht on oma mõõdiku kõrval, mitte teise allika numbri kõrval.</p>
  </header>
  {tabel(["Number", "Mida see loeb", "Allikas", "Kuidas kasutada"], a_read, numbrid=[], piir=True, pealdis="Mida iga avaliku sektori tehisaru number mõõdab")}
  {allikarida([("Digiühiskonna arengukava 2035", DYAK_URL, "valitsus kinnitas 7.05.2026"), ("Digiühiskonna programm 2027–2030 eelnõu", PROG_URL, "2026")])}
</section>
<section class="jaotis" id="numbrid-ei-naita" aria-labelledby="h-numbrid-ei-naita">
  <header>
    <h2 id="h-numbrid-ei-naita">Seitse asja, mida numbrid <b>ei näita</b></h2>
  </header>
  <ul class="teemad ei-naita">{ei}</ul>
</section>"""


def kuidas(A, vaade, vaated=None):
    Al = A["allikad"]
    kontrolli(vaade, f"{len(Al)} allikast")
    riiklik = sum(1 for r in Al if r["tuup"].startswith("riiklik"))
    a_read = [[f'{a(r["veebileht"], r["organisatsioon"])}<small>{e(riik(r["riik"]) if len(r["riik"]) == 2 else r["riik"])} · {e(r["tuup"])}</small>',
               e(r["api_tuup"]), e(r["uuendussagedus"]), e(r["viimane_tehisaru_avaldus"])] for r in Al]
    sec_a = f"""
<section class="jaotis" id="allikad" aria-labelledby="h-allikad">
  <header>
    <h2 id="h-allikad">Ametlik statistika tuleb <b>{len(Al)} allikast</b> ¦ {riiklik} riiklikku statistikaametit ja {len(Al) - riiklik} rahvusvahelist organisatsiooni</h2>
    <p class="alam">Uuringud ja raportid (OECD, Arenguseire, ülikoolid) on lisaks sellele loendile ja nende juures on alati link.</p>
  </header>
  {tabel(["Allikas", "Andmeliides", "Uuendab", "Viimane tehisaru avaldus"], a_read, numbrid=[], piir=True, pealdis="Allikate register")}
</section>"""

    T = A["tooelu"]
    kl = "".join(f'<li><b>{e(nimi)}.</b> {e(t)}</li>' for _, nimi, t in KLASSI_SELGITUS)
    tugevus = {"tugev": "Tugev tõend", "keskmine": "Keskmine tõend", "nork": "Nõrk tõend", "prognoos": "Prognoos"}
    tk = "".join(f'<li><b>{e(tugevus[t])}:</b> {e("; ".join(T["meetodid"][m].split(".")[0].lower() for m in mm))}.</li>'
                 for t, mm in T.get("kindlus", {}).items())
    hn = "".join(f'<li><b>{e(h)}.</b> {e(t)}</li>' for h, (_, t) in HINNANGUD.items())
    sec_m = f"""
<section class="jaotis" id="margid" aria-labelledby="h-margid">
  <header>
    <h2 id="h-margid">Kolm märki näitavad, <b>kui palju numbrit usaldada</b> ¦ kas numbrid on võrreldavad, kui tugev on uuring ja kas väide vastab allikale</h2>
  </header>
  <div class="kolm">
    <div class="plokk"><h3>Võrreldavus</h3><ul class="loend">{kl}</ul></div>
    <div class="plokk"><h3>Uuringu tõend</h3><ul class="loend">{tk}</ul></div>
    <div class="plokk"><h3>Väite hinnang</h3><ul class="loend">{hn}</ul></div>
  </div>
</section>"""

    M = [m for m in A["moodikud"].values() if (m["naitaja"] in A["naitajad"] or m["registri_naitaja"] in A["naitajad"])]
    M.sort(key=lambda m: (m["naitaja"] or m["registri_naitaja"], m["vorreldavus"] != "alus", m["id"]))
    klass_nimi = {k: n for k, n, _ in KLASSI_SELGITUS}
    m_read = [[f'{e(m["nimi"])}<small>{e(m["populatsioon"])} · {e(m["uhik"])}</small>',
               e(NAITAJA_NIMI.get(m["naitaja"] or m["registri_naitaja"], "")),
               f'<b>{e(klass_nimi.get(m["vorreldavus"], m["vorreldavus"]))}</b>', e(m["erinevused"] or "–")] for m in M]
    teisi = sum(1 for m in M if m["vorreldavus"] != "alus")
    sec_v = f"""
<section class="jaotis" id="vorreldavus" aria-labelledby="h-vorreldavus">
  <header>
    <h2 id="h-vorreldavus">Igal näitajal on üks võrdlusalus ja <b>{sonaga(teisi)} teist mõõdikut</b> on sellega võrreldud</h2>
    <p class="alam">Ainult „võrdlusalus“ ja „sama“ võivad olla ühel teljel. Teised on lehtedel skaala all märkega „ei ole otse võrreldav“.</p>
  </header>
  {tabel(["Mõõdik", "Näitaja", "Klass", "Mis erineb"], m_read, numbrid=[], piir=True, pealdis="Mõõdikute võrreldavus")}
</section>"""

    tug = lambda m: next((tugevus[t] for t, mm in T["kindlus"].items() if m in mm), "")  # noqa: E731
    # Tugevam tõend enne, sama tugevuse sees uuem enne: esimesed 12 rida on kõige kaalukamad
    jrk = {"Tugev tõend": 0, "Keskmine tõend": 1, "Nõrk tõend": 2}
    U = sorted(A["uuringud"].values(), key=lambda u: (jrk.get(tug(u["meetod"]), 3), -u["aasta"], u["autorid"]))
    u_read = [[f'{a(u["url"], u["autorid"])}<small>{u["aasta"]} · {e(u["kanal"])}{" · eelretsenseeritud" if u.get("retsenseeritud") else ""}</small>',
               f'{e(u["silt"].capitalize() if u.get("silt") else tug(u["meetod"]))}<small>{e(u["meetod"].replace("_", " "))}</small>', e(u["kus"]), e(u["leid"])] for u in U]
    n_tugev = sum(1 for u in U if tug(u["meetod"]) == "Tugev tõend")
    sec_u = f"""
<section class="jaotis" id="uuringud" aria-labelledby="h-uuringud">
  <header>
    <h2 id="h-uuringud">Kogus on <b>{len(U)} uuringut</b>, neist {n_tugev} tugeva tõendiga (katse või registriandmed)</h2>
    <p class="alam">Iga arv on võetud allika kokkuvõttest ja kontrollitud lingi kaudu ({kp(T.get("kontrollitud", ""))}).</p>
  </header>
  {tabel(["Uuring", "Tõend", "Kus", "Mida leiti"], u_read, numbrid=[], piir=True, pealdis="Uuringute kogu")}
</section>"""

    from lehed_ulevaade import kpi_pais, kpi_plaat
    aside = kpi_pais(
        kpi_plaat("kl-allikad", "Allikad", str(len(Al)), "",
                  {"tekst": f"<b>{riiklik}</b> statistikaametit · <b>{len(Al) - riiklik}</b> rahvusvahelist"},
                  "Allikate register", fookus=True),
        kpi_plaat("kl-klassid", "Võrreldavuse klassid", str(len(KLASSI_SELGITUS)), "",
                  {"tekst": "kas numbrid on <b>võrreldavad</b>"},
                  "Seire kataloog"),
        kpi_plaat("kl-uuringud", "Uuringud tehisarust ja tööst", str(len(U)), "",
                  {"tekst": f"<b>{n_tugev}</b> tugeva tõendiga"},
                  "Uuringute kogu"),
    )
    lead = ""
    sec_uu = _uuenemine(A)
    lingid = [("uuendused", "Mis uueneb ise")] if sec_uu else []
    sec_mt = _metoodika(A, vaated)
    return (pea(A, vaade, lead, lingid + [("moisted", "Mõisted"), ("numbrid-ei-naita", "Mida ei näita"), ("allikad", "Allikad"),
                                          ("margid", "Märgid"), ("vorreldavus", "Võrreldavus"), ("uuringud", "Uuringud")], [], aside=aside)
            + sec_uu + sec_mt + sec_a + sec_m + sec_v + sec_u)


def _ootab(n):
    return "Praegu ei oota midagi." if not n else f"Praegu ootab {n}."


def _uuenemine(A):
    """Mis saidil uueneb ise ja mis käsitsi, koos viimase kuupäevaga (Kadri 6.11.2026 20:03)."""
    O, H, P, F = A.get("uudiste_olek"), A.get("hanked_leht"), A.get("publikatsioonid"), (A.get("koondajad") or {}).get("firmad")
    K = A.get("koondamised") or {}
    T = A.get("tooelu") or {}

    def d(x):
        return kp(x[:10]) if x else "—"
    otsib = min((f["otsib"]["kontrollitud"] for f in (F or {}).values() if f["otsib"].get("kontrollitud")), default="")
    kandidaate = sum(1 for j in K.get("juhtumid", []) if j.get("kandidaat"))
    Oo, Ov = A.get("ootel") or {}, A.get("oecd_valvur") or {}
    viim_uuring = max([T.get("kontrollitud", "")] + [u.get("seire_kinnitatud", "") for u in A.get("uuringud", {}).values() if u.get("lisa")])
    viim_vaide = max([v.get("kuupaev", "") for v in A.get("uudiste_vaited") or []], default="")
    read = [
        ("Uudised Eestist ja maailmast", "ise, kaks korda päevas (7.23 ja 17.53), sh jätkulood; kell 12.53 suured uudised", d(O["viimane_kontroll"]) if O else "—",
         "Mitte midagi. Uudise liigi ja leviku märgib kogumine ise."),
        ("Eesti koondamised (Töö)", "uudistest ise, märkega „uudisest, kontrollimata“", d(K.get("kontrollitud", "")),
         f"Kinnitamine käsitsi peetud nimekirja (tooelu-seire/koondamised_ee.json). Praegu on kinnitamata {kandidaate}."),
        ("Keda koondajad otsivad", "ise, esmaspäeviti ja uue koondaja lisandumisel", d(otsib), "Mitte midagi."),
        ("Ametlikud numbrid (Eurostat, Statistikaamet)", "ise, iga päev", d(A.get("uuendatud", "")),
         "Kui number muutub, peatub ehitus ja pealkiri tuleb üle vaadata. Riikide 2026. aasta numbrid kantakse käsitsi."),
        ("Hanked", "ise, iga päev (GitHub Actions)", d((H or {}).get("seis", {}).get("kuupaev", "")),
         "Klassifikaatori märgendeid pole inimene kontrollinud."),
        ("Publikatsioonid (Töö)", "ise, esmaspäeviti (OpenAlex)", d((P or {}).get("meta", {}).get("aeg", "")), "Mitte midagi."),
        ("Uuringute leiud ja kokkuvõtted (Töö)", "otsing ja mustand ise, iga päev; saidile pärast kinnitust", d(viim_uuring),
         f"Mustandi kinnitamine (leid ja arvud allika kokkuvõttest). {_ootab(Oo.get('uuringud'))}"),
        ("Väited (Usaldus › Väited)", "uudistest ise, kontroll algallika vastu; saidile pärast kinnitust", d(viim_vaide),
         f"Hinnangu kinnitamine. {_ootab(Oo.get('vaited'))}"),
        ("Lahknevused (Usaldus › Lahknevused)", "ise, kui allikad annavad sama asja kohta eri numbri", d(A.get("uuendatud", "")),
         "Põhjuse selgitamine allikaga."),
        ("OECD avaliku sektori raport", "uue väljaande otsing ise, iga päev", d(Ov.get("kontrollitud", "")),
         (f"Leitud uus väljaanne „{Ov['uued'][0]['pealkiri']}“ ({kp(Ov['uued'][0]['kuupaev'])}): numbrid tuleb üle kanda."
          if Ov.get("uued") else "Uue raporti korral numbrite ülekandmine (viimane: 3.11.2026).")),
    ]
    t = "".join(f'<tr><td><b>{e(n)}</b></td><td>{e(k)}</td><td class="n">{v}</td><td>{e(m)}</td></tr>' for n, k, v, m in read)
    ise = sum(1 for r in read if (r[1].startswith("ise") or r[1].startswith("uudistest")) and "kinnitust" not in r[1])
    pool = sum(1 for r in read if " ise" in r[1] and "kinnitust" in r[1] or r[1].startswith("uue väljaande otsing"))
    return f"""
<section class="jaotis" id="uuendused" aria-labelledby="h-uuendused">
  <header>
    <h2 id="h-uuendused">Saidi {sonaga(len(read), "seestytlev")} osast uueneb ise <b>{sonaga(ise)}</b> ¦ {sonaga(pool, "omastav")} puhul otsib arvuti ise ja inimene kinnitab</h2>
    <p class="alam">Sait ehitatakse uuesti kaks korda päevas (7.23 ja 17.53) ja avaldatakse ainult siis, kui kõik testid läbivad. Kuupäev on viimane kontroll või andmete seis.</p>
  </header>
  <div class="tbl"><table><thead><tr><th scope="col">Osa</th><th scope="col">Kuidas uueneb</th><th scope="col">Viimati</th><th scope="col">Mida on vaja käsitsi</th></tr></thead><tbody>{t}</tbody></table></div>
</section>"""


# ---------------------------------------------------------------- Mis see sait on (Kadri 9.11.2026)

SAIDIST_LUGEJAD = [  # (kes, mida otsib, [(vaate id, lingi tekst, ankur)])
    ("Huviline", "kui palju tehisaru Eestis kasutatakse ja mis on viimati juhtunud",
     [("avaleht", "Avaleht", ""), ("uudised", "Uudised", "")]),
    ("Ametnik või otsustaja", "kus Eesti on ELi skaalal, mida riik hangib ja millal määruse nõuded kehtima hakkavad",
     [("avalik-sektor", "Avalik sektor", ""), ("hanked", "Hanked", ""), ("reeglid", "Tehisaru määrus", "")]),
    ("Ajakirjanik", "kas meedias liikuv väide vastab allikale ja kas allikad räägivad sama",
     [("kas-tosi", "Usaldus", "")]),
    ("Uurija või analüütik", "mida uuringud tööturu kohta tegelikult näitavad ja kuidas numbreid võrrelda",
     [("too", "Töö", ""), ("kuidas", "Kuidas lugeda", "")]),
]


def saidist(A, vaade, vaated):
    """Tutvustus uuele lugejale: mis sait on, kellele, mis teemad, kolm sisuliiki, kuidas uueneb, mida sait ei ole."""
    nimi = {v["id"]: v["menuu"] or v["id"] for v in vaated}
    teemad = [v for v in vaated if v["menuu"] and v["olek"] == "valmis"]
    l_read = "".join(
        f'<div class="plokk"><h3>{e(kes)}</h3><p>Leiab, {e(mida)}.</p><p class="vaikne">Alusta: '
        + ", ".join(link(vaated, vid, t, ank) for vid, t, ank in lingid) + "</p></div>"
        for kes, mida, lingid in SAIDIST_LUGEJAD)
    t_read = [[link(vaated, v["id"], nimi[v["id"]]), e(v["kusimus"]), taida(v["h1"], A).split(" ¦ ")[0]] for v in teemad]
    n_allikad = len(A["allikad"])
    return f"""
<div class="pea yks">
  <div class="pea-tekst">
    <h1>{taida(vaade["h1"], A)}</h1>
    <p class="lead">Sait on mõeldud inimesele, kes tahab kiiresti teada, kui palju tehisaru Eestis kasutatakse, mida see tööle teeb ja kas meedias liikuvad väited peavad paika. Iga number on allika lingiga.</p>
  </div>
</div>
<section class="jaotis" id="kellele" aria-labelledby="h-kellele">
  <header><h2 id="h-kellele">Kust alustada: <b>neli lugejat, neli algust</b></h2></header>
  <div class="kolm neli">{l_read}</div>
</section>
<section class="jaotis" id="teemad" aria-labelledby="h-teemad">
  <header>
    <h2 id="h-teemad">Saidil on <b>{ARVSONAD.get(len(teemad), len(teemad))} teemat</b>; iga teema vastab ühele küsimusele</h2>
    <p class="alam">Pealkiri on sama, mis teema lehel, ja selle numbrid tulevad andmetest.</p>
  </header>
  {tabel(["Teema", "Küsimus", "Vastus praegu"], t_read, numbrid=[], piir=True, pealdis="Saidi teemad")}
</section>
<section class="jaotis" id="sisuliigid" aria-labelledby="h-sisuliigid">
  <header><h2 id="h-sisuliigid">Sisu on kolme liiki ja <b>neid ei segata ühele graafikule</b></h2></header>
  <div class="kolm">
    <div class="plokk"><h3>Mõõdetud</h3><p>Ametlik statistika {n_allikad} allikast: Statistikaamet, Eurostat, OECD, ILO ja teiste riikide statistikaametid. Need numbrid korduvad igal aastal sama küsimustikuga.</p></div>
    <div class="plokk"><h3>Uuring</h3><p>Üksikud uuringud ja raportid. Iga uuringu juures on kirjas, kui tugev on tõend: katse ja registriandmed on tugevamad kui küsitlus või prognoos.</p></div>
    <div class="plokk"><h3>Väide</h3><p>Meedias ja organisatsioonide tekstides esitatud väited, mis on võrreldud algallikaga. Väide kuulub väljaandele, mitte üksikule ajakirjanikule.</p></div>
  </div>
  <p class="vaikne">Mõõdetud number ja uuringu tulemus kohtuvad sama küsimuse juures, aga mitte samal teljel. Võrreldavuse reeglid: {link(vaated, "kuidas", "Kuidas lugeda", "vorreldavus")}.</p>
</section>
<section class="jaotis" id="kuidas-tootab" aria-labelledby="h-kuidas-tootab">
  <header><h2 id="h-kuidas-tootab">Sait <b>uueneb ise</b> ¦ uued uuringud ja väited lähevad lehele alles pärast inimese kinnitust</h2></header>
  <ul class="loend">
    <li>Statistika, uudised, koondamised, tööpakkumised ja hanked tulevad allikatest automaatselt. Mis ja kui tihti uueneb: {link(vaated, "kuidas", "Mis uueneb ise", "uuendused")}.</li>
    <li>Kui kaks allikat annavad sama asja kohta eri numbri, jääb lahknevus nähtavale ja seda ei peideta: {link(vaated, "kas-tosi", "Usaldus")}.</li>
    <li>Hangete tehisaru- ja andmehanked märgistab keelemudel; märgistust on võrreldud käsitsi pimeülevaatusega ja tulemus on hangete lehel.</li>
  </ul>
</section>
<section class="jaotis" id="mida-ei-ole" aria-labelledby="h-mida-ei-ole">
  <header><h2 id="h-mida-ei-ole">See sait <b>ei ole ametlik statistika</b> ega ühegi asutuse seisukoht</h2></header>
  <p>Sait näitab, mida allikad ütlevad, ja märgib, kui kindel see on. Kui number on oluline otsuse jaoks, ava allikas: link on iga numbri juures.</p>
</section>
<section class="jaotis" id="autor" aria-labelledby="h-autor">
  <header><h2 id="h-autor">Autor</h2></header>
  <p>Saidi on koostanud {e(AUTOR)} tehisaru (Claude) abiga. Teemad, sisu valik, ülesehitus ja kujundus on autori otsused; koodi, andmete kogumise ja kokkuvõtete mustandid tegi tehisaru. Numbrid ja uuringud kuuluvad oma allikatele. © {autori_aastad()} {e(AUTOR)}.</p>
</section>"""
