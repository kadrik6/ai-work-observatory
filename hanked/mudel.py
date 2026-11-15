"""AI- ja andmehangete klassifikaator, hindamine märksõnaloendi vastu ja kogu registri märgendamine.

    python hanked/mudel.py --valjund valjund

Sisend: <valjund>/hanked.jsonl.gz (lae.py) ja hanked/margendid.csv (märgendatud kihistatud valim).
Mudel: TF-IDF (sõnad 1–2 + tähemärgid 3–5, mis katavad eesti keele käändeid) + logistiline regressioon.
Suurt keelemudelit ega vektorbaasi ei kasutata: andmeid on vähe ja tulemus peab olema korratav ja seletatav.

Hindamine (etapp 4):
- ajapõhine jaotus: treening kuni 2023, test 2024–2026 (mudel peab töötama tulevaste hangete peal);
- täpsus ja saagis kaalutakse kihi valikutõenäosusega, et need kehtiksid kogu registri, mitte valimi kohta;
- võrdlusalus on märksõnaloend (reeglid.py). Accuracy't ei kasutata, sest positiivseid on alla 1%.
- Võrreldakse nelja reeglit: mudel, märksõnaloend, OECD-laadne loend ja „mudel või märksõna“.
- Kogu registri silt tuleb lukustatud reeglist LEHE_REEGEL (Kadri otsus 15.11.2026: „mudel või märksõna“), et
  lehe arv ei kõiguks päevast päeva. Hindamine arvutab endiselt, milline reegel oleks parim (suurim F1, kuid
  märksõnaloend, kui vahe on alla 0,02), ja logib hoiatuse, kui see erineb lukustatud reeglist. Reegel muutub
  ainult siis, kui Kadri seda otsustab.
- Sõnavara valim (25 000 hanget) valitakse hanke võtme räsi järgi, mitte juhuslikult. Nii ei muuda uued
  teated valimit tervikuna, vaid lisavad või vahetavad üksikuid ridu.
- Hindamise populatsioon on eVormide hanked (alates 09/2023), sest valim on sealt võetud.

Väljund: <valjund>/tulemus.jsonl.gz (iga hanke tõenäosus ja silt), logiread "HANKED mudel ..." ja
"HANKED hindamine ...".
"""
import argparse
import csv
import gzip
import json
import math
import re
import sys
from pathlib import Path

import numpy as np
from scipy.sparse import hstack
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

sys.path.insert(0, str(Path(__file__).resolve().parent))
import reeglid as R  # noqa: E402

SIIN = Path(__file__).resolve().parent
POSITIIVNE = {"AI", "ANDMED"}
LAVI = 0.5
LIPP = re.compile(r"\bzzmark\w+")
VAIKE_VAHE = 0.02  # F1 vahe, millest väiksema korral soovitatakse lihtsamat reeglit
LEHE_REEGEL = "mudel_voi_marksona"  # lukustatud (Kadri 15.11.2026); muuta ainult tema otsusega
SONAVARA = 25000


def stabiilne_valim(votmed, n=SONAVARA):
    """n hanke indeksid, mille võtme räsi on väikseim. Uus hange muudab valimit kõige rohkem ühe rea võrra."""
    import hashlib
    jarj = sorted(range(len(votmed)), key=lambda i: hashlib.sha1(str(votmed[i]).encode("utf-8")).hexdigest())
    return sorted(jarj[:n])


def sisend(r):
    """Mudeli tekst: hanke tekst + CPV-tunnused sõnadena (CPV72, CPV7221) + märksõnaloendi tabamused
    tunnustena (zzmarkai jt), et mudel saaks õppida, millal märksõna eksib."""
    cpv = " ".join(f"CPV{c[:2]} CPV{c[:4]}" for c in (r.get("cpv") or [])[:6] if c)
    t = R.tekst(r, 1500)
    m = R.marksonad(t)
    lipud = " ".join(f"zzmark{k}" for k in ("ai", "andmed", "lai") if m[k])
    return R.normaliseeri(t) + " " + cpv + " " + lipud


