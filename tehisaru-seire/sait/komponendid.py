"""Lehe komponendid: skaala (tulbad ja hantlid), tabel, allikarida, faktid, „Mida see ei näita“.

Graafikud tehakse ehitamise ajal staatiliseks HTML-iks (div-tulbad, mitte JS). Nii jääb tekst päris suuruseks ka
390 px laiusel, töötab ilma JavaScriptita ja on testitav. Skaala keeldub panemast eri võrreldavusklassi numbreid
samale teljele: jaga_klassid() paneb võrdlusaluse skaalale ja teised loendisse skaala alla.
"""
import html

from andmekiht import EL, AndmeViga

RIIGID = {
    "EE": "Eesti", "FI": "Soome", "SE": "Rootsi", "DK": "Taani", "NO": "Norra", "DE": "Saksamaa", "NL": "Holland",
    EL: "EL keskmine", "UK": "Ühendkuningriik", "US": "USA", "CA": "Kanada",
    "AT": "Austria", "BE": "Belgia", "BG": "Bulgaaria", "CY": "Küpros", "CZ": "Tšehhi", "EL": "Kreeka",
    "ES": "Hispaania", "FR": "Prantsusmaa", "HR": "Horvaatia", "HU": "Ungari", "IE": "Iirimaa", "IT": "Itaalia",
    "LT": "Leedu", "LU": "Luksemburg", "LV": "Läti", "MT": "Malta", "PL": "Poola", "PT": "Portugal",
    "RO": "Rumeenia", "SI": "Sloveenia", "SK": "Slovakkia",
}
MARGENDID = {"b": "aegrea katkestus", "p": "esialgne", "e": "hinnang", "d": "määratlus erineb", "ep": "hinnang, esialgne"}
KUUD = ["jaanuar", "veebruar", "märts", "aprill", "mai", "juuni", "juuli", "august", "september", "oktoober",
        "november", "detsember"]


class VorreldavusViga(AndmeViga):
    """Eri võrreldavusklassi numbrid ühel teljel."""


def e(t):
    return html.escape(str(t), quote=True)


def pr(x, k=1):
    """Eesti kirjaviis, ümardus pooled üles (19,95 → 20,0), mitte kahendmurru järgi."""
    from decimal import ROUND_HALF_UP, Decimal
    d = Decimal(str(x)).quantize(Decimal(1).scaleb(-k), rounding=ROUND_HALF_UP)
    return f"{d:.{k}f}".replace(".", ",").replace("-", "−")


def kp(iso):
    """2026-09-16 → 16.09.2026; 2026-06 → juuni 2026"""
    osad = str(iso).split("-")
    if len(osad) == 3:
        return f"{int(osad[2])}.{osad[1]}.{osad[0]}"
    if len(osad) == 2:
        return f"{KUUD[int(osad[1]) - 1]} {osad[0]}"
    return str(iso)


def riik(g):
    return RIIGID.get(g, g)


def margend(m):
    return f' <small>{e(MARGENDID.get(m, m))}</small>' if m else ""


def uks_klass(vaatlused):
    klassid = {v["klass"] for v in vaatlused}
    if len(klassid) > 1:
        raise VorreldavusViga(f"Ühel teljel on eri võrreldavusklassid: {sorted(klassid)} "
                              f"({sorted({(v['naitaja'], v['geo'], v['aasta']) for v in vaatlused})})")


def jaga_klassid(vaatlused, klass="alus"):
    """Skaalale ainult üks klass, teised loendina skaala alla märkega „ei ole otse võrreldav“."""
    return [v for v in vaatlused if v["klass"] == klass], [v for v in vaatlused if v["klass"] != klass]


def _telg(alg, lopp, samm, uhik, k=0):
    tick, x = [], alg
    while x <= lopp + 1e-9:
        tick.append(f'<span style="left:{(x - alg) / (lopp - alg) * 100:.2f}%">{pr(x, k)}</span>')
        x += samm
    return f'<div class="telg" aria-hidden="true"><span></span><span class="rada">{"".join(tick)}</span><span>{e(uhik)}</span></div>'


def ribad(vaatlused, lopp, fookus="EE", viide=None, viite_nimi="", samm=10, uhik="%", viite_liik=""):
    """Sorditud horisontaalsed tulbad nullist. vaatlused peavad olema ühes võrreldavusklassis."""
    uks_klass(vaatlused)
    jarjest = sorted(vaatlused, key=lambda v: -v["vaartus"])
    out = ['<div class="ribad" aria-hidden="true">']
    for v in jarjest:
        liik = "fookus" if v["geo"] == fookus else ""
        joon = f'<i class="joon {viite_liik}" style="left:{viide / lopp * 100:.2f}%"></i>' if viide is not None else ""
        pealkiri = f'{riik(v["geo"])} {v["aasta"]}: {pr(v["vaartus"])}{uhik} ({v["allikas"]})'
        out.append(f'<div class="rida {liik}" title="{e(pealkiri)}"><span class="n">{e(riik(v["geo"]))}</span><span class="rada">'
                   f'<span class="tulp" style="width:{v["vaartus"] / lopp * 100:.2f}%"></span>{joon}</span>'
                   f'<span class="v">{pr(v["vaartus"])}</span></div>')
    out.append(_telg(0, lopp, samm, uhik))
    out.append("</div>")
    if viide is not None:
        out.append(f'<p class="margis"><i class="{viite_liik}"></i>{e(viite_nimi)}</p>')
    return "".join(out)


