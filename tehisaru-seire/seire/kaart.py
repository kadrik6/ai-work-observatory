"""Numbrikaardi koostamine: üks leht iga näitaja kohta.

Kaardi osad on alati samad: number, mida see tähendab, värskus,
vastuolud, usaldusväärsus, piirangud, andmed ja muutuste logi.
"""

from decimal import ROUND_HALF_UP, Decimal
from html import escape

RIIKIDE_NIMED = {
    "EE": "Eesti",
    "FI": "Soome",
    "SE": "Rootsi",
    "DK": "Taani",
    "NO": "Norra",
    "DE": "Saksamaa",
    "NL": "Holland",
    "EU27_2020": "EL27",
}

EESTI = "EE"
EL = "EU27_2020"


def riik(kood):
    return RIIKIDE_NIMED.get(kood, kood)


def arv(vaartus):
    """Eesti kirjaviis: koma kümnendkohana. Ümardab poole üles, nagu statistikas (19,95 -> 20,0)."""
    if vaartus is None:
        return "–"
    umardatud = Decimal(str(vaartus)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
    return f"{umardatud}".replace(".", ",")


def protsent(vaartus):
    """Arv koos protsendimärgiga. Puuduv väärtus on lihtsalt kriips."""
    return "–" if vaartus is None else f"{arv(vaartus)}%"


def viimase_aasta_read(read):
    viimane = max(r["time"] for r in read)
    return viimane, [r for r in read if r["time"] == viimane and r["vaartus"] is not None]


def pealkiri_vaitena(read):
    """Graafiku pealkiri on väide, mitte teema."""
    aasta, viimased = viimase_aasta_read(read)
    riigid = sorted((r for r in viimased if r["geo"] != EL), key=lambda r: -r["vaartus"])
    eesti = next((r for r in riigid if r["geo"] == EESTI), None)
    if eesti is None:
        return f"Eesti andmed aasta {aasta} kohta puuduvad"
    koht = riigid.index(eesti) + 1
    el = next((r for r in viimased if r["geo"] == EL), None)
    vordlus = ""
    if el is not None:
        suund = "üle" if eesti["vaartus"] > el["vaartus"] else "alla"
        vordlus = f", {suund} ELi keskmise ({arv(el['vaartus'])}%)"
    return f"Eesti on {len(riigid)} riigi seas {koht}. kohal: {arv(eesti['vaartus'])}% aastal {aasta}{vordlus}"


def graafik_svg(read, uhik="% ettevõtetest"):
    """Rõhtne tulpdiagramm viimase aasta kohta. Eesti on esile tõstetud."""
    aasta, viimased = viimase_aasta_read(read)
    viimased = sorted(viimased, key=lambda r: -r["vaartus"])
    laius, vasak, rida, ulemine = 640, 110, 30, 56
    suurim = max(r["vaartus"] for r in viimased) or 1
    tulba_max = laius - vasak - 70
    korgus = ulemine + rida * len(viimased) + 16

    osad = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {laius} {korgus}" font-family="sans-serif" font-size="13">',
        f'<rect width="{laius}" height="{korgus}" fill="#ffffff"/>',
        f'<text x="16" y="26" font-size="15" font-weight="600" fill="#1a1a1a">{escape(pealkiri_vaitena(read))}</text>',
        f'<text x="16" y="44" font-size="11.5" fill="#555">{uhik}, {aasta}. Allikas: Eurostat</text>',
    ]
    for i, r in enumerate(viimased):
        y = ulemine + i * rida
        pikkus = r["vaartus"] / suurim * tulba_max
        eesti = r["geo"] == EESTI
        el = r["geo"] == EL
        varv = "#5b2a86" if eesti else ("#9a9a9a" if el else "#c9c3d4")
        paks = ' font-weight="600"' if eesti else ""
        osad.append(f'<text x="{vasak - 8}" y="{y + 15}" text-anchor="end" fill="#1a1a1a"{paks}>{riik(r["geo"])}</text>')
        osad.append(f'<rect x="{vasak}" y="{y + 3}" width="{pikkus:.1f}" height="18" rx="3" fill="{varv}"/>')
        osad.append(f'<text x="{vasak + pikkus + 6:.1f}" y="{y + 16}" fill="#1a1a1a"{paks}>{arv(r["vaartus"])}%</text>')
    osad.append("</svg>")
    return "\n".join(osad)


def andmetabel(read):
    aastad = sorted({r["time"] for r in read})
    riigid = list(dict.fromkeys(r["geo"] for r in sorted(read, key=lambda r: list(RIIKIDE_NIMED).index(r["geo"]) if r["geo"] in RIIKIDE_NIMED else 99)))
    vaartused = {(r["geo"], r["time"]): r for r in read}
    read_md = ["| Riik | " + " | ".join(aastad) + " |", "| --- |" + " --- |" * len(aastad)]
    for g in riigid:
        lahtrid = []
        for a in aastad:
            r = vaartused.get((g, a))
            if r is None:
                lahtrid.append("–")
            else:
                lahtrid.append(arv(r["vaartus"]) + (f" ({r['margend']})" if r["margend"] else ""))
        read_md.append(f"| {riik(g)} | " + " | ".join(lahtrid) + " |")
    return "\n".join(read_md)


