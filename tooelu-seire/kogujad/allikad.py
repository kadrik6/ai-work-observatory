"""Allikate kogujad. Iga allikas: päringu aadress ja vastuse lahtipakkimine kirjeteks (vt yhine.py).

Lahtipakkimine on hae-st eraldi, et testid saaksid kasutada salvestatud vastuseid ilma võrguta.
"""

import json
import os
import re
import urllib.parse
import xml.etree.ElementTree as ET

from . import yhine

# --- arXiv (eeltrükid, versioonidega) -------------------------------------------------------------
ARXIV_URL = "https://export.arxiv.org/api/query"
# Proov 30.10: laiem päring (all:, ilma kategooriata) tõi peamiselt masinõppe töid ("jobs" = Kubernetes jne).
# Kitsendatud majanduse ja ühiskonna kategooriatele ning kokkuvõttele; "occupations" tõi müra (occupancy).
ARXIV_PARING = ('(cat:econ.GN OR cat:econ.EM OR cat:cs.CY OR cat:q-fin.GN) '
                'AND (abs:"labor market" OR abs:"labour market" OR abs:employment OR abs:"future of work" '
                'OR abs:workforce OR abs:wages) '
                'AND (abs:"artificial intelligence" OR abs:"generative AI" OR abs:"large language model" '
                'OR abs:automation)')
ATOM = {"a": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}


def arxiv_url(paring=ARXIV_PARING, mitu=50):
    return ARXIV_URL + "?" + urllib.parse.urlencode(
        {"search_query": paring, "sortBy": "lastUpdatedDate", "sortOrder": "descending", "max_results": mitu})


def arxiv_kirjed(sisu):
    juur = ET.fromstring(sisu)
    tulem = []
    for e in juur.findall("a:entry", ATOM):
        aadress = e.findtext("a:id", "", ATOM).strip()
        m = re.search(r"abs/(.+?)(?:v(\d+))?$", aadress)
        if not m:
            continue
        doi = e.findtext("arxiv:doi", None, ATOM)
        tulem.append({
            "allikas": "arxiv", "allika_liik": "eeltrukk", "voti": m.group(1),
            "versioon": int(m.group(2) or 1), "pealkiri": " ".join(e.findtext("a:title", "", ATOM).split()),
            "url": aadress, "doi": doi.strip() if doi else None,
            "avaldatud": e.findtext("a:published", "", ATOM)[:10], "uuendatud": e.findtext("a:updated", "", ATOM)[:10],
        })
    return tulem


# --- OpenAlex (teadustööd, sh ajakirjad ja töödokumendid) -------------------------------------------
# OpenAlexi tüüp "article" ei tähenda, et töö on eelretsenseeritud, seepärast liik "artikkel".
OPENALEX_URL = "https://api.openalex.org/works"
# Proov 30.10: üldotsing (search) ja otsing kokkuvõttest tõid enamasti teemaväliseid töid (~4/15 asjakohased).
# Otsing pealkirjast andis käsitsi kontrollis ~13/15 asjakohast.
OPENALEX_PARING = ('("generative AI" OR "artificial intelligence" OR "large language model" OR automation) AND '
                   '("labor market" OR "labour market" OR employment OR jobs OR wages OR workforce '
                   'OR "future of work" OR workers)')


def openalex_url(alates, paring=OPENALEX_PARING, mitu=50):
    param = {"filter": f"title.search:{paring},from_publication_date:{alates},type:article|preprint|report",
             "sort": "publication_date:desc", "per-page": mitu}
    if os.environ.get("OPENALEX_API_KEY"):
        param["api_key"] = os.environ["OPENALEX_API_KEY"]
    return OPENALEX_URL + "?" + urllib.parse.urlencode(param)


def openalex_kirjed(sisu):
    tulem = []
    for w in json.loads(sisu).get("results", []):
        tuup = (w.get("type") or "").lower()
        tulem.append({
            "allikas": "openalex", "voti": (w.get("id") or "").rsplit("/", 1)[-1],
            "allika_liik": {"preprint": "eeltrukk", "article": "artikkel", "report": "raport"}.get(tuup, tuup or "teadmata"),
            "pealkiri": w.get("display_name") or w.get("title") or "", "url": w.get("id"), "doi": w.get("doi"),
            "avaldatud": w.get("publication_date"), "uuendatud": (w.get("updated_date") or "")[:10] or None,
        })
    return tulem


# --- ERR uudised (varajase hoiatuse kandidaadid, kahepoolne filter) ---------------------------------
ERR_URL = "https://www.err.ee/rss"
MARKSONAD = {
    "kadu": ["koonda", "töökohtade vähend", "töökohad kaovad", "lõpetab tegevuse", "sulgeb tehase", "pankrot"],
    "umberkorraldus": ["ümberkorraldus", "reorganiseeri", "automatiseeri", "tehisaru", "tehisintellekt"],
    "loomine": ["värbab", "uued töökohad", "uut töökohta", "laiendab tootmist", "palkab juurde"],
}


