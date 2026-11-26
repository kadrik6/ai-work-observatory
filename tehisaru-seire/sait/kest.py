"""Lehe kest: päis (saidi nimi, „Kõik teemad“, seis, teemalüliti, teemade menüü), rada, sakid, „Sellel lehel“ ja jalus.

Igal lehel on sama päis ja üks teemalüliti. Ehitamata teema on menüüs tekstina „tulekul“, mitte katkise lingina.
"""
import hashlib
import re
from pathlib import Path

from komponendid import e, kp

_SIIN = Path(__file__).resolve().parent

# Python 3.10: f-stringi avaldises ei tohi olla kaldkriipsu, seepärast on jutumärkidega tekstid konstandid
AKTIIVNE = ' aria-current="page"'
MEGA_NIMI = ' class="mega-nimi"'



# Autor (Kadri 11.11.2026: „lisa saidile minu kui autori info, et oleks mingigi autori kaitse olemas“).
# Kadri 12.11.2026: märge on lühike nagu teistel saitidel; jaluses ainult „© aasta nimi“, ilma „küsi luba“ ja kordamiseta.
# Autoriõigus tekib teose loomisega ise; märge teeb autori ja kasutustingimused lugejale nähtavaks.
# Kadri 27.11.2026: „palun võta lehelt viide minu nimele ka ära. Igaks juhuks praegu.“ Nimi ei ole saidil (jalus, meta,
# „Autor“ lõik); © märge kannab saidi nime. Nime tagasi panekuks muuda AUTOR, lisa meta author ja muuda NIME_KONTROLL (ehita.py).
AUTOR = "Tehisaru seire"
AUTORI_ALGUS = 2026


def autori_aastad(aasta=None):
    import datetime as _dt
    a = aasta or _dt.date.today().year
    return str(AUTORI_ALGUS) if a <= AUTORI_ALGUS else f"{AUTORI_ALGUS}–{a}"

def _v(nimi):
    """Faili sisu räsi lingi lõppu: muudetud stiil või skript ei tule brauseri vahemälust vanana."""
    return hashlib.sha1((_SIIN / nimi).read_bytes()).hexdigest()[:8]


# Teema valitakse lehe sees enne joonistamist, mitte ainult sait.js-is (Kadri 6.11.2026: alamlehel tuli Hele,
# sest brauser võttis vahemälust vana sait.js). Vaikimisi Pehme; süsteemi tumeda korral Tume; salvestatud valik ees.
# Verceli külastusloendur (Kadri 8.11.2026 21:51 „jah, lisa“). Laaditakse ainult Verceli aadressil, mitte Claude'i
# artefaktis ega kohalikus failis. Vercel Web Analytics ei kasuta küpsiseid; analüütika tuleb Vercelis sisse lülitada.
# Oma domeen (Kadri 21.11.2026): tehisaruseire.ee on põhiaadress; teised domeenid suunatakse Vercelis sinna, seega
# nende jaoks analüütikat vaja pole. Domeen sobib täpselt või alamdomeenina (www), mitte lihtsalt sama lõpuga nimi.
VERCEL_HOSTID = (".vercel.app",)
OMA_DOMEENID = ("tehisaruseire.ee",)
# Otsingumootorid (Kadri 21.11.2026: „Remove this no index“): põhiaadress on www.tehisaruseire.ee (teised domeenid suunavad
# sinna). Iga leht ütleb canonical-lingiga oma põhiaadressi, et vercel.app ja suunavad domeenid ei oleks topeltsisu.
SAIDI_AADRESS = "https://www.tehisaruseire.ee/"


def aadress(fail):
    """Lehe põhiaadress ilma .html lõputa (Kadri 26.11.2026: aadressiribal ei peaks olema „index.html“).
    Vercel (vercel.json cleanUrls) suunab „too.html“ aadressile „/too“ ja „index.html“ juurele."""
    return SAIDI_AADRESS + ("" if fail == "index.html" else fail.removesuffix(".html"))
ANALYYTIKA_JS = ("<script>(function(){var h=location.hostname,ok=" + "||".join(
                     [f"h.slice(-{len(x)})==='{x}'" for x in VERCEL_HOSTID]
                     + [f"h==='{d}'||h.slice(-{len(d) + 1})==='.{d}'" for d in OMA_DOMEENID])
                 + ";if(!ok)return;window.va=window.va||function(){(window.vaq=window.vaq||[]).push(arguments)};"
                 "var s=document.createElement('script');s.defer=true;s.src='/_vercel/insights/script.js';"
                 "document.head.appendChild(s)})()</script>")
