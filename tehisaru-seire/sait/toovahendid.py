"""Töö › Arendajate tööriistad (Kadri 27.11.2026): kuidas IT-arendajate töövahendid muutuvad.

Kes loeb: inimene, kes töötab IT-s, otsib pärast koondamist uut tööd või õpib ümber.
Küsimus: milliste tööriistadega arendajad praegu töötavad ja kuidas see on muutunud?
Pärast teab lugeja, et agendid ja käsurea tööriistad on tööl tavaline vahend, ja näeb, kui kindlad need numbrid on.
Põhiline: agentide kasutus tööl (JetBrains), käsurea tööriistade allalaadimised (npm), arenduskeskkonnad (Stack Overflow).
Valikuline: AI üldine kasutus, keelemudelite pakkujad, lokaalsed mudelid, mida me ei tea.

Andmed: sisu/it-toovahendid.csv (uurimislõim 27.11.2026, iga rida koos lingi, perioodi ja võrreldavusega) ja
sisu/cli-allalaadimised.csv (npm ja PyPI täis kuud). Eri allikaid ühte aegritta ei liideta: iga graafik on ühest allikast.
"""
import csv
from pathlib import Path

from andmekiht import AndmeViga
from komponendid import allikarida, e, kp, lihtribad, pr, tabel

SISU = Path(__file__).resolve().parent / "sisu"
NPM_API = "https://api.npmjs.org/downloads/range/{alg}:{lopp}/{pakett}"


