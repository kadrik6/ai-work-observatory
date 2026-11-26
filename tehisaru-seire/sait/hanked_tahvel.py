"""Hangete lehe töölaud (Kadri 19.11.2026 valis näidistest „A ja C koos“).

Leht algab tahvliga (kuus küsimust, iga rida üks pilk), siis „Kuidas hangitakse“ (kolm näitajat kolmes rühmas
ühel skaalal 0–100%) ja „Kust leida hea näide“ (kolm tingimust, igaühe juures teadmata osa). Praegused plokid
on lehe lõpus kokkupandult. Pealkirjad tulevad andmetest; kui andmed neid enam ei toeta, kukub ehitus (AndmeViga).
"""
from andmekiht import AndmeViga
from avaleht_tahvel import osariba
from avalik_tahvel import kaks_riba
from komponendid import e, kp, pr
import teema_tahvel as tt
from too_tahvel import jaotusriba

G = [("tehisaru ja andmed", "ai_andmed"), ("muud IT-hanked", "it_muud"), ("kõik hanked", "koik")]


def _arv(n):
    return f"{n:,}".replace(",", " ")


class Andmed:
    """Tahvli ja tunnuspiltide numbrid koos kontrollidega. H = sisu/hanked-leht.json, kasitsi = lehed_uudised.KASITSI."""

    def __init__(self, H, kasitsi):
        self.H, self.KASITSI = H, kasitsi
        V = self.V = H["hankimise_viis"]
        self.p0, self.p1 = V["periood"]
        rg = [g for _, g in G]
        self.kv = {g: 100 - V[g]["ainult_hind_osakaal"] for g in rg}
        self.uk = {g: V[g]["uks_pakkuja_osakaal"] for g in rg}
        self.ka = {g: V[g]["katkes_osakaal"] for g in rg}
        if not self.kv["ai_andmed"] > self.kv["it_muud"]:
            raise AndmeViga("Hangete tahvel: pealkiri ütleb, et kvaliteeti hinnatakse sagedamini kui teistes IT-hangetes")
        self.K = H["kontsentratsioon"]
        self.L = H["loend"]
        self.seis = H["seis"]["kuupaev"]
        self.u = H["aastad"][-1]
        self.inn = [r for r in H["aastad"] if r.get("innovatsioonimark_osakaal") is not None][-1]
        hm = H["hindamine"]["hindamine"]
        self.tul = hm["tulemused"][hm["valitud"]]
        self.a0, self.a1 = min(r["a"] for r in self.L), max(r["a"] for r in self.L)
        # Kontsentratsioon on arvutatud kogu loendi pealt (kõik aastad), mitte hankimise viisi perioodist.
        top = self.H["hankijad_top"][:self.K["top10_protsenti_hankijaid"]]
        if abs(sum(c for _, c in top) / len(self.L) * 100 - self.K["nende_osakaal"]) > 0.6:
            raise AndmeViga("Hangete tahvel: kontsentratsiooni alus ei ole kogu loend; hankijate perioodi silt oleks vale")
        # Head näited: kolm tingimust
        L = self.L
        self.kq = sum(1 for r in L if (r.get("kv") or 0) > 0 and not r.get("ah"))
        self.ah = sum(1 for r in L if r.get("ah"))
        self.pk2 = sum(1 for r in L if (r.get("pk") or 0) >= 2)
        self.pk1 = sum(1 for r in L if r.get("pk") is not None and r["pk"] < 2)
        self.kf = sum(1 for r in L if r.get("kat") is False)
        self.kt = sum(1 for r in L if r.get("kat") is True)
        self.hea = sum(1 for r in L if r.get("hea") == 3)
        tais = sum(1 for r in L if (r.get("kv") or 0) > 0 and not r.get("ah") and (r.get("pk") or 0) >= 2 and r.get("kat") is False)
        if self.hea != tais:
            raise AndmeViga(f"Hangete tahvel: heade näidete arv ({self.hea}) ei vasta kolmele tingimusele ({tais})")


