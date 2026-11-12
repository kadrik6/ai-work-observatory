"""Riigihangete registri avaandmete XML-ist üks rida iga teate kohta.

Registri avaandmed on kuude kaupa kahes vormingus:
- eVormid (eForms UBL, juur OPEN-DATA, lapsed ContractNotice / ContractAwardNotice), umbes 2023. aastast;
- vanem TED eSenderi vorming (juur OPEN-DATA, lapsed TED_ESENDERS, vormid F02_2014, F03_2014 jne), 2017-09 kuni eVormideni.

Funktsioonid tagastavad sõnastikke, mitte DataFrame'e, et testid jookseksid ilma lisateekideta.
Puuduv väärtus on None, mitte 0 ega tühi tekst (disaininõue 7: puuduv ≠ null).
"""
import collections
import re
import xml.etree.ElementTree as ET

# loendur diagnostikaks (lae.py logib): statistikakoodid ja TED-vormide nimed
DIAG = collections.Counter()
DIAG_NAITED = []  # mõni XML-i lõik, kui struktuur on ootamatu (pakkumuste arv puudub)


def _naide(silt, el):
    if sum(1 for n in DIAG_NAITED if n["silt"] == silt) < 2:
        DIAG_NAITED.append({"silt": silt, "xml": ET.tostring(el, encoding="unicode")[:1800]})

RHR_ID = re.compile(r"procurement/(\d+)/")


def _l(tag):
    """Märgend ilma nimeruumita."""
    return tag.rsplit("}", 1)[-1]


def _lapsed(el, nimi):
    return [k for k in el if _l(k.tag) == nimi]


def _laps(el, *tee):
    """Esimene järeltulija mööda nimede rada (ainult otsesed lapsed igal sammul)."""
    for nimi in tee:
        if el is None:
            return None
        el = next((k for k in el if _l(k.tag) == nimi), None)
    return el


def _tekst(el, *tee):
    el = _laps(el, *tee) if tee else el
    if el is None or el.text is None:
        return None
    t = el.text.strip()
    return t or None


def _koik(el, nimi):
    return [k for k in el.iter() if _l(k.tag) == nimi]


def _arv(t):
    if t is None:
        return None
    try:
        return float(str(t).replace(",", "."))
    except ValueError:
        return None


def _uniq(seq):
    nahtud, valja = set(), []
    for x in seq:
        if x and x not in nahtud:
            nahtud.add(x)
            valja.append(x)
    return valja


# ---------------------------------------------------------------- eVormid

def _eforms_organisatsioonid(teade):
    org = {}
    for o in _koik(teade, "Organization"):
        c = _laps(o, "Company")
        if c is None:
            continue
        oid = _tekst(c, "PartyIdentification", "ID")
        if oid:
            org[oid] = {"nimi": _tekst(c, "PartyName", "Name"), "kood": _tekst(c, "PartyLegalEntity", "CompanyID")}
    return org


def _eforms_kriteeriumid(lot):
    """Hindamiskriteeriumid: [(tüüp, kaal või None)]. Tüüp on price, quality või cost."""
    valja = []
    for k in _koik(lot, "SubordinateAwardingCriterion"):
        tyyp = _tekst(k, "AwardingCriterionTypeCode")
        kaal = None
        for p in _koik(k, "AwardCriterionParameter"):
            kood = _laps(p, "ParameterCode")
            if kood is not None and kood.get("listName") == "number-weight":
                kaal = _arv(_tekst(p, "ParameterNumeric"))
        if tyyp:
            valja.append((tyyp, kaal))
    return valja


def _lisatyybid(projekt):
    """ProcurementAdditionalType koodid listName järgi, nt strategic-procurement: ['inn-pur']."""
    d = {}
    for a in _lapsed(projekt, "ProcurementAdditionalType") if projekt is not None else []:
        kood = _laps(a, "ProcurementTypeCode")
        if kood is not None and kood.text:
            d.setdefault(kood.get("listName") or "?", []).append(kood.text.strip())
    return d


