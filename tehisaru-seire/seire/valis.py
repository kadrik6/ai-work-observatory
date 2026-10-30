"""Välisallikate laadimine: OECD, ILOSTAT ja riikide statistikaametid.

Iga allika jaoks on kaks osa:
  * päring (funktsioonid, mille nimi algab lae_), mis toob vastuse veebist;
  * lahtipakkimine (ülejäänud funktsioonid), mis teeb vastusest read
    {"riik", "aasta", "vaartus", ...}. Need ei käi võrgus ja neid saab testida.

Päringud teeb süsteemi curl, mitte Pythoni urllib. OECD ja ILO serverid (Cloudflare)
keelduvad Pythoni vaikimisi kliendist (HTTP 403), curlile vastavad. Me ei esine
brauserina ega muuda kliendi nime: curl ütleb ise, kes ta on.

Riigikoodid on Eurostati kujul (EE, UK, EL), et neid saaks Eurostati numbritega kõrvutada.
"""

import csv
import io
import json
import re
import subprocess
import urllib.parse
import xml.etree.ElementTree as ET
import zipfile

from seire.eurostat import json_stat_ridadeks

# ---------- võrk ----------


def hae(url, keha=None, paised=None, ooteaeg=180):
    """Toob aadressi sisu baitidena. keha (bytes) korral teeb POST-päringu."""
    kask = ["curl", "-sS", "-f", "-L", "-g", "--max-time", str(ooteaeg)]
    for nimi, vaartus in (paised or {}).items():
        kask += ["-H", f"{nimi}: {vaartus}"]
    if keha is not None:
        kask += ["-X", "POST", "--data-binary", "@-"]
    kask.append(url)
    tulemus = subprocess.run(kask, input=keha, capture_output=True, check=False)
    if tulemus.returncode != 0:
        viga = tulemus.stderr.decode("utf-8", errors="replace").strip()
        raise OSError(f"{url}: {viga or 'curl lõpetas veaga ' + str(tulemus.returncode)}")
    return tulemus.stdout


def hae_json(url, keha=None, paised=None):
    if keha is not None and not isinstance(keha, bytes):
        keha = json.dumps(keha).encode("utf-8")
        paised = {"Content-Type": "application/json", **(paised or {})}
    return json.loads(hae(url, keha, paised).decode("utf-8-sig"))


# ---------- riigikoodid ----------

# ISO 3166 kolmetäheline kood -> Eurostati kood. Kreeka on Eurostatis EL, Ühendkuningriik UK.
ISO3 = {
    "AUS": "AU", "AUT": "AT", "BEL": "BE", "BGR": "BG", "BRA": "BR", "CAN": "CA", "CHE": "CH",
    "CHL": "CL", "COL": "CO", "CRI": "CR", "CYP": "CY", "CZE": "CZ", "DEU": "DE", "DNK": "DK",
    "ESP": "ES", "EST": "EE", "FIN": "FI", "FRA": "FR", "GBR": "UK", "GRC": "EL", "HRV": "HR",
    "HUN": "HU", "IRL": "IE", "ISL": "IS", "ISR": "IL", "ITA": "IT", "JPN": "JP", "KOR": "KR",
    "LTU": "LT", "LUX": "LU", "LVA": "LV", "MEX": "MX", "MLT": "MT", "NLD": "NL", "NOR": "NO",
    "NZL": "NZ", "POL": "PL", "PRT": "PT", "ROU": "RO", "SVK": "SK", "SVN": "SI", "SWE": "SE",
    "TUR": "TR", "USA": "US", "EU27": "EU27_2020", "OECD": "OECD",
}
# Riigid, mille IKT-küsitluse numbri avaldab ka Eurostat (EL ja EMP).
EUROSTATI_RIIGID = {
    "AT", "BE", "BG", "CY", "CZ", "DE", "DK", "EE", "EL", "ES", "FI", "FR", "HR", "HU", "IE", "IS",
    "IT", "LT", "LU", "LV", "MT", "NL", "NO", "PL", "PT", "RO", "SE", "SI", "SK", "EU27_2020",
}