class Mudel:
    def __init__(self, c=4.0):
        self.sonad = TfidfVectorizer(ngram_range=(1, 2), min_df=2, max_features=60000, sublinear_tf=True)
        self.margid = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), min_df=3, max_features=120000,
                                      sublinear_tf=True)
        self.lr = LogisticRegression(C=c, class_weight="balanced", max_iter=3000)

    def _x(self, tekstid, sobita=False):
        # märksõnalipud (zzmark...) on ainult sõnatunnused; tähemärgi-n-grammid neid ei näe
        ilma = [LIPP.sub(" ", t) for t in tekstid]
        if sobita:
            return hstack([self.sonad.fit_transform(tekstid), self.margid.fit_transform(ilma)]).tocsr()
        return hstack([self.sonad.transform(tekstid), self.margid.transform(ilma)]).tocsr()

    def sobita(self, tekstid, y, kaal=None, korpus=None):
        # sõnavara õpitakse kogu korpusest (märgendamata tekst on avalik ja mudel ei näe silte)
        if korpus is not None:
            self._x(list(korpus), sobita=True)
            x = self._x(tekstid)
        else:
            x = self._x(tekstid, sobita=True)
        self.lr.fit(x, y, sample_weight=kaal)
        return self

    def toenaosus(self, tekstid, partii=5000):
        tekstid = list(tekstid)
        osad = [self.lr.predict_proba(self._x(tekstid[i:i + partii]))[:, 1] for i in range(0, len(tekstid), partii)]
        return np.concatenate(osad) if osad else np.array([])

    def olulised(self, n=25):
        nimed = np.concatenate([self.sonad.get_feature_names_out(), self.margid.get_feature_names_out()])
        k = self.lr.coef_[0]
        jarjekord = np.argsort(k)
        return {"jah": [(nimed[i], round(float(k[i]), 2)) for i in jarjekord[::-1][:n]],
                "ei": [(nimed[i], round(float(k[i]), 2)) for i in jarjekord[:n]]}


def loe_margendid(p=SIIN / "margendid.csv"):
    with open(p, encoding="utf-8") as f:
        return [r for r in csv.DictReader(f) if r.get("silt") in POSITIIVNE | {"EI"}]


def kaalutud_moodikud(y, ennustus, kaal):
    """Täpsus, saagis ja F1, kus iga rida kaalutakse 1/valikutõenäosus (Horvitz–Thompson)."""
    y, e, w = np.asarray(y), np.asarray(ennustus), np.asarray(kaal, dtype=float)
    tp = float(np.sum(w * (y == 1) * (e == 1)))
    fp = float(np.sum(w * (y == 0) * (e == 1)))
    fn = float(np.sum(w * (y == 1) * (e == 0)))
    tapsus = tp / (tp + fp) if tp + fp else None
    saagis = tp / (tp + fn) if tp + fn else None
    f1 = 2 * tapsus * saagis / (tapsus + saagis) if tapsus and saagis else None
    return {"tapsus": _r(tapsus), "saagis": _r(saagis), "f1": _r(f1),
            "tp": int(np.sum((y == 1) & (e == 1))), "fp": int(np.sum((y == 0) & (e == 1))),
            "fn": int(np.sum((y == 1) & (e == 0))), "n": int(len(y)), "positiivseid": int(np.sum(y == 1))}


def _r(x, k=3):
    return None if x is None else round(x, k)


def bootstrap(y, ennustus, kaal, kihid, korda=1000, seeme=1):
    """95% vahemik kaalutud täpsusele ja saagisele (kihisisene bootstrap)."""
    rnd = np.random.default_rng(seeme)
    y, e, w, k = map(np.asarray, (y, ennustus, kaal, kihid))
    t, s = [], []
    idx_kihiti = [np.where(k == kk)[0] for kk in np.unique(k)]
    for _ in range(korda):
        idx = np.concatenate([rnd.choice(i, len(i), replace=True) for i in idx_kihiti if len(i)])
        m = kaalutud_moodikud(y[idx], e[idx], w[idx])
        if m["tapsus"] is not None:
            t.append(m["tapsus"])
        if m["saagis"] is not None:
            s.append(m["saagis"])
    q = lambda v: [_r(float(np.percentile(v, 2.5))), _r(float(np.percentile(v, 97.5)))] if v else None  # noqa: E731
    return {"tapsus_95": q(t), "saagis_95": q(s)}


