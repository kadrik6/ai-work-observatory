"""Avaliku sektori lehe töölaud (Kadri 17.11.2026 valis näidistest „A ja C koos“).

Leht algab tahvliga (kuus küsimust, iga rida üks pilk), siis uuenduse teekond (etapid ja hindamine) ja
48 asutust Riigikontrolli küsitlusest (kellel puudub tehisaru kord). Praegused plokid on lehe lõpus kokkupandult.
Pealkirjad tulevad andmetest; kui andmed neid enam ei toeta, kukub ehitus (AndmeViga).
"""
import re

from andmekiht import AndmeViga
from avaleht_tahvel import osariba
from komponendid import e, kp, pr
import teema_tahvel as tt
from too_tahvel import jaotusriba

OECD = "OECD (2026)"
ET = [("Uurimine", "etapp-uurimine"), ("Ideed", "etapp-ideed"), ("Prototüüp", "etapp-prototyyp"),
      ("Hindamine", "etapp-hindamine"), ("Otsus", "etapp-otsus")]
MO = [("Eesmärk", "eesmark"), ("Potentsiaal", "potentsiaal"), ("Võimekus", "voimekus"), ("Mõju", "moju")]
HM = [("Protsess", "hindamine-protsess-tootajad"), ("Tasuvus", "hindamine-vfm-tootajad"), ("Teooriapõhine", "hindamine-teooria-tootajad"),
      ("Kulud ja tulud", "hindamine-cba-tootajad"), ("Katse (RCT)", "hindamine-rct-tootajad"), ("Kvaasikatse", "hindamine-kvaasi-tootajad")]
OSK = [("Tehisaru kasutuselevõtt", "oskus-kasutuselevott"), ("Strateegiline juhtimine", "oskus-strateegia"), ("Suhtlus", "oskus-suhtlus"),
       ("Digi- ja andmeoskused", "oskus-digi"), ("Andmepõhised otsused", "oskus-andmeotsused"), ("Tehisaruoskuste arendamine", "oskus-arendus")]


class Andmed:
    """Tahvli ja tunnuspiltide numbrid koos kontrollidega."""

    def __init__(self, A):
        self.O = A["avalik"]
        v = self.v
        uu = re.search(r"Juhtidest (\d+)%, haldustöötajatest (\d+)%", self.O["uuendajad"]["markus"])
        if not uu:
            raise AndmeViga("avalik-sektor.csv: uuendajate märkuses puudub juhtide ja haldustöötajate osa")
        self.juhid, self.haldus = uu.group(1), uu.group(2)
        self.gk, self.gl = self.O["genai-kesk"], self.O["genai-kov"]
        # Uuenduse teekond: suurim langus ja fookus tulevad andmetest
        self.etapid = [(n, v(k), int(self.O[k]["lugeja"])) for n, k in ET]
        lang = [self.etapid[i][1] - self.etapid[i + 1][1] for i in range(len(ET) - 1)]
        self.suurim = max(range(len(lang)), key=lambda i: lang[i])
        self.langus = round(lang[self.suurim])
        if ET[self.suurim][1] != "etapp-prototyyp":
            raise AndmeViga("OECD etapid: suurim langus ei ole enam prototüübist hindamiseni")
        if not 20 <= v("etapp-otsus") <= 30:
            raise AndmeViga("OECD etapid: „otsuseni jõuab veerand“ ei klapi enam")
        if v("indeks-moju-max") >= min(v(f"indeks-{m}-min") for _, m in MO[:3]) or v("indeks-moju-max") >= 0.25:
            raise AndmeViga("OECD indeks: mõju ei ole enam kõigis valitsemisalades alla 0,25 ega teistest mõõtmetest madalam")
        if max(OSK, key=lambda x: v(x[1]))[1] != "oskus-kasutuselevott":
            raise AndmeViga("OECD oskused: tehisaru kasutuselevõtt ei ole enam kõige soovitum oskus")
        # Riigikontroll: 33 asutust on nende hulgas, kes kasutab (leiud-arvud.csv „Neist ilma asutusesisese korrata“)
        self.rk = A["leiud"]["rk-ai-kord"]
        R = {r["ruhm"]: int(r["vaartus"]) for r in A["leiud_arvud"] if r["leid"] == "rk-ai-kord"}
        self.n, self.k, self.kr = R["vastas"], R["kasutab"], R["korrata"]
        if not 0 < self.kr <= self.k <= self.n:
            raise AndmeViga("Riigikontrolli küsitlus: korrata asutused peavad olema kasutajate hulgas")
        if self.kr * 2 <= self.n:
            raise AndmeViga("Riigikontrolli küsitlus: pealkiri eeldab, et kord puudub enamikul vastanutest")

    def v(self, i):
        return float(self.O[i]["vaartus"])


