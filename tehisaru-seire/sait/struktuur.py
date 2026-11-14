"""Saidi ülesehituse kontroll (oskus andmesaidi-ulesehitus, Kadri 6.11.2026: „pidevad kontrollid on olulised“).

Mõõdab iga ehitatud lehe: sõnad, h2 jaotised, kokkupandavad plokid, tabelid, graafikud, lingid sisse ja välja.
Leiab orvud (kuhu ükski leht ei vii), tupikud (kust ei pääse edasi), lehed, kus menüüs pole märgitud praegust teemat,
ja lehed, mis ületavad tükeldamise rusikareegli (vähemalt kaks: >2500 sõna, >8 h2, >10 tabelit).

Käivita: python3 sait/struktuur.py [valjund/sait]. Testid (tests/test_struktuur.py) kukuvad orbude, tupikute ja
märkimata teema korral; tükeldamise piir on ainult hoiatus, sest otsus on inimese oma.
"""
import html
import re
from html.parser import HTMLParser
import sys
from pathlib import Path

SIIN = Path(__file__).resolve().parent
VAIKIMISI = SIIN.parent / "valjund" / "sait"
PIIR_SONU, PIIR_H2, PIIR_TABELID = 2500, 8, 10


def _sisu(s):
    return re.sub(r"<script.*?</script>|<style.*?</style>", "", s, flags=re.S)


class _Nahtav(HTMLParser):
    """Jätab välja peidetud sakipaneelid (role="tabpanel" hidden): lugeja näeb korraga ühte sakki (teemamall A, 8.11.2026).
    Teemalehe tahvel (14.11.2026): välja jäävad ka telefonivaate koopia (.tv-tel, sama sisu teise paigutusega)
    ja kokkupandud „Üksikasjad“ plokkide sisu (details.tt-pl); plokkide pealkirjad (summary) jäävad sisse."""
    TUHJAD = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}

    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.osad, self.sugavus, self.kokku = [], 0, 0

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if self.sugavus:
            if tag not in self.TUHJAD:
                self.sugavus += 1
            return
        klass = (d.get("class") or "").split()
        if (d.get("role") == "tabpanel" and "hidden" in d) or "tv-tel" in klass:
            self.sugavus = 1
            return
        if tag == "details" and "tt-pl" in klass and "open" not in d:
            self.kokku = 1
        elif self.kokku and tag not in self.TUHJAD:
            self.kokku += 1
        self.osad.append(self.get_starttag_text())

    def handle_startendtag(self, tag, attrs):
        if not self.sugavus:
            self.osad.append(self.get_starttag_text())

    def handle_endtag(self, tag):
        if self.sugavus:
            if tag not in self.TUHJAD:
                self.sugavus -= 1
            return
        self.osad.append(f"</{tag}>")
        if self.kokku and tag not in self.TUHJAD:
            self.kokku -= 1
            if tag == "summary" and self.kokku == 1:  # pealkiri loetud, ülejäänud plokk on kinni kuni </details>
                self.kokku, self.sugavus = 0, 1

    def handle_data(self, data):
        if not self.sugavus:
            self.osad.append(data)

    def handle_entityref(self, name):
        if not self.sugavus:
            self.osad.append(f"&{name};")

    def handle_charref(self, name):
        if not self.sugavus:
            self.osad.append(f"&#{name};")


def nahtav(s):
    p = _Nahtav()
    p.feed(s)
    return "".join(p.osad)


