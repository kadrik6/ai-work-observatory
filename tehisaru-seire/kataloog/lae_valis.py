"""Laeb kataloogi vaatlused välisallikatest faili vaatlused-valis.csv.

Allikad: OECD, ILOSTAT, UNESCO UIS, Eurostati IKT-spetsialistid ja T&A kulud ning Taani, Norra, Soome, Rootsi,
Hollandi, Ühendkuningriigi ja Kanada statistikaametid.

Käivitamine kaustast tehisaru-seire:
    python kataloog/lae_valis.py                    # kõik
    python kataloog/lae_valis.py --ainult dst-itav28,cbs-ict

Kui mõne allika laadimine ebaõnnestub, jäävad selle mõõdiku eelmised read alles ja
olekufailis kataloog/valis-olek.csv on kirjas viga. Teisi allikaid see ei takista.

"avaldatud" on numbri esmaavaldamise kuupäev. See märgitakse ainult siis, kui allikas
selle annab (Statistics Canada, ONS-i väljaande kuupäev; Eurostati puhul andmestiku
uuendus nagu failis lae.py). Teiste allikate tabeli uuenduskuupäev ei ole avaldamise
kuupäev (tabelit parandatakse ka hiljem), seepärast läheb see viimase aasta märkusesse.
"""

import argparse
import csv
import datetime as dt
import json
import sys
from pathlib import Path

JUUR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(JUUR))

from seire import eurostat, valis  # noqa: E402

VALJA = JUUR / "kataloog" / "vaatlused-valis.csv"
OLEK = JUUR / "kataloog" / "valis-olek.csv"
VALJAD = ["moodik", "riik", "aasta", "vaartus", "avaldatud", "kontrollitud", "kuidas", "url", "markus", "margend"]
OLEKU_VALJAD = ["moodik", "olek", "ridu", "viimane_aasta", "kontrollitud", "viga"]

# Teadaolevad esmaavaldamise kuupäevad (kontrollitud uudistest ja väljaannetest, vt allikad/allikad.csv).
AVALDATUD = {("dst-itav28", 2026): "2026-09-15", ("ssb-ikt", 2026): "2026-09-25", ("ssb-14365", 2026): "2026-09-25",
             ("ssb-14365-too", 2026): "2026-09-25"}

FOOKUS = json.loads((JUUR / "naitajad.json").read_text(encoding="utf-8"))["riigid"]
VALJASPOOL_EL = sorted(set(valis.ISO3.values()) - valis.EUROSTATI_RIIGID - {"OECD"})


def arv(v, kohti=4):
    """Arv tekstiks allika täpsusega: üleliigseid nulle ei lisata (4.7, mitte 4.7000)."""
    v = round(float(v), kohti)
    return str(int(v)) if v == int(v) else repr(v)


def viimasele(read, kuup, avaldatud=False):
    """Märgib viimase aasta ridadele tabeli uuenduskuupäeva (märkusesse) või avaldamise kuupäeva."""
    if read and kuup:
        viimane = max(r["aasta"] for r in read)
        for r in read:
            if r["aasta"] != viimane:
                continue
            if avaldatud:
                r.setdefault("avaldatud", kuup)
            else:
                r["markus"] = " ".join(x for x in (r.get("markus", ""), f"Tabel uuendatud {kuup}.") if x)
    return read


def riikidele(read, riigid):
    return [r for r in read if r["riik"] in riigid]


# ---------- laadijad: iga funktsioon tagastab (read, url, kuidas) ----------

OECD_ETTEVOTTED = ("OECD.STI.DEP,DSD_ICT_B@DF_BUSINESSES", ".A.G14_B.PT_ENT._T.S_GE10")
OECD_INIMESED = "OECD.STI.DEP,DSD_ICT_HH_IND@DF_IND"


def oecd(voog, voti, riigid, filtrid=None):
    def lae():
        read = valis.sdmx_vaatlused(valis.lae_oecd(voog, voti), filtrid)
        return riikidele(read, riigid), valis.oecd_veebi_url(voog), "OECD SDMX API"
    return lae


def oecd_inimesed(moode, riigid):
    return oecd(OECD_INIMESED, f".A.{moode}.PT_POP._Z.Y16T74._T._T._T._T", riigid)


