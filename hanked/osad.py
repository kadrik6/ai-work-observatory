"""Ühe pakkumuse riskimudel, 1. samm: osa tasemel põhitabel, andmekontrollid ja mudelid M0–M2.

    python hanked/osad.py --valjund valjund [--test]

Sisend: <valjund>/hanked.jsonl.gz (lae.py põhitabel: hanketeate osad `osade_info`, tulemusteate osad
`osade_pakkumusi`). Plaan: /mnt/project-files/kursus/projekt/ehitus/samm1-plaan.md (kursuse projektiplaan v3).

- Üks rida = üks hanke osa. Osa seotakse tulemusteatega osa numbri järgi (LOT-0001 ja "1" on sama osa).
  Kui hankel on üks osa, võetakse kõigi tulemuste suurim pakkumuste arv ka ilma osa numbrita.
- Sihttunnus: 1 = üks pakkumus, 0 = kaks või rohkem. Null pakkumust ja puuduv arv on eraldi ega lähe mudelisse.
- Tunnused tulevad ainult hanketeatest (mitte tulemusteatest), muidu õpiks mudel tulemusest.
- Jaotus: treening 2017–2023, valideerimine 2024, test 2025. Testi tulemus arvutatakse ainult lipuga --test.
- M0: CPV-grupi (2 numbrit) ühe pakkumuse määr treeningandmetes, harv grupp liigub üldmäära poole.
  M1: logistiline regressioon turu tunnustega. M2: M1 + hanke ülesehituse tunnused.
- Hindamine: PR-AUC, Brieri skoor, kalibreeritus (10 võrdse suurusega kasti, suurim vahe protsendipunktides)
  ning 95% vahemik hanke tasandil rühmitatud bootstrapist (hange võetakse koos kõigi oma osadega).

Väljund: logiread "HANKED riski-...". Andmeid repo ei kirjutata.
"""
import argparse
import datetime as dt
import gzip
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path

TREENING = range(2017, 2024)
VALIDEERIMINE = 2024
TEST = 2025
SILUMINE = 20  # M0: nii mitu "näilist" osa üldmääraga lisatakse igale CPV-grupile

MENETLUS = {
    "open": "avatud", "PT_OPEN": "avatud",
    "restricted": "piiratud", "PT_RESTRICTED": "piiratud",
    "neg-w-call": "väljakuulutamisega läbirääkimine", "PT_COMPETITIVE_NEGOTIATION": "väljakuulutamisega läbirääkimine",
    "PT_NEGOTIATED_WITH_PRIOR_CALL": "väljakuulutamisega läbirääkimine",
    "neg-wo-call": "väljakuulutamiseta läbirääkimine", "PT_NEGOTIATED_WITHOUT_PUBLICATION": "väljakuulutamiseta läbirääkimine",
    "PT_AWARD_CONTRACT_WITHOUT_CALL": "väljakuulutamiseta läbirääkimine",
    "comp-dial": "võistlev dialoog", "PT_COMPETITIVE_DIALOGUE": "võistlev dialoog",
    "innovation": "innovatsioonipartnerlus", "PT_INNOVATION_PARTNERSHIP": "innovatsioonipartnerlus",
}


def kirjuta(osa, **kw):
    print("HANKED", osa, json.dumps(kw, ensure_ascii=False), flush=True)


def hanke_voti(r):
    return r.get("viitenumber") or r.get("rhr_id") or r.get("teate_id")


def osa_voti(x):
    """Osa tunnus võrreldaval kujul: "LOT-0001", "1" ja "Osa 1" → "1". Ilma numbrita tunnus jääb samaks."""
    if x is None:
        return None
    x = str(x).strip()
    if x.startswith("#"):
        return x
    m = re.search(r"\d+", x)
    return str(int(m.group())) if m else x.lower()