def eforms_hanketeade(teade, kuu=None):
    """eVormide hanketeade (ContractNotice) → üks rida."""
    org = _eforms_organisatsioonid(teade)
    ostja_id = _tekst(teade, "ContractingParty", "Party", "PartyIdentification", "ID")
    ostja = org.get(ostja_id, {})
    projekt = _laps(teade, "ProcurementProject")
    osad = _lapsed(teade, "ProcurementProjectLot")
    osa_nimed, osa_kirjeldused, cpv, kriteeriumid, lisatyybid = [], [], [], [], {}
    cpv.append(_tekst(projekt, "MainCommodityClassification", "ItemClassificationCode"))
    for a in _lapsed(projekt, "AdditionalCommodityClassification") if projekt is not None else []:
        cpv.append(_tekst(a, "ItemClassificationCode"))
    for lot in osad:
        lp = _laps(lot, "ProcurementProject")
        osa_nimed.append(_tekst(lp, "Name"))
        osa_kirjeldused.append(_tekst(lp, "Description"))
        cpv.append(_tekst(lp, "MainCommodityClassification", "ItemClassificationCode"))
        for a in _lapsed(lp, "AdditionalCommodityClassification") if lp is not None else []:
            cpv.append(_tekst(a, "ItemClassificationCode"))
        kriteeriumid.extend(_eforms_kriteeriumid(lot))
        for k, v in _lisatyybid(lp).items():
            lisatyybid.setdefault(k, []).extend(v)
    rhr_id = None
    for el in teade.iter():
        if el.text and "procurement/" in el.text:
            m = RHR_ID.search(el.text)
            if m:
                rhr_id = m.group(1)
                break
    alamtyyp = _tekst(teade, "UBLExtensions", "UBLExtension", "ExtensionContent", "EformsExtension",
                      "NoticeSubType", "SubTypeCode")
    return {
        "allikas": "eforms",
        "teade": "CN",
        "kuu": kuu,
        "teate_id": _tekst(teade, "ID"),
        "versioon": _tekst(teade, "VersionID"),
        "kuupaev": (_tekst(teade, "IssueDate") or "")[:10] or None,
        "alamtyyp": alamtyyp,
        "viitenumber": _tekst(projekt, "ID"),
        "rhr_id": rhr_id,
        "pealkiri": _tekst(projekt, "Name"),
        "kirjeldus": _tekst(projekt, "Description"),
        "osade_nimed": _uniq(osa_nimed),
        "osade_kirjeldused": _uniq(osa_kirjeldused),
        "osade_arv": len(osad),
        "cpv": _uniq(cpv),
        "liik": _tekst(projekt, "ProcurementTypeCode"),
        "menetlus": _tekst(teade, "TenderingProcess", "ProcedureCode"),
        "menetluse_kirjeldus": _tekst(teade, "TenderingProcess", "Description"),
        "eeldatav_maksumus": _arv(_tekst(projekt, "RequestedTenderTotal", "EstimatedOverallContractAmount")),
        "hankija": ostja.get("nimi"),
        "hankija_kood": ostja.get("kood"),
        "hankija_liik": _tekst(teade, "ContractingParty", "ContractingPartyType", "PartyTypeCode"),
        "kriteeriumid": kriteeriumid,
        "strateegiline": _uniq(lisatyybid.get("strategic-procurement", [])),
        "innovatsioon": _uniq(lisatyybid.get("innovative-acquisition", [])),
        "muutus": bool(_koik(teade, "Changes")),
    }