def moodik(failid):
    """failid: {nimi: html}. Tagastab {nimi: {...}}."""
    out = {}
    for f, s in failid.items():
        keha = _sisu(s)
        main = re.search(r"<main.*?</main>", keha, re.S)
        m = main.group(0) if main else keha
        mn = nahtav(m)  # sõnad ja h2 ainult nähtavast osast (peidetud sakid välja)
        sonu = len(html.unescape(re.sub(r"<[^>]+>", " ", mn)).split())
        lingid = set(l.split("#")[0] for l in re.findall(r'href="([a-z0-9-]+\.html)(?:#[^"]*)?"', keha))
        lingid_sisu = set(l.split("#")[0] for l in re.findall(r'href="([a-z0-9-]+\.html)(?:#[^"]*)?"', m))
        out[f] = {
            "title": (re.search(r"<title>(.*?)</title>", s) or [None, ""])[1],
            "h1": html.unescape(re.sub(r"<[^>]+>", "", (re.search(r"<h1>(.*?)</h1>", s, re.S) or [None, ""])[1])).strip(),
            "sonu": sonu, "h2": len(re.findall(r"<h2", mn)), "details": len(re.findall(r"<details", m)),
            "tabelid": len(re.findall(r"<table", m)), "graafikud": len(re.findall(r'<figure|role="img"|<svg', m)),
            "valja": sorted(lingid - {f}), "valja_sisust": sorted(lingid_sisu - {f}),
            "menuu_marge": bool(re.search(r'<ul class="menu">.*?aria-current="page".*?</ul>', s, re.S)),
            # Kasutusloogika (oskus kasutusloogika, 6.11.2026): igal tasandil täpselt üks aktiivne märge, iga nupurühm
            # näitab valitud olekut, igal nupul on nimi
            "alam_margid": [len(re.findall(r'aria-current="page"', u)) for u in re.findall(r'<ul class="alamlehed">(.*?)</ul>', s, re.S)],
            "ruhmad_valitud": [len(re.findall(r'aria-pressed="true"', g)) for g in re.findall(r'<div class="u-f" role="group"[^>]*>(.*?)</div>', s, re.S)],
            "nimeta_nupud": len([b for b in re.findall(r'<button\b([^>]*)>(.*?)</button>', keha, re.S)
                                 if not re.sub(r"<[^>]+>", "", b[1]).strip() and "aria-label" not in b[0]]),
        }
    for f in out:
        out[f]["sisse"] = sorted(g for g in out if f in out[g]["valja"] and g != f)
        out[f]["sisse_sisust"] = sorted(g for g in out if f in out[g]["valja_sisust"] and g != f)
    return out


def vead(M, avaleht="index.html", jalus=("saidist.html", "kuidas-lugeda.html", "saidikaart.html")):
    """Kõvad vead: orvud, tupikud, teema märkimata menüüs (v.a avaleht ja jaluse lehed)."""
    v = []
    for f, m in M.items():
        if f != avaleht and not m["sisse"]:
            v.append(f"{f}: orb, ükski leht ei vii siia")
        if not m["valja"]:
            v.append(f"{f}: tupik, siit ei pääse edasi")
        if f != avaleht and f not in jalus and not m["menuu_marge"]:
            v.append(f"{f}: menüüs pole praegust teemat märgitud")
        if not m["h1"]:
            v.append(f"{f}: h1 puudub")
        if any(n != 1 for n in m["alam_margid"]):
            v.append(f"{f}: alamlehtede real ei ole täpselt üks aktiivne märge {m['alam_margid']}")
        if any(n != 1 for n in m["ruhmad_valitud"]):
            v.append(f"{f}: nupurühmas ei ole täpselt üks valitud nupp {m['ruhmad_valitud']}")
        if m["nimeta_nupud"]:
            v.append(f"{f}: {m['nimeta_nupud']} nuppu ilma nimeta (tekst või aria-label)")
    nimed = {}
    for f, m in M.items():
        nimed.setdefault(m["title"], []).append(f)
    v += [f"sama <title> mitmel lehel: {', '.join(ff)}" for t, ff in nimed.items() if len(ff) > 1]
    return v


def hoiatused(M):
    """Tükeldamise rusikareegel (oskus, samm 5): vähemalt kaks tingimust korraga."""
    h = []
    for f, m in M.items():
        t = [n for n, ok in (("sõnu %d" % m["sonu"], m["sonu"] > PIIR_SONU), ("h2 %d" % m["h2"], m["h2"] > PIIR_H2),
                             ("tabeleid %d" % m["tabelid"], m["tabelid"] > PIIR_TABELID)) if ok]
        if len(t) >= 2:
            h.append(f"{f}: tükeldamise piir ületatud ({', '.join(t)})")
        elif t:
            h.append(f"{f}: üks piir ületatud ({t[0]}), jälgi")
    return h


def lae(kaust=VAIKIMISI):
    lehed = {p.name: p.read_text(encoding="utf-8") for p in sorted(Path(kaust).glob("*.html"))}
    return {f: s for f, s in lehed.items() if 'http-equiv="refresh"' not in s}  # vanade aadresside suunajad


if __name__ == "__main__":
    M = moodik(lae(Path(sys.argv[1]) if len(sys.argv) > 1 else VAIKIMISI))
    print(f'{"fail":28} {"sõnu":>5} {"h2":>3} {"det":>3} {"tab":>3} {"graaf":>5} {"välja":>5} {"sisse":>5} {"sisse sisust":>12}')
    for f, m in M.items():
        print(f'{f:28} {m["sonu"]:5} {m["h2"]:3} {m["details"]:3} {m["tabelid"]:3} {m["graafikud"]:5} {len(m["valja"]):5} {len(m["sisse"]):5} {len(m["sisse_sisust"]):12}')
    for x in vead(M):
        print("VIGA", x)
    for x in hoiatused(M):
        print("HOIATUS", x)