def kaks_riba(read, skaala=100, w=150, h=34):
    """Kaks horisontaalset riba samal skaalal ja samal alusel (sama küsitlus). read: [(silt, väärtus, fookus)]."""
    out = []
    for i, (silt, val, f) in enumerate(read):
        y = 2 + i * 14
        out.append(f'<rect class="tv-bg" x="0" y="{y}" width="{w - 34}" height="8" rx="2"/>'
                   f'<rect class="{"tv-v" if f else "tt-jr m"}" x="0" y="{y}" width="{min(val, skaala) / skaala * (w - 34):.1f}" height="8" rx="2"/>'
                   f'<text class="tt-t{" b" if f else ""}" x="{w - 30}" y="{y + 8}">{e(silt)}</text>')
    aria = "; ".join(f"{s} {pr(x, 0)}%" for s, x, _ in read)
    return f'<svg class="tt-svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-label="{aria}">{"".join(out)}</svg>'


# Vastus sõnaga (Kadri 25.11.2026): sõna tuleb numbrist. Piirid on teema_tahvel.sona_osa ja siin.
PIIR_RAHA = (50, 66)       # ELi osa uuendusrahast, %: üle teise = peamiselt, üle esimese = üle poole


def sona_kord(k, kr):
    """k asutust kasutas tehisaru, neist kr ilma oma korrata. Vastus käib küsitluse aasta järele („2025. aastal …“)."""
    if not 0 <= kr <= k or not k:
        raise AndmeViga(f"Asutuste korra arvud ei klapi: {kr} / {k}")
    return "kõigil oli" if kr == 0 else "enamikul veel mitte" if kr * 2 > k else "enamikul oli"


def sona_katse(p):
    """Mitu protsenti hindamistest oli juhuslikustatud katse → sõna."""
    osa = tt.sona_osa(p)
    return f"{osa} hindamine on katse" if float(p) < 15 else f"{osa} hindamistest on katse"


def sona_raha(p):
    return "Peamiselt ELilt" if p >= PIIR_RAHA[1] else "Üle poole ELilt" if p >= PIIR_RAHA[0] else "Osaliselt ELilt"


