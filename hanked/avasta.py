"""Ühekordne avastus: mis väljad ja failid on TED-i API-s, riigihangete registri avaandmetes ja OpenTenderis.

Käivitub GitHub Actionsis (liivakast ei pääse nendele aadressidele). Prindib logisse read "AVASTA <osa> ...".
"""
import gzip
import json
import re
import subprocess
import sys
import urllib.request


def hae(url, data=None, headers=None, limit=4000, timeout=60):
    h = {"Accept": "*/*"}  # vaikimisi User-Agent (repo reegel: ära võltsi)
    h.update(headers or {})
    req = urllib.request.Request(url, data=data, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read()
            return r.status, r.headers.get("Content-Type"), body
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get("Content-Type"), e.read()[:limit]
    except Exception as e:  # noqa: BLE001
        return None, None, str(e).encode()


def kirjuta(osa, **kw):
    print("AVASTA", osa, json.dumps(kw, ensure_ascii=False)[:6000], flush=True)


def ted():
    url = "https://api.ted.europa.eu/v3/notices/search"
    proovid = [
        ["publication-number", "notice-title", "publication-date", "buyer-name", "buyer-country", "classification-cpv",
         "notice-type", "description-lot", "title-lot", "title-proc", "description-proc"],
        ["award-criterion-type-lot", "award-criterion-weight-lot", "award-criterion-name-lot", "procedure-type",
         "estimated-value-lot", "result-value-lot", "received-submissions-type-val", "strategic-procurement-lot",
         "innovative-acquisition-lot", "contract-nature", "buyer-legal-type", "links"],
    ]
    for i, valjad in enumerate(proovid):
        keha = {"query": "buyer-country=EST AND publication-date>=20240101", "fields": valjad, "page": 1, "limit": 3,
                "paginationMode": "PAGE_NUMBER"}
        st, ct, b = hae(url, json.dumps(keha).encode(), {"Content-Type": "application/json", "Accept": "application/json"})
        kirjuta(f"ted-{i}", status=st, ct=ct, keha=b.decode("utf-8", "replace")[:5000])
    # kui palju Eesti teateid aastas
    for a in (2016, 2019, 2022, 2024, 2025):
        keha = {"query": f"buyer-country=EST AND publication-date>={a}0101 AND publication-date<={a}1231",
                "fields": ["publication-number"], "page": 1, "limit": 1, "paginationMode": "PAGE_NUMBER"}
        st, ct, b = hae(url, json.dumps(keha).encode(), {"Content-Type": "application/json", "Accept": "application/json"})
        try:
            n = json.loads(b).get("totalNoticeCount")
        except Exception:  # noqa: BLE001
            n = b[:300].decode("utf-8", "replace")
        kirjuta("ted-maht", aasta=a, status=st, teateid=n)


def register():
    st, ct, b = hae("https://riigihanked.riik.ee/rhr-web/", limit=100000)
    html = b.decode("utf-8", "replace")
    kirjuta("rhr-avaleht", status=st, ct=ct, pikkus=len(html), algus=html[:600])
    skriptid = re.findall(r'src="([^"]+\.js)"', html)
    kirjuta("rhr-skriptid", skriptid=skriptid)
    leitud = set()
    for s in skriptid:
        u = s if s.startswith("http") else "https://riigihanked.riik.ee/rhr-web/" + s.lstrip("/")
        st, ct, b = hae(u, limit=10**8)
        t = b.decode("utf-8", "replace")
        for m in re.findall(r"[\"'`](/?(?:rhr/)?api/[^\"'`\s]{3,120})[\"'`]", t):
            leitud.add(m)
        for m in re.findall(r"[\"'`]([^\"'`\s]*open-?data[^\"'`\s]*)[\"'`]", t, flags=re.I):
            leitud.add(m)
    kirjuta("rhr-api-teed", n=len(leitud), teed=sorted(leitud)[:300])
    for u in ["https://riigihanked.riik.ee/rhr/api/public/v1/opendata/notice/2024/month/1/xml",
              "https://riigihanked.riik.ee/rhr/api/public/v1/opendata/notice/2024/month/1/json",
              "https://riigihanked.riik.ee/rhr/api/public/v1/opendata",
              "https://riigihanked.riik.ee/rhr-web/#/open-data"]:
        st, ct, b = hae(u, limit=1500)
        kirjuta("rhr-proov", url=u, status=st, ct=ct, pikkus=len(b), algus=b[:800].decode("utf-8", "replace"))


def opentender():
    u = "https://data.open-contracting.org/en/publication/50/download?name=2023.jsonl.gz"
    st, ct, b = hae(u, limit=10**9, timeout=120)
    kirjuta("ot-2023", status=st, ct=ct, baite=len(b))
    if st == 200:
        read = gzip.decompress(b).decode("utf-8").splitlines()
        kirjuta("ot-2023-read", n=len(read))
        if read:
            r = json.loads(read[0])
            kirjuta("ot-naide", votmed=list(r.keys()), algus=json.dumps(r, ensure_ascii=False)[:4000])


if __name__ == "__main__":
    for f in (ted, register, opentender):
        try:
            f()
        except Exception as e:  # noqa: BLE001
            kirjuta(f.__name__ + "-viga", viga=repr(e))
    sys.exit(0)