def koosta_kaart(naitaja, read, meta, probleemid, vordlus, muutused):
    """Koostab kaardi Markdownina."""
    varskus = meta["varskus"]
    aasta, viimased = viimase_aasta_read(read)
    eesti = next((r for r in viimased if r["geo"] == EESTI), None)
    el = next((r for r in viimased if r["geo"] == EL), None)

    osad = [f"# {naitaja['nimi']}", "", f"> {naitaja['kusimus']}", ""]

    if not naitaja.get("filtrid_kontrollitud"):
        osad += [
            "> **⚠ Filtrid on kontrollimata.** Enne selle numbri kasutamist veendu käsuga",
            f"> `python run.py --uuri {naitaja['andmestik']}`, et filtrid valivad õige näitaja.",
            "",
        ]

    osad += [
        f"**Staatus:** {varskus['staatus']} · **Allikas uuendas:** {meta['allikas_uuendas']} · "
        f"**Kontrollitud:** {meta['kontrollitud']} · **Järgmine oodatav uuendus:** {varskus['jargmine_oodatav']}",
        "",
        "## Number",
        "",
        f"Eesti {aasta}: **{protsent(eesti['vaartus']) if eesti else '–'}** · EL27: **{protsent(el['vaartus']) if el else '–'}** ({naitaja['uhik']})",
        "",
        f"![{escape(pealkiri_vaitena(read))}]({naitaja['id']}.svg)",
        "",
        "## Mida see tähendab",
        "",
        naitaja["mida_see_tahendab"],
        "",
        "## Vastuolud teiste allikatega",
        "",
    ]

    if vordlus:
        osad += [
            "| Allikas | Usaldus | Riik ja aasta | Väärtus | Eurostat | Vahe (pp) | Vastuolu |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ]
        for v in vordlus:
            vastuolu = "–" if v["vastuolu"] is None else ("**jah**" if v["vastuolu"] else "ei")
            osad.append(
                f"| [{v['allikas']}]({v['url']}) | {v['usaldus']} | {riik(v['riik'])} {v['aasta']} | "
                f"{protsent(v['vaartus'])} | {protsent(v['pohivaartus'])} | {arv(v['vahe'])} | {vastuolu} |"
            )
        osad += ["", f"**Miks allikad erinevad:** {naitaja.get('vastuolu_selgitus') or 'veel selgitamata. Kirjuta selgitus faili naitajad.json väljale vastuolu_selgitus.'}", ""]
    else:
        osad += ["Teisi allikaid pole veel lisatud.", ""]

    osad += [
        "## Usaldusväärsus",
        "",
        f"Ametlik statistika ({naitaja['allikas']}, andmestik `{naitaja['andmestik']}`).",
        "",
        "## Piirangud ja riskid",
        "",
    ]
    osad += [f"- {p}" for p in naitaja["piirangud"]]
    osad += [f"- **{p['tase'].capitalize()}:** {p['tekst']}" for p in probleemid]
    osad += [
        "",
        "## Andmed",
        "",
        andmetabel(read),
        "",
        "Sulgudes on Eurostati märgend, nt (p) tähendab esialgset väärtust.",
        "",
        "## Allikas",
        "",
        f"- Andmestik: `{naitaja['andmestik']}`, {meta['andmestiku_nimi']}",
        f"- Näitaja: {meta['naitaja_nimi']}",
        f"- Päring: {meta['url']}",
        "- Taaskasutus: Eurostati andmeid võib kasutada allikale viidates.",
        "",
        "## Muutuste logi",
        "",
    ]
    if muutused:
        osad += ["| Kuupäev | Riik ja aasta | Oli | On |", "| --- | --- | --- | --- |"]
        osad += [f"| {m['kuupaev']} | {riik(m['geo'])} {m['aasta']} | {m['vana']} | {m['uus']} |" for m in muutused]
    else:
        osad.append("Muutusi pole veel registreeritud.")
    return "\n".join(osad) + "\n"


def koosta_avaleht(kokkuvotted):
    """Avaleht: kõik näitajad ühes tabelis, et ühe pilguga näha seisu."""
    osad = [
        "# Tehisaru ja andmete seire",
        "",
        "Iga rida on üks näitaja. Klõpsa nimel, et näha kaarti koos allikate, vastuolude ja piirangutega.",
        "",
        "| Näitaja | Eesti | Aasta | Staatus | Vastuolu | Vead | Hoiatused |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for k in kokkuvotted:
        osad.append(
            f"| [{k['nimi']}]({k['id']}.md) | {protsent(k['eesti'])} | {k['aasta']} | {k['staatus']} | "
            f"{'jah' if k['vastuolu'] else 'ei'} | {k['vigu']} | {k['hoiatusi']} |"
        )
    return "\n".join(osad) + "\n"