def siht(p):
    """Pakkumuste arv → 1 (üks), 0 (kaks või rohkem), "null" või "puudub"."""
    if p is None:
        return "puudub"
    if p == 0:
        return "null"
    return 1 if p == 1 else 0


# ---------------------------------------------------------------- põhitabel

def osade_tabel(hanked):
    """Hanke read → (osade read, ainult tulemusteates olevate osade arv (aasta, allikas) kaupa)."""
    read, ainult_can, naited = [], Counter(), defaultdict(list)
    for h in hanked:
        info = h.get("osade_info") or []
        if not info:
            info = [{"osa": "#1", "cpv": None, "maksumus": None, "kriteeriumid": [], "tahtaeg": None}]
        can = {}
        for k, n in (h.get("osade_pakkumusi") or {}).items():
            kk = osa_voti(k)
            can[kk] = max(can.get(kk, 0), n)
        tul = {}
        for k, t in (h.get("osade_tulemus") or {}).items():
            if tul.get(osa_voti(k)) != "selec-w":
                tul[osa_voti(k)] = t
        uks = len(info) == 1
        hm = h.get("eeldatav_maksumus")
        kasutatud, seostamata = set(), []
        for o in info:
            k = osa_voti(o.get("osa"))
            osa_tul = tul.get(k) or (next(iter(tul.values())) if uks and len(tul) == 1 else None)
            if k in can:
                p, sid = can[k], "seotud"
                kasutatud.add(k)
            elif uks and can:
                p, sid = max(can.values()), "üks osa"
                kasutatud.update(can)
            elif osa_tul:
                p, sid = None, "tulemus olemas, arv puudub"
                kasutatud.add(k)
            else:
                p, sid = None, "ainult hanketeates" if h.get("tulemus_olemas") else "tulemus puudub"
                if h.get("tulemus_olemas"):
                    seostamata.append(o.get("osa"))
            cpv_h = (h.get("cpv") or [None])[0]
            m, tuletatud = o.get("maksumus"), False
            if m is None and hm:
                m, tuletatud = hm / len(info), not uks
            read.append({
                "hange": f'{h.get("allikas")}:{hanke_voti(h)}',
                "allikas": h.get("allikas"),
                "aasta": h.get("aasta"),
                "kuupaev": (h.get("esimene_kuupaev") or h.get("kuupaev") or "")[:10] or None,
                "osa": o.get("osa"),
                "osade_arv": len(info),
                "cpv": o.get("cpv") or cpv_h,
                "maksumus": m,
                "maksumus_tuletatud": tuletatud,
                "kriteeriumid": o.get("kriteeriumid") or (h.get("kriteeriumid") if uks else []) or [],
                "kriteeriumid_dokumendis": bool(o.get("kriteeriumid_dokumendis")),
                "osa_tulemus": osa_tul,
                "tahtaeg": o.get("tahtaeg"),
                "menetlus": h.get("menetlus"),
                "liik": h.get("liik"),
                "hankija_liik": h.get("hankija_liik"),
                "sidumine": sid,
                "pakkumusi": p,
                "siht": siht(p),
            })
        v = (h.get("aasta"), h.get("allikas"))
        if uks and (can or tul) and read[-1]["sidumine"] != "ainult hanketeates":
            kasutatud |= set(can) | set(tul)
        yle = sorted((set(can) | set(tul)) - kasutatud)
        ainult_can[v] += len(yle)
        if (seostamata or yle) and len(naited[v]) < 4:
            naited[v].append({"hange": hanke_voti(h), "hanketeate_osad": [o.get("osa") for o in info][:8],
                              "tulemuse_osad": sorted(set(h.get("osade_pakkumusi") or {}) | set(h.get("osade_tulemus") or {}))[:8],
                              "seostamata": seostamata[:8]})
    osade_tabel.naited = dict(naited)
    return read, ainult_can