def read(D):
    v, gk, gl = D.v, D.gk, D.gl
    return [
        dict(kys="Kui paljud teenistujad teevad uuendusi?", ank="lehter", ava="Ava uuendajad rühmade kaupa", sona=tt.sona_osa(v("uuendajad")),
             arv=f'{pr(v("uuendajad"), 0)}%', all="viimase 24 kuu jooksul",
             pilt=osariba(v("uuendajad"), 100, silt=f'{pr(v("uuendajad"), 0)}%'),
             mrk=f"Juhtidest {D.juhid}%, haldustöötajatest {D.haldus}%. Keskvalitsuses ja omavalitsustes sama.",
             liik="mõõdetud", allikas="OECD küsitlus", kuup="12.2025–02.2026"),
        dict(kys="Kui paljud uuendused jõuavad laiendamiseni?", ank="teekond", ava="Vaata uuenduse teekonda", sona=tt.sona_osa(v("laiendati")),
             arv=f'{pr(v("laiendati"), 0)}%', all=f'olulisimatest uuendustest; rakendati {pr(v("rakendati"), 0)}%',
             pilt=kaks_riba([("rak.", v("rakendati"), False), ("laiend.", v("laiendati"), True)]),
             mrk=f'Projektidest jõuab hindamiseni {pr(v("etapp-hindamine"), 0)}%, otsuseni {pr(v("etapp-otsus"), 0)}%.',
             liik="mõõdetud", allikas="OECD küsitlus", kuup="12.2025–02.2026"),
        dict(kys="Kui paljud uuendajad kasutavad tehisaru?", ank="tehisaru", ava="Ava tehisaru uuendustes", sona=tt.sona_osa(gk["vaartus"]),
             arv=f'{gk["vaartus"]}%', all=f'keskvalitsuse uuendajatest ({gk["lugeja"]}/{gk["nimetaja"]})',
             pilt=kaks_riba([("kesk", v("genai-kesk"), True), ("KOV", v("genai-kov"), False)], 50),
             mrk=f'Omavalitsustes {gl["vaartus"]}% ({gl["lugeja"]}/{gl["nimetaja"]}). Küsiti ainult uuenduse teinutelt.',
             liik="mõõdetud", allikas="OECD küsitlus", kuup="12.2025–02.2026"),
        dict(kys="Kas uuenduste mõju mõõdetakse?", ank="moju", ava="Ava indeks valitsemisalade kaupa",
             # Kadri 26.11.2026 (nõrgad numbrid): nähtav arv on osakaal, mida saab lugeda (katsete osa hindamistest).
             # OECD mõjuskoor 0–1 on koondhinnang ilma loetava ühikuta; see jääb märkusesse ja plokki.
             sona=sona_katse(v("hindamine-rct-tootajad")),
             arv=f'{pr(v("hindamine-rct-tootajad"), 0)}%', all="hindamistest oli juhuvalikuga katse",
             pilt=osariba(v("hindamine-rct-tootajad"), 100, silt=f'{pr(v("hindamine-rct-tootajad"), 0)}%'),
             mrk=(f'OECD mõjuskoor (0–1, kas uuenduste tulemusi mõõdetakse) on valitsemisalati {pr(v("indeks-moju-min"), 2)}–{pr(v("indeks-moju-max"), 2)}, '
                  f'võimekuse skoor {pr(v("indeks-voimekus-min"), 2)}–{pr(v("indeks-voimekus-max"), 2)}. Skoor on koondhinnang, mitte osakaal. '
                  "Katsete osa on teenistujate vastuste järgi."),
             liik="mõõdetud", allikas="OECD küsitlus", kuup="12.2025–02.2026"),
        # Jagaja on asutused, kes valmislahendusi kasutasid (enne oli jagaja kõik vastanud asutused); aasta on vastuses näha.
        dict(kys="Kas asutustel on tehisaru kord?", ank="asutused", ava="Vaata asutusi", sona=f'{D.rk["aasta"]}. aastal {sona_kord(D.k, D.kr)}',
             arv=f"{D.k - D.kr} / {D.k}", all="tehisaru kasutanud asutusest oli oma kord",
             pilt=jaotusriba([("s", (D.k - D.kr) / D.k * 100)], f"{D.k - D.kr} asutusel {D.k}-st oli oma kord"),
             mrk=(f"Riigikontrolli küsitlusele vastas {D.n} ministeeriumi ja suuremat asutust; {D.k} kasutas välismaiseid valmislahendusi. "
                  f'Seis on aastast {D.rk["aasta"]} ja võib olla muutunud.'),
             liik="mõõdetud", allikas="Riigikontroll", kuup=kp(D.rk["avaldatud"])),
        dict(kys="Kust tuleb uuendusraha?", ank="rahastus", ava="Ava rahastus", sona=sona_raha(v("raha-el")),
             arv=f'{pr(v("raha-el"), 0)}%', all="keskvalitsuse uuendusrahast ELilt",
             pilt=osariba(v("raha-el"), 100, silt=f'{pr(v("raha-el"), 0)}% ELilt'),
             mrk=(f'Innovatsioonihangetele läheb {pr(v("hanked-innovatsioon"), 1)}% hangete eelarvest; neid on alla 1% hangete arvust. '
                  "Riigi siht on 2% aastaks 2027; kas siht käib arvu või eelarve kohta, pole kontrollitud."),
             liik="mõõdetud", allikas="OECD aruanne", kuup="2026"),
    ]


