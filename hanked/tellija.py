"""Kelle jaoks hange tehakse: korraldaja (registri hankija) ja tegelik tellija.

Registri avaandmetest loeme ainult esimese hankija (eVormi esimene ContractingParty). Keskne hankija (nt RTK)
korraldab hankeid teiste asutuste jaoks ja tellija nimi on tavaliselt pealkirjas: „(Riigikantselei)“,
„… Kultuuriministeeriumile“, „PPA …“. Kui pealkiri tellijat ei nimeta, näitame keskse hankija puhul tema
valitsemisala ja muu hankija puhul hankijat ennast. See on tuletus pealkirjast, mitte registri väli.
"""
import re

# Keskse hankija rolliga asutused ja see, kelle jaoks nad tavaliselt hangivad.
KESKSED = {
    "Riigi Tugiteenuste Keskus": "Teine riigiasutus",
    "Siseministeeriumi infotehnoloogia- ja arenduskeskus": "Siseministeeriumi valitsemisala",
    "Rahandusministeeriumi Infotehnoloogiakeskus": "Rahandusministeeriumi valitsemisala",
    "Keskkonnaministeeriumi Infotehnoloogiakeskus": "Kliimaministeeriumi ja REM-i valitsemisala",
    "Tervise ja Heaolu Infosüsteemide Keskus": "Sotsiaalministeeriumi valitsemisala",
    "Registrite ja Infosüsteemide Keskus": "Justiits- ja Digiministeeriumi valitsemisala",
    "Riigi Kinnisvara Aktsiaselts": "Teine riigiasutus",
    "Riigi Kaitseinvesteeringute Keskus": "Kaitseministeeriumi valitsemisala",
    "E-riigi Akadeemia Sihtasutus": "Partnerriik",
}

ASUTUSED = [
    "Justiits- ja Digiministeerium", "Kultuuriministeerium", "Riigikantselei", "Sotsiaalministeerium",
    "Siseministeerium", "Rahandusministeerium", "Haridus- ja Teadusministeerium",
    "Majandus- ja Kommunikatsiooniministeerium", "Kliimaministeerium", "Regionaal- ja Põllumajandusministeerium",
    "Kaitseministeerium", "Välisministeerium", "Sotsiaalkindlustusamet", "Maksu- ja Tolliamet",
    "Politsei- ja Piirivalveamet", "Päästeamet", "Terviseamet", "Ravimiamet", "Patendiamet", "Keskkonnaamet",
    "Keskkonnaagentuur", "Eesti Keele Instituut", "Finantsinspektsioon", "Statistikaamet", "Rahvusarhiiv",
    "Tarbijakaitse ja Tehnilise Järelevalve Amet", "Andmekaitse Inspektsioon", "Tööinspektsioon",
    "Maa- ja Ruumiamet", "Transpordiamet", "Haridus- ja Noorteamet", "Mürgistusteabekeskus", "Eesti Töötukassa",
    "Eesti Haigekassa", "Riigikohus", "Prokuratuur", "Kaitseressursside Amet", "Häirekeskus", "Sisekaitseakadeemia",
    "Põllumajanduse Registrite ja Informatsiooni Amet", "Põllumajandus- ja Toiduamet", "Konkurentsiamet",
    "Riigikontroll", "Õiguskantsleri Kantselei", "Tartu Vangla", "Viru Vangla", "Harku ja Murru Vangla",
    "Loodusmuuseum", "Pärnumaa Kutsehariduskeskus", "Ettevõtluse ja Innovatsiooni Sihtasutus",
    "Riigi Infosüsteemi Amet", "Moldova", "Ukraina", "Gruusia", "Armeenia", "Kenya", "Benin",
]
LUHENDID = {
    "e-MTA": "Maksu- ja Tolliamet", "EMTA": "Maksu- ja Tolliamet", "PPA": "Politsei- ja Piirivalveamet",
    "SKA": "Sotsiaalkindlustusamet", "HTM": "Haridus- ja Teadusministeerium", "JDM": "Justiits- ja Digiministeerium",
    "MKM": "Majandus- ja Kommunikatsiooniministeerium", "JUSTDIGI": "Justiits- ja Digiministeerium", "PRIA": "Põllumajanduse Registrite ja Informatsiooni Amet",
    "Ukraine": "Ukraina", "Loodusemuuseum": "Loodusmuuseum", "Keskkonnaage": "Keskkonnaagentuur",
}


def _tyvi(nimi):
    """Nime tüvi käändes leidmiseks: „Kultuuriministeerium“ leiab ka „Kultuuriministeeriumile“."""
    n = nimi.lower()
    return n[:-2] if len(n) > 8 else n


def asutused(hankijad=()):
    """Tuntud asutuste nimed: käsitsi loend ja registri hankijate nimed."""
    return sorted(set(ASUTUSED) | {h for h in hankijad if h})


def pealkirjast(pealkiri, hankija, nimed):
    """Teised asutused, mida pealkiri nimetab (pikim nimi enne). Hankijat ennast ei loeta."""
    p = (pealkiri or "").replace("\n", " ")
    pl, h = p.lower(), (hankija or "").lower()
    leitud = set()
    for o in nimed:
        t = _tyvi(o)
        if len(t) >= 6 and t in pl and t not in h:
            leitud.add(o)
    for luh, o in LUHENDID.items():
        lopp = "" if len(luh) > 5 else r"(?![a-zõäöü])"
        if re.search(r"(?<![\w-])" + re.escape(luh) + lopp, p) and _tyvi(o) not in h:
            leitud.add(o)
    jarjest = sorted(leitud, key=len, reverse=True)
    return [o for o in jarjest if not any(o != x and _tyvi(o) in x.lower() for x in jarjest)]


def kelle_jaoks(pealkiri, hankija, nimed):
    """Tagastab (tellija, allikas). Allikas: 'pealkiri', 'keskne' või 'sama'."""
    leitud = pealkirjast(pealkiri, hankija, nimed)
    if leitud:
        return "; ".join(leitud[:2]), "pealkiri"
    if hankija in KESKSED:
        return KESKSED[hankija] + " (pealkirjast ei selgu)", "keskne"
    return hankija, "sama"