def sidumise_kontroll(read, ainult_can):
    """(aasta, allikas) → osade arv sidumise viisi järgi ja seotud osakaal tulemusega hangete osades."""
    c = defaultdict(Counter)
    for r in read:
        c[(r["aasta"], r["allikas"])][r["sidumine"]] += 1
    valja = {}
    for v, k in c.items():
        tulemusega = k["seotud"] + k["üks osa"] + k["tulemus olemas, arv puudub"] + k["ainult hanketeates"]
        valja[v] = {**dict(k), "ainult tulemusteates": ainult_can.get(v, 0),
                    "seotud_osakaal": round((k["seotud"] + k["üks osa"] + k["tulemus olemas, arv puudub"]) / tulemusega, 3)
                    if tulemusega else None}
    return valja


# ---------------------------------------------------------------- tunnused

def _paevi(algus, lopp):
    try:
        return (dt.date.fromisoformat(lopp[:10]) - dt.date.fromisoformat(algus[:10])).days
    except (TypeError, ValueError):
        return None


def _vahemik(x, piirid):
    """Väärtuse vahemiku nimi, nt piirid (10, 20) → "≤10", "≤20", ">20"."""
    for p in piirid:
        if x <= p:
            return f"≤{p}"
    return f">{piirid[-1]}"


def tunnused(r, ylesehitus=True, aasta=True, paindlik=True):
    """Ainult hanketeate väljad. Turg: CPV-grupp, maksumus, aasta. Ülesehitus: tähtaeg, osade arv, kriteeriumid, menetlus.

    paindlik=True (samm 1b) lisab CPV 3 numbri täpsusega ning maksumuse ja tähtaja vahemikud, sest seos ei pruugi olla sirge.
    """
    cpv = r.get("cpv") or ""
    t = {"cpv2=" + (cpv[:2] or "puudub"): 1.0}
    if paindlik and cpv:
        t["cpv3=" + cpv[:3]] = 1.0
    m = r.get("maksumus")
    if m is not None and m > 0:
        t["log_maksumus"] = math.log10(m)
        if paindlik:
            t["maksumus=" + _vahemik(m, (10000, 30000, 60000, 140000, 500000, 2000000))] = 1.0
            if r.get("maksumus_tuletatud"):
                t["maksumus_tuletatud"] = 1.0
    else:
        t["maksumus_puudub"] = 1.0
    if aasta:
        t["aasta"] = float(r["aasta"] - 2020)
    if not ylesehitus:
        return t
    p = _paevi(r.get("kuupaev"), r.get("tahtaeg"))
    if p is not None and 0 <= p <= 365:
        t["tahtaeg_paevi"] = float(min(p, 90))
        if paindlik:
            t["tahtaeg=" + _vahemik(p, (7, 10, 14, 21, 30, 45))] = 1.0
    else:
        t["tahtaeg_puudub"] = 1.0
    t["log_osade_arv"] = math.log(r.get("osade_arv") or 1)
    kr = r.get("kriteeriumid") or []
    if not kr and paindlik and r.get("kriteeriumid_dokumendis"):
        t["kriteeriumid_dokumendis"] = 1.0
    elif not kr:
        t["kriteeriumid_puuduvad"] = 1.0
    elif all(k[0] == "price" for k in kr):
        t["ainult_hind"] = 1.0
    else:
        kaalud = [k[1] for k in kr]
        if all(k is not None for k in kaalud) and sum(kaalud) > 0:
            t["hinna_kaal"] = sum(k[1] for k in kr if k[0] == "price") / sum(kaalud)
        else:
            t["hinna_kaal_puudub"] = 1.0
    t["menetlus=" + MENETLUS.get(r.get("menetlus") or "", "muu")] = 1.0
    return t


# ---------------------------------------------------------------- puuduvus