def tahvel(D):
    return tt.vastustahvel("tahvel", "Kuidas riik uuendab ja tehisaru kasutab?",
                           "Iga rida on oma alusel (teenistujad, uuendused, asutused); eri ridade numbreid ei võrrelda.", read(D))


def _mini(read, laius, fookus=None):
    fk = ' class="f"'
    return '<ul class="av-mini">' + "".join(
        f'<li{fk if i == fookus else ""}><span>{e(n)}</span><i style="width:{x * laius:.0f}px"></i><b>{pr(x, 0)}%</b></li>'
        for i, (n, x) in enumerate(read)) + "</ul>"


def sec_teekond(D):
    """A: uuendusprojektid etappide kaupa; fookus pärast suurimat langust."""
    vals, s, w, h = D.etapid, D.suurim, 720, 260
    bw = (w - 40) / len(vals)
    Y = lambda p: h - 40 - p / 100 * (h - 80)  # noqa: E731
    o = []
    for p in (0, 25, 50, 75, 100):
        o.append(f'<line class="tv-ax" x1="30" x2="{w}" y1="{Y(p):.1f}" y2="{Y(p):.1f}" opacity=".35"/>'
                 f'<text class="tt-t" x="24" y="{Y(p) + 4:.1f}" text-anchor="end">{p}%</text>')
    for i, (n, p, cnt) in enumerate(vals):
        x, f, kx = 40 + i * bw, i > s, 40 + i * bw + (bw - 18) / 2
        o.append(f'<rect class="{"tv-v" if f else "tt-jr m"}" x="{x:.1f}" y="{Y(p):.1f}" width="{bw - 18:.1f}" height="{Y(0) - Y(p):.1f}" rx="3"/>'
                 f'<text class="tt-t b" x="{kx:.1f}" y="{Y(p) - 8:.1f}" text-anchor="middle" style="font-size:15px">{pr(p, 0)}%</text>'
                 f'<text class="tt-t tt-as" x="{kx:.1f}" y="{h - 22}" text-anchor="middle">{e(n)}</text>'
                 f'<text class="tt-t" x="{kx:.1f}" y="{h - 6}" text-anchor="middle">{cnt} projekti</text>')
        if i < len(vals) - 1:
            o.append(f'<path class="av-pr" d="M{x + bw - 18:.1f},{Y(p):.1f} L{x + bw:.1f},{Y(vals[i + 1][1]):.1f}" fill="none"/>')
    xm = 40 + s * bw + bw - 9
    o.append(f'<text class="tt-t b f" x="{xm:.1f}" y="{Y(vals[s][1]) - 30:.1f}" text-anchor="middle" style="font-size:14px">−{D.langus} p</text>')
    aria = "Uuendusprojektid etappide kaupa: " + ", ".join(f"{n} {pr(p, 0)}%" for n, p, _ in vals)
    svg = f'<svg class="tt-svg tt-sc-lai" viewBox="0 0 {w} {h}" width="100%" role="img" aria-label="{aria}">{"".join(o)}</svg>'
    kw, rh = 340, 40
    XK = lambda p: 92 + p / 100 * (kw - 140)  # noqa: E731
    ko = []
    for i, (n, p, cnt) in enumerate(vals):
        y, f = 8 + i * rh, i > s
        ko.append(f'<text class="tt-t tt-as" x="0" y="{y + 13}" style="font-size:13px">{e(n)}</text><text class="tt-t" x="0" y="{y + 28}">{cnt} projekti</text>'
                  f'<rect class="{"tv-v" if f else "tt-jr m"}" x="92" y="{y + 4}" width="{XK(p) - 92:.1f}" height="18" rx="3"/>'
                  f'<text class="tt-t b{" f" if f else ""}" x="{XK(p) + 6:.1f}" y="{y + 18}" style="font-size:14px">{pr(p, 0)}%</text>')
    ko.append(f'<text class="tt-t b f" x="{kw}" y="{8 + (s + 1) * rh - 2}" text-anchor="end" style="font-size:13px">−{D.langus} p</text>')
    svg += f'<svg class="tt-svg tt-sc-kitsas" viewBox="0 0 {kw} {8 + len(vals) * rh}" width="100%" role="img" aria-label="{aria}">{"".join(ko)}</svg>'
    return f"""
<section class="jaotis" id="teekond" aria-labelledby="h-teekond">
  <header><h2 id="h-teekond"><span class="kys">Kus uuendus pidama jääb?</span> <b>Prototüübist hindamiseni jõuab {D.langus} protsendipunkti vähem projekte</b> ¦ otsuseni jõuab veerand projektidest</h2>
  <p class="alam">Uuendusprojektide osa, mis jõudis etapini; vastajad kirjeldasid oma projekte. Olulisimatest uuendustest rakendati {pr(D.v("rakendati"), 0)}% ja laiendati {pr(D.v("laiendati"), 0)}%. Tehisaru projekte eraldi ei loendata.</p></header>
  <div class="av-kaks">
    <figure class="av-fig">{svg}</figure>
    <div><p class="gt">Kuidas hinnatakse? % töötajate kirjeldatud hindamistest</p>{_mini([(n, D.v(k)) for n, k in HM], 2)}
      <p class="allikas">Üks hindamine võib kasutada mitut meetodit. Mõju näitavaid katseid on vähe, seepärast on otsustajal vähe tõendeid laiendamiseks (OECD).</p></div>
  </div>
  <p class="allikas">{OECD}, joonised 6.2–6.4 (lk 131–133), küsitlus 12.2025–02.2026.</p>
</section>"""


