"""Eesti allikad tehisaru ja töö kohta: mõttekojad, uudised, lõputööd ja teadusinfo.

OpenAlex leiab Eesti kohta ainult teadustöid (mõnikümmend aastas). Siin on allikad, mida OpenAlexis pole:
Arenguseire Keskuse, Praxise ja OSKA väljaanded, ERR-i ja Novaatori uudised ning Tartu Ülikooli lõputööd.
Allikad, mille vastuse kuju pole veel teada, on proovirežiimis: logi näitab olekut ja vastuse algust.

Salvestame ainult pealkirja, lingi, kuupäeva ja otsingusõna, mis kirje leidis. Mitte teksti.
Tulemus on logis (read "EESTI <allikas> {json}") ja artefaktis. Repo ega avaldatud lehed ei muutu.
"""

import argparse
import datetime as dt
import email.utils
import json
import re
import sys
import time
import urllib.parse
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kogujad import yhine  # noqa: E402

# Tehisaru sõnad eesti ja inglise keeles. Uudisvoogudes peab üks neist olema pealkirjas või kokkuvõttes.
TEHISARU = re.compile(r"tehisintellekt|tehisaru|keelemudel|masinõpe|chatgpt|automatiseeri|robot|\bAI\b|\bTI\b"
                      r"|artificial intelligence|generative ai|machine learning|automation", re.I)
# WordPressi otsing leiab sõna ka teksti seest, seepärast mitu kitsast otsingut.
WP_OTSINGUD = ["tehisaru", "tehisintellekt", "automatiseerimine"]
WP_LEHTI = 5
ETIS_OTSINGUD = ["tehisintellekt", "tehisaru", "artificial intelligence", "generative AI", "automatiseerimine",
                 "keelemudel", "language model"]
# ETIS-e otsing on pealkirjast ja leiab tehisaru tööd igalt alalt. Teemas = pealkirjas on ka töö või oskused.
TOO = re.compile(r"töö|oskus|kutse|tööjõu|töötaja|tööandja|ametikoh|pädevus|labou?r|work|job|employ|skill|occupation"
                 r"|competenc|career|karjäär", re.I)
DSPACE_PARING = ('(tehisintellekt OR tehisintellekti OR tehisaru OR "artificial intelligence" OR "generative AI" '
                 'OR ChatGPT OR keelemudel OR automatiseerimine) AND (töö OR tööturg OR tööturu OR töötajad '
                 'OR töötajate OR oskused OR tööandja OR "labour market" OR employment OR workers OR skills OR workplace)')

ALLIKAD = {
    "arenguseire": {"liik": "mõttekoda", "wp": "https://arenguseire.ee/"},
    "praxis": {"liik": "mõttekoda", "wp": "https://www.praxis.ee/"},
    "oska": {"liik": "tööturu prognoos", "wp": "https://oska.kutsekoda.ee/"},
    "err": {"liik": "uudis", "rss": "https://www.err.ee/rss"},
    "novaator": {"liik": "uudis", "rss": "https://novaator.err.ee/rss"},
    # Proov 30.10: otsing aegus kaks korda (90 s). Proov näitab, kas server on GitHubist üldse kättesaadav.
    "tu_dspace": {"liik": "lõputöö", "dspace": "https://dspace.ut.ee/",
                  "proov": ["https://dspace.ut.ee/server/api", "https://dspace.ut.ee/server/oai/request?verb=Identify"]},
    # Proov: vastuse kuju pole veel teada.
    "taltech_digikogu": {"liik": "lõputöö", "proov": ["https://digikogu.taltech.ee/oai?verb=Identify",
                                                     "https://digikogu.taltech.ee/et/Search/Items?search=tehisintellekt"]},
    # Proov 30.10: SearchText, Keyword ja Search ei kitsenda tulemust, Title kitsendab (pealkirja otsing).
    "etis": {"liik": "teadusinfo", "etis": "https://www.etis.ee:2346/api/publication/getitems"},
}


def kuupaev(tekst):
    """RSS-i kuupäev (RFC 822) või ISO kuupäev -> 'AAAA-KK-PP'. Tundmatu kuju -> None."""
    tekst = (tekst or "").strip()
    if re.match(r"\d{4}-\d{2}-\d{2}", tekst):
        return tekst[:10]
    if re.fullmatch(r"\d{4}", tekst):
        return tekst
    try:
        return email.utils.parsedate_to_datetime(tekst).date().isoformat()
    except (TypeError, ValueError):
        return None


