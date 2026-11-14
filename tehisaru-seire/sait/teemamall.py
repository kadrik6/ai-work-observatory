"""Teemamall A „Teemakeskus“ (Kadri 8.11.2026, näidis 83zfFGjWYZpWwJGznNN7yn #A-too-arvuti).

Igal teemalehel on sama plokkide järjekord: number (KPI-plaadid päises), graafik („Uuri andmeid“ sakkides),
uuringud, väited, reeglid ning allikad ja värskus. Väited ja reeglid on teema juures lühidalt; täisnimekiri
jääb Usalduse ja Tehisaru määruse alla. Vanad ankrud jäävad sakkide sisse alles ja sait.js avab õige saki.
"""
import datetime
import re

from abi import link, sonaga
from andmekiht import AndmeViga
from komponendid import e, kp
from lehed_usaldus import RASKUS, _raskus

VARSKE_PAEVI = 92


def kys(kysimus, vastus):
    """Ploki pealkiri: lugeja küsimus ja vastus (Kadri 14.11.2026: iga plokk vastab ühele küsimusele).
    Küsimus on tavakirjas, vastus paksus. Mõlemad on HTML, kutsuja vastutab e() eest."""
    return f'<span class="kys">{kysimus}</span> <b>{vastus}</b>'


def andmesakid(tid, pealkiri, alam, sakid):
    """sakid: [(saki id, nimi, html)]. Esimene sakk on avatud; ülejäänud on peidus, aga nende ankrud jäävad lehele."""
    sakid = [s for s in sakid if s[2].strip()]
    if len(sakid) < 2:
        raise AndmeViga(f"Teema {tid}: andmesakke peab olema vähemalt kaks")
    nupud = "".join(
        f'<button type="button" role="tab" id="sakk-{sid}-n" aria-controls="sakk-{sid}" '
        f'aria-selected="{"true" if i == 0 else "false"}">{e(nimi)}</button>'
        for i, (sid, nimi, _) in enumerate(sakid))
    paneelid = "".join(
        f'<div role="tabpanel" id="sakk-{sid}" aria-labelledby="sakk-{sid}-n" class="sakk-sisu"{"" if i == 0 else " hidden"}>{html}</div>'
        for i, (sid, _, html) in enumerate(sakid))
    return f"""
<section class="jaotis teema-andmed" id="andmed" aria-labelledby="h-andmed">
  <header>
    <h2 id="h-andmed">{pealkiri}</h2>
    <p class="alam">{alam}</p>
  </header>
  <div class="p-tabs andmesakid" role="tablist" aria-label="Andmed">{nupud}</div>
  {paneelid}
</section>"""


def uuringute_plokk(vaated, read, lingid, vastus=None):
    """read: [(silt, tekst, vaate id, ankur)]; lingid: [(vaate id, tekst, ankur)] alamlehtedele.

    Tühja plokki ei näidata (Kadri 11.11.2026): „pole veel hinnatud“ + link mujale lisas ainult nuppe ja segadust.
    „Sellel lehel“ rida jätab puuduva ploki lingi ise välja (kest.leht).
    """
    if not read:
        return ""
    li = "".join(f'<li><span class="k">{e(s)}</span><span>{t} {link(vaated, vid, "Vaata", ank)}</span></li>' for s, t, vid, ank in read)
    ll = " · ".join(link(vaated, vid, t, ank) for vid, t, ank in lingid)
    return f"""<section class="pn" id="t-uuringud" aria-labelledby="h-t-uuringud">
  <h2 id="h-t-uuringud">{kys("Mida uuringud leidsid?", vastus or (f"{sonaga(len(read)).capitalize()} uuring" + ("ut" if len(read) != 1 else "") + ", igaüks ühe lausega"))}</h2>
  <ul class="t-loend">{li}</ul>
  <p class="lingid">{ll}</p>
</section>"""


def vaidete_plokk(A, vaated, tid, teema_jargi, n=3):
    """Teema väited raskuse järgi (kõige eksitavam enne); kõik väited jäävad Usalduse alla."""
    vv = sorted((v for v in A["vaited"] if teema_jargi(v) == tid), key=lambda v: (_raskus(v), v["kuupaev"]))
    if not vv:
        return ""  # tühja plokki ei näidata (Kadri 11.11.2026); kõik väited on Usalduse all
    muud = sum(_raskus(v) == 0 for v in vv)
    read = "".join(
        f'<li><span class="verd {RASKUS[_raskus(v)][1]}">{e(v["hinnang"])}</span>'
        f'<span>{e(v["vaide"])}<small>{e(v["valjaanne"])}{", " + kp(v["kuupaev"]) if v["kuupaev"] else ""}</small>'
        f'<small class="oige">{e(v["oige_lause"] or v["selgitus"])}</small></span></li>'
        for v in vv[:n])
    return f"""<section class="pn" id="t-vaited" aria-labelledby="h-t-vaited">
  <h2 id="h-t-vaited">{kys("Mida meedias väidetakse?", f"{len(vv)} kontrollitud, " + (f"{muud} ütleb muud kui allikas" if muud else "ükski ei ütle muud kui allikas"))}</h2>
  <ul class="t-vaited">{read}</ul>
  <p class="lingid">{link(vaated, "kas-tosi", "Kõik väited ja hinnangute selgitus (Usaldus)")}</p>
</section>"""