def eforms_tulemus(teade, kuu=None):
    """eVormide lepingu sõlmimise teade (ContractAwardNotice) → pakkumuste arv ja tulemus."""
    org = _eforms_organisatsioonid(teade)
    projekt = _laps(teade, "ProcurementProject")
    pakkumusi, tulemused, voitjad, osad = [], [], [], {}
    for i, lr in enumerate(_koik(teade, "LotResult")):
        tulemused.append(_tekst(lr, "TenderResultCode"))
        osa = _tekst(lr, "TenderLot", "ID") or f"#{i + 1}"
        for s in _koik(lr, "ReceivedSubmissionsStatistics"):
            kood = _tekst(s, "StatisticsCode")
            DIAG["statistika:" + str(kood)] += 1
            if kood is None:
                _naide("statistika_ilma_koodita", s)
            if kood == "tenders":
                n = _arv(_tekst(s, "StatisticsNumeric"))
                pakkumusi.append(n)
                if n is not None:
                    osad[osa] = max(osad.get(osa, 0), n)
    for tp in _koik(teade, "TenderingParty"):
        for t in _lapsed(tp, "Tenderer"):
            o = org.get(_tekst(t, "ID"), {})
            voitjad.append(o.get("nimi"))
    summa = _arv(_tekst(teade, "NoticeResult", "TotalAmount")) if _laps(teade, "NoticeResult") is not None else None
    if summa is None:
        for el in _koik(teade, "TotalAmount"):
            summa = _arv(el.text)
            break
    pakk = [p for p in pakkumusi if p is not None]
    if not pakk and kuu and kuu >= "2026":
        lr = _koik(teade, "LotResult")
        _naide("2026_ilma_pakkumusteta", lr[0] if lr else teade)
    return {
        "allikas": "eforms",
        "teade": "CAN",
        "kuu": kuu,
        "teate_id": _tekst(teade, "ID"),
        "kuupaev": (_tekst(teade, "IssueDate") or "")[:10] or None,
        "viitenumber": _tekst(projekt, "ID"),
        "pakkumusi": max(pakk) if pakk else None,
        "osade_pakkumusi": osad,
        "tulemused": _uniq(tulemused),
        "voitjad": _uniq(voitjad),
        "lepingu_summa": summa,
    }


# ---------------------------------------------------------------- vanem TED eSenderi vorming

def _p(el):
    """TED-i tekstiväli koosneb lõikudest <P>."""
    if el is None:
        return None
    osad = [(" ".join(p.itertext())).strip() for p in el.iter() if _l(p.tag) == "P"]
    t = " ".join(o for o in osad if o) or (" ".join(el.itertext())).strip()
    return t or None


def _vorm(teade):
    """FORM_SECTION sisaldab vormi (F02_2014 jt). Esimene laps võib olla muu element, seega otsime nime järgi."""
    fs = _laps(teade, "FORM_SECTION")
    if fs is None:
        fs = teade
    for k in fs.iter():
        if re.match(r"F\d\d_\d{4}$", _l(k.tag)) or re.match(r"(MOVE|T0\d|F\d\d)$", _l(k.tag)):
            return _l(k.tag), k
    return None, None