def rss(sisu, allikas, liik, reegel=None):
    """RSS-i kirjed. Ilma reeglita jäävad alles ainult kirjed, mille pealkirjas või kokkuvõttes on tehisaru sõna.

    "teemas" näitab, kas tehisaru sõna on pealkirjas või kokkuvõttes. Otsingu leid võib olla ka teksti sees.
    """
    tulem = []
    try:
        juur = ET.fromstring(sisu)
    except ET.ParseError:
        # Proov 30.10: Praxise voog ei ole korrektne XML. Loeme kirjed ükshaaval ja jätame katkised välja.
        juur = ET.Element("rss")
        for tykk in re.findall(rb"<item>.*?</item>", sisu, re.S):
            try:
                juur.append(ET.fromstring(re.sub(rb"&(?!#?\w+;)", b"&amp;", tykk)))
            except ET.ParseError:
                continue
    for i in juur.iter("item"):
        pealkiri = " ".join((i.findtext("title") or "").split())
        leid = TEHISARU.search(pealkiri + " " + (i.findtext("description") or ""))
        if reegel is None and not leid:
            continue
        tulem.append({"allikas": allikas, "liik": liik, "pealkiri": pealkiri, "url": (i.findtext("link") or "").strip(),
                      "avaldatud": kuupaev(i.findtext("pubDate")), "reegel": reegel or leid.group(0).lower(),
                      "teemas": bool(leid)})
    return tulem


def wp_url(alus, sona, leht):
    return alus + "?" + urllib.parse.urlencode({"s": sona, "feed": "rss2", "paged": leht})


def dspace_url(alus, mitu=50):
    return alus + "server/api/discover/search/objects?" + urllib.parse.urlencode(
        {"query": DSPACE_PARING, "dsoType": "ITEM", "sort": "dc.date.issued,DESC", "size": mitu})


def dspace(sisu, alus, allikas, liik):
    """DSpace 7 otsingu vastus -> (kokku, kirjed)."""
    tulemus = json.loads(sisu)["_embedded"]["searchResult"]
    kirjed = []
    for o in tulemus["_embedded"].get("objects", []):
        t = o["_embedded"]["indexableObject"]
        md = t.get("metadata", {})
        esimene = lambda v: (md.get(v) or [{}])[0].get("value")  # noqa: E731
        pealkiri = " ".join((t.get("name") or esimene("dc.title") or "").split())
        kirjed.append({"allikas": allikas, "liik": esimene("dc.type") or liik, "pealkiri": pealkiri,
                       "url": f"{alus}handle/{t['handle']}" if t.get("handle") else None,
                       "avaldatud": kuupaev(esimene("dc.date.issued")), "reegel": "otsing",
                       "teemas": bool(TEHISARU.search(pealkiri))})
    return tulemus["page"]["totalElements"], kirjed


def etis_url(alus, sona, mitu=200):
    return alus + "?" + urllib.parse.urlencode({"Format": "json", "Take": mitu, "Skip": 0, "Title": sona})


def etis(sisu, sona):
    """ETIS-e publikatsioonid. Aasta on kirjes "(AAAA)" kujul, link on ETIS-e portaali kirje."""
    kirjed = []
    for t in json.loads(sisu):
        pealkiri = " ".join((t.get("Title") or t.get("DisplayInfo") or "").split())
        tolge = t.get("TitleTranslation") or ""
        aasta = re.search(r"\((\d{4})\)", t.get("DisplayInfo") or "")
        kirjed.append({"allikas": "etis", "liik": t.get("PublicationTypeName") or "teadusinfo", "pealkiri": pealkiri,
                       "url": f"https://www.etis.ee/Portal/Publications/Display/{t['Guid']}" if t.get("Guid") else None,
                       "avaldatud": aasta.group(1) if aasta else None, "reegel": sona,
                       "teemas": bool(TOO.search(pealkiri + " " + tolge)), "viide": t.get("DisplayInfo")})
    return kirjed


def proov(sisu, sona="tehisintellekt"):
    """Tundmatu vastus: algus ja koht, kus otsingusõna esimest korda esineb, et järgmine kord saaks
    lahtipakkimise kirjutada."""
    tekst = " ".join(sisu.decode("utf-8", "replace").split())
    koht = tekst.lower().find(sona, 600)
    return tekst[:600] + (f" […] {tekst[max(koht - 300, 0):koht + 900]}" if koht > 0 else "")