ILO_AMETID = "DF_EMP_TEMP_SEX_OC2_NB"
ILO_RIIGID = ["EST", "FIN", "SWE", "DNK", "NOR", "DEU", "NLD", "GBR", "USA", "CHE", "JPN", "KOR", "AUS", "CAN"]


def ilo_ikt(riigid):
    def lae():
        voti = "+".join(ILO_RIIGID) + ".A..SEX_T.OC2_ISCO08_TOTAL+OC2_ISCO08_25+OC2_ISCO08_35"
        read = valis.osakaal(valis.lae_ilo(ILO_AMETID, voti), ["OC2_ISCO08_25", "OC2_ISCO08_35"],
                             "OC2_ISCO08_TOTAL", "OC2")
        uuendatud = valis.lae_ilo_uuendatud(ILO_AMETID)
        for r in read:
            r["vaartus"] = round(r["vaartus"], 2)
            r["markus"] = f"Arvutatud ILO arvudest: (ISCO-08 25 + 35) / kõik hõivatud. ILOSTAT uuendas andmevoogu {uuendatud}."
        return riikidele(read, riigid), valis.ILO_VEEB.format(id=ILO_AMETID[3:]), "ILOSTAT SDMX API"
    return lae


def eurostat_ikt():
    filtrid = {"freq": "A", "unit": "PC_EMP"}
    vastus = eurostat.lae("isoc_sks_itspt", filtrid, FOOKUS)
    read = [{"riik": r["geo"], "aasta": int(r["time"]), "vaartus": r["vaartus"], "margend": r["margend"]}
            for r in eurostat.json_stat_ridadeks(vastus) if r["vaartus"] is not None and int(r["time"]) >= 2019]
    for r in read:
        r["avaldatud"] = vastus["updated"][:10]
    return read, eurostat.koosta_url("isoc_sks_itspt", filtrid, FOOKUS), "Eurostati API"


def dst(tabel, valikud):
    def lae():
        read = valis.dst_vaatlused(valis.lae_dst(tabel, valikud))
        return viimasele(read, valis.lae_dst_uuendatud(tabel)), valis.DST_VEEB.format(tabel=tabel), "Danmarks Statistiku API"
    return lae


def pxweb2(riik, tabel, valikud, nimi):
    def lae():
        andmed = valis.lae_pxweb2(riik, tabel, valikud)
        read = valis.pxweb_vaatlused(andmed, "Tid", riik)
        return viimasele(read, (andmed.get("updated") or "")[:10]), valis.PXWEB2_VEEB[riik].format(tabel=tabel), nimi
    return lae


def tk(tabel, valikud):
    def lae():
        andmed = valis.lae_tk(tabel, valikud)
        read = valis.pxweb_vaatlused(andmed, "timeperiod_y", "FI")
        return viimasele(read, (andmed.get("updated") or "")[:10]), valis.tk_veebi_url(tabel), "Statistics Finlandi API"
    return lae


def cbs():
    pealkiri = "ICT-gebruik bij bedrijven; bedrijfsgrootte"
    tabelid = valis.cbs_aastatabelid(valis.lae_cbs_kataloog(pealkiri), pealkiri)
    read = []
    for aasta, (tabel, muudetud) in sorted(tabelid.items()):
        if aasta < 2021:
            continue  # tehisaru küsiti esimest korda 2021. aastal
        v = valis.cbs_vaartus(valis.lae_cbs(tabel), "AIGebruikt_", {"Bedrijfsgrootte": "WP19088"})
        if v is not None:
            read.append({"riik": "NL", "aasta": aasta, "vaartus": v, "margend": "", "markus": f"CBS tabel {tabel}"})
    viimane = max(tabelid) if tabelid else None
    return (viimasele(read, tabelid[viimane][1] if viimane else ""),
            valis.CBS_VEEB.format(tabel=tabelid[viimane][0]) if viimane else "", "CBS OData API")


def statcan():
    # CSBC II kvartali tehisaru küsimus; iga aasta on eraldi tabel. Koordinaat: Kanada, kõik tegevusalad, kasutas.
    tabelid = ["33100825", "33101004", "33101167"]
    read = valis.statcan_vaatlused(valis.lae_statcan(tabelid, "1.1.1.0.0.0.0.0.0.0"))
    for r in read:
        t = r.pop("tabel")
        r["markus"] = f"II kvartal {r['aasta']}, tabel {t[:2]}-{t[2:4]}-{t[4:]}-01, vektor {r.pop('vektor')}."
    return read, valis.STATCAN_VEEB.format(pid=tabelid[-1]), "Statistics Canada WDS API"


