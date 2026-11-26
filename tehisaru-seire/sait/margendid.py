"""Andmestiku märgendid (schema.org Dataset, JSON-LD), et Google'i andmestike otsing ja teised otsingud leiaksid
saidi numbrid koos allikaga (Kadri 27.11.2026: „Teeks esimesed 2 järjest“, punkt 2: nähtavus ilma postitamata).

Iga märgend kirjeldab ainult seda, mis lehel päriselt on: näitaja nimi ja selgitus tulevad kataloogist
(kataloog/naitajad.json), aastad ja kuupäevad vaatlustest, allika aadress algallikast. Andmete looja on algallikas
(Eurostat, Statistikaamet, riigihangete register), mitte see sait; litsentsi ei märgita, sest see on allika oma.
Avalehel on DataCatalog, mis loetleb kõik andmestikud. Ehitus kukub, kui lehte või ankrut pole (ehita.py)."""
import json
import re

from kest import SAIDI_AADRESS

# Näitaja → (leht, ankur). Uus kataloogi näitaja vajab siia rida (test kontrollib).
KOHAD = {
    "inimeste-tehisaru-kasutus": ("inimesed.html", "kasutus"),
    "tooalane-tehisaru-kasutus": ("inimesed.html", "tool"),
    "tehisaru-oskuse-puudus": ("inimesed.html", "ei-oska"),
    "inimeste-digioskused": ("inimesed.html", "digi"),
    "ettevotete-tehisaru-kasutus": ("ettevotted.html", "kasutus"),
    "ettevotete-digiintensiivsus": ("ettevotted.html", "digi"),
    "ta-kulud": ("ettevotted.html", "digi"),
}
ALLIKA_KODU = {
    "Eurostat": "https://ec.europa.eu/eurostat",
    "Statistikaamet": "https://www.stat.ee/",
}
RUUM = {"@type": "Place", "name": "Eesti ja Euroopa Liidu riigid"}


def _aadress(fail, ankur):
    return f"{SAIDI_AADRESS}{fail.removesuffix('.html')}#{ankur}"


def _looja(nimi):
    o = {"@type": "Organization", "name": nimi}
    if nimi in ALLIKA_KODU:
        o["url"] = ALLIKA_KODU[nimi]
    return o


def _kataloogist(A, nid, n):
    V = [v for v in A["vaatlused"] if v["naitaja"] == nid]
    if not V:
        return None
    fail, ankur = KOHAD[nid]
    piirangud = " ".join(n.get("piirangud", []))
    allikad = sorted({v["url"] for v in V if v["url"]})
    loojad = sorted({v["allikas"].split(",")[0].strip() for v in V})
    return {
        "_fail": fail, "_ankur": ankur,
        "@type": "Dataset",
        "@id": _aadress(fail, ankur),
        "url": _aadress(fail, ankur),
        "name": f"{n['nimi']}: Eesti ja EL",
        "description": f"{n['kusimus']} {n['mida_see_tahendab']} {piirangud}".strip(),
        "inLanguage": "et",
        "isAccessibleForFree": True,
        "keywords": ["tehisaru", "tehisintellekt", "Eesti", "Euroopa Liit", "statistika", n["nimi"]],
        "variableMeasured": {"@type": "PropertyValue", "name": n["nimi"], "unitText": n.get("uhik", "")},
        "temporalCoverage": f"{min(v['aasta'] for v in V)}/{max(v['aasta'] for v in V)}",
        "spatialCoverage": RUUM,
        "dateModified": max(v["avaldatud"] for v in V if v["avaldatud"]),
        "creator": [_looja(x) for x in loojad],
        "isBasedOn": allikad,
    }


def _tootus(A):
    from lehed_ulevaade import UNE_URL, UNE_UUENDATUD, tootus
    T = tootus()
    kuud = [k for k, _ in T["EE"]]
    return {
        "_fail": "too.html", "_ankur": "tootus-kuud",
        "@type": "Dataset", "@id": _aadress("too.html", "tootus-kuud"), "url": _aadress("too.html", "tootus-kuud"),
        "name": "Töötuse määr kuu kaupa: Eesti ja EL",
        "description": ("Hooajaliselt korrigeeritud töötuse määr kuu kaupa Eestis ja ELis (Eurostat une_rt_m). "
                        "Kuunumber kirjeldab tööturu seisu; see ei ütle, kas muutuse põhjus on tehisaru."),
        "inLanguage": "et", "isAccessibleForFree": True,
        "keywords": ["töötus", "tööturg", "tehisaru", "Eesti", "Euroopa Liit"],
        "variableMeasured": {"@type": "PropertyValue", "name": "Töötuse määr", "unitText": "% tööjõust"},
        "temporalCoverage": f"{kuud[0]}/{kuud[-1]}",
        "spatialCoverage": RUUM,
        "dateModified": UNE_UUENDATUD,
        "creator": [_looja("Eurostat")],
        "isBasedOn": [UNE_URL],
    }