def _reeglite_vastus(kehtib, ees):
    r = lambda n: f"{sonaga(n)} {'reegel' if n == 1 else 'reeglit'}"  # noqa: E731
    osad = ([f"{r(kehtib)} kehtib juba"] if kehtib else []) + ([f"{r(ees)} jõustub hiljem"] if ees else [])
    t = " ja ".join(osad)
    return t[:1].upper() + t[1:]


def reeglite_plokk(A, vaated, ids, tana=None):
    tana = tana or datetime.date.today().isoformat()
    O = {o["id"]: o for o in A["otsused"]}
    puudu = [i for i in ids if i not in O]
    if puudu:
        raise AndmeViga(f"Teemaploki reeglid puuduvad: {puudu}")
    read, n_kehtib = [], 0
    for i in ids:
        o = O[i]
        kuup = o["kuupaev"] + ("-01" if o.get("tapsus") == "kuu" else "")
        kehtib = kuup < tana
        n_kehtib += kehtib
        read.append(f'<li><span class="k">{kp(o["kuupaev"]) if len(o["kuupaev"]) == 10 else e(o["kuupaev"])}</span>'
                    f'<span><b>{e(o["nimi"])}</b> <span class="chip{"" if kehtib else " exp"}">{"kehtib" if kehtib else "ees"}</span>'
                    f'<small>{e(o["mida_tahendab"])}</small></span></li>')
    return f"""<section class="pn" id="t-reeglid" aria-labelledby="h-t-reeglid">
  <h2 id="h-t-reeglid">{kys("Mis reeglid kehtivad?", _reeglite_vastus(n_kehtib, len(ids) - n_kehtib))}</h2>
  <ul class="t-loend">{"".join(read)}</ul>
  <p class="lingid">{link(vaated, "reeglid", f"Kõik {len(O)} tähtaega (Tehisaru määrus)", "tahtajad")}</p>
</section>"""


def allikate_plokk(read):
    """read: [(nimi, url, kuupäev ISO / AAAA-KK või None, märkus[, näidatav periood])].
    Värske = kuni 92 päeva enne kõige uuemat kuupäeva."""
    read = [(r[0], r[1], (r[2] + "-01" if r[2] and len(r[2]) == 7 else r[2]), r[3], r[4] if len(r) > 4 else None) for r in read]
    kuupaevad = [r[2] for r in read if r[2]]
    if not kuupaevad:
        raise AndmeViga("Allikate plokis pole ühtki kuupäeva")
    viimane = datetime.date.fromisoformat(max(kuupaevad))
    ridu = []
    for nimi, url, kuup, markus, naita in read:
        if kuup:
            varske = (viimane - datetime.date.fromisoformat(kuup)).days <= VARSKE_PAEVI
            tapp = f'<span class="v-tapp{"" if varske else " vana"}" aria-hidden="true"></span>{e(naita) if naita else kp(kuup)}'
        else:
            tapp = '<span class="m-puud">kuupäev puudub</span>'
        nimi_h = f'<a href="{e(url)}">{e(nimi)}</a>' if url else e(nimi)
        ridu.append(f'<tr><td>{nimi_h}{f"<small>{e(markus)}</small>" if markus else ""}</td><td class="n"><span class="kpv">{tapp}</span></td></tr>')
    return f"""<section class="pn" id="t-allikad" aria-labelledby="h-t-allikad">
  <h2 id="h-t-allikad">{kys("Kust numbrid tulevad?", f"{len(read)} allikat, uusim {kp(max(kuupaevad))}")}</h2>
  <div class="tbl"><table><thead><tr><th scope="col">Andmed</th><th scope="col">Uuendatud</th></tr></thead>
  <tbody>{"".join(ridu)}</tbody></table></div>
  <p class="allikas">Täis ring = uuendatud viimase {VARSKE_PAEVI} päeva jooksul; tühi ring = vanem.</p>
</section>"""


def teema_lopp(uuringud, vaited, reeglid, allikad):
    return f'<div class="teema-lopp">{uuringud}{vaited}{reeglid}{allikad}</div>'


def esimene_lause(tekst):
    """Leiu esimene lause; punkt numbri järel („2024. aastal“) ei lõpeta lauset."""
    return re.split(r"(?<![0-9])\. ", tekst, maxsplit=1)[0].rstrip(".") + "."
