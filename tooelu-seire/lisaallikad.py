"""Lisaallikad: tähelepanu (uudised, Vikipeedia, Hacker News), uurimisasutused ja Riigikogu.

OpenAlex näitab teadustöid, aga mitte seda, kui palju teemast räägitakse või mida loetakse. Siin on vabad
ja ametlikud allikad, mis seda lähendavad:
- GDELT: maailma ja Eesti uudiste arv ja nimekiri viimase 3 kuu kohta (tähelepanu mõõt, mitte klikid).
- Vikipeedia: artiklite vaatamised kuu kaupa (mida inimesed järele vaatavad).
- Hacker News: tehnoloogiakogukonna enim hääli saanud lood (populaarsuse lähend).
- NBER, Maailmapank ja Euroopa asutused: töödokumendid ja raportid.
- Riigikogu: istungite stenogrammid (proov).
Allikad, mille vastuse kuju pole veel teada, on proovirežiimis nagu `eesti.py`-s.

Salvestame ainult pealkirja, lingi, kuupäeva ja arvud. Mitte teksti.
Tulemus on logis (read "LISA <allikas> {json}") ja artefaktis. Repo ega avaldatud lehed ei muutu.
"""

import argparse
import datetime as dt
import json
import sys
import time
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import eesti  # noqa: E402
from kogujad import yhine  # noqa: E402

GDELT = "https://api.gdeltproject.org/api/v2/doc/doc"
# GDELT nõuab VÕI-tingimused sulgudes. Eesti: allika riik EN (FIPS kood) ja eestikeelsed sõnad.
GDELT_MAAILM = ('("artificial intelligence" OR "generative AI" OR ChatGPT OR automation) '
                '(jobs OR employment OR layoffs OR workers OR workforce OR "labor market")')
GDELT_EESTI = '(tehisintellekt OR tehisaru OR "artificial intelligence") sourcecountry:EN'
GDELT_PAUS = 6  # GDELT lubab ühe päringu 5 sekundi kohta.

VIKI = "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/{proj}/all-access/user/{art}/monthly/{alates}/{kuni}"
VIKI_ARTIKLID = [("en.wikipedia", "Technological_unemployment"), ("en.wikipedia", "Workplace_impact_of_artificial_intelligence"),
                 ("en.wikipedia", "Generative_artificial_intelligence"), ("en.wikipedia", "Artificial_intelligence"),
                 ("et.wikipedia", "Tehisintellekt")]

HN = "https://hn.algolia.com/api/v1/search"
HN_PARING = "AI jobs"

PANK = "https://search.worldbank.org/api/v2/wds"
PANK_PARING = '"artificial intelligence" jobs'


def gdelt_url(paring, mode, mitu=250):
    return GDELT + "?" + urllib.parse.urlencode({"query": paring, "mode": mode, "format": "json", "timespan": "3months",
                                                 "maxrecords": mitu, "sort": "datedesc"})


def gdelt_artiklid(sisu, allikas):
    tulem = []
    for a in json.loads(sisu).get("articles", []):
        aeg = a.get("seendate") or ""
        tulem.append({"allikas": allikas, "liik": "uudis", "pealkiri": " ".join((a.get("title") or "").split()),
                      "url": a.get("url"), "avaldatud": f"{aeg[:4]}-{aeg[4:6]}-{aeg[6:8]}" if len(aeg) >= 8 else None,
                      "domeen": a.get("domain"), "keel": a.get("language"), "teemas": True})
    return tulem


def gdelt_aegrida(sisu):
    """Uudiste osakaal päevas (protsent kõigist GDELT-i jälgitud uudistest)."""
    read = json.loads(sisu).get("timeline", [])
    return [{"kuupaev": f"{p['date'][:4]}-{p['date'][4:6]}-{p['date'][6:8]}", "vaartus": p["value"]}
            for p in (read[0]["data"] if read else [])]


