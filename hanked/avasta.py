"""Ühekordne avastus (2. ring): riigihangete registri avaandmete URL-id ja eVormide XML-i struktuur, TED-i väljanimed.

Käivitub GitHub Actionsis (liivakast ei pääse nendele aadressidele). Prindib logisse read "AVASTA <osa> ...".
"""
import collections
import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET

RHR = "https://riigihanked.riik.ee/rhr/api/public/v1"


def hae(url, data=None, headers=None, timeout=120):
    h = {"Accept": "*/*"}  # vaikimisi User-Agent (repo reegel: ära võltsi)
    h.update(headers or {})
    req = urllib.request.Request(url, data=data, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.headers.get("Content-Type"), r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get("Content-Type"), e.read()[:3000]
    except Exception as e:  # noqa: BLE001
        return None, None, str(e).encode()


def kirjuta(osa, **kw):
    print("AVASTA", osa, json.dumps(kw, ensure_ascii=False)[:8000], flush=True)


def js_konstandid():
    st, ct, b = hae("https://riigihanked.riik.ee/rhr-web/scripts/scripts.2349a169.js")
    t = b.decode("utf-8", "replace")
    for voti in ["OPENDATA_NOTICE_URL", "OPENDATA_NOTICE_AWARD_URL", "CONTRACT_NOTICE", "PROCUREMENT_NOTICE",
                 "openDataNoticeUrl=", "OpenDataNoticeFileType", "GENERATE_OPENDATA", "MIN_DATE", "/opendata"]:
        for m in list(re.finditer(re.escape(voti), t))[:4]:
            kirjuta("js", voti=voti, umbrus=t[max(0, m.start() - 150): m.end() + 250])


def lyhi(tag):
    return re.sub(r"\{[^}]+\}", "", tag)


def struktuur(aasta, kuu):
    url = f"{RHR}/opendata/notice/{aasta}/month/{kuu}/xml"
    st, ct, b = hae(url, timeout=300)
    kirjuta("rhr-fail", url=url, status=st, baite=len(b), algus=b[:300].decode("utf-8", "replace"))
    if st != 200 or not b.startswith(b"<?xml"):
        return
    juur = ET.fromstring(b)
    tyybid = collections.Counter(lyhi(c.tag) for c in juur)
    kirjuta("rhr-tyybid", aasta=aasta, kuu=kuu, kokku=sum(tyybid.values()), tyybid=dict(tyybid))
    # teate alamtüübid (eForms NoticeSubType) ja vormi tüüp
    alam = collections.Counter()
    for c in juur:
        s = c.find(".//{*}NoticeSubType/{*}SubTypeCode")
        alam[(lyhi(c.tag), s.text if s is not None else None)] += 1
    kirjuta("rhr-alamtyybid", alam={f"{k[0]}:{k[1]}": v for k, v in alam.most_common(40)})
    # teede kataloog: mis teed esinevad mitmes teates + näidisväärtus
    teed = collections.Counter()
    naide = {}
    for c in list(juur)[:400]:
        nahtud = set()
        for el in c.iter():
            pass
        def kaime(el, tee):
            t = tee + "/" + lyhi(el.tag)
            if t not in nahtud:
                nahtud.add(t)
            if el.text and el.text.strip() and t not in naide:
                naide[t] = (el.attrib, el.text.strip()[:120])
            for k in el:
                kaime(k, t)
        kaime(c, "")
        teed.update(nahtud)
    huvi = [t for t in teed if re.search(r"(Name|Description|Note|ItemClassification|ProcurementType|"
                                           r"AwardingCriterion|Strategic|Innovat|TenderResult|ReceivedSubmission|"
                                           r"EstimatedOverall|PartyName|ContractingParty|ProcedureCode|"
                                           r"ContractFolderID|IssueDate|ID$|Amount|Statistics|Received)", t)]
    for t in sorted(huvi)[:400]:
        kirjuta("rhr-tee", tee=t, teateid=teed[t], naide=naide.get(t))


def ted_valjad():
    keha = {"query": "buyer-country=EST", "fields": ["zzz"], "limit": 1}
    st, ct, b = hae("https://api.ted.europa.eu/v3/notices/search", json.dumps(keha).encode(),
                    {"Content-Type": "application/json"})
    t = b.decode("utf-8", "replace")
    m = re.search(r"supported values are: ([^)]+)\)", t)
    koik = m.group(1).split(",") if m else []
    huvi = [v for v in koik if re.search(r"(?i)strateg|innovat|award-crit|submission|title|description|cpv|buyer-name|"
                                         r"buyer-legal|procedure-type|estimated-value|result-value|winner|notice-type|"
                                         r"framework|contract-nature|BT-06|BT-539|BT-541|BT-759", v)]
    kirjuta("ted-valjad", kokku=len(koik), huvi=sorted(huvi))


if __name__ == "__main__":
    for f, a in ((js_konstandid, ()), (ted_valjad, ()), (struktuur, (2024, 3)), (struktuur, (2023, 6)),
                 (struktuur, (2021, 6))):
        try:
            f(*a)
        except Exception as e:  # noqa: BLE001
            kirjuta(f.__name__ + "-viga", viga=repr(e))
    sys.exit(0)