def ted_teade(teade, kuu=None):
    """TED eSenderi teade → hanketeate (CN) või tulemuse (CAN) rida. Muud vormid → None."""
    vorm, f = _vorm(teade)
    DIAG["ted_vorm:" + str(vorm)] += 1
    if f is None:
        return None
    oc = next((e for e in f.iter() if _l(e.tag) == "OBJECT_CONTRACT"), None)
    if oc is None:
        return None
    viitenumber = _tekst(oc, "REFERENCE_NUMBER")
    cb = next((e for e in f.iter() if _l(e.tag) == "ADDRESS_CONTRACTING_BODY"), None)
    uuid = next((e.text for e in teade.iter() if _l(e.tag) == "NOTICE_UUID" and e.text), None)
    saadetud = next((e.text for e in f.iter() if _l(e.tag) == "DATE_DISPATCH_NOTICE" and e.text), None)
    rida_yld = {"allikas": "ted_esender", "kuu": kuu, "vorm": vorm, "teate_id": uuid, "viitenumber": viitenumber,
                "kuupaev": saadetud[:10] if saadetud else None}
    if vorm in ("F03_2014", "F06_2014", "F15_2014"):
        pakk = [_arv(e.text) for e in f.iter() if _l(e.tag) == "NB_TENDERS_RECEIVED"]
        pakk = [p for p in pakk if p is not None]
        osad = {}
        for i, ac in enumerate(e for e in f.iter() if _l(e.tag) == "AWARD_CONTRACT"):
            osa = _tekst(ac, "LOT_NO") or f"#{i + 1}"
            n = [_arv(e.text) for e in ac.iter() if _l(e.tag) == "NB_TENDERS_RECEIVED"]
            n = [x for x in n if x is not None]
            if n:
                osad[osa] = max(osad.get(osa, 0), max(n))
        voitjad = [_tekst(e, "OFFICIALNAME") for e in f.iter() if _l(e.tag) == "ADDRESS_CONTRACTOR"]
        summa = [_arv(e.text) for e in f.iter() if _l(e.tag) == "VAL_TOTAL"]
        summa = [s for s in summa if s is not None]
        mitte = any(_l(e.tag) == "NO_AWARDED_CONTRACT" for e in f.iter())
        return {**rida_yld, "teade": "CAN", "pakkumusi": max(pakk) if pakk else None, "osade_pakkumusi": osad,
                "tulemused": ["clos-nw"] if mitte and not pakk else (["selec-w"] if pakk else []),
                "voitjad": _uniq(voitjad), "lepingu_summa": sum(summa) if summa else None}
    if vorm not in ("F02_2014", "F05_2014", "F21_2014", "F22_2014", "F24_2014", "F17_2014"):
        return None
    cpv = [e.get("CODE") for e in oc.iter() if _l(e.tag) == "CPV_CODE"]
    osad = [e for e in oc if _l(e.tag) == "OBJECT_DESCR"]
    kriteeriumid = []
    for od in osad:
        ac = _laps(od, "AC")
        if ac is None:
            continue
        for k in ac:
            nimi = _l(k.tag)
            tyyp = {"AC_QUALITY": "quality", "AC_COST": "cost", "AC_PRICE": "price"}.get(nimi)
            if tyyp:
                kaal = _arv(re.sub(r"[^0-9.,]", "", _tekst(k, "AC_WEIGHTING") or "") or None)
                kriteeriumid.append((tyyp, kaal))
    menetlus = None
    proc = next((e for e in f.iter() if _l(e.tag) == "PROCEDURE"), None)
    if proc is not None:
        menetlus = next((_l(k.tag) for k in proc if _l(k.tag).startswith("PT_")), None)
    liik = _laps(oc, "TYPE_CONTRACT")
    hind = _laps(oc, "VAL_ESTIMATED_TOTAL")
    return {
        **rida_yld,
        "teade": "CN",
        "versioon": None,
        "alamtyyp": vorm,
        "rhr_id": None,
        "pealkiri": _p(_laps(oc, "TITLE")),
        "kirjeldus": _p(_laps(oc, "SHORT_DESCR")),
        "osade_nimed": _uniq([_p(_laps(od, "TITLE")) for od in osad]),
        "osade_kirjeldused": _uniq([_p(_laps(od, "SHORT_DESCR")) for od in osad]),
        "osade_arv": len(osad),
        "cpv": _uniq(cpv),
        "liik": {"SERVICES": "services", "SUPPLIES": "supplies", "WORKS": "works"}.get(
            liik.get("CTYPE") if liik is not None else None),
        "menetlus": menetlus,
        "menetluse_kirjeldus": None,
        "eeldatav_maksumus": _arv(hind.text) if hind is not None else None,
        "hankija": _tekst(cb, "OFFICIALNAME"),
        "hankija_kood": _tekst(cb, "NATIONALID"),
        "hankija_liik": None,
        "kriteeriumid": kriteeriumid,
        "strateegiline": [],
        "innovatsioon": [],
        "muutus": False,
    }


# ---------------------------------------------------------------- fail

def parsi_fail(sisu, kuu=None):
    """Kuu XML (baidid) → (hanketeated, tulemused). Tundmatud teated jäetakse vahele ja loetakse kokku."""
    juur = ET.fromstring(sisu)
    cn, can, vahele = [], [], 0
    for t in juur:
        nimi = _l(t.tag)
        try:
            if nimi == "ContractNotice":
                cn.append(eforms_hanketeade(t, kuu))
            elif nimi == "ContractAwardNotice":
                can.append(eforms_tulemus(t, kuu))
            elif nimi == "TED_ESENDERS":
                r = ted_teade(t, kuu)
                if r is None:
                    vahele += 1
                elif r["teade"] == "CN":
                    cn.append(r)
                else:
                    can.append(r)
            else:
                vahele += 1
        except Exception:  # noqa: BLE001  üks vigane teade ei tohi kogu kuud peatada
            vahele += 1
    return cn, can, vahele