# ---------- SDMX (OECD ja ILO) ----------

SDMX_CSV = "application/vnd.sdmx.data+csv; charset=utf-8; version=1.0"
OECD_URL = "https://sdmx.oecd.org/public/rest/data/{voog},/{voti}?startPeriod={algus}&dimensionAtObservation=AllDimensions"
OECD_VEEB = "https://data-explorer.oecd.org/vis?df[ds]=dsDisseminateFinalDMZ&df[id]={df}&df[ag]={ag}"
ILO_URL = "https://sdmx.ilo.org/rest/data/ILO,{voog},1.0/{voti}?startPeriod={algus}"
ILO_VOOG_URL = "https://sdmx.ilo.org/rest/dataflow/ILO/{voog}"
ILO_VEEB = "https://rshiny.ilo.org/dataexplorer/?lang=en&id={id}"

# SDMX vaatluse olek (OBS_STATUS). A on tavaline väärtus.
SDMX_OLEKUD = {
    "B": "aegrea katkestus", "D": "määratlus erineb", "E": "hinnang", "P": "esialgne",
    "U": "väike usaldusväärsus", "R": "muudetud", "F": "prognoos",
}


def sdmx_csv_ridadeks(tekst):
    """SDMX-CSV vastus -> read. Iga rida on sõnastik veeru nimega (REF_AREA, TIME_PERIOD, OBS_VALUE ...)."""
    if isinstance(tekst, bytes):
        tekst = tekst.decode("utf-8-sig")
    return list(csv.DictReader(io.StringIO(tekst)))


def sdmx_vaatlused(read, filtrid=None, kood="REF_AREA"):
    """Valib read, mis vastavad filtritele, ja teeb neist vaatlused.

    Iga (riik, aasta) kohta peab jääma üks väärtus, muidu valib filter liiga palju ridu.
    """
    tulemus = {}
    for r in read:
        if any(r.get(m) != v for m, v in (filtrid or {}).items()):
            continue
        if r.get("OBS_VALUE", "") in ("", "NaN"):
            continue
        riik = ISO3.get(r[kood])
        if riik is None:
            continue
        votm = (riik, int(r["TIME_PERIOD"][:4]))
        if votm in tulemus:
            raise ValueError(f"{votm}: mitu väärtust. Filter valib liiga palju ridu.")
        olek = r.get("OBS_STATUS", "")
        tulemus[votm] = {"riik": riik, "aasta": votm[1], "vaartus": float(r["OBS_VALUE"]),
                         "margend": olek if olek in SDMX_OLEKUD else ""}
    return [tulemus[k] for k in sorted(tulemus)]


def lae_oecd(voog, voti, algus=2021):
    return sdmx_csv_ridadeks(hae(OECD_URL.format(voog=voog, voti=voti, algus=algus), paised={"Accept": SDMX_CSV}))


def oecd_veebi_url(voog):
    ag, df = voog.split(",")
    return OECD_VEEB.format(df=df, ag=ag)


def lae_ilo(voog, voti, algus=2019):
    return sdmx_csv_ridadeks(hae(ILO_URL.format(voog=voog, voti=voti, algus=algus), paised={"Accept": SDMX_CSV}))


def ilo_uuendatud(xml_tekst):
    """ILO andmevoo kirjeldusest viimase uuenduse kuupäev (LAST_UPDATE, kujul PP/KK/AAAA) -> AAAA-KK-PP."""
    if isinstance(xml_tekst, bytes):
        xml_tekst = xml_tekst.decode("utf-8")
    m = re.search(r"<common:AnnotationTitle>(\d\d)/(\d\d)/(\d{4})[^<]*</common:AnnotationTitle>\s*"
                  r"<common:AnnotationType>LAST_UPDATE", xml_tekst)
    return f"{m.group(3)}-{m.group(2)}-{m.group(1)}" if m else ""


def lae_ilo_uuendatud(voog):
    return ilo_uuendatud(hae(ILO_VOOG_URL.format(voog=voog)))


