"""Usalduse vaated ja sisenemine: Kas see on tõsi?, Avaleht, Kuidas lugeda (5.11.2026)."""
import re
import andmekiht as andmed
from abi import ARVSONAD, SEESTYTLEV, a, kontrolli, link, pea
from andmekiht import EL, AndmeViga
from komponendid import (allikarida, e, faktid, kohariba, kp, lihtribad, osad, pr, riik, tabel, vastavus)
from pealkiri import taida

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

def kas_tosi_h1(A):
    """Pealkiri andmetest: väidete arv muutub iga päev, sest uudiste väited tulevad samasse loendisse."""
    n = len(A["vaited"])
    muud = sum(1 for v in A["vaited"] if _raskus(v) == 0)
    lahti = sum(1 for l in A["lahknevused"] if l["staatus"] == "selgitamata")
    return (f"{SEESTYTLEV[n].capitalize()} kontrollitud avalikust väitest **{ARVSONAD[muud]} ütleb muud kui allikas** "
            f"ja {ARVSONAD[lahti]} allikate lahknevust on selgitamata.")


def kas_tosi(A, vaade, vaated=None):
    V = sorted(A["vaited"], key=lambda v: (_raskus(v), v["kuupaev"]))
    n = len(V)
    loend = {k: sum(1 for v in V if _raskus(v) == k) for k in RASKUS}
    L = A["lahknevused"]
    lahti = [l for l in L if l["staatus"] == "selgitamata"]
    kontrolli(vaade, f"{SEESTYTLEV[n]} kontrollitud", f"{ARVSONAD[loend[0]]} ütleb muud", f"{ARVSONAD[len(lahti)]} allikate lahknevust")

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
    <h2 id="h-lahknevused">{ARVSONAD[len(lahti)].capitalize()} lahknevust on selgitamata: sama küsitluse kohta annavad Eurostat ja Statistikaamet <b>eri numbri</b></h2>
    <p class="alam">Lahknevus tähendab, et kaks allikat mõõdavad kataloogi järgi sama asja, aga numbrid erinevad rohkem kui ümardus. Kuni põhjus selgub, kasutab seire riikide võrdluseks Eurostati numbrit.</p>
  </header>
  <div class="kaks vordne">{"".join(l_kaardid)}</div>
</section>"""

    ree = [
        (f'{loend[0]} <small>/ {n} väitest</small>', 'ütleb muud kui allikas: vale tõlgendus, vale nimetaja või liialdus.', "Seire väidete kontroll"),
        (f'{len(lahti)} <small>lahknevust</small>', 'Eurostati ja Statistikaameti vahel on selgitamata (C5 ettevõtted, C6 „ei oska“).', "Seire allikate võrdlus"),
        (f'{sum(1 for v in V if v.get("uudisest"))} <small>/ {n} väitest</small>', 'on pärit uudistest ja kontrollitud samal skaalal.', "Seire uudiste kontroll"),
    ]
    lead = ("Siin on avalikud väited, mida seire kontrollis algallika järgi, ka uudistest, ühel skaalal, ja allikate lahknevused. "
            "Iga hinnangu juures on link algallikale. Kui värsked numbrid on, näitab " + link(vaated, "kuidas", "Kuidas lugeda", "varskus") + ".")
    return (pea(A, vaade, lead, [("vaited", "Väited"), ("lahknevused", "Lahknevused")], ree)
            + sec_v + sec_l)


ALLIKA_NIMED = {"ec.europa.eu": "Eurostat", "stat.ee": "Statistikaamet", "scb.se": "SCB (Rootsi)", "statistikbanken.dk": "Danmarks Statistik",
                "dst.dk": "Danmarks Statistik", "ssb.no": "SSB (Norra)", "stat.fi": "Statistikaamet Soome", "oecd.org": "OECD", "ilo.org": "ILO"}


def _allika_nimi(url):
    """Lingi tekst ütleb, kuhu see viib (oskus andmesaidi-ulesehitus): „Allikas“ asemel allika nimi."""
    host = re.sub(r"^https?://([^/]+).*", r"\1", url)
    return next((n for d, n in ALLIKA_NIMED.items() if host == d or host.endswith("." + d)), host.removeprefix("www."))


def varskus_ja_muutused(A, vaated):
    """Näitajate värskus ja allikate muutuste logi (6.11.2026 Kas see on tõsi? lehelt Kuidas lugeda lehele: metoodika)."""
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
    <h2 id="h-varskus">{SEESTYTLEV[len(v_read)].capitalize()} näitajast {"<b>kõik on Eurostatis ajakohased</b>" if koik_ajakohased else "<b>mõni on vananenud</b>"}; {ARVSONAD[uuem]} puhul on riiklikul statistikaametil juba uuem number</h2>
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
    <h2 id="h-muutused">Viimane muutus allikates oli <b>{kp(S[0]["kuupaev"])}</b></h2>
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
        teemad.append(f'<li><h3>{nimi}</h3><p>{taida(v["h1"], A)}</p></li>')
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


def kuidas(A, vaade, vaated=None):
    Al = A["allikad"]
    kontrolli(vaade, f"{len(Al)} allikast")
    riiklik = sum(1 for r in Al if r["tuup"].startswith("riiklik"))
    a_read = [[f'{a(r["veebileht"], r["organisatsioon"])}<small>{e(riik(r["riik"]) if len(r["riik"]) == 2 else r["riik"])} · {e(r["tuup"])}</small>',
               e(r["api_tuup"]), e(r["uuendussagedus"]), e(r["viimane_tehisaru_avaldus"])] for r in Al]
    sec_a = f"""