def _hanked(A):
    from lehed_ulevaade import HANKED_URL
    H = A.get("hanked_leht") or {}
    L = H.get("loend") or []
    if not L:
        return None
    return {
        "_fail": "hanked.html", "_ankur": "aastad",
        "@type": "Dataset", "@id": _aadress("hanked.html", "aastad"), "url": _aadress("hanked.html", "aastad"),
        "name": "Eesti tehisaru- ja andmehanked",
        "description": ("Eesti riigihangete registri avaandmetest kogutud hanked, mille pealkirjas või kirjelduses on "
                        "tehisaru märksõna või mis puudutavad andmeladu, andmehaldust või andmeanalüüsi. Iga hanke juures "
                        "on hankija, kuupäev, eeldatav maksumus ja hindamise viis, kui register need avaldab."),
        "inLanguage": "et", "isAccessibleForFree": True,
        "keywords": ["riigihanked", "tehisaru", "andmed", "avalik sektor", "Eesti"],
        "variableMeasured": [{"@type": "PropertyValue", "name": "Hangete arv aastas"},
                             {"@type": "PropertyValue", "name": "Eeldatav maksumus", "unitText": "EUR"}],
        "temporalCoverage": f"{min(x['kp'] for x in L)[:10]}/{max(x['kp'] for x in L)[:10]}",
        "spatialCoverage": {"@type": "Place", "name": "Eesti"},
        "dateModified": (H.get("seis") or {}).get("kuupaev") or max(x["kp"] for x in L)[:10],
        "creator": [_looja("Riigihangete register")],
        "isBasedOn": [HANKED_URL],
    }


def andmestikud(A):
    tulem = []
    for nid, n in A["naitajad"].items():
        if nid not in KOHAD:
            raise ValueError(f"margendid.KOHAD: näitajal {nid} pole lehte")
        d = _kataloogist(A, nid, n)
        if d:
            tulem.append(d)
    tulem.append(_tootus(A))
    h = _hanked(A)
    if h:
        tulem.append(h)
    return tulem


def _puhas(d):
    return {k: v for k, v in d.items() if not k.startswith("_")}


def _skript(o):
    t = json.dumps(o, ensure_ascii=False, separators=(",", ":"))
    return '<script type="application/ld+json">' + t.replace("</", "<\\/") + "</script>"


def jsonld(A, fail):
    """JSON-LD lehe <head>-i: avalehel WebSite ja DataCatalog, teemalehel selle lehe andmestikud."""
    if not A or not A.get("naitajad"):
        return ""
    D = andmestikud(A)
    if fail == "index.html":
        return _skript({
            "@context": "https://schema.org",
            "@graph": [
                {"@type": "WebSite", "@id": SAIDI_AADRESS, "url": SAIDI_AADRESS, "name": "Tehisaru seire", "inLanguage": "et"},
                {"@type": "DataCatalog", "name": "Tehisaru seire andmed", "url": SAIDI_AADRESS, "inLanguage": "et",
                 "description": ("Avalik statistika ja registriandmed tehisaru kasutusest Eestis ja ELis: inimesed, "
                                 "ettevõtted, töö ja avaliku sektori hanked. Iga number on algallikast koos lingi ja kuupäevaga."),
                 "dataset": [{"@type": "Dataset", "@id": d["@id"], "name": d["name"], "url": d["url"]} for d in D]},
            ],
        })
    oma = [_puhas(d) for d in D if d["_fail"] == fail]
    if not oma:
        return ""
    return _skript({"@context": "https://schema.org", "@graph": oma})


def ankrud(A):
    """[(fail, ankur)] kõigist märgenditest, et ehitus saaks kontrollida, kas need on lehel olemas."""
    return [(d["_fail"], d["_ankur"]) for d in andmestikud(A)]


def kirjeldus_on_piisav(d):
    """Google'i nõue: kirjeldus 50–5000 märki."""
    return 50 <= len(re.sub(r"\s+", " ", d["description"])) <= 5000