def sec_asutused(D):
    """C: 48 asutust Riigikontrolli küsitlusest, üks ruut = üks asutus; kõrval teenistujate soovitud oskused."""
    n, k, kr, rk, O = D.n, D.k, D.kr, D.rk, D.O
    ruudud = "".join(f'<i class="av-q {"a" if i < kr else "b" if i < k else "c"}"></i>' for i in range(n))
    lisa = " ".join(lause for lause in re.split(r"(?<=\.) ", rk["markus"]) if "ChatGPT" in lause or "Ei ole kõigi" in lause)
    if "ChatGPT" not in lisa:
        raise AndmeViga("Riigikontrolli leiu märkuses puudub ChatGPT ja Copiloti arv")
    hoiatus = O["oskus-arendus"]["markus"]
    return f"""
<section class="jaotis" id="asutused" aria-labelledby="h-asutused">
  <header><h2 id="h-asutused"><span class="kys">Kas tehisaru kasutus on asutustes korraldatud?</span> <b>{kr} asutust {n}-st kasutas tehisaru valmislahendusi ilma oma korrata</b> ¦ töötajad tahavad kõige rohkem õppida just kasutuselevõttu</h2>
  <p class="alam">Riigikontrolli küsitlus {rk["aasta"]}: vastas {n} ministeeriumi ja suuremat asutust. Üks ruut on üks asutus.</p></header>
  <div class="av-kaks">
    <div><div class="av-qq" role="img" aria-label="{n} asutust: {kr} kasutas ilma korrata, {k - kr} korraga, {n - k} ei kasutanud">{ruudud}</div>
      <ul class="av-qleg"><li><i class="av-q a"></i><b>{kr}</b> kasutas, kord puudus</li><li><i class="av-q b"></i><b>{k - kr}</b> kasutas, kord oli</li><li><i class="av-q c"></i><b>{n - k}</b> ei kasutanud</li></ul>
      <p class="allikas"><a href="{e(rk["url"])}">Riigikontroll</a>, {kp(rk["avaldatud"])}, {e(rk["koht"].split(";")[0])}. {e(lisa)}</p></div>
    <div><p class="gt">Mida teenistujad tahavad kõige rohkem õppida? % {O["oskus-kasutuselevott"]["nimetaja"]} vastusest</p>{_mini([(x, D.v(kk)) for x, kk in OSK], 4, fookus=0)}
      <p class="allikas">{OECD}, joonis 7.8 (lk 162); vabad vastused rühmitas keelemudel, tõlget kontrollis inimene. {e(hoiatus)}</p></div>
  </div>
</section>"""