def puuduvuse_vordlus(read):
    """Aasta kaupa: osad, mille pakkumuste arv on teada, vs osad, mille arv puudub (keskmised tunnused)."""
    def kirjelda(g):
        n = len(g)
        if not n:
            return {"n": 0}
        mk = sorted(r["maksumus"] for r in g if r.get("maksumus"))
        return {"n": n,
                "maksumuse_mediaan": round(mk[len(mk) // 2]) if mk else None,
                "maksumus_teada": round(len(mk) / n, 3),
                "avatud": round(sum(MENETLUS.get(r.get("menetlus") or "") == "avatud" for r in g) / n, 3),
                "teenus": round(sum(r.get("liik") == "services" for r in g) / n, 3),
                "mitme_osaga": round(sum(r["osade_arv"] > 1 for r in g) / n, 3),
                "it_cpv72_48": round(sum((r.get("cpv") or "")[:2] in ("72", "48") for r in g) / n, 3)}
    valja = {}
    for a in sorted({r["aasta"] for r in read}):
        g = [r for r in read if r["aasta"] == a]
        valja[a] = {"teada": kirjelda([r for r in g if r["siht"] in (0, 1)]),
                    "null": len([r for r in g if r["siht"] == "null"]),
                    "puudub": kirjelda([r for r in g if r["siht"] == "puudub"])}
    return valja


# ---------------------------------------------------------------- mudelid ja hindamine

def m0_maarad(treening):
    """CPV-grupi ühe pakkumuse määr, silutud üldmäära poole."""
    k, n = Counter(), Counter()
    for r in treening:
        g = (r.get("cpv") or "")[:2]
        n[g] += 1
        k[g] += r["siht"]
    yld = sum(k.values()) / max(sum(n.values()), 1)
    return {g: (k[g] + SILUMINE * yld) / (n[g] + SILUMINE) for g in n}, yld


def m0_ennusta(maarad, yld, read):
    return [maarad.get((r.get("cpv") or "")[:2], yld) for r in read]


def logreg(treening, hinnatavad, **kw):
    from sklearn.feature_extraction import DictVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    mudel = make_pipeline(DictVectorizer(sparse=False), StandardScaler(), LogisticRegression(max_iter=2000, C=1.0))
    mudel.fit([tunnused(r, **kw) for r in treening], [r["siht"] for r in treening])
    return [list(mudel.predict_proba([tunnused(r, **kw) for r in h])[:, 1]) for h in hinnatavad]


def kalibreeritus(y, p, kaste=10):
    """Suurim |keskmine tõenäosus − tegelik osakaal| protsendipunktides, võrdse suurusega kastides."""
    jarj = sorted(range(len(p)), key=lambda i: p[i])
    if not jarj:
        return None
    suurim = 0.0
    for b in range(kaste):
        kast = jarj[b * len(jarj) // kaste:(b + 1) * len(jarj) // kaste]
        if kast:
            suurim = max(suurim, abs(sum(p[i] for i in kast) / len(kast) - sum(y[i] for i in kast) / len(kast)))
    return round(100 * suurim, 1)


def hinda(y, ennustused, grupid, kordi=1000, seeme=1):
    """ennustused: {nimi: [p]}. Tagastab punkthinnangud ja 95% vahemikud (rühmitatud bootstrap)."""
    import numpy as np
    from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
    y = np.asarray(y)
    P = {k: np.asarray(v) for k, v in ennustused.items()}
    tulemus = {"n": int(len(y)), "uks_pakkumus": int(y.sum()), "osakaal": round(float(y.mean()), 3)}
    for k, p in P.items():
        tulemus[k] = {"pr_auc": round(float(average_precision_score(y, p)), 3),
                      "roc_auc": round(float(roc_auc_score(y, p)), 3),
                      "brier": round(float(brier_score_loss(y, p)), 4),
                      "kalibreeritus_pp": kalibreeritus(list(y), list(p)),
                      "keskmine_ennustus": round(float(p.mean()), 3)}
    idx = defaultdict(list)
    for i, g in enumerate(grupid):
        idx[g].append(i)
    ryhmad = [np.asarray(v) for v in idx.values()]
    rng = np.random.default_rng(seeme)
    nimed = list(P)
    paarid = [(a, b) for i, a in enumerate(nimed) for b in nimed[i + 1:]]
    jaotus = defaultdict(list)
    for _ in range(kordi):
        valik = np.concatenate([ryhmad[j] for j in rng.integers(0, len(ryhmad), len(ryhmad))])
        yy = y[valik]
        if yy.min() == yy.max():
            continue
        ap = {k: average_precision_score(yy, P[k][valik]) for k in nimed}
        for k in nimed:
            jaotus[k].append(ap[k])
        for a, b in paarid:
            jaotus[f"{b}-{a}"].append(ap[b] - ap[a])
    for k, v in jaotus.items():
        lo, hi = np.percentile(v, [2.5, 97.5])
        rida = {"vahemik_95": [round(float(lo), 3), round(float(hi), 3)]}
        if k in tulemus:
            tulemus[k]["pr_auc_vahemik_95"] = rida["vahemik_95"]
        else:
            a, b = k.split("-")[1], k.split("-")[0]
            tulemus[k] = {"pr_auc_vahe": round(tulemus[b]["pr_auc"] - tulemus[a]["pr_auc"], 3), **rida,
                          "jareldus": "pole piisavalt tõendeid" if lo <= 0 <= hi else ("suurem" if lo > 0 else "väiksem")}
    tulemus["bootstrap"] = {"kordi": len(jaotus[nimed[0]]) if nimed else 0, "hankeid": len(ryhmad)}
    return tulemus


def mudelid(read, test=False):
    """Treenib M0–M2 aastatel 2017–2023 ja hindab 2024 (ja lipuga ka 2025)."""
    sobiv = [r for r in read if r["siht"] in (0, 1)]
    treening = [r for r in sobiv if r["aasta"] in TREENING]
    hinnata = {"valideerimine_2024": [r for r in sobiv if r["aasta"] == VALIDEERIMINE]}
    if test:
        hinnata["test_2025"] = [r for r in sobiv if r["aasta"] == TEST]
    hinnata = {k: v for k, v in hinnata.items() if v and len({r["siht"] for r in v}) == 2}
    if not treening or not hinnata:
        return {"viga": "treening- või hindamisandmeid pole", "treening": len(treening)}
    maarad, yld = m0_maarad(treening)
    hh = list(hinnata.values())
    m1 = logreg(treening, hh, ylesehitus=False)
    m2 = logreg(treening, hh, ylesehitus=True)
    # võrdlused ainult punkthinnanguna (valideerimisel valiku tegemiseks, mitte järelduseks)
    lisad = {"M2_ilma_aastata": logreg(treening, hh, aasta=False),
             "M2_samm1_tunnused": logreg(treening, hh, paindlik=False)}
    eforms = [r for r in treening if r["allikas"] == "eforms"]
    if len({r["siht"] for r in eforms}) == 2:
        lisad["M2_ainult_evormid"] = logreg(eforms, hh, aasta=False)
    valja = {"treening": {"n": len(treening), "uks_pakkumus": sum(r["siht"] for r in treening), "yldmaar": round(yld, 3),
                          "evormides": len(eforms)}}
    for j, (nimi, h) in enumerate(hinnata.items()):
        e = {"M0": m0_ennusta(maarad, yld, h), "M1": m1[j], "M2": m2[j]}
        valja[nimi] = hinda([r["siht"] for r in h], e, [r["hange"] for r in h])
        for k, pp in lisad.items():
            valja[nimi][k] = hinda([r["siht"] for r in h], {k: pp[j]}, [r["hange"] for r in h], kordi=0)[k]
    return valja


def skeemi_kontroll(read):
    """Skeemi vahetus: ühe pakkumuse määr aasta ja skeemi kaupa ning tunnused, mille osakaal erineb treeningu
    TED-osade ja valideerimisaasta vahel kõige rohkem."""
    sobiv = [r for r in read if r["siht"] in (0, 1)]
    maarad = defaultdict(lambda: [0, 0])
    for r in sobiv:
        maarad[(r["aasta"], r["allikas"])][0] += r["siht"]
        maarad[(r["aasta"], r["allikas"])][1] += 1
    def keskm(g):
        """Iga tunnuse osakaal ridadest, kus see on olemas (arvtunnusel: kus väärtus on teada)."""
        c = Counter(k for r in g for k in tunnused(r) if not k.startswith("cpv3="))
        return {k: x / max(len(g), 1) for k, x in c.items()}
    ted = keskm([r for r in sobiv if r["aasta"] in TREENING and r["allikas"] == "ted_esender"])
    val = keskm([r for r in sobiv if r["aasta"] == VALIDEERIMINE])
    vahe = sorted(set(ted) | set(val), key=lambda k: -abs(ted.get(k, 0) - val.get(k, 0)))[:15]
    return {"uks_pakkumus": {f"{a} {s}": [k, n, round(k / n, 3)] for (a, s), (k, n) in sorted(maarad.items())},
            "suurimad_erinevused": {k: [round(ted.get(k, 0), 3), round(val.get(k, 0), 3)] for k in vahe},
            "menetlus": {s: dict(Counter(r.get("menetlus") for r in sobiv if r["allikas"] == s).most_common(12))
                         for s in ("ted_esender", "eforms")}}


# ---------------------------------------------------------------- käivitus

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--valjund", default="valjund")
    ap.add_argument("--test", action="store_true", help="arvuta ka testiaasta 2025 tulemus (ainult pärast mudeli valikut)")
    a = ap.parse_args()
    with gzip.open(Path(a.valjund) / "hanked.jsonl.gz", "rt", encoding="utf-8") as f:
        hanked = [json.loads(x) for x in f]
    read, ainult_can = osade_tabel(hanked)
    kirjuta("riski-osad", osi=len(read), hankeid=len(hanked),
            aastad=dict(sorted(Counter(r["aasta"] for r in read).items())))
    for (aasta, allikas), c in sorted(sidumise_kontroll(read, ainult_can).items()):
        kirjuta("riski-sidumine", aasta=aasta, allikas=allikas, **c)
    for (aasta, allikas), n in sorted(getattr(osade_tabel, "naited", {}).items()):
        kirjuta("riski-sidumine-naide", aasta=aasta, allikas=allikas, naited=n)
    tul = defaultdict(Counter)
    for r in read:
        if r["sidumine"] in ("tulemus olemas, arv puudub", "seotud", "üks osa"):
            tul[(r["aasta"], r["allikas"])][f'{r["sidumine"]}: {r.get("osa_tulemus")}'] += 1
    for (aasta, allikas), c in sorted(tul.items()):
        kirjuta("riski-osa-tulemus", aasta=aasta, allikas=allikas, **dict(c.most_common(8)))
    for aasta, c in puuduvuse_vordlus(read).items():
        kirjuta("riski-puuduvus", aasta=aasta, **c)
    tt = defaultdict(Counter)
    for r in read:
        t = tunnused(r)
        tt[r["aasta"]]["osi"] += 1
        for k in ("tahtaeg_puudub", "maksumus_puudub", "maksumus_tuletatud", "kriteeriumid_puuduvad", "kriteeriumid_dokumendis"):
            tt[r["aasta"]][k] += k in t
    for aasta, c in sorted(tt.items()):
        kirjuta("riski-tunnuste-taitumus", aasta=aasta, **c)
    kirjuta("riski-skeem", **skeemi_kontroll(read))
    kirjuta("riski-mudelid", test=a.test, **mudelid(read, test=a.test))


if __name__ == "__main__":
    main()
