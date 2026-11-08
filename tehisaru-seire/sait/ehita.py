"""Tehisaru seire sait: üks generaator kogu saidile (ehitatud nullist 4.11.2026).

Kes loeb: kodanik, ajakirjanik, ministeeriumi analüütik, ettevõtja; esimene lugeja on Kadri.
Mis küsimusele sait vastab: kui palju tehisaru kasutatakse, kas see mõjutab tööd ja kas numbrit võib usaldada.
Mida lugeja pärast teab: Eesti uusima numbri, koha ELis, allika ja selle, mida number ei näita.
Põhiline: pealkirja number ja võrdlus. Toetav: graafik ja piirangud. Valikuline: andmetabel ja määratlused.

Sisu: sisuloogika hinnang (doc VZ3PrrjkCpDpvc4PXocAG6, Kadri kinnitas 4.11.2026).
Arhitektuur: doc 9U9shhAfRvuJb2Uvbz7SSy. Graafikud: seire-uus-versioon/GRAAFIKUD.md.

Moodulid: andmekiht.py (arhitektuuris andmed.py; nimi muudetud, sest kaust andmed/ varjaks seda), pealkiri.py (h1 mallid), komponendid.py, kest.py, lehed.py (vaadete sisu).
Käivitus (kaustast tehisaru-seire):  python3 sait/ehita.py [VÄLJUND]   (vaikimisi valjund/sait/)
Ainult Pythoni standardteek. Ehitus kukub, kui number, link või pealkiri ei ole korras.
"""
import json
import re
import shutil
import sys
from html.parser import HTMLParser
from pathlib import Path

SIIN = Path(__file__).resolve().parent
sys.path.insert(0, str(SIIN))

import andmekiht as andmed  # noqa: E402
import kest  # noqa: E402
import lehed  # noqa: E402
from pealkiri import taida  # noqa: E402

VALJUND = SIIN.parent / "valjund" / "sait"


class EhitusViga(Exception):
    pass


def lae_vaated():
    v = json.loads((SIIN / "vaated.json").read_text(encoding="utf-8"))["vaated"]
    failid = [x["fail"] for x in v]
    if len(set(failid)) != len(failid):
        raise EhitusViga("vaated.json: kaks vaadet sama failinimega")
    return v