def levimus(margendid, kihi_suurused):
    """Kihistatud hinnang: mitu AI- või andmehanget on populatsioonis kokku (valimi põhjal, mudelist sõltumata).

    Kui kihis ei leitud ühtegi positiivset, on tavaline vahemik null laiune. Siis lisatakse ülemisele piirile
    „kolme reegel“ (3/n kihist), sest 0 leidu 300 seas ei tähenda, et neid pole.
    """
    kokku, var, lisa = 0.0, 0.0, 0.0
    kihiti = {}
    for kiht, n_kiht in kihi_suurused.items():
        rid = [m for m in margendid if m["kiht"] == kiht]
        if not rid:
            continue
        pos = sum(m["silt"] in POSITIIVNE for m in rid)
        p = pos / len(rid)
        kokku += n_kiht * p
        var += (n_kiht ** 2) * p * (1 - p) / max(len(rid) - 1, 1) * max(0.0, 1 - len(rid) / n_kiht)
        if pos == 0 and len(rid) < n_kiht:
            lisa += n_kiht * 3 / len(rid)
        kihiti[kiht] = {"suurus": n_kiht, "valimis": len(rid), "positiivseid": pos}
    sd = math.sqrt(var)
    return {"hinnang": round(kokku), "vahemik_95": [max(0, round(kokku - 1.96 * sd)), round(kokku + 1.96 * sd + lisa)],
            "kihid": kihiti}


ARUANNE = {}


def kirjuta(osa, **kw):
    """Logirida ja sama sisu faili hindamine.json (leht loeb seda)."""
    ARUANNE[osa] = kw
    print("HANKED", osa, json.dumps(kw, ensure_ascii=False), flush=True)


def marksona_ennustus(r):
    m = R.marksonad(R.tekst(r))
    return int(bool(m["ai"] or m["andmed"]))


def oecd_ennustus(r):
    """OECD-laadne lai loend: AI-sõnad + 'algoritm', ilma andmesõnadeta."""
    m = R.marksonad(R.tekst(r))
    return int(bool(m["ai"] or m["lai"]))


def kiht(r):
    """Sama kihijaotus nagu valimi koostamisel (kirjelda.py)."""
    m = R.marksonad(R.tekst(r))
    if m["ai"] or m["andmed"]:
        return "marksona"
    if R.cpv_ruhm(r.get("cpv"))["it"]:
        return "it_cpv"
    return "muu"