def hantlid(paarid, alg, lopp, samm, uhik, k=1, fookus="EE", ref=EL, viide=None, viite_nimi="", lisa=None):
    """Kaks aastat ühel teljel. paarid: [(vana, uus)] vaatlusi; kõik ühes klassis. lisa: {geo: vaatlus} kriipsring."""
    koik = [v for p in paarid for v in p] + list((lisa or {}).values())
    uks_klass(koik)
    pos = lambda x: (x - alg) / (lopp - alg) * 100  # noqa: E731
    out = ['<div class="ribad hantlid" aria-hidden="true">']
    for v0, v1 in sorted(paarid, key=lambda p: -p[1]["vaartus"]):
        g = v1["geo"]
        liik = "fookus" if g == fookus else ("ref" if g == ref else "")
        a, b = sorted((pos(v0["vaartus"]), pos(v1["vaartus"])))
        joon = f'<i class="joon siht" style="left:{pos(viide):.2f}%"></i>' if viide is not None else ""
        lv = (lisa or {}).get(g)
        lisa_html = f'<span class="tapp lisa" style="left:{pos(lv["vaartus"]):.2f}%"></span>' if lv else ""
        pealkiri = f'{riik(g)}: {v0["aasta"]} {pr(v0["vaartus"], k)} → {v1["aasta"]} {pr(v1["vaartus"], k)} {uhik}'
        out.append(f'<div class="rida {liik}" title="{e(pealkiri)}"><span class="n">{e(riik(g))}</span><span class="rada">{joon}'
                   f'<span class="hant" style="left:{a:.2f}%;width:{b - a:.2f}%"></span>'
                   f'<span class="tapp vana" style="left:{pos(v0["vaartus"]):.2f}%"></span>'
                   f'<span class="tapp uus" style="left:{pos(v1["vaartus"]):.2f}%"></span>{lisa_html}</span>'
                   f'<span class="v">{pr(v0["vaartus"], k)} → {pr(v1["vaartus"], k)}</span></div>')
    out.append(_telg(alg, lopp, samm, uhik, 0 if samm >= 1 else 1))
    out.append("</div>")
    if viide is not None:
        out.append(f'<p class="margis"><i class="siht"></i>{e(viite_nimi)}</p>')
    return "".join(out)


def leiu_ribad(read, lopp, fookus_silt, samm=10, uhik="%"):
    """Uuringu numbrid (mitte statistika vaatlused). read: [(silt, väärtus või None, olulisus)]."""
    out = []
    for silt, v, ol in read:
        liik = "fookus" if silt == fookus_silt else ""
        vt = "ei olnud oluline" if v is None else "+" + pr(v) + ("*" if ol == "nõrk" else "")
        out.append(f'<div class="rida {liik}"><span class="n">{e(silt)}</span><span class="rada">'
                   f'<span class="tulp" style="width:{(v or 0) / lopp * 100:.2f}%"></span></span>'
                   f'<span class="v">{e(vt)}</span></div>')
    return "".join(out)


def telg(alg, lopp, samm, uhik):
    return _telg(alg, lopp, samm, uhik)


def tabel(pais, read, fookus_rida=None, piir=False, pealdis="", numbrid=None):
    """numbrid: veergude indeksid, mis joondatakse paremale (vaikimisi kõik peale esimese)."""
    numbrid = set(range(1, len(pais))) if numbrid is None else set(numbrid)
    th = "".join(f'<th scope="col"{" class=v" if i in numbrid else ""}>{e(p)}</th>' for i, p in enumerate(pais))
    tr = []
    for i, r in enumerate(read):
        kl = ' class="fookus"' if fookus_rida is not None and i == fookus_rida else ""
        tr.append(f"<tr{kl}>" + "".join(f'<td{" class=v" if j in numbrid else ""}>{c}</td>' for j, c in enumerate(r)) + "</tr>")
    cap = f'<caption class="peidus">{e(pealdis)}</caption>' if pealdis else ""
    return (f'<div class="tbl"><table{" data-piir" if piir else ""}>{cap}<thead><tr>{th}</tr></thead>'
            f'<tbody>{"".join(tr)}</tbody></table></div>')


def allikarida(osad):
    """osad: [(tekst, url, lisatekst)]"""
    jupid = []
    for tekst, url, lisa in osad:
        if not url:
            raise AndmeViga(f"Allikal „{tekst}“ puudub link")
        jupid.append(f'<a href="{e(url)}">{e(tekst)}</a>' + (f" ({e(lisa)})" if lisa else ""))
    return '<p class="allikas">Allikas: ' + "; ".join(jupid) + ".</p>"


def faktid(read):
    """read: [(märgis, klass, html)]; klass ∈ {"", "risk", "s"}."""
    return '<ul class="faktid">' + "".join(
        f'<li><span class="mark-l {k}">{e(m)}</span><span>{t}</span></li>' for m, k, t in read) + "</ul>"


def vastavus(hinnang, tekst):
    """„Kas andmed vastavad küsimusele?“ jah / osaliselt / ei, joon ja sõna."""
    return (f'<p class="vastab {e(hinnang)}"><span>Kas andmed vastavad küsimusele?</span> '
            f'<b>{e(hinnang.capitalize())}.</b> {tekst}</p>')


def ei_naita(piirangud, lisa=""):
    return f'<ul>{"".join(f"<li>{e(p)}</li>" for p in piirangud)}</ul>{lisa}'