def viki_url(proj, art, tana):
    alates = f"{tana.year - 3}0101"
    return VIKI.format(proj=proj, art=urllib.parse.quote(art), alates=alates, kuni=tana.strftime("%Y%m01"))


def viki(sisu):
    return [{"kuu": r["timestamp"][:4] + "-" + r["timestamp"][4:6], "vaatamisi": r["views"]}
            for r in json.loads(sisu).get("items", [])]


def hn_url(tana, paevi=365, mitu=50):
    alates = int(dt.datetime.combine(tana - dt.timedelta(days=paevi), dt.time()).timestamp())
    return HN + "?" + urllib.parse.urlencode({"query": HN_PARING, "tags": "story", "hitsPerPage": mitu,
                                              "numericFilters": f"created_at_i>{alates},points>100"})


def hn(sisu):
    tulem = []
    for h in json.loads(sisu).get("hits", []):
        tulem.append({"allikas": "hacker_news", "liik": "kogukond", "pealkiri": h.get("title"),
                      "url": h.get("url") or f"https://news.ycombinator.com/item?id={h.get('objectID')}",
                      "avaldatud": (h.get("created_at") or "")[:10] or None, "punkte": h.get("points"),
                      "kommentaare": h.get("num_comments"), "teemas": bool(eesti.TEHISARU.search(h.get("title") or ""))})
    return sorted(tulem, key=lambda k: -(k["punkte"] or 0))


def pank_url(mitu=50):
    return PANK + "?" + urllib.parse.urlencode({"format": "json", "qterm": PANK_PARING, "rows": mitu, "srt": "docdt",
                                                "order": "desc", "fl": "docdt,display_title,url,docty"})


def pank(sisu):
    d = json.loads(sisu)
    kirjed = []
    for voti, t in (d.get("documents") or {}).items():
        if not isinstance(t, dict) or "display_title" not in t:
            continue  # "facets" jm
        pealkiri = " ".join(str(t.get("display_title") or "").split())
        kirjed.append({"allikas": "maailmapank", "liik": t.get("docty") or "raport", "pealkiri": pealkiri,
                       "url": t.get("url"), "avaldatud": eesti.kuupaev((t.get("docdt") or "")[:10]),
                       "teemas": bool(eesti.TEHISARU.search(pealkiri))})
    return int(d.get("total") or 0), sorted(kirjed, key=lambda k: k["avaldatud"] or "", reverse=True)


# Uurimisasutuste uudisvood: ainult tehisaru sõnadega kirjed (eesti.rss filter). Aadressid on proovis.
VOOD = {
    "nber": ("töödokument", ["https://www.nber.org/rss/new.xml"]),
    "eurofound": ("raport", ["https://www.eurofound.europa.eu/en/rss.xml", "https://www.eurofound.europa.eu/rss.xml"]),
    "cedefop": ("raport", ["https://www.cedefop.europa.eu/en/rss.xml", "https://www.cedefop.europa.eu/en/news/rss"]),
    "ilo": ("raport", ["https://www.ilo.org/rss.xml", "https://www.ilo.org/feed"]),
    "brookings": ("mõttekoda", ["https://www.brookings.edu/feed/"]),
    "eesti_pank": ("keskpank", ["https://www.eestipank.ee/rss", "https://www.eestipank.ee/en/rss"]),
}
PROOVID = {
    "riigikogu": ["https://api.riigikogu.ee/api/steno/verbatims?startDate=2026-09-01&endDate=2026-10-30&lang=ET",
                  "https://api.riigikogu.ee/swagger-ui/index.html"],
    "semantic_scholar": ["https://api.semanticscholar.org/graph/v1/paper/search?query=generative+AI+labor+market"
                         "&fields=title,year,citationCount,influentialCitationCount&limit=5"],
}


def uus(liik):
    return {"liik": liik, "kokku": None, "kirjed": [], "aegrida": None, "vead": [], "proov": {}}