class _Pealkirjad(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tasemed, self.lingid, self.ankrud = [], [], set()

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if re.fullmatch(r"h[1-6]", tag):
            self.tasemed.append(int(tag[1]))
        if tag == "a" and a.get("href"):
            self.lingid.append(a["href"])
        if a.get("id"):
            self.ankrud.add(a["id"])


def kontrolli(failinimi, html_tekst, olemas):
    """Üks h1, tasemed ei hüppa, sisemised lingid viivad olemasolevale lehele või ankrule."""
    p = _Pealkirjad()
    p.feed(html_tekst)
    if p.tasemed.count(1) != 1:
        raise EhitusViga(f"{failinimi}: h1 on {p.tasemed.count(1)} korda, peab olema 1")
    for eelmine, jargmine in zip(p.tasemed, p.tasemed[1:]):
        if jargmine > eelmine + 1:
            raise EhitusViga(f"{failinimi}: pealkirja tase hüppab h{eelmine} → h{jargmine}")
    for href in p.lingid:
        if href.startswith(("http://", "https://", "mailto:")):
            continue
        leht, _, ankur = href.partition("#")
        if leht and leht not in olemas:
            raise EhitusViga(f"{failinimi}: link viib olematule lehele {href}")
        if not leht and ankur and ankur not in p.ankrud:
            raise EhitusViga(f"{failinimi}: ankur #{ankur} puudub")
    if "{" in re.sub(r"<(script|style)[^>]*>.*?</\1>", "", html_tekst, flags=re.S):
        raise EhitusViga(f"{failinimi}: lehel on täitmata mall")


def suuna_ankrud(lehed, vaated):
    """Link vaate põhilehe ankrule (too.html#hoive) suunatakse teema alamlehele, kus see ankur tegelikult on
    (too-ametid.html#hoive). Nii ei pea iga link teadma, millisele alamlehele jaotis jäi. Mitmeti mõistetav = viga."""
    ankrud = {}
    for f, t in lehed.items():
        p = _Pealkirjad()
        p.feed(t)
        ankrud[f] = set(p.ankrud)
    grupp = {}
    for v in vaated:
        failid = [v["fail"]] + [s["fail"] for s in v.get("alamlehed", [])]
        for f in failid:
            grupp.setdefault(f, set()).update(failid)

    def asenda(m, f):
        leht, ankur = m.group(1), m.group(2)
        if leht not in ankrud or ankur in ankrud[leht]:
            return m.group(0)
        kus = [g for g in sorted(grupp.get(leht, ())) if g in ankrud and ankur in ankrud[g]]
        if len(kus) > 1:
            raise EhitusViga(f"{f}: ankur #{ankur} on mitmel teema lehel: {kus}")
        return f'href="{kus[0]}#{ankur}"' if kus else m.group(0)

    return {f: re.sub(r'href="([a-z0-9-]+\.html)#([^"]+)"', lambda m, f=f: asenda(m, f), t) for f, t in lehed.items()}


def kontrolli_ankrud(lehed):
    """Link teise lehe ankrule (leht.html#x) peab leidma sellel lehel id="x"; muidu viib link lehe algusesse."""
    ankrud = {}
    for f, t in lehed.items():
        p = _Pealkirjad()
        p.feed(t)
        ankrud[f] = p.ankrud
    for f, t in lehed.items():
        for leht, ankur in re.findall(r'href="([a-z0-9-]+\.html)#([^"]+)"', t):
            if leht in ankrud and ankur not in ankrud[leht]:
                raise EhitusViga(f"{f}: link {leht}#{ankur} viib olematule ankrule")


# Vana aadress jääb tööle ja viitab uuele (oskus andmesaidi-ulesehitus, samm 5; struktuuri kontroll 6.11.2026)
VANAD_AADRESSID = {"reeglid-ja-sihid.html": "tehisaru-maarus.html", "uudised-vaited.html": "kas-see-on-tosi.html"}


def suunaja(uus):
    return (f'<!doctype html>\n<html lang="et"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<meta http-equiv="refresh" content="0; url={uus}"><title>Leht on kolinud · Tehisaru seire</title></head>'
            f'<body style="font-family:system-ui,sans-serif;margin:2rem;background:#fff;color:#222"><p>Leht on kolinud: <a href="{uus}">{uus}</a>.</p></body></html>\n')


def ehita(valjund=VALJUND, A=None):
    A = A or andmed.lae()
    vaated = lae_vaated()
    for v in vaated:
        if v["id"] == "kas-tosi":  # väidete arv muutub iga päev (uudiste väited): pealkiri arvutatakse andmetest
            from lehed_usaldus import kas_tosi_h1
            v["h1"] = kas_tosi_h1(A)
        taida(v["h1"], A)  # iga h1 mall peab olema täidetav, ka ehitamata vaatel
    valjund = Path(valjund)
    valjund.mkdir(parents=True, exist_ok=True)
    valmis = [v for v in vaated if v["olek"] == "valmis"]
    olemas = {v["fail"] for v in valmis} | {s["fail"] for v in valmis for s in v.get("alamlehed", [])}
    kirjutatud = {}
    for v in valmis:
        if v["id"] == "saidikaart":
            sisu = lehed.saidikaart(A, v, vaated)
        elif v["id"] in lehed.EHITAJAD:
            sisu = lehed.EHITAJAD[v["id"]](A, v, vaated)
        else:
            raise EhitusViga(f"Vaade {v['id']} on „valmis“, aga sellel pole ehitajat (lehed.EHITAJAD)")
        nimi = v["menuu"] or {"avaleht": "Avaleht", "kuidas": "Kuidas lugeda", "saidikaart": "Saidikaart"}[v["id"]]
        pealkiri_ = "SEIRE · Tehisaru seire" if v["id"] == "avaleht" else f"{nimi} · Tehisaru seire"  # artefakti nimi „ID · Nimi“
        if getattr(sisu, "lehed", None):  # teema on jagatud alamlehtedeks
            nimed = {s["fail"]: s["nimi"] for s in v["alamlehed"]}
            for f, osa in sisu.lehed.items():
                t = pealkiri_ if f == v["fail"] else f"{nimi} · {nimed[f]} · Tehisaru seire"
                kirjutatud[f] = kest.leht(A, vaated, v, osa, t, fail=f)
        else:
            kirjutatud[v["fail"]] = kest.leht(A, vaated, v, sisu, pealkiri_)
    kirjutatud = suuna_ankrud(kirjutatud, vaated)
    for f, t in kirjutatud.items():
        kontrolli(f, t, olemas)
    kontrolli_ankrud(kirjutatud)
    for f, t in kirjutatud.items():
        (valjund / f).write_text(t, encoding="utf-8")
    for vana, uus in VANAD_AADRESSID.items():
        if uus not in kirjutatud:
            raise EhitusViga(f"Vana aadress {vana} suunab olematule lehele {uus}")
        (valjund / vana).write_text(suunaja(uus), encoding="utf-8")
    for nimi in ("stiil.css", "sait.js"):
        shutil.copyfile(SIIN / nimi, valjund / nimi)
    # Veebis (Vercel) on sait esialgu link, mida otsingumootorid ei indekseeri (Kadri 8.11.2026).
    # Sama keeld on ka päises X-Robots-Tag (vercel.json). Avalikuks tegemine on Kadri otsus.
    (valjund / "robots.txt").write_text(ROBOTS, encoding="utf-8")
    return sorted(kirjutatud)


ROBOTS = "User-agent: *\nDisallow: /\n"


if __name__ == "__main__":
    siht = Path(sys.argv[1]) if len(sys.argv) > 1 else VALJUND
    for f in ehita(siht):
        print(siht / f)