def bics():
    lained, url, kuup = valis.lae_bics()
    read = valis.bics_aastate_kaupa(lained)
    for r in read:
        r["vaartus"] = round(r["vaartus"], 1)
    return viimasele(read, kuup, avaldatud=True), url, "ONS BICS andmefail (arvutatud: 100 − ei kasuta − ei tea)"


UIS_RIIGID = ["EST", "FIN", "SWE", "DNK", "NOR", "DEU", "NLD", "GBR", "USA", "CAN", "JPN", "KOR", "CHE", "AUS"]


def uis(naitaja, teema, riigid, kohti=2):
    def lae():
        read = valis.uis_vaatlused(valis.lae_uis(naitaja, UIS_RIIGID))
        for r in read:
            r["vaartus"] = round(r["vaartus"], kohti)
        uuendatud = valis.uis_uuendatud(valis.hae_json(valis.UIS_VERSIOONID), teema)
        return viimasele(riikidele(read, riigid), uuendatud), valis.UIS_VEEB, "UNESCO UIS API"
    return lae


def eurostat_gerd():
    filtrid = {"freq": "A", "sectperf": "TOTAL", "unit": "PC_GDP"}
    vastus = eurostat.lae("rd_e_gerdtot", filtrid, FOOKUS)
    read = [{"riik": r["geo"], "aasta": int(r["time"]), "vaartus": r["vaartus"], "margend": r["margend"],
             "avaldatud": vastus["updated"][:10]}
            for r in eurostat.json_stat_ridadeks(vastus) if r["vaartus"] is not None and int(r["time"]) >= 2015]
    return read, eurostat.koosta_url("rd_e_gerdtot", filtrid, FOOKUS), "Eurostati API"


MOODIKUD = {
    "oecd-g14b-el": oecd(*OECD_ETTEVOTTED, FOOKUS),
    "oecd-g14b-muud": oecd(*OECD_ETTEVOTTED, VALJASPOOL_EL),
    "oecd-d1x-el": oecd_inimesed("D1X_I", FOOKUS),
    "oecd-d1x-muud": oecd_inimesed("D1X_I", VALJASPOOL_EL),
    "oecd-d1xb-el": oecd_inimesed("D1XB_I", FOOKUS),
    "oecd-d1xb-muud": oecd_inimesed("D1XB_I", VALJASPOOL_EL),
    "eurostat-isoc-sks-itspt": eurostat_ikt,
    "ilo-ikt-ametid": ilo_ikt(FOOKUS),
    "ilo-ikt-ametid-muud": ilo_ikt(VALJASPOOL_EL),
    "dst-itav28": dst("ITAV28", {"VIRKSTRRDA": ["1010"], "BRANCHEDB25UDVALG": ["C-O_T95XL"], "ANVEND": ["1680"], "Tid": ["*"]}),
    "ssb-ikt": pxweb2("NO", "14942", {"NACE2025": ["_T"], "SyssGrpIKT": ["00"], "ContentsCode": ["BrukarKunstigIntelli"],
                                     "Tid": ["*"]}, "SSB PxWebApi 2"),
    "ssb-14365": pxweb2("NO", "14365", {"Kjonn": ["0"], "Alder": ["16-74"], "ContentsCode": ["BruktGenerativKI"],
                                       "Tid": ["*"]}, "SSB PxWebApi 2"),
    "ssb-14365-too": pxweb2("NO", "14365", {"Kjonn": ["0"], "Alder": ["16-74"], "ContentsCode": ["BruktKIjobb"],
                                           "Tid": ["*"]}, "SSB PxWebApi 2"),
    "scb-tab6405": pxweb2("SE", "TAB6405", {"TypAvTeknik": ["0080"], "Redovisningsgrupp": ["Tot250"],
                                           "ContentsCode": ["000007JC"], "Tid": ["*"]}, "SCB PxWebApi 2"),
    "scb-tab6388": pxweb2("SE", "TAB6388", {"AnvInternet": ["1280"], "Kon": ["1+2"], "Redovisningsgrupp": ["tot16-74"],
                                           "ContentsCode": ["000007L5"], "Tid": ["*"]}, "SCB PxWebApi 2"),
    "tk-icte": tk("icte/14yc.px", {"toimiala_79_20180101": ["SSS"], "contentscode": ["icte22"]}),
    "tk-sutivi": tk("sutivi/13ud.px", {"sukupuoli_9_20180101": ["SSS"], "ika_10v_15_20221116": ["SSS"],
                                       "contentscode": ["iuai"], "timeperiod_y": ["2024", "2025"]}),
    "cbs-ict": cbs,
    "statcan-csbc": statcan,
    "ons-bics": bics,
    "eurostat-rd-e-gerdtot": eurostat_gerd,
    "uis-gerd": uis("EXPGDP.TOT", "SCIENCE_TECHNOLOGY_INNOVATION", FOOKUS),
    "uis-gerd-muud": uis("EXPGDP.TOT", "SCIENCE_TECHNOLOGY_INNOVATION", VALJASPOOL_EL),
    "uis-teadlased": uis("RESDEN.INHAB.TFTE", "SCIENCE_TECHNOLOGY_INNOVATION", FOOKUS + VALJASPOOL_EL, 0),
    "uis-ikt-lopetajad": uis("FOSGP.5T8.F600", "EDUCATION", FOOKUS + VALJASPOOL_EL),
}


