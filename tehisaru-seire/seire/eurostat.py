"""Eurostati andmete laadimine ja lahtipakkimine.

Eurostat annab andmed JSON-stat 2.0 vormingus. Selles on kõik väärtused ühes
pikas nimekirjas ja iga väärtuse asukoht ütleb, millisele riigile, aastale
jne see kuulub. Funktsioon json_stat_ridadeks teeb sellest tavalise tabeli.
"""

import json
import urllib.parse
import urllib.request

API_URL = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/{andmestik}"

# Eurostati märgendid (flags) ja nende tähendus
MARGENDID = {
    "p": "esialgne väärtus",
    "e": "hinnanguline väärtus",
    "b": "aegrea katkestus",
    "u": "väike usaldusväärsus",
    "c": "konfidentsiaalne",
    "d": "definitsioon erineb",
    "r": "muudetud väärtus",
}


def koosta_url(andmestik, filtrid=None, riigid=None):
    """Teeb päringu aadressi. Iga filter ja riik lähevad aadressi parameetriks."""
    parameetrid = [("format", "JSON"), ("lang", "EN")]
    for nimi, vaartus in (filtrid or {}).items():
        parameetrid.append((nimi, vaartus))
    for riik in riigid or []:
        parameetrid.append(("geo", riik))
    return API_URL.format(andmestik=andmestik) + "?" + urllib.parse.urlencode(parameetrid)


def lae(andmestik, filtrid=None, riigid=None, ooteaeg=60):
    """Laadib andmestiku Eurostatist ja tagastab JSON-i Pythoni sõnastikuna."""
    url = koosta_url(andmestik, filtrid, riigid)
    with urllib.request.urlopen(url, timeout=ooteaeg) as vastus:
        return json.loads(vastus.read().decode("utf-8"))


def _kood_asukoha_jargi(moode):
    """Pöörab mõõtme indeksi ümber: asukoht -> kood."""
    indeks = moode["category"]["index"]
    if isinstance(indeks, list):
        return dict(enumerate(indeks))
    return {asukoht: kood for kood, asukoht in indeks.items()}


def json_stat_ridadeks(andmed):
    """Teeb JSON-stat vastusest ridade nimekirja.

    Iga rida on sõnastik, kus on iga mõõtme kood (nt geo, time),
    väärtus ja märgend.
    """
    moodete_nimed = andmed["id"]
    suurused = andmed["size"]
    koodid = [_kood_asukoha_jargi(andmed["dimension"][nimi]) for nimi in moodete_nimed]
    margendid = andmed.get("status") or {}

    # Eurostat annab väärtused sõnastikuna {"0": 1.2}, Statistikaamet (PxWeb) nimekirjana [1.2, ...]
    vaartused = andmed["value"]
    if isinstance(vaartused, list):
        vaartused = {str(i): v for i, v in enumerate(vaartused) if v is not None}
    if isinstance(margendid, list):
        margendid = {str(i): m for i, m in enumerate(margendid) if m}

    read = []
    for asukoht_tekstina, vaartus in vaartused.items():
        asukoht = int(asukoht_tekstina)
        rida = {}
        # Asukoht on "segaalusega arv": viimane mõõde muutub kõige kiiremini
        jaak = asukoht
        for i in range(len(moodete_nimed) - 1, -1, -1):
            rida[moodete_nimed[i]] = koodid[i][jaak % suurused[i]]
            jaak //= suurused[i]
        rida["vaartus"] = vaartus
        rida["margend"] = margendid.get(asukoht_tekstina, "")
        read.append(rida)
    return read


def moodete_kirjeldus(andmed):
    """Tagastab iga mõõtme koodid ja nende nimed. Vajalik filtrite valimiseks."""
    kirjeldus = {}
    for nimi in andmed["id"]:
        kategooria = andmed["dimension"][nimi]["category"]
        nimed = kategooria.get("label", {})
        kirjeldus[nimi] = [(kood, nimed.get(kood, "")) for kood in _kood_asukoha_jargi(andmed["dimension"][nimi]).values()]
    return kirjeldus