<section class="jaotis" id="allikad" aria-labelledby="h-allikad">
  <header>
    <h2 id="h-allikad">Numbrid tulevad <b>{len(Al)} allikast</b>: {riiklik} riiklikku statistikaametit ja {len(Al) - riiklik} rahvusvahelist organisatsiooni</h2>
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
    <h2 id="h-margid">Kolm märki: kas numbrid on <b>võrreldavad</b>, kui tugev on uuring ja kas väide vastab allikale</h2>
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
    <h2 id="h-vorreldavus">Igal näitajal on üks võrdlusalus ja <b>{teisi} teist mõõdikut</b> on sellega võrreldud</h2>
    <p class="alam">Ainult „võrdlusalus“ ja „sama“ võivad olla ühel teljel. Teised on lehtedel skaala all märkega „ei ole otse võrreldav“.</p>
  </header>
  {tabel(["Mõõdik", "Näitaja", "Klass", "Mis erineb"], m_read, numbrid=[], piir=True, pealdis="Mõõdikute võrreldavus")}
</section>"""

    tug = lambda m: next((tugevus[t] for t, mm in T["kindlus"].items() if m in mm), "")  # noqa: E731
    # Tugevam tõend enne, sama tugevuse sees uuem enne: esimesed 12 rida on kõige kaalukamad
    jrk = {"Tugev tõend": 0, "Keskmine tõend": 1, "Nõrk tõend": 2}
    U = sorted(A["uuringud"].values(), key=lambda u: (jrk.get(tug(u["meetod"]), 3), -u["aasta"], u["autorid"]))
    u_read = [[f'{a(u["url"], u["autorid"])}<small>{u["aasta"]} · {e(u["kanal"])}{" · eelretsenseeritud" if u.get("retsenseeritud") else ""}</small>',
               f'{e(tug(u["meetod"]))}<small>{e(u["meetod"].replace("_", " "))}</small>', e(u["kus"]), e(u["leid"])] for u in U]
    n_tugev = sum(1 for u in U if tug(u["meetod"]) == "Tugev tõend")
    sec_u = f"""
