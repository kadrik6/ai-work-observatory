"""Pealkirja mallid: number tuleb vaatlusest, mitte käsitsi kirjutatud tekstist.

Mall viitab vaatlusele kujul {näitaja|riik|aasta|vorm}:
  aasta  täisarv, „uusim“ (mis tahes allikas) või „uusim:alus“ (ainult ELiga võrreldav võrdlusalus)
  vorm   p0 / p1 / p2 = väärtus 0, 1 või 2 komakohaga; a = vaatluse aasta; koht = koht ELi 27 riigi seas
**fraas** on pealkirja fookusfraas (paks ja sinine).
Kui viidatud vaatlust pole, tõstab täitmine AndmeViga ja ehitus peatub.
"""
import html
import re

import andmekiht as andmed

MALL = re.compile(r"\{([a-z0-9-]+)\|([A-Z0-9_]+)\|([a-z0-9:]+)\|([a-z0-9]+)\}")


def pr(x, k=1):
    """Eesti kirjaviis, ümardus pooled üles (19,95 → 20,0), mitte kahendmurru järgi."""
    from decimal import ROUND_HALF_UP, Decimal
    d = Decimal(str(x)).quantize(Decimal(1).scaleb(-k), rounding=ROUND_HALF_UP)
    return f"{d:.{k}f}".replace(".", ",").replace("-", "−")


def vaartus(A, naitaja, geo, aasta, vorm):
    a = aasta if aasta.startswith("uusim") else int(aasta)
    v = andmed.leia(A, naitaja, geo, a)
    if vorm in ("p0", "p1", "p2"):
        return pr(v["vaartus"], int(vorm[1]))
    if vorm == "a":
        return str(v["aasta"])
    if vorm == "koht":
        return str(andmed.koht(A, naitaja, geo, v["aasta"]))
    raise andmed.AndmeViga(f"Tundmatu vorm {vorm!r} mallis")


def taida(mall, A):
    """Mall → HTML. Viited asendatakse, tekst escape'itakse, **fraas** → <b>fraas</b>."""
    if mall is None:
        return None
    tukid, eelmine = [], 0
    for m in MALL.finditer(mall):
        tukid.append(html.escape(mall[eelmine:m.start()], quote=False))
        tukid.append(vaartus(A, *m.groups()))
        eelmine = m.end()
    tukid.append(html.escape(mall[eelmine:], quote=False))
    tekst = "".join(tukid)
    if "{" in tekst or "}" in tekst:
        raise andmed.AndmeViga(f"Mallis on viide, mida ei saanud täita: {mall}")
    if tekst.count("**") % 2:
        raise andmed.AndmeViga(f"Mallis on paaritu **: {mall}")
    return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", tekst)


def viited(mall):
    """Kõik vaatlused, millele mall viitab (testide jaoks)."""
    return MALL.findall(mall or "")