# Vastus sõnaga (Kadri 25.11.2026): sõna tuleb numbrist. Piirid on teema_tahvel.sona_osa ja siin.
PIIR_HANKIJAD = (33, 50)   # kümnendiku hankijate osa hangetest, %: üle teise = peamiselt, üle esimese = suur osa
PIIR_TAPSUS = (60, 75, 90)  # täpsuse ja saagise väiksem väärtus, %


def sona_hankijad(p):
    return "Peamiselt mõni suur hankija" if p >= PIIR_HANKIJAD[1] else "Suur osa vähestelt hankijatelt" if p >= PIIR_HANKIJAD[0] else "Paljud eri hankijad"


def sona_siht(v, siht):
    return "Jah" if v >= siht else "Veel mitte"


def sona_tapsus(tapsus, saagis):
    m = min(tapsus, saagis)
    return "Väga täpne" if m >= PIIR_TAPSUS[2] else "Üsna täpne" if m >= PIIR_TAPSUS[1] else "Keskmiselt täpne" if m >= PIIR_TAPSUS[0] else "Ebatäpne"


def read(D):
    u, kv, uk, K, V, tul, KS = D.u, D.kv, D.uk, D.K, D.V, D.tul, D.KASITSI
    n_ai = u["ai_marksonaga"]
    n_and = u["ai_andmed"] - n_ai
    return [
        dict(kys="Kui palju riik tehisaru ja andmeid hangib?", ank="aastad", ava="Ava hanked aastate kaupa",
             sona=tt.sona_osa(u["ai_andmed_osakaal"]) + " hange", arv=str(u["ai_andmed"]),
             all=f'hanget {u["aasta"]}, {pr(u["ai_andmed_osakaal"])}% kõigist; seisuga {kp(D.seis)}',
             pilt=jaotusriba([("s", n_ai / u["ai_andmed"] * 100), ("m", n_and / u["ai_andmed"] * 100)], f"{n_ai} tehisaru, {n_and} andmed"),
             mrk=f'Tehisaru {n_ai}, andmed {n_and}. Aastaid ei võrrelda enne klassifikaatori uuendust.',
             liik="arvutatud", allikas="Riigihangete register", kuup=kp(D.seis)),
        dict(kys="Kas hinnatakse ka kvaliteeti?", ank="kuidas", ava="Vaata, kuidas hangitakse", sona=tt.sona_osa(kv["ai_andmed"]) + " hangetest",
             arv=f'{pr(kv["ai_andmed"], 0)}%', all=f"hangetest {D.p0}–{D.p1}",
             pilt=kaks_riba([("need", kv["ai_andmed"], True), ("IT", kv["it_muud"], False), ("kõik", kv["koik"], False)], h=44),
             mrk=f'Teistes IT-hangetes {pr(kv["it_muud"], 0)}%, kõigis hangetes {pr(kv["koik"], 0)}%. Ülejäänud hindasid ainult hinda.',
             liik="mõõdetud", allikas="Riigihangete register", kuup=f"{D.p0}–{D.p1}"),
        dict(kys="Kui sageli tuleb ainult üks pakkumus?", ank="kuidas", ava="Vaata, kuidas hangitakse", sona=tt.sona_osa(uk["ai_andmed"]) + " hangetest",
             arv=f'{pr(uk["ai_andmed"], 0)}%', all=f'{V["ai_andmed"]["pakkumusi_teada"]} hankest, mille pakkumuste arv on teada',
             pilt=kaks_riba([("need", uk["ai_andmed"], True), ("IT", uk["it_muud"], False), ("kõik", uk["koik"], False)], h=44),
             mrk=f'Teistes IT-hangetes {pr(uk["it_muud"], 0)}%, kõigis {pr(uk["koik"], 0)}%. Pakkumuste arv on teada '
                 f'{V["ai_andmed"]["pakkumusi_teada"]} hankel {V["ai_andmed"]["hankeid"]}-st.',
             liik="mõõdetud", allikas="Riigihangete register", kuup=f"{D.p0}–{D.p1}"),
        dict(kys="Kes hangib?", ank="hankijad", ava="Ava hankijad", sona=sona_hankijad(K["nende_osakaal"]),
             arv=f'{pr(K["nende_osakaal"], 0)}%', all=f'hangetest teeb {K["top10_protsenti_hankijaid"]} hankijat {K["hankijaid"]}-st',
             pilt=jaotusriba([("s", K["nende_osakaal"])], f'{K["top10_protsenti_hankijaid"]} hankijat teeb {pr(K["nende_osakaal"], 0)}%'),
             mrk=f'{K["uks_hange_hankijaid"]} hankijat tegi ühe hanke. Suurimad on riigi IT-majad, mis hangivad ka teistele asutustele.',
             liik="arvutatud", allikas="Riigihangete register", kuup=f"{D.a0}–{D.a1}"),
        dict(kys="Kas innovatsioonihangete siht täitub?", ank="innovatsioon", ava="Ava innovatsioonihanked",
             sona=sona_siht(D.inn["innovatsioonimark_osakaal"], 2), arv=f'{pr(D.inn["innovatsioonimark_osakaal"])}%',
             all=f'hangetest {D.inn["aasta"]}, hankija märkega; siht 2% aastaks 2027',
             pilt=osariba(D.inn["innovatsioonimark_osakaal"], 2.5, siht=2, silt=f'{pr(D.inn["innovatsioonimark_osakaal"])}%, siht 2%'),
             mrk="Sihi allikas on OECD aruanne (2026). Märge on hankija enda linnuke; sisu keegi ei kontrolli.",
             liik="mõõdetud", allikas="eForms", kuup=f'{D.inn["aasta"]}, osaline'),
        dict(kys="Kui täpne on hangete leidmine?", ank="tapsus", ava="Ava klassifikaatori test",
             sona=sona_tapsus(tul["tapsus"] * 100, tul["saagis"] * 100), arv=f'{pr(tul["tapsus"] * 100, 0)}%',
             all=f'täpsus; saagis {pr(tul["saagis"] * 100, 0)}%',
             pilt=kaks_riba([("täps.", tul["tapsus"] * 100, True), ("saagis", tul["saagis"] * 100, False)]),
             mrk=f'Mõõdetud masinmärgendite vastu. {KS["n"]} hanget vaadati käsitsi üle, kokkulangevus {KS["kokku"]}%.',
             liik="arvutatud", allikas="Klassifikaatori test", kuup=kp(KS["kuupaev"])),
    ]