vota = R.voti


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--valjund", default="valjund")
    ap.add_argument("--testi-alates", type=int, default=2024)
    a = ap.parse_args()
    v = Path(a.valjund)
    with gzip.open(v / "hanked.jsonl.gz", "rt", encoding="utf-8") as f:
        hanked = [json.loads(x) for x in f]
    voti = {vota(r): r for r in hanked}
    koik_margendid = loe_margendid()
    margendid = [m for m in koik_margendid if m["voti"] in voti]
    kirjuta("margendid", kokku=len(koik_margendid), leitud_registrist=len(margendid),
            positiivseid=sum(m["silt"] in POSITIIVNE for m in margendid))
    korpus = [sisend(r) for r in hanked]
    # sõnavara õpitakse 25 000 hanke tekstist (mälu piir), märgendatud read on alati sees
    sonavara = [korpus[i] for i in stabiilne_valim([vota(r) for r in hanked])]
    y = np.array([int(m["silt"] in POSITIIVNE) for m in margendid])
    w = np.array([1.0 / float(m["valiku_toenaosus"]) for m in margendid])
    aasta = np.array([voti[m["voti"]]["aasta"] for m in margendid])
    kihid = np.array([m["kiht"] for m in margendid])
    x_tekst = [sisend(voti[m["voti"]]) for m in margendid]
    marks = np.array([marksona_ennustus(voti[m["voti"]]) for m in margendid])

    # 1) ajapõhine hindamine
    tr, te = aasta < a.testi_alates, aasta >= a.testi_alates
    tulemused, valitud, soovitus = {}, LEHE_REEGEL, None
    if tr.sum() and te.sum() and y[tr].sum() and y[te].sum():
        m = Mudel().sobita([x_tekst[i] for i in np.where(tr)[0]], y[tr], korpus=sonavara + x_tekst)
        p = m.toenaosus([x_tekst[i] for i in np.where(te)[0]])
        e = (p >= LAVI).astype(int)
        oecd = np.array([oecd_ennustus(voti[margendid[i]["voti"]]) for i in np.where(te)[0]])
        reeglid = {"mudel": e, "marksonaloend": marks[te], "mudel_voi_marksona": np.maximum(e, marks[te]),
                   "oecd_laadne": oecd}
        for nimi, eb in reeglid.items():
            tulemused[nimi] = {**kaalutud_moodikud(y[te], eb, w[te]), **bootstrap(y[te], eb, w[te], kihid[te])}
        kandidaadid = {k: tulemused[k]["f1"] or 0 for k in ("mudel", "marksonaloend", "mudel_voi_marksona")}
        soovitus = max(kandidaadid, key=kandidaadid.get)
        # lihtsam reegel oleks soovitus, kui vahe on väike (märksõnaloendit saab igaüks kontrollida ja korrata)
        if kandidaadid[soovitus] - kandidaadid["marksonaloend"] < VAIKE_VAHE:
            soovitus = "marksonaloend"
        if soovitus != LEHE_REEGEL:
            kirjuta("hoiatus", tekst="hindamine soovitaks teist reeglit; leht kasutab lukustatud reeglit",
                    lukustatud=LEHE_REEGEL, soovitus=soovitus, f1=kandidaadid)
        # vead üle vaatamiseks (ainult võti ja pealkiri; tekst on registris avalik)
        vead = []
        for j, i in enumerate(np.where(te)[0]):
            if reeglid[valitud][j] != y[i]:
                r = voti[margendid[i]["voti"]]
                vead.append({"voti": margendid[i]["voti"], "silt": margendid[i]["silt"], "p": round(float(p[j]), 2),
                             "marksona": int(marks[i]), "pealkiri": (r.get("pealkiri") or "")[:140]})
        kirjuta("vead", reegel=valitud, n=len(vead), read=vead[:60])
    kirjuta("hindamine", testi_alates=a.testi_alates, treening=int(tr.sum()), test=int(te.sum()),
            treening_pos=int(y[tr].sum()), test_pos=int(y[te].sum()), lavi=LAVI, valitud=valitud, soovitus=soovitus,
            tulemused=tulemused)

    # 2) lõplik mudel kõigil märgendustel → kogu registri märgendamine valitud reegliga
    lopp = Mudel().sobita(x_tekst, y, korpus=sonavara + x_tekst)
    kirjuta("olulised", **lopp.olulised())
    p_koik = lopp.toenaosus(korpus)
    m_koik = np.array([marksona_ennustus(r) for r in hanked])
    e_koik = (p_koik >= LAVI).astype(int)
    silt = {"mudel": e_koik, "marksonaloend": m_koik, "mudel_voi_marksona": np.maximum(e_koik, m_koik)}[valitud]

    # 3) levimus eVormide populatsioonis (valimi põhjal) ja mida iga reegel seal leiab
    ef = [i for i, r in enumerate(hanked) if r["allikas"] == "eforms"]
    kihi_suurus = {}
    for i in ef:
        if hanked[i].get("pealkiri"):
            k = kiht(hanked[i])
            kihi_suurus[k] = kihi_suurus.get(k, 0) + 1
    kirjuta("levimus", populatsioon="eforms", hankeid=len(ef), valimi_pohjal=levimus(margendid, kihi_suurus),
            mudel_leidis=int(e_koik[ef].sum()), marksonaloend_leidis=int(m_koik[ef].sum()),
            valitud_leidis=int(silt[ef].sum()), valitud=valitud)

    # 4) märgendamiseks järgmised: mudel peab tõenäoliseks, märksõna ei leia, silti veel pole
    margendatud = {m["voti"] for m in koik_margendid}
    jarg = sorted((i for i in range(len(hanked)) if not m_koik[i] and vota(hanked[i]) not in margendatud),
                  key=lambda i: -p_koik[i])[:40]
    kirjuta("margenda_jargmiseks", read=[{"voti": vota(hanked[i]), "p": round(float(p_koik[i]), 2),
                                          "pealkiri": (hanked[i].get("pealkiri") or "")[:140]} for i in jarg])

    with gzip.open(v / "tulemus.jsonl.gz", "wt", encoding="utf-8") as f:
        for r, pp, s_, mk in zip(hanked, p_koik, silt, m_koik):
            f.write(json.dumps({"voti": vota(r), "p": round(float(pp), 4), "silt": int(s_),
                                "marksona": int(mk)}) + "\n")
    (v / "hindamine.json").write_text(json.dumps(ARUANNE, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
