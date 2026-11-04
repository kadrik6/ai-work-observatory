"""Reeglipõhised tunnused: märksõnaloend (võrdlusalus), CPV-rühmad ja hindamiskriteeriumide kokkuvõte.

Märksõnaloend on mudeli mõõdupuu: mudel peab olema sellest parem, muidu pole mudelit vaja.
OECD (2026, lisa 2.B) kasutas märksõnaloendit innovatsioonihangete leidmiseks; siin on sama mõte
AI- ja andmehangete jaoks. Loend on lühike ja avalik, et tulemust saaks korrata.
"""
import re
import unicodedata

# Sõnatüved: sobivad sõna alguses, nii et eesti keele käändevormid tulevad kaasa
# ("tehisintellekti", "tehisintellektiga"). Lühendid ja ingliskeelsed fraasid on täpse sõnapiiriga.
AI_TYVED = [
    "tehisintellekt", "tehisaru", "masinõp", "masinõpp", "sügavõp", "närvivõrk", "keelemudel", "juturobot",
    "vestlusrobot", "virtuaalassistent", "kõnetuvastus", "kõnesüntees", "kõnest teksti", "masintõlge", "masintõlke",
    "masinnägemi", "pildituvastus", "objektituvastus", "näotuvastus", "tekstituvastus", "tekstianalüütika",
    "loomuliku keele", "ennustusmudel", "ennustav analüütika", "prognoosimudel",
    "artificial intelligence", "machine learning", "deep learning", "neural network", "language model",
    "chatbot", "speech recognition", "computer vision", "natural language", "predictive model",
]
AI_SONAD = ["ai", "llm", "nlp", "gpt", "ocr", "genai", "krattide", "kratt", "krati"]
ANDMED_TYVED = [
    "andmeanalüüs", "andmeanalüüt", "andmeteadus", "andmeladu", "andmelao", "andmeait", "andmejärv",
    "andmeplatvorm", "andmekvaliteet", "andmehaldus", "andmekaeve", "andmete analüüs", "andmete visualiseeri",
    "andmemudel", "suurandme", "ärianalüüti", "analüütikaplatvorm", "analüütikalahendus", "aruandlusplatvorm",
    "statistiline modelleeri", "statistilise modelleeri", "andmeteenus",
    "data warehouse", "data lake", "data analytics", "data platform", "big data", "business intelligence",
    "data science", "data quality", "data governance", "dashboard",
]
ANDMED_SONAD = ["bi", "etl", "power bi", "powerbi", "tableau", "qlik"]

# Algoritm oli OECD loendis, aga eesti hangetes tähendab see sageli liikluskorraldust või arvutusvalemit.
# Hoiame selle eraldi, et võrdlusalust saaks hinnata nii OECD-laadse kui kitsama loendiga.
LAI_TYVED = ["algoritm"]

CPV_IT = ("72", "48")  # IT-teenused ja tarkvara
CPV_UURING = ("7331", "7320", "7931", "7341", "7342")  # teadus- ja arendustöö, uuringud, statistika, nõustamine


def normaliseeri(t):
    t = unicodedata.normalize("NFC", t or "").lower()
    return re.sub(r"\s+", " ", t)


def _muster(tyved, sonad):
    osad = [r"(?<![\wõäöüšž])" + re.escape(t) for t in tyved]
    osad += [r"(?<![\wõäöüšž])" + re.escape(s) + r"(?![\wõäöüšž])" for s in sonad]
    return re.compile("|".join(osad))


AI_RE = _muster(AI_TYVED, AI_SONAD)
ANDMED_RE = _muster(ANDMED_TYVED, ANDMED_SONAD)
LAI_RE = _muster(LAI_TYVED, [])


def tekst(r, piir=4000):
    """Hanke tekst mudelile: pealkiri, kirjeldus ning osade nimed ja kirjeldused, kordused välja."""
    osad = [r.get("pealkiri"), r.get("kirjeldus")] + list(r.get("osade_nimed") or []) + list(
        r.get("osade_kirjeldused") or [])
    nahtud, valja = set(), []
    for o in osad:
        if o and o not in nahtud:
            nahtud.add(o)
            valja.append(o)
    return " \n".join(valja)[:piir]


def marksonad(t):
    """Tagastab leitud märksõnad rühmade kaupa."""
    n = normaliseeri(t)
    return {
        "ai": sorted(set(m.group(0).strip() for m in AI_RE.finditer(n))),
        "andmed": sorted(set(m.group(0).strip() for m in ANDMED_RE.finditer(n))),
        "lai": sorted(set(m.group(0).strip() for m in LAI_RE.finditer(n))),
    }


def cpv_ruhm(cpv):
    cpv = [c for c in (cpv or []) if c]
    return {
        "it": any(c.startswith(CPV_IT) for c in cpv),
        "uuring": any(c.startswith(CPV_UURING) for c in cpv),
        "pohi_it": bool(cpv) and cpv[0].startswith(CPV_IT),
    }


def kriteeriumid(kr):
    """Hinna ja kvaliteedi kokkuvõte. Kaal on protsent; puuduv kaal jääb None.

    Tagastab: ainult_hind (bool või None, kui kriteeriume pole), kvaliteedi_kaal (0–100 või None).
    """
    kr = [(t, k) for t, k in (kr or []) if t]
    if not kr:
        return {"ainult_hind": None, "kvaliteedi_kaal": None}
    tyybid = {t for t, _ in kr}
    ainult_hind = tyybid <= {"price", "cost"}
    if ainult_hind:
        return {"ainult_hind": True, "kvaliteedi_kaal": 0.0}
    kaalud = [(t, k) for t, k in kr if k is not None]
    if not kaalud:
        return {"ainult_hind": False, "kvaliteedi_kaal": None}
    kokku = sum(k for _, k in kaalud)
    kval = sum(k for t, k in kaalud if t == "quality")
    if kokku <= 0:
        return {"ainult_hind": False, "kvaliteedi_kaal": None}
    # osadega hankes korduvad kriteeriumid iga osa juures; osakaal jääb sama
    return {"ainult_hind": False, "kvaliteedi_kaal": round(100 * kval / kokku, 1)}


def innovatsiooni_mark(r):
    """Kas hankija märkis eVormil innovatsiooni (BT-06 strateegiline hange 'inn-pur' või BT-776)."""
    s = set(r.get("strateegiline") or [])
    i = set(x for x in (r.get("innovatsioon") or []) if x and x != "none")
    return "inn-pur" in s or bool(i)
