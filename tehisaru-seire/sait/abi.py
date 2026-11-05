"""Vaadete ühised tükid: lehe algus, vastuse kast, pealkirja kontroll ja vaatelink.

Pealkirjad, mida mall {näitaja|riik|aasta|vorm} ei kata (loendid, tähtajad, uuringute numbrid), kontrollitakse siin:
ehitaja arvutab väärtuse andmetest ja kontrolli() kukub, kui vaated.json pealkiri ütleb muud.
"""
from andmekiht import AndmeViga
from komponendid import e
from kest import sellel_lehel
from pealkiri import taida

ARVSONAD = {0: "null", 1: "üks", 2: "kaks", 3: "kolm", 4: "neli", 5: "viis", 6: "kuus", 7: "seitse", 8: "kaheksa",
            9: "üheksa", 10: "kümme"}
SEESTYTLEV = {2: "kahest", 3: "kolmest", 4: "neljast", 5: "viiest", 6: "kuuest", 7: "seitsmest", 8: "kaheksast",
              9: "üheksast", 10: "kümnest"}


def kontrolli(vaade, *jupid):
    """Iga jupp (andmetest arvutatud tekst) peab olema vaate h1 mallis. Nii ei jää pealkiri andmetest maha."""
    for j in jupid:
        if j.lower() not in vaade["h1"].lower():
            raise AndmeViga(f"Vaate {vaade['id']} pealkiri ei klapi andmetega: oodatud „{j}“, mall: {vaade['h1']}")


def vastus(read, silt="Peamised numbrid"):
    """read: [(suur_html, tekst_html, allikas_html)]"""
    osad = "".join(f'<div><span class="big">{b}</span><p>{t}</p><p class="src">{s}</p></div>' for b, t, s in read)
    return f'<aside class="vastus" aria-label="{e(silt)}">{osad}</aside>'


def pea(A, vaade, lead, lingid, vastuse_read):
    return f"""
<div class="pea">
  <div class="pea-tekst">
    <h1>{taida(vaade["h1"], A)}</h1>
    <p class="lead">{lead}</p>
    {sellel_lehel(lingid)}
  </div>
  {vastus(vastuse_read)}
</div>"""


def link(vaated, vid, tekst, ankur=""):
    """Link teisele vaatele ainult siis, kui see on valmis; muidu tavaline tekst (ehitus ei luba katkist linki)."""
    v = next((x for x in (vaated or []) if x["id"] == vid), None)
    if v and v["olek"] == "valmis":
        return f'<a href="{v["fail"]}{"#" + ankur if ankur else ""}">{e(tekst)}</a>'
    return e(tekst)


def a(url, tekst):
    if not url:
        raise AndmeViga(f"Lingil „{tekst}“ puudub aadress")
    return f'<a href="{e(url)}">{e(tekst)}</a>'
