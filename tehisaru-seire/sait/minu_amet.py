"""Töö › Minu amet (Kadri 27.11.2026, topelt-teemandi samm 2, kontseptsioon K2).

Kes loeb: töötaja, kes tahab teada, kas tehisaru puudutab tema ametit.
Küsimus: kui avatud on minu amet tehisarule ja kas minu ametirühmas on tööd vähem?
Pärast teab lugeja oma ameti ILO astet, kui palju inimesi selles Eestis töötab, kuidas ametirühma hõive on muutunud
ja kas koondajad on seda liiki töökohti kaotanud. Ta teab ka, et aste ei ütle, kas töö kaob.
Põhiline: ameti valik ja vastus. Toetav: ametirühmade tabel. Valikuline: kuidas lugeda, mida see ei näita.

Andmed:
- ILO 2025 kokkupuute indeks 4-kohaliste ametite kaupa (sisu/ilo-kokkupuude-2025.csv);
- Statistikaamet PA633, töötajad ameti järgi täistööajale taandatult, oktoober 2022 (sisu/ee-tootajad-ametid-2022.csv);
- Eurostat lfsq_eisn2, hõivatud pearühma järgi kvartalis (sisu/ee-hoive-pearyhm-kvartal.csv, sait/lae_ee_kvartal.py);
- koondajate kaotatud ametiliigid (sisu/koondajad.json) ja liikide seos ISCO-ga (sisu/ametiliigid-isco.json, Kadri valik A).
Kvartalite asemel võrreldakse nelja kvartali keskmist, et aastaaeg ei moonutaks muutust.
"""
import csv
import json
from pathlib import Path

from andmekiht import ASTMED, PA633_URL, AndmeViga
from komponendid import allikarida, e, pr, tabel

SISU = Path(__file__).resolve().parent / "sisu"
EUROSTAT_URL = "https://ec.europa.eu/eurostat/databrowser/view/lfsq_eisn2/default/table"
AVATUD = ("1", "2", "3", "4")
ASTE_NIMI = {"4": "aste 4, kõige avatum", "3": "aste 3", "2": "aste 2", "1": "aste 1",
             "minimaalne": "minimaalne kokkupuude", "ei": "ei puutu kokku"}
ALUS = "2022"  # sama algusaasta mis Töö lehe hõive võrdlusel