def _loe(p):
    if not p.exists():
        return []
    with open(p, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _kirjuta(p, valjad, read):
    with open(p, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=valjad)
        w.writeheader()
        w.writerows(read)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--ainult", help="komaga eraldatud mõõdikud")
    args = ap.parse_args(argv)
    valitud = args.ainult.split(",") if args.ainult else list(MOODIKUD)
    tundmatu = [m for m in valitud if m not in MOODIKUD]
    if tundmatu:
        ap.error(f"tundmatu mõõdik: {', '.join(tundmatu)}")

    tana = dt.date.today().isoformat()
    vanad = _loe(VALJA)
    olek = {r["moodik"]: r for r in _loe(OLEK)}
    uued = {}
    for moodik in valitud:
        try:
            read, url, kuidas = MOODIKUD[moodik]()
            if not read:
                raise ValueError("allikas ei andnud ühtegi rida")
        except Exception as viga:  # üks allikas ei tohi teisi peatada
            vanu = sum(1 for r in vanad if r["moodik"] == moodik)
            olek[moodik] = {"moodik": moodik, "olek": "viga", "ridu": vanu,
                            "viimane_aasta": olek.get(moodik, {}).get("viimane_aasta", ""),
                            "kontrollitud": olek.get(moodik, {}).get("kontrollitud", ""), "viga": str(viga)[:300]}
            print(f"VIGA {moodik}: {viga}. Jäävad eelmised read ({vanu}).", file=sys.stderr)
            continue
        uued[moodik] = [{"moodik": moodik, "riik": r["riik"], "aasta": r["aasta"], "vaartus": arv(r["vaartus"]),
                         "avaldatud": r.get("avaldatud") or AVALDATUD.get((moodik, r["aasta"]), ""), "kontrollitud": tana, "kuidas": kuidas, "url": url,
                         "markus": r.get("markus", ""), "margend": r.get("margend", "")} for r in read]
        viimane = max(r["aasta"] for r in read)
        olek[moodik] = {"moodik": moodik, "olek": "ok", "ridu": len(read), "viimane_aasta": viimane,
                        "kontrollitud": tana, "viga": ""}
        naide = ", ".join(f'{r["riik"]} {r["vaartus"]}' for r in uued[moodik] if r["aasta"] == viimane)
        print(f"{moodik}: {len(read)} rida, viimane aasta {viimane}: {naide[:120]}")

    read = [r for r in vanad if r["moodik"] not in uued and r["moodik"] in MOODIKUD]
    for moodik in MOODIKUD:
        read += uued.get(moodik, [])
    read.sort(key=lambda r: (list(MOODIKUD).index(r["moodik"]), r["riik"], int(r["aasta"])))
    _kirjuta(VALJA, VALJAD, read)
    _kirjuta(OLEK, OLEKU_VALJAD, [olek[m] for m in MOODIKUD if m in olek])
    vigu = sum(1 for m in valitud if olek[m]["olek"] == "viga")
    print(f"Valmis: {len(read)} vaatlust failis {VALJA.name}. Vigu: {vigu}.")
    return 1 if vigu else 0


if __name__ == "__main__":
    raise SystemExit(main())