def osakaal(read, lugejad, nimetaja, veerg):
    """ILO arvudest protsent: 100 * (lugejate summa) / nimetaja iga riigi ja aasta kohta.

    Arvutatakse ainult siis, kui kõik lugejad ja nimetaja on olemas.
    """
    grupid = {}
    for r in read:
        riik = ISO3.get(r["REF_AREA"])
        if riik is None or r.get("OBS_VALUE", "") == "":
            continue
        grupid.setdefault((riik, int(r["TIME_PERIOD"][:4])), {})[r[veerg]] = (float(r["OBS_VALUE"]), r.get("OBS_STATUS", ""))
    tulemus = []
    for (riik, aasta), v in sorted(grupid.items()):
        if nimetaja not in v or any(k not in v for k in lugejad) or not v[nimetaja][0]:
            continue
        olekud = {v[k][1] for k in [*lugejad, nimetaja]} & set(SDMX_OLEKUD)
        tulemus.append({"riik": riik, "aasta": aasta,
                        "vaartus": 100 * sum(v[k][0] for k in lugejad) / v[nimetaja][0],
                        "margend": ",".join(sorted(olekud))})
    return tulemus


# ---------- PxWeb (Soome, Rootsi, Norra) ----------

TK_URL = "https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin/{tabel}"
TK_VEEB = "https://pxdata.stat.fi/PxWeb/pxweb/en/StatFin/StatFin__{kaust}/statfin_{nimi}.px/"
PXWEB2_URL = {
    "NO": "https://data.ssb.no/api/pxwebapi/v2/tables/{tabel}/data?lang=en&outputFormat=json-stat2",
    "SE": "https://statistikdatabasen.scb.se/api/v2/tables/{tabel}/data?lang=en&outputFormat=json-stat2",
}
PXWEB2_VEEB = {
    "NO": "https://www.ssb.no/en/statbank/table/{tabel}",
    "SE": "https://www.statistikdatabasen.scb.se/pxweb/en/ssd/?query={tabel}",
}


def pxweb_vaatlused(andmed, aasta_moode, riik):
    """json-stat2 vastus -> vaatlused. Iga aasta kohta peab olema üks väärtus."""
    tulemus = {}
    for r in json_stat_ridadeks(andmed):
        aasta = int(str(r[aasta_moode])[:4])
        if aasta in tulemus:
            raise ValueError(f"{riik} {aasta}: mitu väärtust. Päring valib liiga palju ridu.")
        tulemus[aasta] = {"riik": riik, "aasta": aasta, "vaartus": float(r["vaartus"]), "margend": r.get("margend", "")}
    return [tulemus[a] for a in sorted(tulemus)]


def lae_tk(tabel, valikud):
    """Statistics Finland (PxWeb v1). valikud: {muutuja: [koodid]}."""
    keha = {"query": [{"code": k, "selection": {"filter": "item", "values": v}} for k, v in valikud.items()],
            "response": {"format": "json-stat2"}}
    return hae_json(TK_URL.format(tabel=tabel), keha)


def tk_veebi_url(tabel):
    kaust, nimi = tabel.split("/")
    return TK_VEEB.format(kaust=kaust, nimi=nimi)


def lae_pxweb2(riik, tabel, valikud):
    """SSB ja SCB PxWebApi 2. valikud: {muutuja: [koodid]}; "*" tähendab kõiki väärtusi."""
    url = PXWEB2_URL[riik].format(tabel=tabel)
    for k, v in valikud.items():
        url += f"&valueCodes[{urllib.parse.quote(k)}]=" + ",".join(urllib.parse.quote(x, safe="*") for x in v)
    return hae_json(url)


# ---------- Danmarks Statistik ----------

DST_URL = "https://api.statbank.dk/v1/data"
DST_INFO = "https://api.statbank.dk/v1/tableinfo/{tabel}?format=JSON&lang=en"
DST_VEEB = "https://www.statistikbanken.dk/{tabel}"


def lae_dst(tabel, valikud):
    keha = {"table": tabel, "format": "CSV", "lang": "en", "valuePresentation": "Code",
            "variables": [{"code": k, "values": v} for k, v in valikud.items()]}
    return hae(DST_URL, json.dumps(keha).encode("utf-8"), {"Content-Type": "application/json"})