def _csv(nimi):
    with open(SISU / nimi, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _json(nimi):
    return json.loads((SISU / nimi).read_text(encoding="utf-8"))


def ametid():
    """4-kohalised ametid, millel on ILO aste ja eestikeelne nimi: [{kood, nimi, fte, aste}]."""
    aste = {r["isco4"]: r["aste"] for r in _csv("ilo-kokkupuude-2025.csv")}
    out = []
    for r in _csv("ee-tootajad-ametid-2022.csv"):
        if len(r["kood"]) == 4 and r["kood"] in aste and r["nimi_et"]:
            if aste[r["kood"]] not in ASTMED:
                raise AndmeViga(f"ILO amet {r['kood']}: tundmatu aste")
            out.append({"kood": r["kood"], "nimi": r["nimi_et"], "fte": int(r["tootajad_fte"]), "aste": aste[r["kood"]]})
    if len(out) < 300:
        raise AndmeViga(f"Minu amet: ametite loendis on ainult {len(out)} ametit, oodatud üle 300")
    return out


def _kv(k):
    """'2025-Q3' → 'III kv 2025'"""
    return f'{("I", "II", "III", "IV")[int(k[-1]) - 1]} kv {k[:4]}'


def ryhmad(am):
    """Pearühmad: nimi, avatud ametite töötajate osa (2022), hõive 2022 ja viimase nelja kvartali keskmine."""
    nimed = {r["kood"]: r["nimi_et"] for r in _csv("ee-tootajad-ametid-2022.csv") if len(r["kood"]) == 1}
    kv = _csv("ee-hoive-pearyhm-kvartal.csv")
    out = {}
    for g in map(str, range(1, 10)):
        rr = sorted((r for r in kv if r["isco"] == f"OC{g}"), key=lambda r: r["kvartal"])
        alus = [r for r in rr if r["kvartal"].startswith(ALUS)]
        viim = rr[-4:]
        if len(alus) != 4 or len(viim) != 4 or viim[0]["kvartal"][:4] <= ALUS:
            raise AndmeViga(f"Ametirühm {g}: {ALUS}. aasta või viimase nelja kvartali andmed puuduvad")
        k0 = sum(float(r["tuhat"]) for r in alus) / 4
        k1 = sum(float(r["tuhat"]) for r in viim) / 4
        osa = [a for a in am if a["kood"][0] == g]
        kokku = sum(a["fte"] for a in osa)
        out[g] = {"nimi": nimed[g], "avatud": sum(a["fte"] for a in osa if a["aste"] in AVATUD) / kokku * 100 if kokku else 0,
                  "korge": sum(a["fte"] for a in osa if a["aste"] in ("3", "4")) / kokku * 100 if kokku else 0,
                  "k0": k0, "k1": k1, "m": (k1 / k0 - 1) * 100, "periood": f'{_kv(viim[0]["kvartal"])} – {_kv(viim[-1]["kvartal"])}',
                  "u": sorted({r["kvartal"] for r in alus + viim if "u" in r["margend"]}),
                  "uuendatud": rr[-1]["uuendatud"], "read": [(r["kvartal"], float(r["tuhat"])) for r in rr]}
    return out


def koondajad():
    """Ametiliik → [firma], kui firma kaotatud ametiliikides on see liik; ametiliik → ISCO koodide algused."""
    K, S = _json("koondajad.json"), _json("ametiliigid-isco.json")
    seos = {liik: v["isco"] for liik, v in S["seosed"].items() if v["isco"]}
    firmad = {}
    for f, v in K["firmad"].items():
        for liik in v.get("kaotatud", []):
            if liik in seos:
                firmad.setdefault(liik, []).append(f)
    return seos, firmad


def _muutus(m):
    from too_tahvel import PIIR_HOIVE_PR
    if abs(m) < PIIR_HOIVE_PR:
        return "pole selgelt muutunud"
    return f'{"kasvas" if m > 0 else "vähenes"} {pr(abs(m))}%'


def h1(R):
    from too_tahvel import PIIR_HOIVE_PR, mt
    g, r = max(R.items(), key=lambda x: x[1]["avatud"])
    if g != "4" or abs(r["m"]) >= PIIR_HOIVE_PR:
        raise AndmeViga(f"Minu amet: kõige avatum rühm on {r['nimi']}, hõive muutus {pr(r['m'])}%; kirjuta pealkiri ümber")
    return (f'Kõige avatumas rühmas, **kontoritöötajatel, on tööd sama palju kui {ALUS}. aastal** ¦ '
            f'{pr(r["avatud"], 0)}% kontoritöötajatest ja klienditeenindajatest töötab ametites, mida ILO hinnangul '
            f'generatiivne tehisaru puudutab. Hõive on sama mis {ALUS}. aastal ({mt(r["m"])}).')


def ryhmade_vastus(R):
    """Tabeli pealkiri: rühmad, kus hõive selgelt vähenes. Kui mõni neist on tehisarule avatud, tuleb lause ümber kirjutada."""
    from too_tahvel import PIIR_HOIVE_PR
    v = [r for r in R.values() if r["m"] <= -PIIR_HOIVE_PR]
    if any(r["avatud"] >= 25 for r in v):
        raise AndmeViga("Minu amet: avatud ametirühmas vähenes hõive selgelt; kirjuta tabeli pealkiri ümber")
    if not v:
        return "Selgelt ei vähenenud hõive üheski rühmas"
    nimed = " ja ".join(r["nimi"].lower() for r in v)
    return f'Selgelt vähenes hõive ainult {"rühmas" if len(v) == 1 else "rühmades"} {nimed}, mille ametid on tehisarule vähe avatud'


def sec_vali(A, am, R):
    seos, firmad = koondajad()
    K = A["kokkupuude"]
    ilo = A["uuringud"]["ilo2025"]
    andmed = {
        "ametid": [[a["kood"], a["nimi"], a["fte"], a["aste"]] for a in sorted(am, key=lambda a: -a["fte"])],
        "ryhmad": {g: {"nimi": r["nimi"], "k0": round(r["k0"], 1), "k1": round(r["k1"], 1), "m": round(r["m"], 1),
                       "muutus": _muutus(r["m"]), "periood": r["periood"]} for g, r in R.items()},
        "astmed": {a: {"nimi": ASTE_NIMI[a], "osa": round(K["osa"][a], 1)} for a in ASTMED},
        "koondajad": [{"liik": liik, "isco": seos[liik], "firmad": ff} for liik, ff in firmad.items()],
        "alus": ALUS,
    }
    js = json.dumps(andmed, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    skaala = "".join(f'<li data-a="{a}"><span>{e(ASTE_NIMI[a])}</span></li>' for a in reversed(ASTMED))
    return f"""
<section class="jaotis ma" id="minu-amet" aria-labelledby="h-minu-amet">
  <header>
    <h2 id="h-minu-amet"><span class="kys">Kui avatud on minu amet?</span> Kirjuta ameti nimi</h2>
    <p class="alam">{len(am)} ametit Statistikaameti ja ILO ametiloendist. Aste näitab, kui suurt osa ameti ülesannetest generatiivne tehisaru puudutab. See ei ütle, kas töö kaob.</p>
  </header>
  <div class="ma-otsi" hidden>
    <label for="ma-sisend">Amet</label>
    <input id="ma-sisend" type="search" autocomplete="off" placeholder="nt raamatupidaja, õpetaja, keevitaja" aria-controls="ma-tulemused" aria-describedby="ma-abi">
    <p id="ma-abi" class="ps">Kirjuta vähemalt kolm tähte. Nimed on Statistikaameti ametiloendist, näiteks „Raamatupidamise tippspetsialistid“; otsing leiab ka sõna tüve järgi.</p>
    <ul id="ma-tulemused" class="ma-tul" aria-live="polite"></ul>
  </div>
  <noscript><p class="ps">Ameti otsing vajab JavaScripti. Ametirühmade kokkuvõte on allpool tabelis.</p></noscript>
  <article class="ma-kaart" id="ma-kaart" hidden aria-live="polite">
    <h3 id="ma-nimi"></h3>
    <ol class="ma-sk" aria-hidden="true">{skaala}</ol>
    <p id="ma-aste"></p>
    <p id="ma-tootajad"></p>
    <p id="ma-ryhm"></p>
    <p id="ma-koond"></p>
    <p class="ps"><a id="ma-link" href="#minu-amet">Link sellele ametile</a></p>
  </article>
  <script type="application/json" id="ma-andmed">{js}</script>
  {allikarida([(f"ILO {ilo['aasta']}, kokkupuute indeks", ilo["url"], "4-kohalised ametid"),
               ("Statistikaamet, PA633", PA633_URL, "töötajad ameti järgi, oktoober 2022"),
               ("Eurostat, lfsq_eisn2", EUROSTAT_URL, f'uuendatud {R["1"]["uuendatud"]}')])}
</section>"""


def sec_ryhmad(R):
    from too_tahvel import PIIR_HOIVE_PR
    jr = sorted(R.items(), key=lambda x: -x[1]["avatud"])
    per = jr[0][1]["periood"]
    read = [[f'<b>{e(r["nimi"])}</b>', f'{pr(r["avatud"], 0)}%', f'{pr(r["korge"], 0)}%', pr(r["k0"]), pr(r["k1"]),
             f'{"+" if r["m"] >= 0 else "−"}{pr(abs(r["m"]))}%{"" if abs(r["m"]) >= PIIR_HOIVE_PR else " <small>väike</small>"}']
            for _, r in jr]
    u = sorted({r["nimi"] for _, r in jr if r["u"]})
    return f"""
<section class="jaotis" id="ametiryhmad" aria-labelledby="h-ametiryhmad">
  <header>
    <h2 id="h-ametiryhmad"><span class="kys">Kas avatumates ametirühmades on tööd vähem?</span> {ryhmade_vastus(R)}</h2>
    <p class="alam">Üheksa ametirühma, kõige avatum üleval. Hõivatud tuhandetes: {ALUS}. aasta ja viimase nelja kvartali ({e(per)}) keskmine.</p>
  </header>
  {tabel(["Ametirühm", "Avatud ametites", "neist aste 3–4", f"Hõivatud {ALUS}", "Viimased 4 kv", "Muutus"], read, fookus_rida=0,
         pealdis="Ametirühmad tehisarule avatuse ja hõive muutuse järgi", tel="1:9em -3 -4")}
  {allikarida([("Eurostat, lfsq_eisn2", EUROSTAT_URL, "tööjõu-uuring, 15+"), ("Statistikaamet, PA633", PA633_URL, "ametite töötajad 2022")])}
  <p class="allikas">„Avatud ametites“ = rühma töötajate osa, kes 2022. aastal töötasid ametites, mida ILO peab generatiivsele tehisarule avatuks (aste 1–4). „Väike“ = alla {PIIR_HOIVE_PR}% muutus võib olla tööjõu-uuringu valimiviga. {("Eurostat märgib väikese usaldusväärsusega: " + e(", ".join(u)) + ".") if u else ""}</p>
</section>"""


def uksikasjad():
    import teema_tahvel as tt
    lugemine = """
<ul>
<li><b>Aste tuleb ILO 2025. aasta indeksist.</b> ILO hindas iga ameti ülesandeid: kui suurt osa neist generatiivne tehisaru suudab teha või toetada. Astmed 1–4 on avatud ametid, 4 on kõige avatum.</li>
<li><b>Töötajate arv on 2022. aasta oktoobri seis</b> (Statistikaamet, täistööajale taandatult). Uuemat ametite kaupa arvu Statistikaamet ei avalda.</li>
<li><b>Hõive muutus on ametirühma, mitte ameti kohta.</b> Tööjõu-uuring avaldab kvartali kaupa ainult üheksa pearühma. Nelja kvartali keskmine silub aastaaja mõju.</li>
<li><b>Koondajad on uudistest.</b> Ametiliigi seos ISCO ametitega on lihtsustus: uudis ütleb näiteks „analüütikud“, mitte täpset ametit.</li>
</ul>"""
    ei_naita = """
<ul>
<li><b>Aste ei ütle, kas töö kaob.</b> Sama ameti töö võib muutuda, kiireneda või vajada uusi oskusi.</li>
<li><b>Aste ei ole sinu töö hinnang.</b> Sama nimega ametis on eri ülesandeid ja tööandjad kasutavad tehisaru eri moodi.</li>
<li><b>Hõive muutus ei näita põhjust.</b> Eesti majandus oli 2023–2024 langusel ja see mõjutas harusid eri moodi.</li>
</ul>"""
    return tt.uksikasjad([
        ("ma-lugemine", "Kuidas numbreid lugeda?", "aste, töötajad, hõive, koondajad", lugemine),
        ("ma-ei-naita", "Mida see ei näita?", "kas töö kaob, sinu töö, põhjus", ei_naita),
    ]).replace('id="h-uksikasjad"', 'id="h-ma-uksikasjad"').replace('aria-labelledby="h-uksikasjad"', 'aria-labelledby="h-ma-uksikasjad"')


def plokid(A, vaade):
    """Töö vaate plokid alamlehele too-minu-amet.html."""
    from abi import alam_h1
    am = ametid()
    R = ryhmad(am)
    alam_h1(vaade, "too-minu-amet.html", h1(R))
    return [
        ("ma-vali", [("minu-amet", "Minu amet")], sec_vali(A, am, R)),
        ("ma-ryhmad", [("ametiryhmad", "Ametirühmad")], sec_ryhmad(R)),
        ("ma-uksikasjad", [("h-ma-uksikasjad", "Üksikasjad")], uksikasjad()),
    ]
