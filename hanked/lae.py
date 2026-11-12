"""Laeb riigihangete registri avaandmed kuude kaupa ja koostab põhitabeli (üks rida = üks hange).

    python hanked/lae.py --valjund valjund [--algus 2017-09] [--lopp 2026-10]

Allikas: https://riigihanked.riik.ee/rhr/api/public/v1/opendata/{notice|notice_award}/AAAA/month/K/xml
(registri avaandmete leht, litsents CC BY-SA 3.0 EE). Toorfailid hoitakse gzipituna kaustas
<valjund>/toores/, et GitHub Actionsi vahemälu saaks neid korduskäivitustel kasutada. Kaks viimast kuud
laaditakse alati uuesti, sest register lisab hilinenud teateid.

Väljund:
- <valjund>/teated.jsonl.gz      kõik hanketeated (CN), üks rida teate kohta
- <valjund>/hanked.jsonl.gz      põhitabel: üks rida hanke kohta, viimane teateversioon + tulemus
- logiread "HANKED kuu {...}" ja "HANKED kokku {...}"
"""
import argparse
import datetime as dt
import gzip
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from parsi import DIAG, DIAG_NAITED, parsi_fail  # noqa: E402

BAAS = "https://riigihanked.riik.ee/rhr/api/public/v1/opendata"


def kuud(algus, lopp):
    a = dt.date(int(algus[:4]), int(algus[5:7]), 1)
    l = dt.date(int(lopp[:4]), int(lopp[5:7]), 1)
    while a <= l:
        yield a.year, a.month
        a = dt.date(a.year + (a.month == 12), a.month % 12 + 1, 1)


def hae(url, katseid=4):
    for i in range(katseid):
        try:
            req = urllib.request.Request(url, headers={"Accept": "application/xml"})
            with urllib.request.urlopen(req, timeout=300) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code in (404, 500) and i >= 1:
                return None
            time.sleep(2 ** (i + 1))
        except Exception:  # noqa: BLE001
            time.sleep(2 ** (i + 1))
    return None


def toorfail(kaust, tyyp, a, k, uuesti):
    p = kaust / f"{tyyp}-{a}-{k:02d}.xml.gz"
    if p.exists() and not uuesti:
        return gzip.decompress(p.read_bytes())
    sisu = hae(f"{BAAS}/{tyyp}/{a}/month/{k}/xml")
    if sisu is None or not sisu.lstrip().startswith(b"<?xml"):
        return None
    p.write_bytes(gzip.compress(sisu, 6))
    return sisu


def kirjuta(osa, **kw):
    print("HANKED", osa, json.dumps(kw, ensure_ascii=False), flush=True)


def hanke_voti(r):
    return r.get("viitenumber") or r.get("rhr_id") or r.get("teate_id")


def _versioon(v):
    """eVormi VersionID ("01", "2", "10") arvuna, et "10" tuleks pärast "9"."""
    return int(v) if v and str(v).isdigit() else 0


def pohitabel(cn, can):
    """Üks rida hanke kohta: viimane hanketeade (kuupäev, versioon) + kõigi tulemusteadete kokkuvõte."""
    hanked = {}
    for r in sorted(cn, key=lambda r: (r.get("kuupaev") or r.get("kuu") or "", _versioon(r.get("versioon")))):
        v = (r["allikas"], hanke_voti(r))
        esimene = hanked.get(v, {}).get("esimene_kuupaev") or r.get("kuupaev") or r.get("kuu")
        teateid = hanked.get(v, {}).get("teateid", 0) + 1
        hanked[v] = {**r, "esimene_kuupaev": esimene, "teateid": teateid}
    tulemus = {}
    for r in can:
        v = (r["allikas"], hanke_voti(r))
        t = tulemus.setdefault(v, {"pakkumusi": None, "osade_pakkumusi": {}, "osade_tulemus": {}, "tulemused": [], "voitjad": [], "lepingu_summa": None})
        if r.get("pakkumusi") is not None:
            t["pakkumusi"] = max(t["pakkumusi"] or 0, r["pakkumusi"])
        for osa, n in (r.get("osade_pakkumusi") or {}).items():
            t["osade_pakkumusi"][osa] = max(t["osade_pakkumusi"].get(osa, 0), n)
        for osa, k in (r.get("osade_tulemus") or {}).items():
            if t["osade_tulemus"].get(osa) != "selec-w":
                t["osade_tulemus"][osa] = k
        t["tulemused"] = sorted(set(t["tulemused"]) | set(x for x in r.get("tulemused", []) if x))
        t["voitjad"] = sorted(set(t["voitjad"]) | set(x for x in r.get("voitjad", []) if x))
        if r.get("lepingu_summa") is not None:
            t["lepingu_summa"] = (t["lepingu_summa"] or 0) + r["lepingu_summa"]
    valja = []
    for v, r in hanked.items():
        t = tulemus.get(v)
        r = dict(r)
        r["tulemus_olemas"] = t is not None
        r.update(t or {"pakkumusi": None, "osade_pakkumusi": {}, "osade_tulemus": {}, "tulemused": [], "voitjad": [], "lepingu_summa": None})
        r["aasta"] = int((r.get("esimene_kuupaev") or r["kuu"])[:4])
        valja.append(r)
    return valja


