"""Põhitabeli kirjeldus (etapp 2: täidetus, katvus, duplikaadid) ja märgendamise valim (kihistatud).

    python hanked/kirjelda.py --valjund valjund

Väljund: logiread "HANKED kirjeldus ..." ja <valjund>/valim.jsonl (märgendamiseks, kihid + valikutõenäosus).
"""
import argparse
import collections
import gzip
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import reeglid as R  # noqa: E402

KIHID = {"marksona": 300, "it_cpv": 300, "muu": 300}  # mitu hanget igast kihist valimisse
SEEME = 20261104


def loe(p):
    with gzip.open(p, "rt", encoding="utf-8") as f:
        for rida in f:
            yield json.loads(rida)


def kiht(r):
    m = R.marksonad(R.tekst(r))
    if m["ai"] or m["andmed"]:
        return "marksona"
    if R.cpv_ruhm(r.get("cpv"))["it"]:
        return "it_cpv"
    return "muu"


def kirjuta(osa, **kw):
    print("HANKED", osa, json.dumps(kw, ensure_ascii=False), flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--valjund", default="valjund")
    ap.add_argument("--valim-logisse", action="store_true", help="kirjuta valimi read logisse (VALIM ...)")
    a = ap.parse_args()
    v = Path(a.valjund)
    hanked = list(loe(v / "hanked.jsonl.gz"))
    # täidetus aasta ja allika kaupa
    tab = collections.defaultdict(collections.Counter)
    for r in hanked:
        k = (r["aasta"], r["allikas"])
        c = tab[k]
        c["n"] += 1
        c["pealkiri"] += bool(r.get("pealkiri"))
        c["kirjeldus"] += bool(r.get("kirjeldus"))
        c["kirjeldus_50"] += len(r.get("kirjeldus") or "") >= 50
        c["cpv"] += bool(r.get("cpv"))
        c["kriteeriumid"] += bool(r.get("kriteeriumid"))
        c["kaal"] += any(kk is not None for _, kk in r.get("kriteeriumid") or [])
        c["hankija"] += bool(r.get("hankija"))
        c["tulemus"] += bool(r.get("tulemus_olemas"))
        c["pakkumusi"] += r.get("pakkumusi") is not None
        c["innovatsioon"] += R.innovatsiooni_mark(r)
        c["strateegiline_valja"] += bool(r.get("strateegiline"))
        c["viitenumber"] += bool(r.get("viitenumber"))
        c[kiht(r)] += 1
    for (aasta, allikas), c in sorted(tab.items()):
        kirjuta("taidetus", aasta=aasta, allikas=allikas, **c)
    # menetluse kirjeldused (kas väikehanked on sees) ja alamtüübid
    kirjuta("menetlused", top=collections.Counter(r.get("menetluse_kirjeldus") or r.get("menetlus")
                                                    for r in hanked).most_common(25))
    kirjuta("alamtyybid", top=collections.Counter(r.get("alamtyyp") for r in hanked).most_common(25))
    kirjuta("strateegilised", top=collections.Counter(x for r in hanked for x in (r.get("strateegiline") or [])
                                                        ).most_common(10),
            innov=collections.Counter(x for r in hanked for x in (r.get("innovatsioon") or [])).most_common(10))
    # märksõnad
    mk = collections.Counter()
    for r in hanked:
        m = R.marksonad(R.tekst(r))
        mk.update(m["ai"] + m["andmed"] + m["lai"])
    kirjuta("marksonad", top=mk.most_common(80))
    # kihistatud valim märgendamiseks. Ainult eVormide hanked (alates 09/2023): see on hindamise populatsioon.
    rnd = random.Random(SEEME)
    kihiti = collections.defaultdict(list)
    for r in hanked:
        if r.get("pealkiri") and r["allikas"] == "eforms":
            kihiti[kiht(r)].append(r)
    valim = []
    for k, n in KIHID.items():
        rid = kihiti[k]
        vali = rnd.sample(rid, min(n, len(rid)))
        p = len(vali) / len(rid) if rid else 0
        for r in vali:
            valim.append({"kiht": k, "valiku_toenaosus": p, "kihi_suurus": len(rid), "allikas": r["allikas"],
                          "voti": f"{r['allikas']}:{r.get('viitenumber') or r.get('rhr_id') or r.get('teate_id')}",
                          "aasta": r["aasta"], "hankija": r.get("hankija"), "cpv": (r.get("cpv") or [])[:4],
                          "pealkiri": r.get("pealkiri"), "tekst": R.tekst(r, 700),
                          "marksonad": R.marksonad(R.tekst(r))})
    with open(v / "valim.jsonl", "w", encoding="utf-8") as f:
        for r in valim:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    kirjuta("valim", kihid={k: len(kihiti[k]) for k in KIHID}, valimis=len(valim))
    # valim ka logisse, et seda saaks lugeda ka siis, kui artefakti alla laadida ei saa
    for r in valim if a.valim_logisse else []:
        print("VALIM", json.dumps(r, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