def dst_vaatlused(tekst, riik="DK"):
    """DST CSV (semikooloniga, aasta veerus TID, väärtus veerus INDHOLD) -> vaatlused."""
    if isinstance(tekst, bytes):
        tekst = tekst.decode("utf-8-sig")
    tulemus = {}
    for r in csv.DictReader(io.StringIO(tekst), delimiter=";"):
        if r["INDHOLD"] in ("", ".", ".."):
            continue
        aasta = int(r["TID"][:4])
        if aasta in tulemus:
            raise ValueError(f"{riik} {aasta}: mitu väärtust. Päring valib liiga palju ridu.")
        tulemus[aasta] = {"riik": riik, "aasta": aasta, "vaartus": float(r["INDHOLD"].replace(",", ".")), "margend": ""}
    return [tulemus[a] for a in sorted(tulemus)]


def lae_dst_uuendatud(tabel):
    return hae_json(DST_INFO.format(tabel=tabel)).get("updated", "")[:10]


# ---------- CBS (Holland) ----------

CBS_KATALOOG = ("https://opendata.cbs.nl/ODataCatalog/Tables?$format=json&$select=Identifier,Title,Modified"
                "&$filter=substringof('{otsing}',Title)")
CBS_ANDMED = "https://opendata.cbs.nl/ODataApi/odata/{tabel}/TypedDataSet?$format=json"
CBS_VEEB = "https://opendata.cbs.nl/statline/#/CBS/nl/dataset/{tabel}/table"


def cbs_aastatabelid(kataloog, pealkiri):
    """CBS avaldab IKT-küsitluse igal aastal uue tabelina. Pealkiri lõpeb aastaga: "<pealkiri>, 2025".

    Tagastab {aasta: (tabeli id, muudetud)}.
    """
    tulemus = {}
    for t in kataloog["value"]:
        m = re.fullmatch(re.escape(pealkiri) + r",\s*(\d{4})\s*", t["Title"])
        if m:
            tulemus[int(m.group(1))] = (t["Identifier"], (t.get("Modified") or "")[:10])
    return tulemus


def lae_cbs_kataloog(pealkiri):
    return hae_json(CBS_KATALOOG.format(otsing=urllib.parse.quote(pealkiri)))


def cbs_vaartus(andmed, veeru_algus, filtrid):
    """Leiab tabelist rea filtrite järgi ja tagastab veeru, mille nimi algab veeru_algus (CBS lisab numbri)."""
    for r in andmed["value"]:
        if all(str(r.get(k, "")).strip() == v for k, v in filtrid.items()):
            veerg = next((k for k in r if k.startswith(veeru_algus)), None)
            if veerg is None:
                raise ValueError(f"Veergu {veeru_algus}* pole tabelis.")
            return r[veerg]
    raise ValueError(f"Rida {filtrid} puudub tabelis.")


def lae_cbs(tabel):
    return hae_json(CBS_ANDMED.format(tabel=tabel))


# ---------- Statistics Canada ----------

STATCAN_URL = "https://www150.statcan.gc.ca/t1/wds/rest/getDataFromCubePidCoordAndLatestNPeriods"
STATCAN_VEEB = "https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid={pid}01"


def lae_statcan(tabelid, koordinaat):
    keha = [{"productId": int(t), "coordinate": koordinaat, "latestN": 1} for t in tabelid]
    return hae_json(STATCAN_URL, keha)


def statcan_vaatlused(vastus, riik="CA"):
    tulemus = []
    for o in vastus:
        if o.get("status") != "SUCCESS":
            raise ValueError(f"StatCan: {o}")
        for p in o["object"]["vectorDataPoint"]:
            if p.get("value") is None:
                continue
            tulemus.append({"riik": riik, "aasta": int(p["refPer"][:4]), "vaartus": float(p["value"]),
                            "avaldatud": (p.get("releaseTime") or "")[:10], "margend": "",
                            "tabel": str(o["object"]["productId"]), "vektor": o["object"]["vectorId"]})
    return sorted(tulemus, key=lambda r: r["aasta"])