def koonda(kirjed):
    """Sama link ainult üks kord, uusim ees."""
    nahtud, tulem = set(), []
    for k in kirjed:
        voti = k["url"] or k["pealkiri"]
        if voti in nahtud:
            continue
        nahtud.add(voti)
        tulem.append(k)
    return sorted(tulem, key=lambda k: k["avaldatud"] or "", reverse=True)


def allikas(nimi, seade, hae, paus=1.0):
    """Üks allikas -> {liik, kokku, kirjed, vead, proov}. Viga ühes päringus ei peata teisi."""
    tulem = {"liik": seade["liik"], "kokku": None, "kirjed": [], "vead": [], "proov": {}}
    if "wp" in seade:
        for sona in WP_OTSINGUD:
            for leht in range(1, WP_LEHTI + 1):
                try:
                    uued = rss(hae(wp_url(seade["wp"], sona, leht)), nimi, seade["liik"], reegel=sona)
                except yhine.KogujaViga as e:
                    # Tühja lehe korral annab WordPress 404: see on otsingu lõpp, mitte viga.
                    if leht == 1 or "HTTP 404" not in str(e):
                        tulem["vead"].append(str(e))
                    break
                except ET.ParseError as e:
                    tulem["vead"].append(f"{sona} leht {leht}: {e}")
                    break
                tulem["kirjed"] += uued
                if paus:
                    time.sleep(paus)
                if len(uued) < 10:
                    break
    if "rss" in seade:
        try:
            tulem["kirjed"] += rss(hae(seade["rss"]), nimi, seade["liik"])
        except (yhine.KogujaViga, ET.ParseError) as e:
            tulem["vead"].append(str(e))
    if "dspace" in seade:
        try:
            tulem["kokku"], uued = dspace(hae(dspace_url(seade["dspace"])), seade["dspace"], nimi, seade["liik"])
            tulem["kirjed"] += uued
        except (yhine.KogujaViga, ValueError, KeyError) as e:
            tulem["vead"].append(str(e))
    if "etis" in seade:
        for sona in ETIS_OTSINGUD:
            try:
                tulem["kirjed"] += etis(hae(etis_url(seade["etis"], sona)), sona)
            except (yhine.KogujaViga, ValueError, KeyError, TypeError) as e:
                tulem["vead"].append(str(e))
            if paus:
                time.sleep(paus)
    for aadress in seade.get("proov", []):
        try:
            tulem["proov"][yhine.peida_votmed(aadress)] = "OK " + proov(hae(aadress))
        except yhine.KogujaViga as e:
            tulem["proov"][yhine.peida_votmed(aadress)] = str(e)
        if paus:
            time.sleep(paus)
    tulem["kirjed"] = koonda(tulem["kirjed"])
    if tulem["kokku"] is None and ("wp" in seade or "rss" in seade or "etis" in seade):
        tulem["kokku"] = len(tulem["kirjed"])
    return tulem


def kaivita(valjund, hae=None, paus=1.0):
    # Tartu Ülikooli DSpace vastas 30.10 proovis aeglaselt: pikem ooteaeg.
    hae = hae or (lambda aadress: yhine.hae(aadress, ooteaeg=90))
    valjund = Path(valjund)
    valjund.mkdir(parents=True, exist_ok=True)
    tulem = {"aeg": yhine.nuud(), "allikad": {nimi: allikas(nimi, s, hae, paus) for nimi, s in ALLIKAD.items()}}
    (valjund / "eesti.json").write_text(json.dumps(tulem, ensure_ascii=False, indent=1), encoding="utf-8")
    return tulem


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--valjund", required=True)
    a = p.parse_args(argv)
    tulem = kaivita(a.valjund)
    print("EESTI meta " + json.dumps({"aeg": tulem["aeg"], "kuupaev": dt.date.today().isoformat()}))
    for nimi, sisu in tulem["allikad"].items():
        print(f"EESTI {nimi} " + json.dumps(sisu, ensure_ascii=False))
    toimis = [n for n, s in tulem["allikad"].items() if s["kirjed"] or any(v.startswith("OK") for v in s["proov"].values())]
    print(f"Töötas {len(toimis)}/{len(ALLIKAD)} allikat: {', '.join(toimis)}", file=sys.stderr)
    return 0 if toimis else 1


if __name__ == "__main__":
    sys.exit(main())