def osade_koond(rid):
    """Hanke osade (lot) ülevaade aasta ja allika kaupa: mitme osaga hanked ja osade tasemel pakkumuste arv."""
    koond = {}
    for r in rid:
        c = koond.setdefault((r["aasta"], r.get("allikas")), {
            "hankeid": 0, "osade_arv_teada": 0, "mitme_osaga": 0, "osi": 0,
            "hankeid_pakkumustega": 0, "osi_pakkumustega": 0, "osi_1_pakkumus": 0, "osi_0_pakkumust": 0,
            "hankeid_1_pakkumus": 0})
        c["hankeid"] += 1
        if r.get("osade_arv"):
            c["osade_arv_teada"] += 1
            c["osi"] += r["osade_arv"]
            c["mitme_osaga"] += r["osade_arv"] >= 2
        op = r.get("osade_pakkumusi") or {}
        c["osi_pakkumustega"] += len(op)
        c["osi_1_pakkumus"] += sum(n == 1 for n in op.values())
        c["osi_0_pakkumust"] += sum(n == 0 for n in op.values())
        if r.get("pakkumusi") is not None:
            c["hankeid_pakkumustega"] += 1
            c["hankeid_1_pakkumus"] += r["pakkumusi"] == 1
    return koond


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--valjund", default="valjund")
    ap.add_argument("--algus", default="2017-09")
    ap.add_argument("--lopp", default=None)
    a = ap.parse_args()
    tana = dt.date.today()
    lopp = a.lopp or f"{tana.year}-{tana.month:02d}"
    v = Path(a.valjund)
    toores = v / "toores"
    toores.mkdir(parents=True, exist_ok=True)
    koik = list(kuud(a.algus, lopp))
    uuesti_alates = koik[-2] if len(koik) >= 2 else koik[0]
    cn, can = [], []
    for aasta, kuu in koik:
        uuesti = (aasta, kuu) >= uuesti_alates
        info = {"kuu": f"{aasta}-{kuu:02d}"}
        for tyyp in ("notice", "notice_award"):
            sisu = toorfail(toores, tyyp, aasta, kuu, uuesti)
            if sisu is None:
                info[tyyp] = None
                continue
            c, n, vahele = parsi_fail(sisu, info["kuu"])
            cn.extend(c)
            can.extend(n)
            info[tyyp] = {"baite": len(sisu), "cn": len(c), "can": len(n), "vahele": vahele,
                          "vorming": (c or n or [{}])[0].get("allikas")}
        kirjuta("kuu", **info)
    hanked = pohitabel(cn, can)
    with gzip.open(v / "teated.jsonl.gz", "wt", encoding="utf-8") as f:
        for r in cn:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with gzip.open(v / "hanked.jsonl.gz", "wt", encoding="utf-8") as f:
        for r in hanked:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    aastad = {}
    for r in hanked:
        aastad.setdefault(r["aasta"], 0)
        aastad[r["aasta"]] += 1
    kirjuta("diagnostika", **dict(DIAG.most_common(40)))
    for n in DIAG_NAITED:
        kirjuta("diagnostika_naide", **n)
    pakk = {}
    for r in hanked:
        c = pakk.setdefault(r["aasta"], {"hankeid": 0, "tulemus": 0, "pakkumusi": 0})
        c["hankeid"] += 1
        c["tulemus"] += bool(r.get("tulemus_olemas"))
        c["pakkumusi"] += r.get("pakkumusi") is not None
    kirjuta("tulemuste_taitumus", **{str(k): v for k, v in sorted(pakk.items())})
    for (aasta, allikas), c in sorted(osade_koond(hanked).items()):
        kirjuta("osad", aasta=aasta, allikas=allikas, **c)
    kirjuta("kokku", hanketeateid=len(cn), tulemusteateid=len(can), hankeid=len(hanked),
            aastad=dict(sorted(aastad.items())))


if __name__ == "__main__":
    main()
