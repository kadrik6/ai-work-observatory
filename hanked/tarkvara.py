"""Tarkvara- ja platvormihanked tootja kaupa: Microsoft (M365, Power BI, Fabric, Azure) ja alternatiivid.

Kadri küsimus 8.11.2026: kui palju kulutab avalik sektor Microsofti litsentsidele ja mis kulud on neil,
kes kasutavad muid tööriistu (Tableau, Qlik, SAS, Google, avatud lähtekood). Loeb lae.py põhitabelit
(valjund/hanked.jsonl.gz) ja kirjutab logisse read "TARKVARA rida ..." ja "TARKVARA koond ...".

Piirid: registris pole alla 30 000 euro hankeid. Raamlepingu summa on sageli lagi, mitte tegelik kulu.
Keskhanke (RIT) minikonkursid ja tellimused ei tule registrisse eraldi hangetena.
"""
import argparse
import gzip
import json
import re
from collections import defaultdict
from pathlib import Path

import reeglid as R

E = r"(?<![\wõäöüšž])"
L = r"(?![\wõäöüšž])"

TOOTED = {
    "microsoft": E + r"(microsoft|m365|office ?365|ms ?office|azure|dynamics ?365|sharepoint|ovs-?es)",
    "power_bi": E + r"power ?bi" + L,
    "ms_fabric": E + r"(microsoft fabric|fabric-?i? (võimsus|capacity|platvorm|litsents))",
    "tableau": E + r"tableau",
    "qlik": E + r"qlik",
    "sas": E + r"(sas institute|sas viya|sas enterprise|sas (tarkvara|litsents|platvorm)|sas-?i (tarkvara|litsents))",
    "google": E + r"(google workspace|g suite|looker|google cloud|bigquery)",
    "oracle_bi": E + r"(oracle (bi|analytics|business intelligence)|obiee)" + L,
    "ibm_cognos": E + r"cognos",
    "sap_bi": E + r"(businessobjects|business objects|sap analytics cloud|sap bw)",
    "microstrategy": E + r"microstrategy",
    "databricks_snowflake": E + r"(databricks|snowflake)",
    "avatud_lahtekood": E + r"(apache superset|superset|metabase|grafana|kibana|redash|libreoffice|nextcloud)" + L,
}
MUSTRID = {k: re.compile(v) for k, v in TOOTED.items()}
LITSENTS = re.compile(E + r"(litsents|license|licence|tarkvararent|rentimi|tellimus|subscription|tarkvara ost"
                      r"|tarkvara soeta|kasutusõigus|tootetugi|tootetoe|uuendus)")
TEENUS = re.compile(E + r"(arendus|hooldus|haldus|konsult|koolitus|juurutus|analüütiku|arendaja|tugiteenus)")


def tooted(t):
    return [k for k, m in MUSTRID.items() if m.search(t)]


def liik(t, cpv):
    lits = bool(LITSENTS.search(t)) or any(str(c).startswith("48") for c in cpv or [])
    teen = bool(TEENUS.search(t)) or any(str(c).startswith("72") for c in cpv or [])
    return "litsents+teenus" if lits and teen else "litsents" if lits else "teenus" if teen else "muu"


def kirjuta(osa, **kw):
    print("TARKVARA", osa, json.dumps(kw, ensure_ascii=False), flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--valjund", default="valjund")
    a = ap.parse_args()
    v = Path(a.valjund)
    koond = defaultdict(lambda: {"hankeid": 0, "hankijad": set(), "eeldatav": 0.0, "eeldatav_n": 0,
                                 "leping": 0.0, "leping_n": 0, "aastad": defaultdict(int),
                                 "liik": defaultdict(int)})
    hankija_koond = defaultdict(lambda: defaultdict(float))
    n = 0
    with gzip.open(v / "hanked.jsonl.gz", "rt", encoding="utf-8") as f:
        for rida in f:
            r = json.loads(rida)
            t = R.normaliseeri(R.tekst(r, piir=6000))
            leitud = tooted(t)
            if not leitud:
                continue
            n += 1
            lk = liik(t, r.get("cpv"))
            ee, le = r.get("eeldatav_maksumus"), r.get("lepingu_summa")
            kirjuta("rida", tooted=leitud, liik=lk, aasta=r.get("aasta"), kuupaev=r.get("esimene_kuupaev"),
                    hankija=r.get("hankija"), pealkiri=r.get("pealkiri"), kirjeldus=(r.get("kirjeldus") or "")[:400],
                    cpv=r.get("cpv"), eeldatav=ee, leping=le, voitjad=r.get("voitjad"), pakkumusi=r.get("pakkumusi"),
                    menetlus=r.get("menetlus"), vn=r.get("viitenumber"), rhr_id=r.get("rhr_id"),
                    allikas=r.get("allikas"))
            for k in leitud:
                c = koond[k]
                c["hankeid"] += 1
                c["hankijad"].add(r.get("hankija"))
                c["aastad"][r.get("aasta")] += 1
                c["liik"][lk] += 1
                if ee:
                    c["eeldatav"] += ee
                    c["eeldatav_n"] += 1
                if le:
                    c["leping"] += le
                    c["leping_n"] += 1
                hankija_koond[k][r.get("hankija")] += ee or le or 0
    for k, c in sorted(koond.items()):
        top = sorted(hankija_koond[k].items(), key=lambda x: -x[1])[:15]
        kirjuta("koond", toode=k, hankeid=c["hankeid"], hankijaid=len(c["hankijad"]),
                eeldatav_summa=round(c["eeldatav"]), eeldatav_n=c["eeldatav_n"],
                leping_summa=round(c["leping"]), leping_n=c["leping_n"],
                aastad=dict(sorted(c["aastad"].items())), liik=dict(c["liik"]), top_hankijad=top)
    kirjuta("kokku", leitud=n)


if __name__ == "__main__":
    main()
