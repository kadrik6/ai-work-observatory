"""Usalduskiht: kui värske number on ja kas teised allikad ütlevad sama.

See on süsteemi tuum. Number üksi ei ütle, kas seda võib uskuda.
"""

from datetime import date, timedelta

# Kui palju võib uus väljalase hilineda, enne kui andmed loetakse aegunuks
VARU_PAEVI = 60

# Kui suur vahe allikate vahel loetakse vastuoluks (protsendipunktides)
VASTUOLU_PIIR = 0.5


def lisa_kuud(alg, kuud):
    """Liidab kuupäevale kuud. Kuu lõpu puhul võetakse uue kuu viimane päev."""
    kuu_indeks = alg.month - 1 + kuud
    aasta = alg.year + kuu_indeks // 12
    kuu = kuu_indeks % 12 + 1
    for paev in (alg.day, 30, 29, 28):
        try:
            return date(aasta, kuu, paev)
        except ValueError:
            continue


def varskus(uuendatud, sagedus_kuudes, tana=None):
    """Tagastab staatuse ja järgmise oodatava uuenduse kuupäeva.

    ajakohane: järgmise uuenduseni on rohkem kui VARU_PAEVI päeva
    aegumas:   uus väljalase peaks tulema praegu või varsti
    aegunud:   oodatud uuendus hilineb rohkem kui VARU_PAEVI päeva
    """
    tana = tana or date.today()
    jargmine = lisa_kuud(uuendatud, sagedus_kuudes)
    varu = timedelta(days=VARU_PAEVI)
    if tana < jargmine - varu:
        staatus = "ajakohane"
    elif tana <= jargmine + varu:
        staatus = "aegumas"
    else:
        staatus = "aegunud"
    return {"staatus": staatus, "jargmine_oodatav": jargmine.isoformat()}


def uuem_allikas(read, teised_allikad, riik="EE"):
    """Leiab teise allika, millel on uuem aasta kui põhiallikal.

    Näiteks Statistikaamet avaldab Eesti numbri sageli enne Eurostati.
    Siis on põhiallika number küll "ajakohane", aga mitte kõige värskem.
    """
    riigi_aastad = [int(r["time"]) for r in read if r["geo"] == riik and r["vaartus"] is not None]
    if not riigi_aastad:
        return None
    viimane = max(riigi_aastad)
    uuemad = [t for t in teised_allikad if t["riik"] == riik and int(t["aasta"]) > viimane]
    return max(uuemad, key=lambda t: int(t["aasta"]), default=None)


def vordle_allikaid(read, teised_allikad):
    """Võrdleb põhiallika numbrit teiste allikatega sama riigi ja aasta kohta."""
    tulemus = []
    for teine in teised_allikad:
        pohi = next(
            (r for r in read if r["geo"] == teine["riik"] and str(r["time"]) == str(teine["aasta"])),
            None,
        )
        if pohi is None or pohi["vaartus"] is None:
            tulemus.append({**teine, "pohivaartus": None, "vahe": None, "vastuolu": None})
            continue
        vahe = round(teine["vaartus"] - pohi["vaartus"], 2)
        tulemus.append({**teine, "pohivaartus": pohi["vaartus"], "vahe": vahe, "vastuolu": abs(vahe) >= VASTUOLU_PIIR})
    return tulemus
