"""Statistikaameti andmete laadimine (PxWeb API).

Statistikaamet avaldab Eesti andmed sageli varem kui Eurostat. Seepärast
kontrollib seire ka Statistikaameti tabelit ja annab märku, kui seal on
uuem aasta kui Eurostatis.

Tabeli tee on aadressi osa pärast /stat/, näiteks
majandus/infotehnoloogia/infotehnoloogia-ettevettes/IT1490
"""

import json
import urllib.request

from seire.eurostat import json_stat_ridadeks

API_URL = "https://andmed.stat.ee/api/v1/{keel}/stat/{tabel}.px"
VEEBI_URL = "https://andmed.stat.ee/et/stat/{tabel_alakriipsuga}"


def tabeli_url(tabel, keel="et"):
    return API_URL.format(keel=keel, tabel=tabel)


def veebi_url(tabel):
    """Inimesele mõeldud aadress, kus tabelit saab brauseris vaadata."""
    *kaustad, nimi = tabel.split("/")
    return VEEBI_URL.format(tabel_alakriipsuga="__".join(kaustad) + "/" + nimi)


def metaandmed(tabel, keel="et", ooteaeg=60):
    """Tabeli muutujad ja nende võimalikud väärtused. Vajalik päringu koostamiseks."""
    with urllib.request.urlopen(tabeli_url(tabel, keel), timeout=ooteaeg) as vastus:
        return json.loads(vastus.read().decode("utf-8"))


def koosta_paring(valikud):
    """valikud: {"Näitaja": ["kood"], "Aasta": [...]} -> PxWeb päringu keha."""
    return {
        "query": [{"code": kood, "selection": {"filter": "item", "values": vaartused}} for kood, vaartused in valikud.items()],
        "response": {"format": "json-stat2"},
    }


def lae(tabel, valikud, keel="et", ooteaeg=60):
    """Laadib tabelist valitud read ja tagastab JSON-stat2 vastuse."""
    keha = json.dumps(koosta_paring(valikud)).encode("utf-8")
    paring = urllib.request.Request(tabeli_url(tabel, keel), data=keha, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(paring, timeout=ooteaeg) as vastus:
        return json.loads(vastus.read().decode("utf-8"))


def aastate_vaartused(andmed, aasta_moode):
    """Teeb vastusest {aasta: väärtus}. Iga aasta kohta peab olema täpselt üks väärtus.

    Kui neid on rohkem, valib päring liiga palju ridu ja tulemus oleks juhuslik.
    """
    tulemus = {}
    for rida in json_stat_ridadeks(andmed):
        aasta = rida[aasta_moode]
        if aasta in tulemus:
            raise ValueError(f"Aastal {aasta} on mitu väärtust. Päring valib liiga palju ridu.")
        tulemus[aasta] = rida["vaartus"]
    return tulemus


def riiklik_allikas(seadistus, andmed):
    """Teeb Statistikaameti vastusest kirje, mida usalduskiht oskab võrrelda.

    Tagastab viimase aasta väärtuse samas vormis nagu naitajad.json teised_allikad.
    """
    aastad = aastate_vaartused(andmed, seadistus["aasta_moode"])
    viimane = max(aastad)
    kirje = {
        "allikas": f"Statistikaamet, tabel {seadistus['tabel'].split('/')[-1]} (laaditud automaatselt)",
        "riik": "EE",
        "aasta": int(viimane),
        "vaartus": aastad[viimane],
        "usaldus": "ametlik statistika",
        "url": veebi_url(seadistus["tabel"]),
    }
    if seadistus.get("moodik"):
        kirje["moodik"] = seadistus["moodik"]  # kataloogi mõõdiku id, et kooskõlakontroll seoks õige reaga
    return kirje