def tahvel(D):
    return tt.vastustahvel("tahvel", "Mida riik tehisaru ja andmete kohta hangib?",
                           "Hanked leidis klassifikaator. Iga rida on oma alusel (hanked, hankijad); eri ridade numbreid ei võrrelda.", read(D))


# ---------------------------------------------------------------- A: kuidas hangitakse

def _kuidas_svg(D, w, kitsas):
    lx = 0 if kitsas else 170
    X = lambda x: lx + 6 + x / 100 * (w - lx - 6 - 40)  # noqa: E731
    rid = [("Hindas ka kvaliteeti", D.kv), ("Sai ühe pakkumuse", D.uk), ("Hange katkes", D.ka)]
    rh = 84 if kitsas else 48
    y0 = 62 if kitsas else 30
    h = y0 + len(rid) * rh + 6
    o = []
    for t in (0, 25, 50, 75, 100):
        o.append(f'<line class="tv-ax" x1="{X(t):.1f}" x2="{X(t):.1f}" y1="14" y2="{h - 22}" opacity=".35"/>'
                 f'<text class="tt-t" x="{X(t):.1f}" y="{h - 6}" text-anchor="middle">{t}%</text>')
    for i, (n, d) in enumerate(rid):
        y = y0 + i * rh
        lo, hi = min(d.values()), max(d.values())
        o.append(f'<text class="tt-t tt-as" x="{X(0) if kitsas else 0}" y="{y - 32 if kitsas else y + 5}" style="font-size:{13 if kitsas else 15}px">{e(n)}</text>'
                 f'<line class="av-hall" x1="{X(lo):.1f}" x2="{X(hi):.1f}" y1="{y}" y2="{y}" stroke-width="2"/>')
        # Kui kaks halli punkti on lähestikku, tuleb üks ühine silt paremale (muidu sildid kattuvad)
        tihe = abs(d["it_muud"] - d["koik"]) < 8
        if tihe:
            o.append(f'<text class="tt-t" x="{X(hi) + 12:.1f}" y="{y + 4}">IT {pr(d["it_muud"], 0)} · kõik {pr(d["koik"], 0)}</text>')
        for g in ("koik", "it_muud", "ai_andmed"):
            x = X(d[g])
            silt = "" if tihe else pr(d[g], 0)
            if g == "ai_andmed":
                o.append(f'<circle class="tv-pf" cx="{x:.1f}" cy="{y}" r="7"/>'
                         f'<text class="tt-t b f" x="{x:.1f}" y="{y - 11}" text-anchor="middle" style="font-size:13px">{pr(d[g], 0)}%</text>')
            elif g == "it_muud":
                o.append(f'<circle class="hk-it" cx="{x:.1f}" cy="{y}" r="6"/><text class="tt-t" x="{x:.1f}" y="{y + 20}" text-anchor="middle">{silt}</text>')
            else:
                o.append(f'<rect class="hk-ko" x="{x - 5:.1f}" y="{y - 5}" width="10" height="10" transform="rotate(45 {x:.1f} {y})"/>'
                         f'<text class="tt-t" x="{x:.1f}" y="{y + 20}" text-anchor="middle">{silt}</text>')
    kl = "tt-sc-kitsas" if kitsas else "tt-sc-lai"
    aria = "; ".join(f"{n}: " + ", ".join(f"{gn} {pr(d[g], 0)}%" for gn, g in G) for n, d in rid)
    return f'<svg class="tt-svg {kl}" viewBox="0 0 {w} {h}" width="100%" role="img" aria-label="{aria}">{"".join(o)}</svg>'