TEEMA_JS = ("<script>(function(){var t=null;try{t=localStorage.getItem('seire-teema-2')}catch(e){}"
            "if(t!=='dark')t='soft';"  # Hele (endine Pehme) ka tumedas seadmes; valge Hele eemaldati (Kadri 8.11.2026)
            "if(t)document.documentElement.setAttribute('data-seire-teema',t);"
            # A1 kujundus (Kadri 8.11.2026 23:41); artefakti kest kirjutab <html> üle, seepärast ka skriptiga
            "document.documentElement.setAttribute('data-t','1')})()</script>")


def menuu(vaated, praegune):
    # Avaleht menüü esimeseks (Kadri 9.11.2026 00:25: ainult saidi nime kaudu ei olnud avaleht leitav)
    kodu = next((v for v in vaated if v["id"] == "avaleht"), None)
    cur = ' aria-current="page"' if praegune == "avaleht" else ""
    out = [f'<li><a href="{kodu["fail"]}"{cur}>Avaleht</a></li>'] if kodu else []
    for v in vaated:
        if not v["menuu"] or v.get("teema"):  # teema alamvaade (nt Hanked) on teema teisel real, mitte menüüs
            continue
        if v["olek"] == "valmis":
            cur = ' aria-current="page"' if v["id"] == praegune else ""
            out.append(f'<li><a href="{v["fail"]}"{cur}>{e(v["menuu"])}</a></li>')
        else:
            out.append(f'<li><span>{e(v["menuu"])}<small>tulekul</small></span></li>')
    return "".join(out)


def sellel_lehel(lingid):
    """lingid: [(ankur, lühike nimi)]. Lühikesed nimed, et rida ei lõikaks pealkirju pooleks."""
    if not lingid:  # tühi riba päises näeb välja nagu viga (tehisaru-maarus.html, 6.11.2026)
        return ""
    li = "".join(f'<li><a href="#{e(a)}">{e(n)}</a></li>' for a, n in lingid)
    return f'<nav aria-label="Sellel lehel"><ul class="sellel">{li}</ul></nav>'


def alamlehed(vaade, fail):
    """Teema alamlehed sakkidena pealkirja all (navigatsioon B, Kadri 6.11.2026 22:51)."""
    li = "".join(f'<li><a href="{s["fail"]}"{AKTIIVNE if s["fail"] == fail else ""}>{e(s["nimi"])}</a></li>'
                 for s in vaade["alamlehed"])
    # Kadri 11.11.2026 (C): alamlehtede rida on teine menüürida, mitte sakk; sakid on ainult andmevaadetel samal lehel
    return (f'<nav class="alam" aria-label="{e(vaade["menuu"])}: alamlehed"><span class="alam-silt">{e(vaade["menuu"])}:</span>'
            f'<ul class="alamlehed">{li}</ul></nav>')


def mega(vaated, fail, kodu, teema_id=None):
    """„Kõik teemad“: kogu sait ühes paneelis (navigatsioon B). <details> töötab ka ilma skriptita.
    Telefonis on paneel „Menüü“ ja näitab ainult teemade linke: teema avab oma esimese lehe, edasi viivad sakid
    (Kadri 6.11.2026 22:52: ära pane menüüsse „+“ märki)."""
    def a(href, tekst, cls="", vid=None):
        cur = ' aria-current="page"' if href == fail else (' aria-current="true"' if vid and vid == teema_id else "")
        return f'<a href="{href}"{cls}{cur}>{tekst}</a>'
    veerud = []
    for v in vaated:
        if not v["menuu"] or v.get("teema") or v["olek"] != "valmis":
            continue
        alam = v.get("alamlehed") or []
        ul = ("<ul>" + "".join(f'<li>{a(s["fail"], e(s["nimi"]))}</li>' for s in alam) + "</ul>") if len(alam) > 1 else ""
        veerud.append(f'<div class="mega-t">{a(v["fail"], e(v["menuu"]), MEGA_NIMI, v["id"])}{ul}'
                      f'<p>{e(v.get("kusimus") or "")}</p></div>')
    lisa = [a(kodu, "Avaleht")] + [a(v["fail"], {"saidist": "Mis see sait on", "kuidas": "Kuidas lugeda", "saidikaart": "Saidikaart"}.get(v["id"], e(v["id"])))
                                   for v in vaated if not v["menuu"] and v["id"] != "avaleht" and v["olek"] == "valmis"]
    return (f'<details class="mega"><summary><span class="mega-arvuti">Kõik teemad</span><span class="mega-tel">Menüü</span></summary>'
            f'<nav class="mega-paneel" aria-label="Kõik teemad"><div class="mega-ruut">{"".join(veerud)}</div>'
            f'<p class="mega-lisa">{" · ".join(lisa)}</p></nav></details>')


def _lehel(nav, cls):
    return nav.replace('<nav aria-label="Sellel lehel">', f'<nav class="lehel {cls}" aria-label="Sellel lehel">', 1)


LEHEL_MIN = 4  # Kadri 11.11.2026 (ülesehituse kontroll, A): alla nelja lingiga rida on lihtsalt üks nupurida rohkem


