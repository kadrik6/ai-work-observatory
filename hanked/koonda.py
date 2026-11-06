"""Koondab mudeli tulemuse lehe andmeteks: aastanäitajad, hankimise viis, hankijad ja otsingu loend.

    python hanked/koonda.py --valjund valjund

Sisend: <valjund>/hanked.jsonl.gz, tulemus.jsonl.gz, hindamine.json.
Väljund: <valjund>/leht.json ja logiread "HANKED koond ...".

Mõisted (kõik on hanked, mitte lepingud ega eurod):
- AI- või andmehange: mudeli tõenäosus vähemalt 0,5 (mudel.py LAVI).
- Innovatsioonimärge: hankija märkis eVormil strateegilise hanke liigiks innovatsiooni ('inn-pur') või
  innovatsioonihanke liigi (BT-776). Vanemas vormingus seda välja ei olnud, seega ainult eVormide aastad.
- Hea hanke tunnused (OECD 2026 lk 41–49 ja Kadri plaan): kvaliteedikriteerium on olemas, pakkumusi on
  vähemalt 2, hange ei katkenud. Need on tunnused, mitte hinnang hanke tulemusele.
"""
import argparse
import collections
import gzip
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import reeglid as R  # noqa: E402
import tellija as T  # noqa: E402

RHR_LEHT = "https://riigihanked.riik.ee/rhr-web/#/procurement/{}/general-info"


def loe(p):
    with gzip.open(p, "rt", encoding="utf-8") as f:
        return [json.loads(x) for x in f]


voti = R.voti


def katkes(r):
    t = set(r.get("tulemused") or [])
    return bool(t) and "selec-w" not in t


def hea_tunnused(r):
    k = R.kriteeriumid(r.get("kriteeriumid"))
    return {
        "kvaliteet": k["ainult_hind"] is False,
        "mitu_pakkujat": (r.get("pakkumusi") or 0) >= 2,
        "ei_katkenud": r.get("tulemus_olemas") and not katkes(r),
    }


def hankimise_viis(rid):
    """Hindamiskriteeriumid ja konkurents hangete rühmas. Puuduvad väärtused jäetakse nimetajast välja."""
    kr = [R.kriteeriumid(r.get("kriteeriumid")) for r in rid]
    kriteeriumiga = [k for k in kr if k["ainult_hind"] is not None]
    kaalud = [k["kvaliteedi_kaal"] for k in kriteeriumiga if k["kvaliteedi_kaal"] is not None and not k["ainult_hind"]]
    pakk = [r["pakkumusi"] for r in rid if r.get("pakkumusi") is not None]
    tulemusega = [r for r in rid if r.get("tulemus_olemas")]
    return {
        "hankeid": len(rid),
        "kriteeriumid_teada": len(kriteeriumiga),
        "ainult_hind_osakaal": _o(sum(k["ainult_hind"] for k in kriteeriumiga), len(kriteeriumiga)),
        "kvaliteedi_kaal_mediaan": statistics.median(kaalud) if kaalud else None,
        "kvaliteedi_kaal_n": len(kaalud),
        "pakkumusi_teada": len(pakk),
        "pakkumusi_mediaan": statistics.median(pakk) if pakk else None,
        "uks_pakkuja_osakaal": _o(sum(p == 1 for p in pakk), len(pakk)),
        "tulemus_teada": len(tulemusega),
        "katkes_osakaal": _o(sum(katkes(r) for r in tulemusega), len(tulemusega)),
    }


