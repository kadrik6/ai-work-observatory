"""Kogujate proovikäivitus. Kirjutab ainult väljundkausta; repo faile, avaldatud lehti ega prognoose ei muuda.

    python tooelu-seire/proov.py --valjund valjund                         üks käivitus
    python tooelu-seire/proov.py --valjund uus --eelmine vana/koik.jsonl    võrdle eelmise käivitusega

Väljund:
    olek.json           iga allika kohta ok/viga, kirjete arv, aeg
    koik.jsonl          kõik selle käivituse kirjed (järgmise käivituse --eelmine)
    kirjed.jsonl        uued KONTROLLIMATA kandidaadid
    versioonid.jsonl    sama töö uuem versioon (nt arXiv v2)
    duplikaadid.jsonl   kirjed, mis olid juba olemas
    vead.jsonl          iga ebaõnnestunud allikas koos veaga
    kokkuvote.md        inimesele loetav kokkuvõte
Väljumiskood on 0, kui vähemalt üks allikas töötas, muidu 1.
"""

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kogujad import allikad, yhine  # noqa: E402


def kaivita(valjund, eelmine=(), paevi=14, hae=None):
    valjund = Path(valjund)
    valjund.mkdir(parents=True, exist_ok=True)
    alates = (dt.date.today() - dt.timedelta(days=paevi)).isoformat()
    kirjed, olek = allikad.hae_koik(alates, hae=hae)
    varasemad = [k for tee in eelmine for k in yhine.loe_jsonl(tee)]
    uued, versioonid, duplikaadid = yhine.eralda(kirjed, varasemad)
    for nimi, rida in [("koik", kirjed), ("kirjed", uued), ("versioonid", versioonid), ("duplikaadid", duplikaadid)]:
        (valjund / f"{nimi}.jsonl").unlink(missing_ok=True)
        yhine.kirjuta_jsonl(valjund / f"{nimi}.jsonl", rida)
    vead = [{"allikas": n, **o} for n, o in olek.items() if o["olek"] == "viga"]
    (valjund / "vead.jsonl").unlink(missing_ok=True)
    yhine.kirjuta_jsonl(valjund / "vead.jsonl", vead)
    kokku = {"aeg": yhine.nuud(), "alates": alates, "allikaid": len(olek), "varasemaid": len(varasemad),
             "toimis": sum(o["olek"] == "ok" for o in olek.values()), "uusi": len(uued),
             "uusi_versioone": len(versioonid), "duplikaate": len(duplikaadid), "allikad": olek}
    (valjund / "olek.json").write_text(json.dumps(kokku, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    (valjund / "kokkuvote.md").write_text(kokkuvote(kokku, uued, kirjed), encoding="utf-8")
    return kokku


def kokkuvote(k, uued, koik=()):
    read = [f"# Kogujate proov {k['aeg']}", "",
            "Kõik kirjed on KONTROLLIMATA kandidaadid. Kogumine ei tee järeldusi.", "",
            f"Allikaid {k['allikaid']}, toimis {k['toimis']}. Uusi kirjeid {k['uusi']}, uusi versioone "
            f"{k['uusi_versioone']}, duplikaate {k['duplikaate']}.", "",
            "| Allikas | Olek | Kirjeid | Märkus |", "|---|---|---|---|"]
    for nimi, o in k["allikad"].items():
        markus = re.sub(r"https?://([^/?]+)\S*", r"\1", o.get("viga", o.get("markus", "")))
        if "voos" in o:
            markus = f"voos {o['voos']} kirjet, märksõnaga {o['kirjeid']}. {markus}".strip()
        read.append(f"| {nimi} | {o['olek']} | {o.get('kirjeid', '')} | {markus} |")
    read += ["", "## Näited uutest (kuni 3 iga allika kohta), asjakohasuse kontrolliks", ""]
    for allikas in dict.fromkeys(x["allikas"] for x in uued):
        read += [f"- [{allikas}] {x['pealkiri'][:120]}" for x in [y for y in uued if y["allikas"] == allikas][:3]]
    hoiatused = [x for x in koik if x.get("markus")]
    if hoiatused:
        read += ["", "## Hoiatused", ""] + [f"- {x['allikas']}:{x['voti']}: {x['markus']}" for x in hoiatused]
    return "\n".join(read) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--valjund", required=True, help="kaust, kuhu tulemus kirjutatakse (ei lähe repo)")
    ap.add_argument("--eelmine", nargs="*", default=[], help="varasemate käivituste koik.jsonl (duplikaadid, versioonid)")
    ap.add_argument("--paevi", type=int, default=14, help="mitu päeva tagasi OpenAlexist otsida")
    args = ap.parse_args(argv)
    k = kaivita(args.valjund, args.eelmine, args.paevi)
    print((Path(args.valjund) / "kokkuvote.md").read_text(encoding="utf-8"))
    return 0 if k["toimis"] else 1


if __name__ == "__main__":
    sys.exit(main())
