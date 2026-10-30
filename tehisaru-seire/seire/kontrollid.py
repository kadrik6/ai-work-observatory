"""Andmekvaliteedi kontrollid.

Iga kontroll tagastab probleemide nimekirja. Tase "viga" tähendab, et
numbrit ei tohi kasutada enne, kui viga on parandatud. Tase "hoiatus"
tähendab, et numbrit võib kasutada, aga piirang peab olema kaardil näha.
"""

from collections import Counter

from seire.eurostat import MARGENDID


def probleem(tase, tekst):
    return {"tase": tase, "tekst": tekst}


def kontrolli(read, riigid, protsent=True):
    """Käivitab kõik kontrollid ja tagastab leitud probleemid."""
    probleemid = []
    probleemid += kontrolli_tuhjust(read)
    probleemid += kontrolli_kordusi(read)
    probleemid += kontrolli_riike(read, riigid)
    probleemid += kontrolli_aastaid(read, riigid)
    if protsent:
        probleemid += kontrolli_vahemikku(read, 0, 100)
    probleemid += kirjelda_margendeid(read)
    return probleemid


def kontrolli_tuhjust(read):
    if not read:
        return [probleem("viga", "Andmeid ei tulnud. Kontrolli filtreid failis naitajad.json.")]
    return []


def kontrolli_kordusi(read):
    """Igal riigil peab iga aasta kohta olema täpselt üks väärtus.

    Kui neid on rohkem, on filtrid liiga laiad ja number oleks juhuslik.
    """
    loendur = Counter((r["geo"], r["time"]) for r in read)
    kordused = sorted(voti for voti, arv in loendur.items() if arv > 1)
    if kordused:
        naited = ", ".join(f"{geo} {aasta}" for geo, aasta in kordused[:5])
        return [probleem("viga", f"Samal riigil ja aastal on mitu väärtust ({naited}). Filtrid on liiga laiad.")]
    return []


def kontrolli_riike(read, riigid):
    olemas = {r["geo"] for r in read}
    puudu = [riik for riik in riigid if riik not in olemas]
    if puudu:
        return [probleem("hoiatus", f"Andmed puuduvad riikide kohta: {', '.join(puudu)}.")]
    return []


def kontrolli_aastaid(read, riigid):
    """Kas viimase aasta väärtus on olemas kõigi riikide kohta, kellel andmeid on."""
    if not read:
        return []
    viimane = max(r["time"] for r in read)
    viimase_riigid = {r["geo"] for r in read if r["time"] == viimane}
    puudu = [riik for riik in riigid if riik in {r["geo"] for r in read} and riik not in viimase_riigid]
    if puudu:
        return [probleem("hoiatus", f"Aasta {viimane} väärtus puudub: {', '.join(puudu)}.")]
    return []


def kontrolli_vahemikku(read, alumine, ulemine):
    valed = [r for r in read if r["vaartus"] is not None and not (alumine <= r["vaartus"] <= ulemine)]
    if valed:
        naited = ", ".join(f"{r['geo']} {r['time']}: {r['vaartus']}" for r in valed[:5])
        return [probleem("viga", f"Väärtus väljaspool vahemikku {alumine}–{ulemine}: {naited}.")]
    return []


def kirjelda_margendeid(read):
    """Märgend ei ole viga, aga lugeja peab sellest teadma."""
    probleemid = []
    for r in read:
        for taht in r.get("margend") or "":
            selgitus = MARGENDID.get(taht, f"tundmatu märgend '{taht}'")
            probleemid.append(probleem("hoiatus", f"{r['geo']} {r['time']}: {selgitus}."))
    return probleemid