<section class="jaotis" id="uuringud" aria-labelledby="h-uuringud">
  <header>
    <h2 id="h-uuringud">Uuringute kogus on <b>{len(U)} uuringut</b>, neist {n_tugev} tugeva tõendiga (katse või registriandmed)</h2>
    <p class="alam">Iga arv on võetud allika kokkuvõttest ja kontrollitud lingi kaudu ({kp(T.get("kontrollitud", ""))}).</p>
  </header>
  {tabel(["Uuring", "Tõend", "Kus", "Mida leiti"], u_read, numbrid=[], piir=True, pealdis="Uuringute kogu")}
</section>"""

    ree = [
        (f'{len(Al)} <small>allikat</small>', f'{riiklik} riiklikku statistikaametit ja {len(Al) - riiklik} rahvusvahelist organisatsiooni.', "Allikate register"),
        (f'{len(KLASSI_SELGITUS)} <small>klassi</small>', 'näitavad, kas kaks numbrit on võrreldavad. Ühel teljel võivad olla ainult „võrdlusalus“ ja „sama“.', "Seire kataloog"),
        (f'{len(U)} <small>uuringut</small>', 'tehisaru ja töö kohta, igaühel tõendi tugevus.', "Uuringute kogu"),
    ]
    lead = "Siin on kõik allikad, märgid ja reeglid, mille järgi seire numbreid näitab ja võrdleb."
    sec_uu = _uuenemine(A)
    lingid = [("uuendused", "Mis uueneb ise")] if sec_uu else []
    return (pea(A, vaade, lead, lingid + [("varskus", "Värskus"), ("muutused", "Mis muutus"), ("allikad", "Allikad"), ("margid", "Märgid"), ("vorreldavus", "Võrreldavus"), ("uuringud", "Uuringud")], ree)
            + sec_uu + varskus_ja_muutused(A, vaated) + sec_a + sec_m + sec_v + sec_u)


def _uuenemine(A):
    """Mis saidil uueneb ise ja mis käsitsi, koos viimase kuupäevaga (Kadri 6.11.2026 20:03)."""
    O, H, P, F = A.get("uudiste_olek"), A.get("hanked_leht"), A.get("publikatsioonid"), (A.get("koondajad") or {}).get("firmad")
    K = A.get("koondamised") or {}
    T = A.get("tooelu") or {}

    def d(x):
        return kp(x[:10]) if x else "—"
    otsib = min((f["otsib"]["kontrollitud"] for f in (F or {}).values() if f["otsib"].get("kontrollitud")), default="")
    kandidaate = sum(1 for j in K.get("juhtumid", []) if j.get("kandidaat"))
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
        ("Uuringute leiud ja kokkuvõtted (Töö)", "käsitsi", d(T.get("kontrollitud", "")), "Uue uuringu lisamine ja kontroll."),
        ("Väited ja lahknevused (Uudised ja väited › Väited)", "käsitsi", "—", "Uue väite kontroll algallika vastu."),
        ("OECD avaliku sektori raport", "käsitsi, ühekordne", kp("2026-11-03"), "Uue raporti korral numbrite ülekandmine."),
    ]
    t = "".join(f'<tr><td><b>{e(n)}</b></td><td>{e(k)}</td><td class="n">{v}</td><td>{e(m)}</td></tr>' for n, k, v, m in read)
    ise = sum(1 for r in read if r[1].startswith("ise") or r[1].startswith("uudistest"))
    return f"""
<section class="jaotis" id="uuendused" aria-labelledby="h-uuendused">
  <header>
    <h2 id="h-uuendused">Saidi {len(read)} osast uueneb ise <b>{ise}</b>, ülejäänud käsitsi</h2>
    <p class="alam">Sait ehitatakse uuesti kaks korda päevas (7.23 ja 17.53) ja avaldatakse ainult siis, kui kõik testid läbivad. Kuupäev on viimane kontroll või andmete seis.</p>
  </header>
  <div class="tbl"><table><thead><tr><th scope="col">Osa</th><th scope="col">Kuidas uueneb</th><th scope="col">Viimati</th><th scope="col">Mida on vaja käsitsi</th></tr></thead><tbody>{t}</tbody></table></div>
</section>"""