def _o(a, b):
    return round(100 * a / b, 1) if b else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--valjund", default="valjund")
    a = ap.parse_args()
    v = Path(a.valjund)
    hanked = loe(v / "hanked.jsonl.gz")
    tul = {t["voti"]: t for t in loe(v / "tulemus.jsonl.gz")}
    hindamine = json.loads((v / "hindamine.json").read_text(encoding="utf-8"))
    for r in hanked:
        t = tul.get(voti(r), {})
        r["_p"], r["_silt"], r["_marksona"] = t.get("p"), t.get("silt", 0), t.get("marksona", 0)

    eforms_aastad = sorted({r["aasta"] for r in hanked if r["allikas"] == "eforms"})
    aastad = []
    for aasta in sorted({r["aasta"] for r in hanked}):
        rid = [r for r in hanked if r["aasta"] == aasta]
        ai = [r for r in rid if r["_silt"]]
        ef = [r for r in rid if r["allikas"] == "eforms"]
        aastad.append({
            "aasta": aasta,
            "hankeid": len(rid),
            "allikad": dict(collections.Counter(r["allikas"] for r in rid)),
            "ai_andmed": len(ai),
            "ai_andmed_osakaal": _o(len(ai), len(rid)),
            "marksonaloend": sum(r["_marksona"] for r in rid),
            "ai_marksonaga": sum(bool(R.marksonad(R.tekst(r))["ai"]) for r in ai),
            "eeldatav_maksumus_ai": round(sum(r.get("eeldatav_maksumus") or 0 for r in ai)),
            "eeldatav_maksumus_teada_ai": sum(r.get("eeldatav_maksumus") is not None for r in ai),
            "innovatsioonimark": sum(R.innovatsiooni_mark(r) for r in ef) if ef else None,
            "innovatsioonimark_osakaal": _o(sum(R.innovatsiooni_mark(r) for r in ef), len(ef)) if ef else None,
            "eforms_hankeid": len(ef),
        })

    ai_koik = [r for r in hanked if r["_silt"]]
    viimased = [r for r in hanked if r["aasta"] >= (max(eforms_aastad) - 2 if eforms_aastad else 0)]
    viis = {
        "periood": [min(r["aasta"] for r in viimased), max(r["aasta"] for r in viimased)] if viimased else None,
        "ai_andmed": hankimise_viis([r for r in viimased if r["_silt"]]),
        "it_muud": hankimise_viis([r for r in viimased if not r["_silt"] and R.cpv_ruhm(r.get("cpv"))["it"]]),
        "koik": hankimise_viis(viimased),
    }

    hankijad = collections.Counter(r.get("hankija") or "?" for r in ai_koik)
    jarjest = hankijad.most_common()
    top10 = max(1, round(len(jarjest) * 0.1))
    kontsentratsioon = {"hankijaid": len(jarjest), "top10_protsenti_hankijaid": top10,
                        "nende_osakaal": _o(sum(n for _, n in jarjest[:top10]), len(ai_koik)),
                        "uks_hange_hankijaid": sum(1 for _, n in jarjest if n == 1)}

    loend = []
    for r in sorted(ai_koik, key=lambda r: (r.get("esimene_kuupaev") or r.get("kuu") or ""), reverse=True):
        k = R.kriteeriumid(r.get("kriteeriumid"))
        h = hea_tunnused(r)
        m = R.marksonad(R.tekst(r))
        loend.append({
            "id": voti(r), "a": r["aasta"], "kp": r.get("esimene_kuupaev"), "t": r.get("pealkiri"),
            "k": (R.tekst(r, 600) or "")[len(r.get("pealkiri") or ""):].strip()[:420],
            "h": r.get("hankija"), "cpv": (r.get("cpv") or [])[:3], "v": r.get("eeldatav_maksumus"),
            "pk": r.get("pakkumusi"), "kv": k["kvaliteedi_kaal"], "ah": k["ainult_hind"],
            "kat": katkes(r) if r.get("tulemus_olemas") else None, "p": r["_p"],
            "ai": bool(m["ai"]), "inn": R.innovatsiooni_mark(r),
            "url": RHR_LEHT.format(r["rhr_id"]) if r.get("rhr_id") else None, "vn": r.get("viitenumber"),
            "hea": sum(bool(x) for x in h.values()),
        })
    # tehisaru uuringud ja mõjuanalüüsid (katseline, Kadri 5.11.2026)
    moju = []
    for r in hanked:
        m = R.moju_uuring(r)
        if m:
            moju.append((r, m))
    nimed = T.asutused(r.get("hankija") for r, _ in moju)
    moju_loend = []
    for r, m in sorted(moju, key=lambda x: (x[0].get("esimene_kuupaev") or x[0].get("kuu") or ""), reverse=True):
        kj, kja = T.kelle_jaoks(r.get("pealkiri"), r.get("hankija"), nimed)
        moju_loend.append({
            "id": voti(r), "a": r["aasta"], "kp": r.get("esimene_kuupaev"), "t": r.get("pealkiri"),
            "korraldaja": r.get("hankija"), "kelle_jaoks": kj, "kelle_allikas": kja,
            "cpv": (r.get("cpv") or [])[:3], "v": r.get("eeldatav_maksumus"),
            "url": RHR_LEHT.format(r["rhr_id"]) if r.get("rhr_id") else None,
            "tyyp": m["tyyp"], "cpv_73_79": m["cpv_73_79"], "uuring_pealkirjas": m["uuring_pealkirjas"],
            "sonad": m["sonad"], "ai_tuvastuses": bool(r["_silt"]),
        })
    moju_aastad = []
    for aasta in sorted({x["a"] for x in moju_loend}):
        rid = [x for x in moju_loend if x["a"] == aasta]
        moju_aastad.append({"aasta": aasta, "kokku": len(rid),
                            "tehisaru": sum(x["tyyp"] == "tehisaru" for x in rid),
                            "digi_automatiseerimine": sum(x["tyyp"] != "tehisaru" for x in rid),
                            "ai_tuvastuses": sum(x["ai_tuvastuses"] for x in rid),
                            "eeldatav_maksumus": round(sum(x["v"] or 0 for x in rid))})
    moju_koond = {"silt": "katseline", "aastad": moju_aastad, "loend": moju_loend}

    leht = {"aastad": aastad, "eforms_aastad": eforms_aastad, "hankimise_viis": viis,
            "kontsentratsioon": kontsentratsioon, "hankijad_top": jarjest[:15], "hindamine": hindamine,
            "loend": loend, "moju": moju_koond}
    (v / "leht.json").write_text(json.dumps(leht, ensure_ascii=False), encoding="utf-8")
    kirjuta = lambda osa, **kw: print("HANKED", osa, json.dumps(kw, ensure_ascii=False), flush=True)  # noqa: E731
    kirjuta("koond-aastad", read=aastad)
    kirjuta("koond-viis", **viis)
    kirjuta("koond-kontsentratsioon", **kontsentratsioon, top=jarjest[:15])
    kirjuta("koond-loend", n=len(loend))
    kirjuta("moju-aastad", silt="katseline", read=moju_aastad)
    # diagnostika: otsi registrist sõnu failist otsi.txt (üks sõna real), et näha, miks hange tuvastusest välja jäi
    otsi_fail = Path(__file__).with_name("otsi.txt")
    sonad = [s.strip().lower() for s in otsi_fail.read_text(encoding="utf-8").splitlines()
             if s.strip() and not s.startswith("#")] if otsi_fail.exists() else []
    for r in hanked:
        t = R.normaliseeri(R.tekst(r)) + " " + (r.get("viitenumber") or "").lower()
        leitud = [s for s in sonad if s in t]
        if leitud:
            kirjuta("otsing", sonad=leitud, id=voti(r), aasta=r["aasta"], hankija=r.get("hankija"),
                    pealkiri=r.get("pealkiri"), cpv=r.get("cpv"), vn=r.get("viitenumber"), allikas=r.get("allikas"),
                    p=r.get("_p"), silt=r.get("_silt"), marksonad=R.marksonad(R.tekst(r)), moju=R.moju_uuring(r))


if __name__ == "__main__":
    main()
