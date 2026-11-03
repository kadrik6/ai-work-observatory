"""Mis numbrid on allikates muutunud võrreldes repos oleva seisuga.

Igapäevane seire laeb andmed uuesti (run.py ja kataloog/lae_valis.py) ja see skript võrdleb värskeid faile
repos olevate (git HEAD) failidega. Repo seis on sama, millest „Tehisaru 2027“ leht on ehitatud (lehe lukk), nii et
siin näidatud uued ja muutunud numbrid on kandidaadid lehe uuendamiseks. Skript ise midagi ei muuda ega avalda.

    python kataloog/uued_numbrid.py --valjund valjund/uued-numbrid

Väljund: uued-numbrid.md (kokkuvõte) ja uued-numbrid.json. Ainult kontrollimise kuupäeva muutus ja ümardamine
(alla --lubatud) ei loe muutuseks.
"""
import argparse
import csv
import io
import json
import subprocess
from pathlib import Path

SIIN = Path(__file__).resolve().parent.parent  # tehisaru-seire/
FAILID = {
    "kataloog/vaatlused-valis.csv": ("moodik", "riik", "aasta"),
    "kataloog/vaatlused-api.csv": ("moodik", "riik", "aasta"),
    "andmed/ettevotete-tehisaru-kasutus.csv": ("geo", "time"),
    "andmed/inimeste-tehisaru-kasutus.csv": ("geo", "time"),
    "andmed/tooalane-tehisaru-kasutus.csv": ("geo", "time"),
    "andmed/tehisaru-oskuse-puudus.csv": ("geo", "time"),
    "andmed/inimeste-digioskused.csv": ("geo", "time"),
}
# Riigid, mida „Tehisaru 2027“ leht näitab; teised read lähevad eraldi loendisse.
LEHE_RIIGID = {"EE", "EU27_2020", "FI", "SE", "DK", "NO", "DE", "NL"}


def loe(tekst, voti):
    read = {}
    for r in csv.DictReader(io.StringIO(tekst)):
        k = tuple(r.get(v, "") for v in voti)
        read[k] = r
    return read


def vana_tekst(suhteline, viide):
    tee = f"tehisaru-seire/{suhteline}"
    try:
        return subprocess.run(["git", "show", f"{viide}:{tee}"], capture_output=True, text=True, check=True,
                              cwd=SIIN.parent).stdout
    except subprocess.CalledProcessError:
        return ""


def arv(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def vorrdle(lubatud, viide):
    leiud = []
    for nimi, voti in FAILID.items():
        uus_fail = SIIN / nimi
        if not uus_fail.exists():
            continue
        vana = loe(vana_tekst(nimi, viide), voti)
        uus = loe(uus_fail.read_text(encoding="utf-8"), voti)
        for k, r in uus.items():
            v_uus = r.get("vaartus")
            if k not in vana:
                leiud.append({"fail": nimi, "voti": list(k), "vana": None, "uus": v_uus, "liik": "uus",
                              "avaldatud": r.get("avaldatud", ""), "margend": r.get("margend", "")})
                continue
            v_vana = vana[k].get("vaartus")
            a, b = arv(v_vana), arv(v_uus)
            muutus = (v_vana != v_uus) if a is None or b is None else abs(a - b) > lubatud
            if muutus:
                leiud.append({"fail": nimi, "voti": list(k), "vana": v_vana, "uus": v_uus, "liik": "muutus",
                              "avaldatud": r.get("avaldatud", ""), "margend": r.get("margend", "")})
    return leiud


def lehe_jaoks(l):
    riik = l["voti"][1] if l["fail"].startswith("kataloog/") else l["voti"][0]
    return riik in LEHE_RIIGID


def markdown(leiud):
    olulised = [l for l in leiud if lehe_jaoks(l)]
    muud = len(leiud) - len(olulised)
    if not leiud:
        return "## Uued numbrid\n\nAllikates ei ole repo seisuga võrreldes uusi ega muutunud numbreid.\n"
    rida = ["## Uued numbrid", "",
            f"Lehe riikide kohta {len(olulised)} uut või muutunud numbrit, teiste riikide kohta {muud}.", "",
            "| Fail | Võti | Enne | Nüüd | Liik | Märgend |", "|---|---|---|---|---|---|"]
    for l in olulised:
        rida.append(f"| {l['fail']} | {' · '.join(l['voti'])} | {l['vana'] or '–'} | {l['uus']} | {l['liik']} | {l['margend']} |")
    rida += ["", "Lehte see ei muuda. Uuendamiseks: digiriik-2027/lukk.py mis-muutuks, seejärel teadlik otsus."]
    return "\n".join(rida) + "\n"


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--valjund", default="valjund/uued-numbrid", help="väljundi kaust")
    p.add_argument("--lubatud", type=float, default=0.006, help="ümardamise lubatud erinevus")
    p.add_argument("--viide", default="HEAD", help="git viide, millega võrrelda")
    a = p.parse_args()
    leiud = vorrdle(a.lubatud, a.viide)
    kaust = Path(a.valjund)
    kaust.mkdir(parents=True, exist_ok=True)
    (kaust / "uued-numbrid.json").write_text(json.dumps(leiud, ensure_ascii=False, indent=1), encoding="utf-8")
    md = markdown(leiud)
    (kaust / "uued-numbrid.md").write_text(md, encoding="utf-8")
    print(md)


if __name__ == "__main__":
    main()
