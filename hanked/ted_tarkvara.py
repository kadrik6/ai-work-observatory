"""TED: tarkvara- ja platvormihanked Euroopas tootja kaupa (Microsoft vs alternatiivid).

Kadri küsimus 8.11.2026: kui palju kulutavad Euroopa riikide avalikud asutused Microsofti toodetele, mis litsentse
nad ostavad ja mida kasutatakse Microsofti asemel. Päring käib TED-i avalikku otsinguliidesesse (API v3, võtmeta).
Logisse lähevad read "TED ...". Ainult lugemine.

Piirid: TED-is on ainult EL-i piirmäärast suuremad hanked (ja osa vabatahtlikke teateid). Eeldatav maksumus on
sageli raamlepingu lagi. Teade ei ütle, kas raha ka kulus. Sama hange võib olla mitu korda (eri teated).
"""
import json
import time
import urllib.error
import urllib.request

URL = "https://api.ted.europa.eu/v3/notices/search"

TOOTED = {
    "microsoft": '"Microsoft"',
    "m365": '"Microsoft 365" OR "Office 365" OR "M365"',
    "azure": '"Azure"',
    "power_bi": '"Power BI"',
    "tableau": '"Tableau"',
    "qlik": '"Qlik"',
    "sas": '"SAS Institute" OR "SAS Viya"',
    "google_workspace": '"Google Workspace"',
    "libreoffice": '"LibreOffice"',
    "nextcloud": '"Nextcloud"',
    "collabora": '"Collabora"',
    "opendesk": '"openDesk"',
    "onlyoffice": '"OnlyOffice"',
    "oracle": '"Oracle"',
    "sap": '"SAP"',
}

KANDIDAADID = ["publication-number", "notice-title", "buyer-country", "buyer-name", "publication-date",
               "notice-type", "classification-cpv", "BT-27-Procedure", "BT-27-Lot", "BT-161-NoticeResult",
               "BT-720-Tender", "BT-709-LotResult", "contract-nature", "framework-agreement-lot",
               "estimated-value-proc", "estimated-value-lot", "total-value", "TV"]


def kirjuta(osa, **kw):
    print("TED", osa, json.dumps(kw, ensure_ascii=False), flush=True)


def paring(keha, katseid=4):
    data = json.dumps(keha).encode()
    for k in range(katseid):
        req = urllib.request.Request(URL, data=data, headers={"Content-Type": "application/json",
                                                               "Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            sisu = e.read().decode(errors="replace")[:600]
            if e.code in (429, 500, 502, 503) and k < katseid - 1:
                time.sleep(5 * (k + 1))
                continue
            return {"_viga": e.code, "_sisu": sisu}
        except Exception as e:  # noqa: BLE001
            if k < katseid - 1:
                time.sleep(5 * (k + 1))
                continue
            return {"_viga": str(e)}


def valjad():
    """Proovib iga välja eraldi ja jätab alles need, mida liides tunneb."""
    head = []
    for v in KANDIDAADID:
        vastus = paring({"query": 'FT ~ ("Microsoft") AND publication-date >= 20250101', "fields": [v], "limit": 1})
        ok = "_viga" not in vastus
        kirjuta("valja_proov", vali=v, ok=ok, viga=None if ok else vastus.get("_sisu", vastus.get("_viga")))
        if ok:
            head.append(v)
    return head


def main():
    v = valjad()
    if not v:
        kirjuta("loobun", pohjus="ükski väli ei sobinud")
        return
    naide_tehtud = False
    for toode, otsing in TOOTED.items():
        # pealkirjas (notice-title) = hanke põhiese; täistekstis (FT) = mainitakse kuskil
        for kus in ("notice-title", "FT"):
            q = f"{kus} ~ ({otsing}) AND publication-date >= 20200101"
            leht, kokku, token = 0, None, None
            while True:
                keha = {"query": q, "fields": v, "limit": 250, "paginationMode": "ITERATION",
                        "checkQuerySyntax": False}
                if token:
                    keha["iterationNextToken"] = token
                vastus = paring(keha)
                if "_viga" in vastus:
                    kirjuta("viga", toode=toode, kus=kus, viga=vastus)
                    break
                kokku = vastus.get("totalNoticeCount", kokku)
                teated = vastus.get("notices", [])
                if not naide_tehtud and teated:
                    kirjuta("naide", teade=teated[0])
                    naide_tehtud = True
                if kus == "notice-title" or kokku and kokku <= 3000:
                    for t in teated:
                        kirjuta("rida", toode=toode, kus=kus, **{k: t.get(k) for k in v})
                leht += 1
                token = vastus.get("iterationNextToken")
                if not token or not teated or leht >= 40 or (kus == "FT" and (kokku or 0) > 3000):
                    break
            kirjuta("arv", toode=toode, kus=kus, kokku=kokku)


if __name__ == "__main__":
    main()