# ---------- ONS BICS (Ühendkuningriik) ----------

ONS = "https://www.ons.gov.uk"
BICS_LEHT = ONS + "/economy/economicoutputandproductivity/output/datasets/businessinsightsandimpactontheukeconomy"
KUUD = {k: i for i, k in enumerate(["January", "February", "March", "April", "May", "June", "July", "August",
                                     "September", "October", "November", "December"], 1)}


def _kuupaev(tekst):
    m = re.search(r"(\d{1,2}) (\w+) (\d{4})", tekst)
    return f"{m.group(3)}-{KUUD[m.group(2)]:02d}-{int(m.group(1)):02d}" if m and m.group(2) in KUUD else ""


def bics_failid(html):
    """BICS andmestiku lehelt xlsx-failide aadressid ja avaldamise kuupäevad, uuemad eespool.

    Iga varasema laine fail on pealkirja "BICS Wave N edition of this dataset <kuupäev>" all.
    Uusima faili kuupäev on lehe väljal "Release date".
    """
    if isinstance(html, bytes):
        html = html.decode("utf-8")
    vabastus = re.search(r'Release date:</div>\s*<div>([^<]+)</div>', html)
    failid, eelmine = [], 0
    for m in re.finditer(r'href="(/file\?uri=[^"]+\.xlsx)"', html):
        valjaanne = re.findall(r"edition of this dataset\s+(\d{1,2} \w+ \d{4})", html[eelmine:m.start()])
        kuup = _kuupaev(valjaanne[-1]) if valjaanne else (_kuupaev(vabastus.group(1)) if vabastus and not failid else "")
        failid.append((ONS + m.group(1), kuup))
        eelmine = m.end()
    return failid


_X = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
_R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"


def _veeru_nr(taht):
    """Excel'i veeru tähis -> number nullist: A -> 0, Z -> 25, AA -> 26."""
    nr = 0
    for t in taht:
        nr = nr * 26 + ord(t) - 64
    return nr - 1


def xlsx_leht(sisu, leht):
    """Loeb xlsx-failist ühe lehe ridadeks (iga rida on lahtrite tekstide loend). Ainult standardteek.

    Tagastab None, kui lehte pole.
    """
    z = zipfile.ZipFile(io.BytesIO(sisu))
    raamat = ET.fromstring(z.read("xl/workbook.xml"))
    seosed = {r.get("Id"): r.get("Target") for r in ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))}
    siht = None
    for s in raamat.iter(_X + "sheet"):
        if s.get("name") == leht:
            siht = seosed[s.get(_R + "id")].lstrip("/")
            siht = siht if siht.startswith("xl/") else "xl/" + siht
    if siht is None:
        return None
    jagatud = []
    if "xl/sharedStrings.xml" in z.namelist():
        for si in ET.fromstring(z.read("xl/sharedStrings.xml")).iter(_X + "si"):
            jagatud.append("".join(t.text or "" for t in si.iter(_X + "t")))
    read = []
    for rida in ET.fromstring(z.read(siht)).iter(_X + "row"):
        lahtrid = {}
        for c in rida.iter(_X + "c"):
            veerg = re.match(r"[A-Z]+", c.get("r")).group(0)
            v = c.find(_X + "v")
            if c.get("t") == "s" and v is not None:
                lahtrid[veerg] = jagatud[int(v.text)]
            elif c.get("t") == "inlineStr":
                lahtrid[veerg] = "".join(t.text or "" for t in c.iter(_X + "t"))
            else:
                lahtrid[veerg] = v.text if v is not None else ""
        laius = max((_veeru_nr(k) for k in lahtrid), default=-1) + 1
        read.append([""] * laius)
        for k, v in lahtrid.items():
            read[-1][_veeru_nr(k)] = v
    return read


BICS_LEHT_AI = "AI Current Usage TS (WTD)"


