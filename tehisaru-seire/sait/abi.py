"""Vaadete ühised tükid: lehe algus, vastuse kast, pealkirja kontroll ja vaatelink.

Pealkirjad, mida mall {näitaja|riik|aasta|vorm} ei kata (loendid, tähtajad, uuringute numbrid), kontrollitakse siin:
ehitaja arvutab väärtuse andmetest ja kontrolli() kukub, kui vaated.json pealkiri ütleb muud.
"""
from andmekiht import AndmeViga
from komponendid import e
from kest import sellel_lehel
from pealkiri import taida

ARVSONAD = {0: "null", 1: "üks", 2: "kaks", 3: "kolm", 4: "neli", 5: "viis", 6: "kuus", 7: "seitse", 8: "kaheksa",
            9: "üheksa", 10: "kümme", 11: "üksteist", 12: "kaksteist", 13: "kolmteist",
            14: "neliteist", 15: "viisteist"}
SEESTYTLEV = {2: "kahest", 3: "kolmest", 4: "neljast", 5: "viiest", 6: "kuuest", 7: "seitsmest", 8: "kaheksast",
              9: "üheksast", 10: "kümnest", 11: "üheteistkümnest", 12: "kaheteistkümnest",
              13: "kolmeteistkümnest", 14: "neljateistkümnest", 15: "viieteistkümnest"}


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


class Jagatud(str):
    """Vaade, mis on jagatud alamlehtedeks (Kadri 6.11.2026: pikad teemad eraldi lehtedeks).

    Sõnena on see kõigi alamlehtede sisu kokku (testid saavad otsida nagu varem); .lehed = {fail: sisu}.
    """
    lehed: dict

    def __new__(cls, lehed):
        s = super().__new__(cls, "".join(lehed.values()))
        s.lehed = lehed
        return s


def jaga(A, vaade, lead, ree, plokid):
    """plokid: [(võti, [(ankur, lühike nimi)], html)]. vaade["alamlehed"]: [{fail, nimi, h1?, lead?, jaotised:[võti]}].

    Esimene alamleht saab vaate pealkirja ja numbrikastid. Tühi html (nt andmeid pole) jäetakse välja.
    Ehitus kukub, kui mõni plokk jääb alamlehest välja või on kahes kohas.
    """
    plokid = [p for p in plokid if p[2].strip()]
    alamad = [s for s in vaade.get("alamlehed", []) if "vaade" not in s]  # {"vaade": id} = teine vaade sama teema all
    if not alamad:
        return pea(A, vaade, lead, [l for _, ll, _ in plokid for l in ll], ree) + "".join(h for *_, h in plokid)
    voti = {p[0]: p for p in plokid}
    kasutatud = [k for s in alamad for k in s["jaotised"] if k in voti]
    if sorted(kasutatud) != sorted(voti) or len(set(kasutatud)) != len(kasutatud):
        raise AndmeViga(f"Vaate {vaade['id']} alamlehed ei jaga plokke täpselt: {sorted(voti)} vs {kasutatud}")
    lehed = {}
    for i, s in enumerate(alamad):
        oma = [voti[k] for k in s["jaotised"] if k in voti]
        lingid = [l for _, ll, _ in oma for l in ll]
        lingid = lingid if len(lingid) > 1 else []
        if i == 0:
            algus = pea(A, vaade, lead, lingid, ree)
        else:
            algus = f"""
<div class="pea yks alam-pea">
  <div class="pea-tekst">
    <h1>{e(s["h1"])}</h1>
    <p class="lead">{s["lead"]}</p>
    {sellel_lehel(lingid) if lingid else ""}
  </div>
</div>"""
        lehed[s["fail"]] = algus + "".join(h for *_, h in oma)
    return Jagatud(lehed)


def seotud(vaated, lingid):
    """Rida „Seotud“ lehe lõpus (Kadri 6.11.2026 22:27, ettepanek 8): lingid [(vaate id, tekst)] lähedastele teemadele."""
    li = " · ".join(link(vaated, vid, tekst) for vid, tekst in lingid)
    return f'<nav class="seotud" aria-label="Seotud teemad"><p><span>Seotud</span> {li}</p></nav>'
