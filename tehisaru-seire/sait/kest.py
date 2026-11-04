"""Lehe kest: üks päis (saidi nimi, „Uuendatud“, teemalüliti), siis teemade menüü, „Sellel lehel“ ja jalus.

Igal lehel on sama päis ja üks teemalüliti. Ehitamata teema on menüüs tekstina „tulekul“, mitte katkise lingina.
"""
from komponendid import e, kp


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


def leht(A, vaated, vaade, sisu, title):
    avaleht = next(v for v in vaated if v["id"] == "avaleht")
    kodu = avaleht["fail"] if avaleht["olek"] == "valmis" else "saidikaart.html"
    jalus_lingid = [f'<a href="{v["fail"]}">{e(v["menuu"] or v["id"].capitalize())}</a>'
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
<link rel="stylesheet" href="stiil.css">
<script src="sait.js"></script>
</head>
<body>
<a class="skip" href="#sisu">Mine sisu juurde</a>
<header class="top">
  <div class="wrap">
    <div class="top-1">
      <a class="mark" href="{kodu}">Tehisaru seire</a>
      <span class="seis">Uuendatud {kp(A["uuendatud"])}</span>
      <button class="teema" type="button" aria-pressed="false">Tume teema</button>
    </div>
    <nav aria-label="Teemad"><ul class="menu">{menuu(vaated, vaade["id"])}</ul></nav>
  </div>
</header>
<main id="sisu" class="wrap">
{sisu}
</main>
<footer class="jalus">
  <div class="wrap">
    <p>Tehisaru seire koondab avalikku statistikat ja uuringuid tehisaru kasutusest Eestis ja Euroopas. Iga number on avalikust allikast koos lingi ja kuupäevaga.</p>
    <p>{" · ".join(jalus_lingid)} · Eelvaade, ei ole avaldatud.</p>
  </div>
</footer>
</body>
</html>
"""