def rss_arv(sisu):
    """Mitu kirjet voos kokku (enne filtrit). 0 sobivat kirjet on normaalne, 0 kirjet voos ei ole."""
    return sum(1 for _ in ET.fromstring(sisu).iter("item"))


def rss_kirjed(sisu, allikas="err"):
    """Kõik RSS-i kirjed, millel on mõni märksõna. Salvestatakse ainult pealkiri, link, kuupäev ja reegel."""
    juur = ET.fromstring(sisu)
    tulem = []
    for i in juur.iter("item"):
        pealkiri = " ".join((i.findtext("title") or "").split())
        tekst = (pealkiri + " " + (i.findtext("description") or "")).lower()
        leitud = [(suund, s) for suund, sonad in MARKSONAD.items() for s in sonad if s in tekst]
        if not leitud:
            continue
        link = (i.findtext("link") or "").strip()
        tulem.append({
            "allikas": allikas, "allika_liik": "teade", "voti": (i.findtext("guid") or link).strip(),
            "pealkiri": pealkiri, "url": link, "avaldatud": (i.findtext("pubDate") or "").strip(),
            "suund": leitud[0][0], "reegel": ", ".join(sorted({s for _, s in leitud})),
        })
    return tulem


# --- Eurostat (statistika: andmestiku viimane uuendus = vintage) ------------------------------------
EUROSTAT_URL = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/{kood}"
# jvs_q_nace2 suleti 2026 (NACE Rev. 2, kuni 2025-Q4); asendaja on jvs_q_r21 (NACE Rev. 2.1).
EUROSTAT_ANDMESTIKUD = ["lfsq_egais", "lfsa_egai2d", "jvs_q_r21", "isoc_eb_ain2", "isoc_sks_itspt"]


def eurostat_url(kood):
    return EUROSTAT_URL.format(kood=kood) + "?" + urllib.parse.urlencode(
        {"format": "JSON", "lang": "EN", "geo": "EE", "lastTimePeriod": 1})


def eurostat_kirje(kood, sisu):
    """Andmestiku uuenduse kirje: võti = andmestik, 'uuendatud' = Eurostati uuendusaeg (vintage)."""
    d = json.loads(sisu)
    ajad = list((d.get("dimension", {}).get("time", {}).get("category", {}).get("index") or {}))
    kirje = {"allikas": "eurostat", "allika_liik": "ametlik_statistika", "voti": kood,
             "pealkiri": d.get("label", kood), "url": EUROSTAT_URL.format(kood=kood),
             "uuendatud": d.get("updated"), "viimane_periood": ajad[-1] if ajad else None,
             "vaartusi": len(d.get("value") or {})}
    if re.search(r"\(\d{4}-\d{4}\)\s*$", kirje["pealkiri"]):
        kirje["markus"] = "andmestik on suletud (lõppaasta pealkirjas), otsi asendajat"
    return kirje


def hae_koik(alates, hae=None):
    """Käivitab kõik allikad. Tagastab (kirjed, olek), kus olek on iga allika kohta ok/viga, arv ja aeg."""
    hae = hae or yhine.hae
    kirjed, olek = [], {}
    def err():
        sisu = hae(ERR_URL)
        arv = rss_arv(sisu)
        if not arv:
            raise ValueError("voos pole ühtki kirjet")
        return rss_kirjed(sisu), {"voos": arv}

    tood = [("arxiv", lambda: (arxiv_kirjed(hae(arxiv_url())), {})),
            ("openalex", lambda: (openalex_kirjed(hae(openalex_url(alates))), {})),
            ("err", err)]
    tood += [(f"eurostat:{k}", (lambda k=k: ([eurostat_kirje(k, hae(eurostat_url(k)))], {})))
             for k in EUROSTAT_ANDMESTIKUD]
    for nimi, too in tood:
        algus = yhine.nuud()
        try:
            uued, lisa = too()
            kirjed.extend(uued)
            olek[nimi] = {"olek": "ok", "kirjeid": len(uued), "aeg": algus, **lisa}
        except (yhine.KogujaViga, ET.ParseError, json.JSONDecodeError, KeyError, ValueError) as e:
            olek[nimi] = {"olek": "viga", "viga": f"{type(e).__name__}: {e}", "aeg": algus}
    if "openalex" in olek and not os.environ.get("OPENALEX_API_KEY"):
        olek["openalex"]["markus"] = "OPENALEX_API_KEY puudub"
    return kirjed, olek