def sec_kuidas(D, allikas_a):
    V, kv, uk, KS = D.V, D.kv, D.uk, D.KASITSI
    leg = ('<ul class="hk-leg">'
           f'<li><svg width="14" height="14" aria-hidden="true"><circle class="tv-pf" cx="7" cy="7" r="6"/></svg><b>tehisaru ja andmed</b> ({_arv(V["ai_andmed"]["hankeid"])})</li>'
           f'<li><svg width="14" height="14" aria-hidden="true"><circle class="hk-it" cx="7" cy="7" r="5"/></svg>muud IT-hanked ({_arv(V["it_muud"]["hankeid"])})</li>'
           f'<li><svg width="14" height="14" aria-hidden="true"><rect class="hk-ko" x="3" y="3" width="8" height="8" transform="rotate(45 7 7)"/></svg>kõik hanked ({_arv(V["koik"]["hankeid"])})</li></ul>')
    return f"""
<section class="jaotis" id="kuidas" aria-labelledby="h-kuidas">
  <header><h2 id="h-kuidas"><span class="kys">Kuidas tehisaru ja andmeid hangitakse?</span> <b>Kvaliteeti hinnatakse {pr(kv["ai_andmed"], 0)}% hangetest, teistes IT-hangetes {pr(kv["it_muud"], 0)}%</b> ¦ ühe pakkumuse sai {pr(uk["ai_andmed"], 0)}%, teistes IT-hangetes {pr(uk["it_muud"], 0)}%</h2>
  <p class="alam">Hanked {D.p0}–{D.p1}. Iga rida on osa hangetest, kus see juhtus; rühmad on eri suurusega. Pakkumuste arv on teada {V["ai_andmed"]["pakkumusi_teada"]} tehisaru- ja andmehankel {V["ai_andmed"]["hankeid"]}-st, {D.p1}. aasta pakkumusi avaandmetes pole.</p></header>
  <div class="av-kaks">
    <figure class="av-fig">{leg}{_kuidas_svg(D, 720, False)}{_kuidas_svg(D, 340, True)}</figure>
    <div><p class="gt">Kui kvaliteeti hinnati, oli selle kaal</p>
      <p class="hk-suur"><b>{pr(V["ai_andmed"]["kvaliteedi_kaal_mediaan"], 1)}%</b> mediaan, {V["ai_andmed"]["kvaliteedi_kaal_n"]} hanget</p>
      <p class="allikas">Teistes IT-hangetes {pr(V["it_muud"]["kvaliteedi_kaal_mediaan"], 0)}%, kõigis {pr(V["koik"]["kvaliteedi_kaal_mediaan"], 0)}%. Pakkumusi oli mediaanis {pr(V["ai_andmed"]["pakkumusi_mediaan"], 0)}, kõigis hangetes {pr(V["koik"]["pakkumusi_mediaan"], 0)}.</p></div>
  </div>
  <p class="allikas">{allikas_a}, seisuga {kp(D.seis)}. Hanked leidis klassifikaator; {KS["n"]} hanget on käsitsi üle vaadatud.</p>
</section>"""


