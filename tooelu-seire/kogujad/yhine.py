"""Kogujate ühised osad: päring koos korduskatsega, kirje kuju, duplikaadid, versioonid ja vigade logi.

Kirje on sõnastik. Kohustuslikud väljad: allikas, voti (püsiv tunnus ilma versioonita), pealkiri, url.
Valikulised: versioon, doi, avaldatud, uuendatud, suund, reegel, allika_liik.
Iga kirje on KONTROLLIMATA kandidaat: kogumine ei tee järeldusi ega muuda kinnitatud andmeid.
"""

import datetime as dt
import json
import re
import time
import unicodedata
import urllib.error
import urllib.request

OOTEAEG = 30


class KogujaViga(Exception):
    """Allikat ei õnnestunud lugeda; sõnum läheb vigade logisse."""


def hae(url, ooteaeg=OOTEAEG, katseid=3, paus=2.0):
    """Tagastab vastuse baitidena. Ajutise vea (võrk, 429, 5xx) korral proovib uuesti; muu viga kohe."""
    viimane = None
    for katse in range(katseid):
        try:
            with urllib.request.urlopen(url, timeout=ooteaeg) as vastus:
                return vastus.read()
        except urllib.error.HTTPError as e:
            viimane = f"HTTP {e.code}"
            if e.code not in (429, 500, 502, 503, 504):
                break
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            viimane = f"võrguviga: {getattr(e, 'reason', e)}"
        if katse < katseid - 1:
            time.sleep(paus * (2 ** katse))
    raise KogujaViga(f"{peida_votmed(url)}: {viimane}")


def peida_votmed(url):
    """Võti ei tohi sattuda vigade logisse ega Actionsi väljundisse."""
    return re.sub(r"(?i)(api_key|mailto|token)=[^&]+", r"\1=***", url)


def nuud():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def normaliseeri(tekst):
    """Pealkiri võrdlemiseks: väiketähed, ilma diakriitikute ja kirjavahemärkideta, üks tühik."""
    tekst = unicodedata.normalize("NFKD", tekst or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", tekst.lower()).strip()


def votmed(kirje):
    """Kõik tunnused, mille järgi sama töö võib korduda: allika võti, DOI ja normaliseeritud pealkiri."""
    tulem = {f"voti:{kirje['allikas']}:{kirje['voti']}"}
    if kirje.get("doi"):
        tulem.add("doi:" + kirje["doi"].lower().removeprefix("https://doi.org/"))
    pealkiri = normaliseeri(kirje.get("pealkiri"))
    if len(pealkiri) >= 20:
        tulem.add("pealkiri:" + pealkiri)
    return tulem


def eralda(kirjed, varasemad=()):
    """Jagab kirjed: uued, uued versioonid ja duplikaadid.

    Duplikaat: mõni tunnus on juba nähtud (selles käivituses või varem) ja versioon pole suurem.
    Uus versioon: sama allika võti, aga suurem versiooninumber (nt arXiv v1 -> v2) või uuem 'uuendatud'.
    """
    nahtud = {}
    for k in varasemad:
        for v in votmed(k):
            nahtud.setdefault(v, k)
    uued, versioonid, duplikaadid = [], [], []
    for k in kirjed:
        vana = next((nahtud[v] for v in votmed(k) if v in nahtud), None)
        if vana is None:
            uued.append(k)
        elif _on_uuem(k, vana):
            versioonid.append({**k, "eelmine_versioon": vana.get("versioon"), "eelmine_uuendatud": vana.get("uuendatud")})
        else:
            duplikaadid.append({**k, "duplikaat": f"{vana['allikas']}:{vana['voti']}"})
        for v in votmed(k):
            nahtud[v] = k
    return uued, versioonid, duplikaadid


def _on_uuem(uus, vana):
    if uus["allikas"] != vana["allikas"] or uus["voti"] != vana["voti"]:
        return False
    if uus.get("versioon") and vana.get("versioon"):
        return uus["versioon"] > vana["versioon"]
    return bool(uus.get("uuendatud") and vana.get("uuendatud") and uus["uuendatud"] > vana["uuendatud"])


def kirjuta_jsonl(tee, kirjed):
    with open(tee, "a", encoding="utf-8") as f:
        for k in kirjed:
            f.write(json.dumps(k, ensure_ascii=False) + "\n")


def loe_jsonl(tee):
    try:
        with open(tee, encoding="utf-8") as f:
            return [json.loads(r) for r in f if r.strip()]
    except FileNotFoundError:
        return []
