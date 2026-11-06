#!/usr/bin/env python3
"""Ehitab TOOELU uudistelehe: python3 ehita_leht.py -> UUDISED/leht/uudised.html

Sisend andmekaustas UUDISED (vaikimisi /mnt/project-files/tooelu-uudised): uudised.jsonl, vaited.json, olek.json;
lisaks repo tooelu-seire/koondamised_ee.json (31.10 alates kogutud Eesti koondamised). Mall uudised-mall.html on siin kaustas.
Andmed lähevad lehte sisse, leht ei loe midagi võrgust.
"""
import json
import os
import pathlib
from datetime import date

SIIN = pathlib.Path(__file__).resolve().parent
KAUST = pathlib.Path(os.environ.get("UUDISED", os.path.join(os.environ.get("UUENDUS_ANDMED", "/mnt/project-files"), "tooelu-uudised")))
REPO_KOOND = SIIN.parent / "koondamised_ee.json"


def loe():
    uudised = [json.loads(r) for r in (KAUST / "uudised.jsonl").read_text().splitlines() if r.strip()]
    vaited = json.loads((KAUST / "vaited.json").read_text())
    olek = json.loads((KAUST / "olek.json").read_text())
    koond = []
    if REPO_KOOND.exists():
        for j in json.loads(REPO_KOOND.read_text())["juhtumid"]:
            koond.append(dict(kuupaev=j["kuupaev"], ettevote=j["ettevote"], sektor=j.get("sektor", ""),
                              arv_tekst=j.get("arv_tekst", ""), ai_roll=j["roll"], kes_utles=j.get("kes_utles", ""),
                              pohjus=j.get("pohjus", ""), pealkiri=j["pealkiri"], url=j["url"], allikas=j["allikas"]))
    nahtud = {k["url"] for k in koond}
    for u in uudised:
        if u.get("teema") == "koondamine" and u.get("piirkond") == "EE" and u["url"] not in nahtud:
            koond.append({k: u.get(k, "") for k in ("kuupaev", "ettevote", "sektor", "arv_tekst", "ai_roll",
                                                    "kes_utles", "pohjus", "pealkiri", "url", "allikas")})
            nahtud.add(u["url"])
    koond.sort(key=lambda k: k["kuupaev"], reverse=True)
    uudised.sort(key=lambda u: u["kuupaev"], reverse=True)
    return uudised, vaited, olek, koond


def main():
    uudised, vaited, olek, koond = loe()
    andmed = dict(uudised=uudised, vaited=vaited, olek=olek, koond=koond, ehitatud=date.today().isoformat())
    mall = (SIIN / "uudised-mall.html").read_text()
    html = mall.replace("/*ANDMED*/null", json.dumps(andmed, ensure_ascii=False).replace("</", "<\\/"))
    valja = KAUST / "leht" / "uudised.html"
    valja.parent.mkdir(exist_ok=True)
    valja.write_text(html)
    print(f"{valja}: {len(uudised)} uudist, {len(koond)} koondamist, {len(vaited)} väidet")


if __name__ == "__main__":
    main()