def bics_vaatlused(read, grupp="All size bands excluding 0 - 9"):
    """BICS tehisaru lehelt iga laine kasutusmäär protsentides: 100 × (1 − ei kasuta − ei tea).

    Leht annab iga tehnoloogia osakaalu eraldi. Kasutajate osakaal on see, mis jääb alles,
    kui lahutada „ei kasuta“ ja „ei tea“ (nii arvutab ka ONS bülletään).
    """
    pais = next(i for i, r in enumerate(read) if r and r[0] == "Dates")
    veerud = read[pais]
    ei_kasuta = next(i for i, v in enumerate(veerud) if v.startswith("Business does not currently use"))
    ei_tea = veerud.index("Not sure")
    tulemus = []
    for r in read[pais + 1:]:
        if len(r) <= max(ei_kasuta, ei_tea) or r[2].strip() != grupp:
            continue
        try:
            v = 100 * (1 - float(r[ei_kasuta]) - float(r[ei_tea]))
        except ValueError:
            continue  # [c] = konfidentsiaalne
        tulemus.append({"periood": r[0], "laine": r[1], "lopp": _kuupaev(r[0].split(" to ")[-1]),
                        "vaartus": v, "ei_tea": 100 * float(r[ei_tea])})
    return tulemus


def bics_aastate_kaupa(lained, riik="UK"):
    """Igast aastast viimane laine (BICS küsib tehisaru kohta mitu korda aastas)."""
    parim = {}
    for l in lained:
        aasta = int(l["lopp"][:4])
        if aasta not in parim or l["lopp"] > parim[aasta]["lopp"]:
            parim[aasta] = l
    return [{"riik": riik, "aasta": a, "vaartus": l["vaartus"], "margend": "",
             "markus": f'{l["laine"]}, {l["periood"]}. „Ei tea“ vastas {l["ei_tea"]:.1f}%.'}
            for a, l in sorted(parim.items())]


def lae_bics(max_faile=6):
    """Leiab uusima BICS-i faili, kus on tehisaru leht, ja tagastab (lained, faili url, avaldatud)."""
    for url, kuup in bics_failid(hae(BICS_LEHT))[:max_faile]:
        read = xlsx_leht(hae(url), BICS_LEHT_AI)
        if read:
            return bics_vaatlused(read), url, kuup
    raise ValueError(f"Viimases {max_faile} BICS-i failis pole lehte „{BICS_LEHT_AI}“.")


# ---------- UNESCO UIS ----------

UIS_URL = "https://api.uis.unesco.org/api/public/data/indicators"
UIS_VERSIOONID = "https://api.uis.unesco.org/api/public/versions"
UIS_VEEB = "https://databrowser.uis.unesco.org/"


def lae_uis(naitaja, riigid_iso3, algus=2015):
    parameetrid = [("indicator", naitaja), ("start", algus)] + [("geoUnit", r) for r in riigid_iso3]
    return hae_json(UIS_URL + "?" + urllib.parse.urlencode(parameetrid))


def uis_vaatlused(vastus):
    """UIS vastus {"records": [{"indicatorId", "geoUnit", "year", "value", "qualifier"}]} -> vaatlused."""
    tulemus = {}
    for r in vastus.get("records", []):
        riik = ISO3.get(r["geoUnit"])
        if riik is None or r.get("value") is None:
            continue
        votm = (riik, int(r["year"]))
        if votm in tulemus:
            raise ValueError(f"{votm}: mitu väärtust.")
        tulemus[votm] = {"riik": riik, "aasta": votm[1], "vaartus": float(r["value"]),
                         "margend": "", "markus": f"UIS märge: {r['qualifier']}" if r.get("qualifier") else ""}
    return [tulemus[k] for k in sorted(tulemus)]


def uis_uuendatud(versioonid, teema):
    """Viimase versiooni teema uuenduskuupäev (UIS annab KK/PP/AAAA) -> AAAA-KK-PP."""
    uusim = max(versioonid, key=lambda v: v.get("publicationDate", ""), default={})
    for t in uusim.get("themeDataStatus", []):
        if t["theme"] == teema:
            m = re.fullmatch(r"(\d\d)/(\d\d)/(\d{4})", t["lastUpdate"])
            return f"{m.group(3)}-{m.group(1)}-{m.group(2)}" if m else ""
    return ""
