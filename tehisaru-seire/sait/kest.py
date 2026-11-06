"""Lehe kest: üks päis (saidi nimi, „Uuendatud“, teemalüliti), siis teemade menüü, „Sellel lehel“ ja jalus.

Igal lehel on sama päis ja üks teemalüliti. Ehitamata teema on menüüs tekstina „tulekul“, mitte katkise lingina.
"""
import hashlib
import re
from pathlib import Path

from komponendid import e, kp

_SIIN = Path(__file__).resolve().parent


def _v(nimi):
    """Faili sisu räsi lingi lõppu: muudetud stiil või skript ei tule brauseri vahemälust vanana."""
    return hashlib.sha1((_SIIN / nimi).read_bytes()).hexdigest()[:8]


# Teema valitakse lehe sees enne joonistamist, mitte ainult sait.js-is (Kadri 6.11.2026: alamlehel tuli Hele,
# sest brauser võttis vahemälust vana sait.js). Vaikimisi Pehme; süsteemi tumeda korral Tume; salvestatud valik ees.
TEEMA_JS = ("<script>(function(){var t=null;try{t=localStorage.getItem('seire-teema-2')}catch(e){}"
            "if(['light','soft','dark'].indexOf(t)<0)t=(window.matchMedia&&matchMedia('(prefers-color-scheme: dark)').matches)?null:'soft';"
            "if(t)document.documentElement.setAttribute('data-seire-teema',t)})()</script>")


def menuu(vaated, praegune):
    out = []
    for v in vaated:
        if not v["menuu"]:
            continue
        if v["olek"] == "valmis":
            cur = ' aria-current="page"' if v["id"] == praegune else ""
            out.append(f'<li><a href="{v["fail"]}"{cur}>{e(v["menuu"])}</a></li>')
        else:
            out.append(f'<li><span>{e(v["menuu"])}<small>tulekul</small></span></li>')
    return "".join(out)


def sellel_lehel(lingid):
    """lingid: [(ankur, lühike nimi)]. Lühikesed nimed, et rida ei lõikaks pealkirju pooleks."""
    li = "".join(f'<li><a href="#{e(a)}">{e(n)}</a></li>' for a, n in lingid)
    return f'<nav aria-label="Sellel lehel"><ul class="sellel">{li}</ul></nav>'


def alamlehed(vaade, fail):
    """Teema alamlehtede rida (Kadri 6.11.2026): teine tase teema sees."""
    li = "".join(f'<li><a href="{s["fail"]}"{" aria-current=\"page\"" if s["fail"] == fail else ""}>{e(s["nimi"])}</a></li>'
                 for s in vaade["alamlehed"])
    return f'<nav class="alam" aria-label="{e(vaade["menuu"])}: alamlehed"><ul class="alamlehed">{li}</ul></nav>'


def leht(A, vaated, vaade, sisu, title, fail=None):
    # „Sellel lehel“ tõstetakse kleepuvasse päisesse teemade menüü alla (Kadri 6.11.2026): alamnavigatsioon
    # jääb kerimisel nähtavaks ja ankurlink viib jaotise pealkirja päise alla, mitte suvalisse kohta.
    alam = ""
    m = re.search(r'<nav aria-label="Sellel lehel">.*?</nav>', sisu, re.S)
    if m:
        alam, sisu = m.group(0).replace('<nav ', '<nav class="lehel" ', 1), sisu[:m.start()] + sisu[m.end():]
    if vaade.get("alamlehed"):
        rida2 = f'<div class="rida2">{alamlehed(vaade, fail or vaade["fail"])}{alam}</div>'
    else:
        rida2 = alam
    avaleht = next(v for v in vaated if v["id"] == "avaleht")
    kodu = avaleht["fail"] if avaleht["olek"] == "valmis" else "saidikaart.html"
    nimed = {"kuidas": "Kuidas lugeda", "saidikaart": "Saidikaart"}
    jalus_lingid = [f'<a href="{v["fail"]}">{e(v["menuu"] or nimed.get(v["id"], v["id"]))}</a>'
                    for v in vaated if not v["menuu"] and v["id"] != "avaleht" and v["olek"] == "valmis"]
    kavas = [v for v in vaated if not v["menuu"] and v["olek"] != "valmis" and v["id"] != "avaleht"]
    jalus_lingid += [f'{e("Kuidas lugeda" if v["id"] == "kuidas" else v["id"])} (tulekul)' for v in kavas]
    return f"""<!doctype html>
<html lang="et">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="claude:viewport-fit-sides" content="cover">
<title>{e(title)}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;700&amp;family=Inter:wght@400;600;700&amp;display=swap">
{TEEMA_JS}
<link rel="stylesheet" href="stiil.css?v={_v("stiil.css")}">
<script src="sait.js?v={_v("sait.js")}"></script>
</head>
<body>
<a class="skip" href="#sisu">Mine sisu juurde</a>
<header class="top">
  <div class="wrap">
    <div class="top-1">
      <a class="mark" href="{kodu}">Tehisaru seire</a>
      <a class="seis" href="kuidas-lugeda.html#uuendused" title="Mis uueneb ise ja mis käsitsi">Numbrid {kp(A["uuendatud"])}{f" · uudised {kp(A['uudiste_olek']['viimane_kontroll'][:10])}" if A.get("uudiste_olek") else ""}</a>
      <button class="teema" type="button" aria-label="Teema" title="Teema"><svg class="pool" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><circle cx="12" cy="12" r="8"/><path d="M12 4a8 8 0 0 1 0 16Z" fill="currentColor"/></svg><svg class="kuu" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5Z"/></svg><svg class="paike" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><circle cx="12" cy="12" r="4"/><path d="M12 2.5v2M12 19.5v2M2.5 12h2M19.5 12h2M5.3 5.3l1.4 1.4M17.3 17.3l1.4 1.4M5.3 18.7l1.4-1.4M17.3 6.7l1.4-1.4"/></svg></button>
    </div>
    <nav aria-label="Teemad"><ul class="menu">{menuu(vaated, vaade["id"])}</ul></nav>
    {rida2}
  </div>
</header>
<main id="sisu" class="wrap">
{sisu}
</main>
<footer class="jalus">
  <div class="wrap">
    <p>Tehisaru seire koondab avalikku statistikat ja uuringuid tehisaru kasutusest Eestis ja Euroopas. Iga number on avalikust allikast koos lingi ja kuupäevaga.</p>
    <p>{" · ".join(jalus_lingid)}</p>
  </div>
</footer>
</body>
</html>
"""