def _loe(nimi):
    with open(SISU / nimi, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def uuring():
    """Read failist sisu/it-toovahendid.csv. Rida ilma lingi või allikata kukutab ehituse."""
    out = _loe("it-toovahendid.csv")
    for r in out:
        if not r["url"].startswith("https://") or not r["allikas"]:
            raise AndmeViga(f"sisu/it-toovahendid.csv: real „{r['naitaja']}“ puudub allikas või link")
    return out


def _read(U, naitaja, allikas=None):
    return [r for r in U if r["naitaja"] == naitaja and (allikas is None or r["allikas"] == allikas) and r["vaartus_protsent"]]


def allalaadimised():
    """{nimi: {"read": [(kuu, arv)], "url", "register", "laaditud"}}; ainult täis kuud."""
    out = {}
    for r in _loe("cli-allalaadimised.csv"):
        t = out.setdefault(r["nimi"], {"read": [], "url": r["url"], "register": r["register"], "laaditud": r["laaditud"],
                                       "pakett": r["pakett"]})
        t["read"].append((r["kuu"], int(r["allalaadimised"])))
    for t in out.values():
        t["read"].sort()
    return out


def _v(U, naitaja, allikas, aasta, kogumine=""):
    """Üks väärtus. kogumine: kogumisperioodi algus, kui samal aastal on mitu mõõtmist."""
    rr = [r for r in _read(U, naitaja, allikas) if r["aasta"] == aasta and r["valja_kogumine"].startswith(kogumine)]
    if len(rr) != 1:
        raise AndmeViga(f"sisu/it-toovahendid.csv: „{naitaja}“ ({allikas}, {aasta}, {kogumine or 'kogumine'}) "
                        f"ridu {len(rr)}, vaja täpselt üks")
    return float(rr[0]["vaartus_protsent"]), rr[0]


JB = "JetBrains Developer Ecosystem"
JBP = "JetBrains AI Pulse"
SO = "Stack Overflow Developer Survey"
GH = "GitHub Octoverse"
OR = "OpenRouter State of AI"

# JetBrainsi kolm lainet. x on kuu number alates jaanuarist 2025 (laine keskkoht), et vahed oleksid õiged.
LAINED = [(4, "kevad 2025"), (12, "jaan 2026"), (18, "mai–juuli 2026")]


def _laine(r):
    if r["allikas"] == JBP and r["aasta"] == "2025":
        return 4
    if r["allikas"] == JB and r["aasta"] == "2025":
        return 4
    if r["allikas"] == JBP and r["aasta"] == "2026":
        return 12
    if r["allikas"] == JB and r["aasta"] == "2026":
        return 18
    raise AndmeViga(f"JetBrainsi laine on tundmata: {r['naitaja']} {r['allikas']} {r['aasta']}")


def _mln(n):
    return pr(n / 1e6, 1)


def _arvu(n):
    """Allalaadimised loetavalt: miljonid ühe komakohaga, alla 100 000 tuhanded."""
    return f"{_mln(n)} mln" if n >= 1e5 else f"{pr(n / 1e3, 0)} tuh"


def _tuh(s):
    return f"{int(s):,}".replace(",", "\u00a0") if str(s).isdigit() else s


def h1(U):
    """Alamlehe h1 andmetest (sisuloogika: h1 on vastuse lause)."""
    v1, _ = _v(U, "Claude Code kasutus tööl", JB, "2026")
    v0, _ = _v(U, "Claude Code kasutus tööl", JBP, "2025")
    if v1 <= v0:
        raise AndmeViga("Arendajate tööriistade h1 ütleb, et agentide kasutus kasvas; andmed seda ei näita")
    return (f"**Arendajad töötavad üha rohkem agentidega**: Claude Code'i kasutas tööl {pr(v1, 0)}% ¦ "
            f"Nii suur osa professionaalsetest arendajatest kasutas Claude Code'i 2026. aasta mai–juulis, 2025. aasta "
            f"kevadel umbes {pr(v0, 0)}%. Eesti kohta eraldi numbrit ei ole.")


def sec_agendid(U):
    from lehed_ulevaade import joon
    seeriad = []
    for nimi, naitaja, liik in [("Claude Code", "Claude Code kasutus tööl", "fookus"),
                                ("Copilot", "GitHub Copilot kasutus tööl", ""),
                                ("Codex", "OpenAI Codex kasutus tööl", ""),
                                ("Cursor", "Cursor kasutus tööl", "")]:
        pts = sorted((_laine(r), float(r["vaartus_protsent"])) for r in _read(U, naitaja))
        if len(pts) < 2:
            raise AndmeViga(f"Agentide graafik vajab vähemalt kahte lainet: {naitaja}")
        seeriad.append((nimi, pts, liik))
    silt = dict(LAINED)
    joonis = joon(seeriad, 4, 18, 45, 10, w=460, h=220, ml=30, mr=96, x_margid=[x for x, _ in LAINED],
                  x_silt=lambda x: silt[x], silt="Tööriista kasutav osa arendajatest tööl, %, JetBrainsi kolm küsitlust")
    nadal, r_n = _v(U, "Kasutab agente vähemalt kord nädalas tööl", JB, "2026")
    pr0, r_pr = _v(U, "Agendi alustatud PR-id GitHubis", GH, "2026", "märts")
    pr1, _ = _v(U, "Agendi alustatud PR-id GitHubis", GH, "2026", "september")
    gh = lihtribad([("märts 2026", pr0, f"{pr(pr0, 0)}%"), ("september 2026", pr1, f"üle {pr(pr1, 0)}%")], 50, 10, fookus=1)
    return f"""
<div class="g12">
<section class="pn sp6" id="agendid" aria-labelledby="h-agendid">
  <div class="pn-h"><h2 id="h-agendid">Claude Code tõusis umbes aastaga <b>umbes 3%-lt {pr(seeriad[0][1][-1][1], 0)}%-le</b> arendajatest, Copilot ja Cursor langesid</h2></div>
  <p class="ps">Osa professionaalsetest arendajatest, kes kasutab tööriista tööl, %. Kolm JetBrainsi küsitlust, iga laine üle 10 000 vastaja, kaalutud sama moodi. Üks inimene võib kasutada mitut tööriista, nii et summa on üle 100%. {pr(nadal, 0)}% vastanutest kasutas mõnda agenti vähemalt kord nädalas.</p>
  {joonis}
  {allikarida([("JetBrains AI Pulse, aprill 2026", _v(U, "Claude Code kasutus tööl", JBP, "2026")[1]["url"], "kevad 2025 ja jaanuar 2026"),
               ("JetBrains Developer Ecosystem 2026", r_n["url"], "mai–juuli 2026")])}
</section>
<section class="pn sp6" id="agendi-pr" aria-labelledby="h-agendi-pr">
  <div class="pn-h"><h2 id="h-agendi-pr">GitHubis alustas agent pool aastaga <b>{pr(pr0, 0)}%-lt üle {pr(pr1, 0)}%-ni</b> uutest koodimuudatustest</h2></div>
  <p class="ps">Osa GitHubi muudatusettepanekutest (PR), mille esimese mustandi tegi tuvastatav agent. See on platvormi enda mõõtmine ja alampiir: agenti, mis end ei märgi, ei loeta.</p>
  {gh}
  {allikarida([("GitHub Octoverse 2026", r_pr["url"], "")])}
</section>
</div>"""


def sec_kasurida(L):
    """Käsurea agentide allalaadimised kuus, iga tööriist oma skaalal (väike graafik), sest paigaldusviisid erinevad."""
    from lehed_ulevaade import joon
    paneelid = []
    for nimi in ("Claude Code", "OpenAI Codex CLI", "GitHub Copilot CLI", "Gemini CLI"):
        t = L.get(nimi)
        if not t or len(t["read"]) < 6:
            raise AndmeViga(f"sisu/cli-allalaadimised.csv: tööriistal {nimi} on vähem kui 6 kuud")
        rr = t["read"]
        idx = {k: i for i, (k, _) in enumerate(rr)}
        n = len(rr) - 1
        kuu = lambda i: rr[int(i)][0][5:] + "." + rr[int(i)][0][:4]  # noqa: E731
        g = joon([(nimi.replace("OpenAI ", "").replace("GitHub ", ""), [(idx[k], v / 1e6) for k, v in rr],
                   "fookus" if nimi == "Claude Code" else "ref")],
                 0, n, 1, 1, w=300, h=130, ml=8, mr=64, mb=20, x_margid=[0, n], x_silt=kuu, lihtne=True,
                 silt=f"{nimi}: allalaadimised kuus, miljonites")
        tipp_k, tipp = max(rr, key=lambda r: r[1])
        lopp_k, lopp = rr[-1]
        tipp_lause = "" if tipp_k == lopp_k else f" Suurim kuu {tipp_k[5:]}.{tipp_k[:4]}: {_arvu(tipp)}."
        aasta_k = f"{int(lopp_k[:4]) - 1}{lopp_k[4:]}"
        varem = dict(rr).get(aasta_k)
        vrd = (f"aasta varem {_arvu(varem)}" if varem else f"esimene täis kuu {rr[0][0][5:]}.{rr[0][0][:4]}: {_arvu(rr[0][1])}")
        paneelid.append(f"""
<section class="pn sp3 cli" aria-label="{e(nimi)}">
  <h3 class="gt">{e(nimi)}</h3>
  <p class="ps"><b>{_arvu(lopp)}</b> allalaadimist {lopp_k[5:]}.{lopp_k[:4]}, {vrd}.{tipp_lause}</p>
  {g}
  {allikarida([(f"{t['register']}, {t['pakett']}", t["url"], f"laaditud {kp(t['laaditud'])}")])}
</section>""")
    cc = L["Claude Code"]["read"]
    cc_k, cc_n = cc[-1]
    cc_0 = dict(cc).get(f"{int(cc_k[:4]) - 1}{cc_k[4:]}")
    if not cc_0 or cc_n <= cc_0:
        raise AndmeViga("Käsurea pealkiri ütleb, et Claude Code'i allalaadimised kasvasid aastaga; andmed seda ei näita")
    a = L.get("Aider")
    aider = ""
    if a:
        aider = (f'<p class="ps">Pythoni käsurea agent Aider: {_arvu(a["read"][0][1])} allalaadimist {a["read"][0][0][5:]}.{a["read"][0][0][:4]}, '
                 f'{_arvu(a["read"][-1][1])} {a["read"][-1][0][5:]}.{a["read"][-1][0][:4]} '
                 f'(<a href="{e(a["url"])}">PyPI, pypistats</a>; varasemad kuud pole saadaval).</p>')
    return f"""
<section class="jaotis" id="kasurida" aria-labelledby="h-kasurida">
  <header>
    <h2 id="h-kasurida"><span class="kys">Kas arendajad töötavad käsureal agentidega?</span> Käsurea agente laaditakse alla <b>kümneid miljoneid kordi kuus</b>: Claude Code'i {cc_k[5:]}.{cc_k[:4]} {_arvu(cc_n)} korda, aasta varem {_arvu(cc_0)}</h2>
    <p class="alam">Käsurea agent on tööriist, millele arendaja kirjutab terminalis ülesande ja mis loeb ning muudab koodi ise. Allalaadimised kuus, miljonites, täis kuud. Igal graafikul on oma skaala.</p>
  </header>
  <div class="g12">{"".join(paneelid)}</div>
  <p class="allikas"><b>Allalaadimine ei ole kasutaja.</b> Arvu kasvatavad automaatsed uuendused, testserverid ja robotid. Tööriistu saab paigaldada ka ilma npm-ita (näiteks oma paigaldaja või rakendusega), seepärast ei saa tööriistu nende arvude järgi omavahel võrrelda: vaata ainult iga joone suunda. Codexi mai 2026 hüppe põhjust ei ole teada. Arvud on kogu maailma kohta, Eesti oma ei ole eraldi saadaval.</p>
  {aider}
</section>"""


def sec_ide(U):
    from lehed_ulevaade import joon
    seeriad = []
    for nimi, naitaja, liik in [("VS Code", "VS Code kasutajad", "fookus"), ("Sublime Text", "Sublime Text kasutajad", ""),
                                ("Neovim", "Neovim kasutajad", ""), ("Cursor", "Cursor kasutajad", "")]:
        pts = sorted((int(r["aasta"]), float(r["vaartus_protsent"])) for r in _read(U, naitaja, SO))
        if len(pts) < 2:
            raise AndmeViga(f"Arenduskeskkondade graafik vajab vähemalt kahte aastat: {naitaja}")
        seeriad.append((nimi, pts, liik))
    joonis = joon(seeriad, 2018, 2026, 80, 20, w=460, h=220, ml=30, mr=104, x_margid=[2018, 2021, 2026],
                  silt="Arenduskeskkonda kasutav osa vastajatest, %, Stack Overflow 2018–2026")
    vs = dict(seeriad[0][1])
    n18 = _v(U, "VS Code kasutajad", SO, "2018")[1]["valim_kusimusele"]
    n26 = _v(U, "VS Code kasutajad", SO, "2026")[1]["valim_kusimusele"]
    return f"""
<section class="jaotis" id="ide" aria-labelledby="h-ide">
  <header>
    <h2 id="h-ide"><span class="kys">Millises programmis koodi kirjutatakse?</span> <b>VS Code on kõige levinum</b>: 2018. aastal kasutas seda {pr(vs[2018])}%, 2026. aastal {pr(vs[2026])}% vastajatest</h2>
    <p class="alam">Arenduskeskkond (IDE) on programm, milles koodi kirjutatakse. Stack Overflow küsitlus, kõik vastajad, %. Vanad redaktorid (Sublime Text) langesid; tehisaruga redaktor Cursor ja terminalis töötav Neovim tõusid.</p>
  </header>
  <figure class="as-fig">{joonis}</figure>
  {allikarida([("Stack Overflow Developer Survey 2018", _v(U, "Sublime Text kasutajad", SO, "2018")[1]["url"], ""),
               ("2025", _v(U, "Cursor kasutajad", SO, "2025")[1]["url"], ""),
               ("2026", _v(U, "Cursor kasutajad", SO, "2026")[1]["url"], "")])}
  <p class="allikas">Vastajad valivad end ise, nii et need ei ole kõik arendajad. 2026. aastal oli küsimus laiem ja vastajaid vähem ({_tuh(n26)}, 2018. aastal {_tuh(n18)}), seepärast ei tähenda VS Code'i langus {pr(vs[2025])}%-lt {pr(vs[2026])}%-le kindlat muutust.</p>
</section>"""


def _ribad(U, read, lopp, fookus=0):
    return lihtribad([(silt, _v(U, n, a, y)[0], None) for silt, n, a, y in read], lopp, 20, fookus=fookus, k=0)


def uksikasjad(U, L):
    import teema_tahvel as tt
    ai = [(y, _v(U, "Kasutab AI-tööriistu arendustöös", SO, y)[0]) for y in ("2023", "2024", "2025")]
    v26, r26 = _v(U, "Kasutab mõnda AI-tööriista", SO, "2026")
    agent_kood, r_k = _v(U, "Agendi täielikult kirjutatud koodi osa (keskmine)", JB, "2026")
    kasitsi, _ = _v(U, "Täiesti käsitsi kirjutatud koodi osa (keskmine)", JB, "2026")
    paev, _ = _v(U, "Kasutab agente iga päev tööl", JB, "2026")
    kasutus = f"""
<p class="ps">Stack Overflow küsitluses ütles, et kasutab tehisaru arendustöös: {", ".join(f"{y}. aastal {pr(v)}%" for y, v in ai)}. 2026. aastal küsiti teisiti (tööriistaliikide kaupa): mõnda tehisaru tööriista kasutas {pr(v26)}%. Seda ei panda eelmistega ühte ritta.</p>
{lihtribad([(f"{y}", v, None) for y, v in ai], 100, 20, fookus=2, k=0)}
{allikarida([(f"Stack Overflow {y}", _v(U, "Kasutab AI-tööriistu arendustöös", SO, y)[1]["url"], "") for y, _ in ai] + [("2026", r26["url"], "teine küsimus")])}
<p class="ps">JetBrainsi 2026. aasta küsitluses kasutas agenti iga päev {pr(paev, 0)}% professionaalsetest arendajatest. Vastajate hinnangul kirjutas agent eelmisel kuul keskmiselt {pr(agent_kood, 0)}% nende töökoodist täielikult ja {pr(kasitsi, 0)}% kirjutati täiesti käsitsi. See on enesehinnang, mitte mõõtmine.</p>
{allikarida([("JetBrains, 2026", r_k["url"], "mai–juuli 2026")])}"""
    pakkujad = [("Anthropic", "Anthropic (pakkuja)"), ("OpenAI", "OpenAI (pakkuja)"), ("Google", "Google (pakkuja)"),
                ("DeepSeek", "DeepSeek (pakkuja)"), ("Alibaba Qwen", "Alibaba Qwen (pakkuja)"), ("Mistral", "Mistral AI (pakkuja)")]
    _, r_p = _v(U, "Anthropic (pakkuja)", SO, "2026")
    p0, r_o = _v(U, "Programmeerimise osa kõigist tokenitest", OR, "2025", "alguses")
    p1, _ = _v(U, "Programmeerimise osa kõigist tokenitest", OR, "2025", "nov")
    mudelid = f"""
<p class="ps">Stack Overflow 2026: milliste pakkujate keelemudeleid arendajad kasutasid, % neist, kes küsimusele vastasid (n {_tuh(r_p["valim_kusimusele"])}). Üks inimene võib kasutada mitut.</p>
{_ribad(U, [(s, n, SO, "2026") for s, n in pakkujad], 100)}
{allikarida([("Stack Overflow 2026", r_p["url"], "")])}
<p class="ps">Vahendusplatvormil OpenRouter kasvas programmeerimise osa kõigist töödeldud tokenitest 2025. aastal umbes {pr(p0, 0)}%-lt üle {pr(p1, 0)}%-ni. See on ühe platvormi liiklus, mitte kogu turg.</p>
{allikarida([("OpenRouter, State of AI", r_o["url"], "nov 2024 – nov 2025")])}"""
    ollama, r_ol = _v(U, "Ollama agentide raamistikuna", SO, "2025")
    avatud, r_av = _v(U, "Avatud kaaludega mudelite osa tokenitest", OR, "2025")
    lokaal = f"""
<p class="ps"><b>Kui palju arendajad kasutavad oma arvutis töötavaid mudeleid, ei ole hästi mõõdetud.</b> Esinduslikku numbrit ei leidnud. Kaks kaudset märki:</p>
<ul>
<li>Stack Overflow 2025: neist, kes ehitavad või kasutavad AI-agente, nimetas {pr(ollama)}% lokaalsete mudelite tööriista Ollama. See on väike alamhulk, mitte kõik arendajad (<a href="{e(r_ol["url"])}">allikas</a>).</li>
<li>OpenRouteris oli 2025. aasta lõpus avatud kaaludega mudelite osa tokenitest umbes {pr(avatud, 0)}%. Need töötavad pilves, mitte arendaja arvutis (<a href="{e(r_av["url"])}">allikas</a>).</li>
</ul>"""
    ei_tea = """
<ul>
<li><b>Eesti kohta eraldi numbrit ei ole.</b> Rahvusvahelistes küsitlustes on Eesti vastajaid vähe ja nende arvu pole kontrollitud.</li>
<li><b>Käsurea ja arenduskeskkonna jaotust ei mõõda keegi otse.</b> Allalaadimised näitavad suunda, mitte kasutajate arvu.</li>
<li><b>Küsitlustele vastavad need, kes ise tahavad.</b> Stack Overflow ja JetBrainsi vastajad ei ole kõigi arendajate juhuvalim; JetBrains kaalub tulemusi, Stack Overflow mitte.</li>
<li><b>Allikaid ei liideta.</b> Stack Overflow ja JetBrainsi numbreid ei panda ühte aegritta, sest küsimus ja vastajad on erinevad.</li>
</ul>"""
    return tt.uksikasjad([
        ("tv-kasutus", "Kui paljud arendajad kasutavad tehisaru?", "Stack Overflow 2023–2026, agendi kirjutatud kood", kasutus),
        ("tv-mudelid", "Milliste ettevõtete mudeleid kasutatakse?", "Stack Overflow 2026, OpenRouter", mudelid),
        ("tv-lokaal", "Kas kasutatakse oma arvutis töötavaid mudeleid?", "esinduslikku numbrit pole", lokaal),
        ("tv-ei-tea", "Mida need numbrid ei näita?", "Eesti, kasutajate arv, valim", ei_tea),
    ]).replace('id="h-uksikasjad"', 'id="h-tv-uksikasjad"').replace('aria-labelledby="h-uksikasjad"', 'aria-labelledby="h-tv-uksikasjad"')


RYHMAD = ("1–5", "6–15", "16+")
JB_2026 = "https://blog.jetbrains.com/research/2026/11/state-of-developer-ecosystem-2026"
SLASHDATA = "https://www.slashdata.co/blog/ai-developer-tools-roi-experience"


def kogemus():
    """{(küsimus, näitaja, rühm): rida} failist sisu/so2026-kogemus.csv (sait/lae_so_kogemus.py, Stack Overflow toorandmed)."""
    out = {}
    for r in _loe("so2026-kogemus.csv"):
        if not r["url"].startswith("https://"):
            raise AndmeViga(f"sisu/so2026-kogemus.csv: real {r['naitaja']} puudub link")
        out[(r["kusimus"], r["naitaja"], r["ryhm"])] = {**r, "osa": float(r["osa"]), "valim": int(r["valim"])}
    return out


def sec_kogemus(K, U):
    """Kadri 27.11.2026: kas kogenud (senior) arendajad kasutavad teisi tööriistu kui teised?
    Stack Overflow ei avalda tööriistu staaži järgi; arvutasime toorandmetest (lae_so_kogemus.py). Kogu valimi arvud
    peavad klappima Stack Overflow' avaldatud arvudega, muidu on arvutus vale."""
    def o(kus, n, g):
        r = K.get((kus, n, g))
        if r is None:
            raise AndmeViga(f"sisu/so2026-kogemus.csv: puudub {kus} {n} {g}")
        return r
    avaldatud = _v(U, "Kasutab koodiassistenti või koodiagenti", SO, "2026")[0]
    if abs(o("AISelect", "Kasutab koodiassistenti või koodiagenti", "kõik")["osa"] - avaldatud) > 0.05:
        raise AndmeViga("Toorandmetest arvutatud koodiagentide osa ei klapi Stack Overflow' avaldatud arvuga")
    pea = "Kasutab koodiassistenti või koodiagenti"
    a = [o("AISelect", pea, g) for g in RYHMAD]
    if not (a[0]["osa"] < a[1]["osa"] and a[0]["osa"] < a[2]["osa"]):
        raise AndmeViga("Kogemuse pealkiri ütleb, et 1–5 aasta staažiga arendajad kasutavad koodiagente kõige vähem")
    ribad = lihtribad([(f"{g} aastat tööl", r["osa"], f"{pr(r['osa'])}%") for g, r in zip(RYHMAD, a)], 100, 20, fookus=0)
    def rida(kus, n, nimi=None):
        return [f"<b>{e(nimi or n)}</b>"] + [f"{pr(o(kus, n, g)['osa'], 0)}%" for g in RYHMAD]
    agendid = tabel(["Koodiagent", "1–5 a", "6–15 a", "16+ a"],
                    [rida("AICodeAgent", n, s) for n, s in [("Claude Code", None), ("GitHub Copilot", None), ("OpenAI Codex", None),
                                                           ("Cursor", None), ("Open Code", "OpenCode")]],
                    pealdis="Koodiagendi kasutajatest, kes tööriista kasutas, tööstaaži järgi", tel="1:40%")
    ide = tabel(["Arenduskeskkond", "1–5 a", "6–15 a", "16+ a"],
                [rida("DevIDE", n, s) for n, s in [("Visual Studio Code", "VS Code"), ("Neovim", None), ("Zed", None),
                                                   ("Cursor", None), ("Visual Studio", None)]],
                pealdis="Arenduskeskkonna kasutajad tööstaaži järgi", tel="1:40%")
    cc = [o("AICodeAgent", "Claude Code", g)["osa"] for g in RYHMAD]
    nv = [o("DevIDE", "Neovim", g)["osa"] for g in RYHMAD]
    va = lambda kus, n: "; ".join(f"{g} a: {_tuh(o(kus, n, g)['valim'])}" for g in RYHMAD)  # noqa: E731
    return f"""
<section class="jaotis" id="kogemus" aria-labelledby="h-kogemus">
  <header>
    <h2 id="h-kogemus"><span class="kys">Kas kogenud arendajad kasutavad teisi tööriistu?</span> <b>Alla kuueaastase staažiga arendajad kasutavad koodiagente kõige vähem</b>: {pr(a[0]["osa"])}%, 6–15 aasta staažiga {pr(a[1]["osa"])}%</h2>
    <p class="alam">Stack Overflow 2026, kõik vastajad, % igas staažirühmas. Staaž on aastad tööl, mitte ametinimetus (näiteks senior). Toorandmetest arvutanud seire; kõigi vastajate arvud klapivad Stack Overflow' avaldatud arvudega.</p>
  </header>
  {ribad}
  <div class="g12">
    <section class="pn sp6" aria-label="Koodiagendid staaži järgi">
      <h3 class="gt">Kogenumad kasutavad sagedamini Claude Code'i: {pr(cc[0], 0)}% vs {pr(min(cc[1:]), 0)}–{pr(max(cc[1:]), 0)}%</h3>
      <p class="ps">% koodiagendi kasutajatest. Copiloti ja Codexi kasutus staažist peaaegu ei sõltu.</p>
      {agendid}
    </section>
    <section class="pn sp6" aria-label="Arenduskeskkonnad staaži järgi">
      <h3 class="gt">Algajad kasutavad sagedamini Neovimi: {pr(nv[0], 0)}% vs {pr(nv[2], 0)}% 16+ aasta staažiga</h3>
      <p class="ps">% arenduskeskkonna küsimusele vastanutest. Neovim on terminalis töötav redaktor.</p>
      {ide}
    </section>
  </div>
  {allikarida([("Stack Overflow Developer Survey 2026, toorandmed", o("AISelect", pea, "kõik")["url"], "kogutud 23.06.–05.08.2026")])}
  <p class="allikas">Tehisaru tööriistade küsimusele vastas {va("AISelect", pea)}. Vastajad valivad end ise ja tulemusi ei kaaluta. Eestist vastas 35 inimest, seepärast Eesti jaotust ei näidata. Teised uuringud kogemuse kohta: JetBrainsi 2026. aasta küsitluses peab AI lahendust enda omast paremaks 60% 1–2 aasta ja 47% 16+ aasta kogemusega arendajatest (<a href="{JB_2026}">JetBrains</a>); SlashData Q1 2026 järgi hoiab AI kordusülesannetelt aega kokku 62%-l 16+ aasta ja 42%-l 0–2 aasta kogemusega arendajatest (<a href="{SLASHDATA}">SlashData</a>).</p>
</section>"""


def plokid(A, vaade):
    """Töö vaate plokid alamlehele too-toovahendid.html."""
    from abi import alam_h1
    U, L = uuring(), allalaadimised()
    alam_h1(vaade, "too-toovahendid.html", h1(U))
    return [
        ("tv-agendid", [("agendid", "Agendid")], sec_agendid(U)),
        ("tv-kasurida", [("kasurida", "Käsurida")], sec_kasurida(L)),
        ("tv-kogemus", [("kogemus", "Staaži järgi")], sec_kogemus(kogemus(), U)),
        ("tv-ide", [("ide", "Arenduskeskkonnad")], sec_ide(U)),
        ("tv-uksikasjad", [("h-tv-uksikasjad", "Üksikasjad")], uksikasjad(U, L)),
    ]