# ---------------------------------------------------------------- C: head näited

def sec_naited(D):
    n = len(D.L)
    rid = [("Hindas ka kvaliteeti", D.kq, "ainult hind", D.ah), ("Vähemalt kaks pakkumust", D.pk2, "alla kahe", D.pk1),
           ("Hange ei katkenud", D.kf, "katkes", D.kt)]
    out = []
    for nimi, jah, ei_n, ei in rid:
        tea = n - jah - ei
        out.append(f'<div class="hk-c"><p><span>{e(nimi)}</span><b>{jah}</b></p>'
                   f'{jaotusriba([("s", jah / n * 100), ("m", ei / n * 100)], f"{nimi}: jah {jah}, {ei_n} {ei}, teadmata {tea}", w=420)}'
                   f'<small>{ei_n} {ei} · teadmata {tea}</small></div>')
    return f"""
<section class="jaotis" id="naited-kokku" aria-labelledby="h-naited-kokku">
  <header><h2 id="h-naited-kokku"><span class="kys">Kust leida hea näide?</span> <b>{D.hea} hanget {n}-st vastab kõigile kolmele tingimusele</b> ¦ pakkumuste arv on teadmata {n - D.pk2 - D.pk1} hankel</h2>
  <p class="alam">Kõik klassifikaatori leitud hanked {D.a0}–{D.a1}. Hea näide: kvaliteeti hinnati, pakkumusi oli vähemalt kaks ja hange ei katkenud. Teadmata väärtus loeb tingimuse täitmata.</p></header>
  <div class="av-kaks">
    <div><ul class="hk-leg"><li><i class="av-q b hk-l"></i>täidetud</li><li><i class="av-q hk-m hk-l"></i>täitmata</li><li><i class="av-q c hk-l"></i>teadmata</li></ul>
      <div class="hk-cc">{"".join(out)}</div></div>
    <div><p class="gt">Miks osa on teadmata?</p>
      <p class="allikas">Pakkumuste arv puudub {D.p1}. aasta hangetel, sest registri avaandmetes seda veel pole, ja osal vanematel hangetel. Hindamiskriteeriumid ja tulemus on teadmata, kui hange on veel pooleli või andmed on puudu. Kui pakkumuste arv lisandub, võib heade näidete hulk kasvada.</p></div>
  </div>
  <p class="hk-link"><a href="hanked-naited.html">Vaata kõiki {D.hea} head näidet ja otsi sarnast hanget →</a></p>
</section>"""