def _olemasolevad(nav, sisu):
    """„Sellel lehel“ reast välja lingid, mille plokki lehel pole (nt tühi uuringute plokk, Kadri 11.11.2026).
    Kui linke jääb alla LEHEL_MIN, kaob kogu rida: lühikesel lehel leiab lugeja jaotised kerides."""
    nav = re.sub(r'<li><a href="#([^"]+)">[^<]*</a></li>', lambda m: m.group(0) if f'id="{m.group(1)}"' in sisu else "", nav)
    return "" if nav.count("<li>") < LEHEL_MIN else nav


def _ploki_lopp(sisu, i):
    """Koht pärast välimist <div>-i, mille sees on indeks i (või i ise, kui see pole ühegi div-i sees)."""
    sugavus, algus = 0, None
    for t in re.finditer(r"<(/?)div\b[^>]*>", sisu[:i]):
        if t.group(1):
            sugavus -= 1
        else:
            if sugavus == 0:
                algus = t.start()
            sugavus += 1
    if sugavus <= 0:
        return i
    for t in re.finditer(r"<(/?)div\b[^>]*>", sisu[i:]):
        sugavus += -1 if t.group(1) else 1
        if sugavus == 0:
            return i + t.end()
    return i


JAGA = " ¦ "


def _lause(t):
    """Teine pool algab suure tähega (ka siis, kui ees on silt) ja lõpeb punktiga."""
    t = t.strip()
    m = re.match(r"((?:<[^>]+>)*)(.)", t, re.S)
    if m:
        t = t[:m.start(2)] + m.group(2).upper() + t[m.end(2):]
    return t if re.search(r"[.!?](?:</[^>]+>)*$", t) else t + "."


def lyhenda_pealkirjad(sisu):
    """Lühike pealkiri ja detail eraldi (Kadri 10.11.2026: pealkirjad olid liiga pikad ja lärmakad).

    Mallis eraldab „ ¦ “ pealkirja (vastus lühidalt) ja detaili. h1 detail läheb sissejuhatuse (lead) algusesse,
    h2 detail pealkirja alla eraldi reale (p.h-lisa). Nii jäävad andmetest arvutatud jupid alles, aga pealkiri on lühike.
    """
    def h1(m):
        pais, lyhike, lisa, lopp, lead_ava, lead = m.groups()
        if lead_ava:
            return f"{pais}{lyhike}{lopp}{lead_ava}{_lause(lisa)} {lead}</p>"
        return f'{pais}{lyhike}{lopp}\n    <p class="lead">{_lause(lisa)}</p>'
    sisu = re.sub(r'(<h1[^>]*>)(.*?)' + re.escape(JAGA) + r'(.*?)(</h1>)(?:(\s*<p class="lead">)(.*?)</p>)?', h1, sisu, flags=re.S)
    sisu = re.sub(r'(<h2[^>]*>)(.*?)' + re.escape(JAGA) + r'(.*?)(</h2>)',
                  lambda m: f'{m.group(1)}{m.group(2)}{m.group(4)}<p class="h-lisa">{_lause(m.group(3))}</p>', sisu, flags=re.S)
    if JAGA.strip() in sisu:
        i = sisu.index(JAGA.strip())
        raise ValueError("Pealkirja eraldaja „¦“ jäi lehele: " + sisu[max(0, i - 80):i + 80])
    return sisu