def kaivita(valjund, hae=None, tana=None, paus=1.0, valmis=None):
    hae = hae or (lambda aadress: yhine.hae(aadress, ooteaeg=45, katseid=2))
    tana = tana or dt.date.today()
    valjund = Path(valjund)
    valjund.mkdir(parents=True, exist_ok=True)
    tulem = {"aeg": yhine.nuud(), "allikad": {}}

    def tee(nimi, liik, too):
        t = uus(liik)
        try:
            too(t)
        except (yhine.KogujaViga, ValueError, KeyError, TypeError, IndexError) as e:
            t["vead"].append(str(e))
        tulem["allikad"][nimi] = t
        if valmis:
            valmis(nimi, t)

    def gdelt(paring, allikas):
        def too(t):
            t["kirjed"] = gdelt_artiklid(hae(gdelt_url(paring, "artlist")), allikas)
            t["kokku"] = len(t["kirjed"])
            time.sleep(GDELT_PAUS if paus else 0)
            t["aegrida"] = gdelt_aegrida(hae(gdelt_url(paring, "timelinevol")))
            time.sleep(GDELT_PAUS if paus else 0)
        return too

    tee("gdelt_maailm", "uudis", gdelt(GDELT_MAAILM, "gdelt_maailm"))
    tee("gdelt_eesti", "uudis", gdelt(GDELT_EESTI, "gdelt_eesti"))

    def vikipeedia(t):
        t["aegrida"] = {}
        for proj, art in VIKI_ARTIKLID:
            try:
                t["aegrida"][f"{proj}/{art}"] = viki(hae(viki_url(proj, art, tana)))
            except yhine.KogujaViga as e:
                t["vead"].append(str(e))
            time.sleep(paus)
    tee("vikipeedia", "vaatamised", vikipeedia)

    def hacker_news(t):
        t["kirjed"] = hn(hae(hn_url(tana)))
        t["kokku"] = len(t["kirjed"])
    tee("hacker_news", "kogukond", hacker_news)

    def maailmapank(t):
        t["kokku"], t["kirjed"] = pank(hae(pank_url()))
    tee("maailmapank", "raport", maailmapank)

    for nimi, (liik, aadressid) in VOOD.items():
        def voog(t, nimi=nimi, liik=liik, aadressid=aadressid):
            for aadress in aadressid:
                try:
                    sisu = hae(aadress)
                    t["kirjed"] = eesti.rss(sisu, nimi, liik)
                    t["kokku"] = len(t["kirjed"])
                    t["proov"][aadress] = "OK"
                    return
                except (yhine.KogujaViga, eesti.ET.ParseError) as e:
                    t["proov"][aadress] = str(e)
                time.sleep(paus)
        tee(nimi, liik, voog)

    for nimi, aadressid in PROOVID.items():
        def proovi(t, aadressid=aadressid):
            for aadress in aadressid:
                try:
                    t["proov"][aadress] = "OK " + eesti.proov(hae(aadress))
                except yhine.KogujaViga as e:
                    t["proov"][aadress] = str(e)
                time.sleep(paus)
        tee(nimi, "proov", proovi)

    (valjund / "lisaallikad.json").write_text(json.dumps(tulem, ensure_ascii=False, indent=1), encoding="utf-8")
    return tulem


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--valjund", required=True)
    a = p.parse_args(argv)
    print("LISA meta " + json.dumps({"aeg": yhine.nuud()}), flush=True)
    tulem = kaivita(a.valjund, valmis=lambda nimi, sisu: print(f"LISA {nimi} " + json.dumps(sisu, ensure_ascii=False),
                                                                 flush=True))
    toimis = [n for n, s in tulem["allikad"].items()
              if s["kirjed"] or s["aegrida"] or any(v.startswith("OK") for v in s["proov"].values())]
    print(f"Töötas {len(toimis)}/{len(tulem['allikad'])} allikat: {', '.join(toimis)}", file=sys.stderr)
    return 0 if toimis else 1


if __name__ == "__main__":
    sys.exit(main())