def leht(A, vaated, vaade, sisu, title, fail=None):
    fail = fail or vaade["fail"]
    sisu = lyhenda_pealkirjad(sisu)
    # Navigatsioon B (Kadri 6.11.2026 22:51): päises teemad ja „Kõik teemad“; teema alamlehed sakkidena pealkirja all;
    # „Sellel lehel“ on igal ekraanil üks rida sakkide all, mis kerimisel jääb päise alla kleepuma
    # (Kadri lukustas 8.11.2026 21:24 R1; parem veerg kitsendas sisu).
    teema = next((v for v in vaated if v["id"] == vaade["teema"]), None) if vaade.get("teema") else vaade
    sakid = alamlehed(teema, fail) if teema.get("alamlehed") else ""
    m = re.search(r'<nav aria-label="Sellel lehel">.*?</nav>', sisu, re.S)
    lehel = _olemasolevad(m.group(0), sisu) if m else ""
    if m and not lehel:
        sisu = sisu[:m.start()] + sisu[m.end():]
    if lehel:
        # Kleepuv rida peab olema <main> otsene laps (sticky töötab ainult vanema piires), seega läheb see
        # pealkirjaploki (div.pea) järele; sakid jäävad oma kohale.
        sisu = sisu[:m.start()] + sakid + sisu[m.end():]
        k = _ploki_lopp(sisu, m.start())
        sisu = sisu[:k] + _lehel(lehel, "lehel-rida") + sisu[k:]
    elif sakid:
        lead = re.search(r'<p class="lead">.*?</p>', sisu, re.S)
        k = lead.end() if lead else sisu.index("</h1>") + 5
        sisu = sisu[:k] + sakid + sisu[k:]
    avaleht = next(v for v in vaated if v["id"] == "avaleht")
    kodu = avaleht["fail"] if avaleht["olek"] == "valmis" else "saidikaart.html"
    if vaade["id"] != "avaleht":  # rada: kus lugeja on (Avaleht › Töö › Uuringud)
        osad = [f'<a href="{kodu}">Avaleht</a>']
        nimi = teema["menuu"] or {"saidist": "Mis see sait on", "kuidas": "Kuidas lugeda", "saidikaart": "Saidikaart"}.get(teema["id"], teema["id"])
        alam = next((s for s in teema.get("alamlehed", []) if s["fail"] == fail), None)
        osad.append(f'<a href="{teema["fail"]}">{e(nimi)}</a>' if alam and fail != teema["fail"] else f"<span>{e(nimi)}</span>")
        if alam and fail != teema["fail"]:
            osad.append(f'<span>{e(alam["nimi"])}</span>')
        k = sisu.index("<h1")
        sisu = sisu[:k] + f'<nav class="rada" aria-label="Asukoht"><p>{" › ".join(osad)}</p></nav>' + sisu[k:]
    nimed = {"saidist": "Mis see sait on", "kuidas": "Kuidas lugeda", "saidikaart": "Saidikaart"}
    jalus_lingid = [f'<a href="{v["fail"]}">{e(v["menuu"] or nimed.get(v["id"], v["id"]))}</a>'
                    for v in vaated if not v["menuu"] and v["id"] != "avaleht" and v["olek"] == "valmis"]
    kavas = [v for v in vaated if not v["menuu"] and v["olek"] != "valmis" and v["id"] != "avaleht"]
    jalus_lingid += [f'{e("Kuidas lugeda" if v["id"] == "kuidas" else v["id"])} (tulekul)' for v in kavas]
    import margendid  # andmestiku märgendid (Kadri 27.11.2026, nähtavus otsingus)
    andmestik = margendid.jsonld(A, fail)
    kirjeldus = (vaade.get("kusimus") or "") + " Tehisaru kasutus ja mõju Eestis ja Euroopas: numbrid otse avalikest allikatest koos kuupäevaga."
    return f"""<!doctype html>
<html lang="et" data-t="1">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="claude:viewport-fit-sides" content="cover">
<meta name="copyright" content="© {autori_aastad()} {e(AUTOR)}">
<title>{e(title)}</title>
<meta name="description" content="{e(kirjeldus)}">
<link rel="canonical" href="{aadress(fail)}">
{andmestik}
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;700&amp;family=Inter:wght@400;600;700&amp;display=swap">
{TEEMA_JS}
<link rel="stylesheet" href="stiil.css?v={_v("stiil.css")}">
<script src="sait.js?v={_v("sait.js")}"></script>
{ANALYYTIKA_JS}
</head>
<body>
<a class="skip" href="#sisu">Mine sisu juurde</a>
<header class="top">
  <div class="wrap">
    <div class="top-1">
      <a class="mark" href="{kodu}"{' aria-current="page"' if vaade["id"] == "avaleht" else ""}>Tehisaru seire</a>
      {mega(vaated, fail, kodu, vaade.get("teema") or vaade["id"])}
      <button class="teema" type="button" aria-label="Teema" title="Teema"><svg class="pool" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><circle cx="12" cy="12" r="8"/><path d="M12 4a8 8 0 0 1 0 16Z" fill="currentColor"/></svg><svg class="kuu" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5Z"/></svg><svg class="paike" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><circle cx="12" cy="12" r="4"/><path d="M12 2.5v2M12 19.5v2M2.5 12h2M19.5 12h2M5.3 5.3l1.4 1.4M17.3 17.3l1.4 1.4M5.3 18.7l1.4-1.4M17.3 6.7l1.4-1.4"/></svg></button>
    </div>
    <nav aria-label="Teemad" class="paisteemad"><ul class="menu">{menuu(vaated, vaade.get("teema") or vaade["id"])}</ul></nav>
  </div>
</header>
<main id="sisu" class="wrap">
{sisu}
</main>
<footer class="jalus">
  <div class="wrap">
    <p>Tehisaru seire koondab avalikku statistikat ja uuringuid tehisaru kasutusest Eestis ja Euroopas. Iga number on avalikust allikast koos lingi ja kuupäevaga.</p>
    <p>{" · ".join(jalus_lingid)}</p>
    <p class="autor">© {autori_aastad()} <a href="saidist.html#autor">{e(AUTOR)}</a></p>
  </div>
</footer>
</body>
</html>
"""
