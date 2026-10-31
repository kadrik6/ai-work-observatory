"""Lisab lehele vahekaardi "Mida leiti" failist tooelu-seire/leiud.json (staatiline HTML, värvid tokenitest).

Lugeja: Kadri, ministeerium, huviline kodanik. Küsimus: mida on uuringud tehisaru mõjust tööle seni leidnud
ja kui kindlad need leiud on? Põhiline: vastus ja kindlus. Toetav: graafik. Valikuline: uuringute tabel.
"""
import html
import json
import sys

# Kaustad: LEHT = see kaust (mall, Eurostati väljavõte), TS = tooelu-seire (leiud, koondamised),
# TOO = töökaust väljaspool repot (käivituste andmed ja väljund), vt README.md.
import os
from decimal import Decimal, ROUND_HALF_UP
LEHT = os.path.dirname(os.path.abspath(__file__)) + '/'
TS = os.path.dirname(LEHT.rstrip('/')) + '/'
TOO = os.environ.get('TOOELU_TOO', '/mnt/project-files/tooelu-leht-andmed').rstrip('/') + '/'


def yks(x):
    """Üks koht pärast koma, pool üles (19,95 -> 20,0), nagu teistel saitidel."""
    return f"{Decimal(str(x)).quantize(Decimal('0.1'), rounding=ROUND_HALF_UP)}".replace('.', ',')
L = json.load(open(sys.argv[1] if len(sys.argv) > 1 else TS + 'leiud.json'))
U = {u['id']: u for u in L['uuringud']}
KINDLUS = {m: k for k, ms in L['kindlus'].items() for m in ms}
K_NIMI = {'tugev': 'Tugev tõend', 'keskmine': 'Keskmine tõend', 'nork': 'Nõrk tõend', 'prognoos': 'Prognoos'}
M_NIMI = {'katse': 'juhuslik katse', 'loomulik_katse': 'loomulik katse', 'registriandmed': 'registri- või platvormiandmed',
          'kirjeldav': 'kirjeldav analüüs', 'kusitlus': 'küsitlus', 'hinnang': 'hinnang ülesannete kohta', 'mudel': 'majandusmudel',
          'ekspertintervjuud': 'ekspertintervjuud', 'prognoos': 'prognoos või ootus, mitte mõõtmine'}
e = html.escape


def arv(x, koma=1):
    s = f'{abs(x):.{koma}f}'.rstrip('0').rstrip('.') if isinstance(x, float) else str(abs(x))
    return s.replace('.', ',')


def silt(u):
    k = KINDLUS[u['meetod']]
    r = '' if u['retsenseeritud'] or u['meetod'] == 'prognoos' else ' · retsenseerimata'
    return f'<span class="ts-tag ts-tag-{k}">{K_NIMI[k]}</span> <span class="ts-t-sub ts-inline">{M_NIMI[u["meetod"]]}{r}</span>'


def tabel(ids, pealkiri='Uuringud selle vastuse taga'):
    read = []
    for i in ids:
        u = U[i]
        read.append(f'''<tr><td><a class="ts-t-name" href="{e(u['url'])}" target="_blank" rel="noopener">{e(u['pealkiri'])}</a>
<span class="ts-t-sub">{e(u['autorid'])} · {e(u['kanal'])} · {e(u['avaldatud'])}</span></td>
<td><p class="ts-leid">{e(u['leid'])}</p><p class="ts-leid-meta">{silt(u)}<span class="ts-t-sub">{e(u['kus'])}: {e(u['valim'])}</span></p></td></tr>''')
    return f'''<details class="ts-details">
          <summary>{pealkiri} ({len(ids)})</summary>
          <div class="ts-twbox ts-twbox-auto"><table class="ts-tw ts-tw-leiud"><thead><tr><th>Uuring</th><th>Mida leiti ja kui kindel</th></tr></thead><tbody>
{''.join(read)}
          </tbody></table></div>
        </details>'''


def kaart(kysimus, vastus, lause, sisu, ids, allikas):
    return f'''      <section class="ts-finding ts-leiu-kaart">
        <div class="ts-verdict">
          <h3>{kysimus}</h3>
          <p class="ts-v-big">{vastus}</p>
          <p>{lause}</p>
        </div>
        <div class="ts-leiu-sisu">
{sisu}
          <p class="ts-source"><b>Allikas:</b> {allikas}</p>
          {tabel(ids) if ids else ''}
        </div>
      </section>
'''


# 1. Kiirus: hajuv tulpdiagramm, null ühel joonel
MIN, MAX = -25, 100
poss = lambda v: (v - MIN) / (MAX - MIN) * 100
nul = poss(0)
read = []
for r in L['kiirus']:
    v = r['kiiremini']
    neg = v < 0
    a, b = sorted([nul, poss(v)])
    tekst = f'{arv(v)}% aeglasemalt' if neg else f'{arv(v)}% kiiremini'
    read.append(f'''<li class="{'is-fokus' if neg else ''}"><span class="ts-hb-name">{e(r['nimi'])}</span>
<span class="ts-dv-track" style="--null:{nul:.1f}%"><span class="ts-dv-bar" style="left:{a:.1f}%;width:{b - a:.1f}%"></span>
<span class="ts-dv-v" style="left:{nul if neg else b:.1f}%">{tekst}</span></span></li>''')
kiirus = f'''          <div class="ts-head-sm">
            <p class="ts-kicker">Aeg ühel ülesandel, tehisaruga võrreldes ilma</p>
            <h4 class="ts-ctitle ts-ctitle-sm">Kolmes katses neljast tehti töö kiiremini, kogenud arendajad olid <span class="ts-sig">aeglasemad</span></h4>
          </div>
          <ul class="ts-dv" aria-label="Ajasääst neljas katses">{''.join(read)}</ul>
          <p class="ts-csub">Klienditoes lahendati tunnis 14% rohkem pöördumisi, algajatel 34% rohkem. Kogenud töötajate tulemus peaaegu ei muutunud.</p>'''

# 2. Töökohad: tabel, sest mõõdikud on eri
read = []
for r in L['tookohad']:
    u = U[r['uuring']]
    langus = r['muutus'] != '0'
    read.append(f'''<tr><td><span class="ts-t-name">{e(r['kes'])}</span><span class="ts-t-sub">{e(r['selgitus'])}</span></td>
<td class="ts-num {'ts-t-key' if langus else ''}">{'muutust pole' if not langus else e(r['muutus'])}</td></tr>''')
tookohad = f'''          <div class="ts-head-sm">
            <p class="ts-kicker">Muutus pärast ChatGPT tulekut</p>
            <h4 class="ts-ctitle ts-ctitle-sm">Kogu tööturul muutust pole, langus on <span class="ts-sig">noortel ja vabakutselistel</span></h4>
            <p class="ts-csub">Iga rida mõõdab eri asja, seepärast on need tabelis, mitte ühel graafikul.</p>
          </div>
          <table class="ts-tw"><thead><tr><th>Kes</th><th class="ts-num">Muutus</th></tr></thead><tbody>{''.join(read)}</tbody></table>'''

# 3. Avatus: kaks väikest tulpdiagrammi
def hb(read, max_, fokus):
    li = []
    for r in read:
        w = r['protsent'] / max_ * 100
        li.append(f'''<li class="{'is-fokus' if r['nimi'] == fokus else ''}"><span class="ts-hb-name">{e(r['nimi'])}</span>
<span class="ts-hb-track"><span class="ts-hb-bar" style="width:{w:.1f}%"></span><span class="ts-hb-v" style="left:{w:.1f}%">{arv(float(r['protsent']))}%</span></span></li>''')
    return f'<ul class="ts-hb">{"".join(li)}</ul>'

a = L['avatus']
avatus = f'''          <div class="ts-head-sm">
            <p class="ts-kicker">Töötajad ametites, kus osa ülesandeid on tehisarule avatud</p>
            <h4 class="ts-ctitle ts-ctitle-sm">Kõrge sissetulekuga riikides on avatud <span class="ts-sig">iga kolmas</span> töötaja</h4>
          </div>
          {hb(a['riigid'], 40, 'Kõrge sissetulekuga riigid')}
          <div class="ts-head-sm">
            <p class="ts-kicker">Kõige avatumas rühmas, kõrge sissetulekuga riigid</p>
            <h4 class="ts-ctitle ts-ctitle-sm">Naisi on seal ligi <span class="ts-sig">kolm korda</span> rohkem kui mehi</h4>
          </div>
          {hb(a['sugu_korge_sissetulek'], 40, 'Naised')}
          <p class="ts-csub">Avatud ei tähenda kaotatud. ILO hinnangul on kõige tõenäolisem, et töö muutub. Katsetes võitsid algajad ja nõrgemad töötajad rohkem kui kogenud.</p>'''

# 4. Majandus: kaks arvu, mida ei võrrelda
majandus = '''          <div class="ts-pair">
            <div><span class="ts-big">1,4%</span><p>kogu tööajast säästeti inimeste enda hinnangul <span class="ts-t-sub">USA, 2024. aasta lõpp, küsitlus</span></p></div>
            <div><span class="ts-big">≤0,66%</span><p>kogutootlikkuse kasv 10 aastaga majandusmudeli järgi <span class="ts-t-sub">USA, prognoos 2024</span></p></div>
          </div>
          <p class="ts-csub">Need on eri mõõdikud ja neid ei liideta. Optimistlikumaid prognoose on ka: OSKA viitab Implement Consulting Groupi 2024. aasta hinnangule, et Eesti SKP kasv võib tippaastal ulatuda 8%-ni. Seda algallikat ei ole siin kontrollitud.</p>'''

# 5. Eesti tootlikkus: kaks tulpa rea kohta
et = L['eesti_tootlikkus']['read']
li = []
for i, r in enumerate(et):
    if r['toostus'] is None:
        li.append(f'''<li class="ts-g-row"><span class="ts-hb-name">{e(r['nimi'])}</span><span class="ts-g-puudu">olulist mõju ei leitud</span></li>''')
        continue
    osad = []
    for k, n in (('toostus', 'tööstus'), ('teenused', 'teenused')):
        w = r[k] / 40 * 100
        osad.append(f'<span class="ts-hb-track ts-g-track"><span class="ts-hb-bar" style="width:{w:.1f}%"></span><span class="ts-hb-v" style="left:{w:.1f}%">{arv(r[k])}% <small>{n}</small></span></span>')
    li.append(f'''<li class="ts-g-row {'is-fokus' if i == 0 else ''}"><span class="ts-hb-name">{e(r['nimi'])}</span><span class="ts-g-bars">{''.join(osad)}</span></li>''')
eesti1 = f'''          <div class="ts-head-sm">
            <p class="ts-kicker">Tootlikkuse kasv Eesti ettevõtetes, 2000–2023</p>
            <h4 class="ts-ctitle ts-ctitle-sm">Tehisaru tõstis tootlikkust ainult <span class="ts-sig">koos töökorralduse muutmisega</span></h4>
            <p class="ts-csub">Igal real ülemine tulp on töötlev tööstus, alumine teadmusmahukad teenused. Tehisaru koos muutustega on statistiliselt oluline, aga nõrgemalt kui automatiseerimine.</p>
          </div>
          <ul class="ts-hb ts-g">{''.join(li)}</ul>'''

# 5b. Töökorraldus: mida see tähendab ja kus mõjus (hantlid: üksi -> koos)
TK = L['tookorraldus']
HMAX = 35
def hant(nimi, a, b, sa, sb):
    pa = (a or 0) / HMAX * 100; pb = b / HMAX * 100
    a_m = f'<span class="ts-hd-a" style="left:{pa:.1f}%"></span>' if a is not None else '<span class="ts-hd-a ts-hd-ns" style="left:0%"></span>'
    a_t = f'{sa} {arv(float(a))}%' if a is not None else f'{sa}: pole oluline'
    return f"""<li><span class="ts-hb-name">{e(nimi)}</span><span class="ts-hd-track"><span class="ts-hd-line" style="left:{pa:.1f}%;width:{pb - pa:.1f}%"></span>{a_m}<span class="ts-hd-b" style="left:{pb:.1f}%"></span><span class="ts-hd-v" style="left:{pb:.1f}%">{sb} {arv(float(b))}%</span><span class="ts-hd-av">{a_t}</span></span></li>"""
h1 = ''.join(hant(r['nimi'], r['uksi'], r['koos'], 'üksi', 'koos') for r in TK['koos'])
h2 = ''.join(hant(r['nimi'], r['uks_kord'], r['regulaarne'], 'ühekordne', 'regulaarne') for r in TK['jarjepidevus'])
kim = U['kim2026']
tookorraldus = f'''          <div class="ts-head-sm">
            <p class="ts-kicker">Mida töökorralduse muutmine uuringus tähendab</p>
            <h4 class="ts-ctitle ts-ctitle-sm">Viis asja, mida ettevõte võib uut moodi teha</h4>
          </div>
          <ul class="ts-chips">{''.join(f'<li>{e(x)}</li>' for x in TK['maaratlus'])}</ul>
          <p class="ts-csub">Määratlus: {e(TK['maaratluse_allikas'])}. {e(TK['markus'])}</p>
          <div class="ts-head-sm">
            <p class="ts-kicker">Tootlikkuse kasv Eesti ettevõtetes, 2000–2023: tehnoloogia üksi ja koos töökorralduse muutmisega</p>
            <h4 class="ts-ctitle ts-ctitle-sm">Muutustest võitsid kõige rohkem <span class="ts-sig">teenused ja väikeettevõtted</span></h4>
          </div>
          <ul class="ts-hd" aria-label="Tootlikkuse kasv tehnoloogia üksi ja koos töökorralduse muutmisega">{h1}</ul>
          <p class="ts-csub">Hall täpp on tehnoloogia üksi, lilla koos töökorralduse muutmisega. Tehisaru read: konkurentsivõime raport 2026 tabel 9.1; automatiseerimise read: tabel 9.2 (töötlev tööstus). Tehisaru tulemus on nõrgima olulisusega.</p>
          <div class="ts-head-sm">
            <p class="ts-kicker">Automatiseerimise mõju tootlikkusele: ühekordne või regulaarne investeering</p>
            <h4 class="ts-ctitle ts-ctitle-sm">Järjepidev investeerimine andis <span class="ts-sig">2,5–5 korda</span> suurema mõju</h4>
          </div>
          <ul class="ts-hd" aria-label="Ühekordne ja regulaarne automatiseerimisinvesteering">{h2}</ul>
          <div class="ts-pair">
            <div><p class="ts-kicker">Mida teevad teisiti ettevõtted, kes peavad tehisaru oluliseks</p><ul>{''.join(f'<li>{e(x)}</li>' for x in TK['tehisaru_ettevotted'])}</ul><span class="ts-t-sub">{e(TK['tehisaru_ettevotted_allikas'])}</span></div>
            <div><p class="ts-kicker">Katse: näited töökorralduse muutmisest</p><span class="ts-big">1,9×</span><p>rohkem tulu said idufirmad, kellele näidati, kuidas teised on töövood ja meeskonnad tehisaru ümber korraldanud. Tööriistad ja koolitus olid kõigil samad. <span class="ts-t-sub">{e(kim['autorid'])} {kim['aasta']}, 515 firmat, retsenseerimata</span></p></div>
          </div>
          <p class="ts-csub">Näide samast katsest: üks firma ehitas dispetšeri, raamatupidaja, graafikukoostaja ja võlgade sissenõudja töö ümber tehisaru moodulite ahelaks. Eesti ehitusettevõtete uuringutes (Laager 2026, Moorats 2026) kasutatakse tehisaru pigem selleks, et sama teha väiksema ressursiga, mitte töökorraldust ümber mõtestada.</p>'''


# 5c. Välismaa sama muster ja mõõtmise astmed
def lyh(u):
    n = u['autorid'].split(' (')[0]
    return n.split(',')[0] + (' jt' if ',' in n else '')
vm = ''.join(f"""<li><span class="ts-vm-kes">{lyh(U[r['uuring']])} {U[r['uuring']]['aasta']}</span><span class="ts-vm-lause">{e(r['lause'])} <span class="ts-inline">{silt(U[r['uuring']])}</span></span></li>""" for r in TK['valismaa'])
tookorraldus += f"""
          <div class="ts-head-sm">
            <p class="ts-kicker">Välismaa uuringud</p>
            <h4 class="ts-ctitle ts-ctitle-sm">Mujal sama muster: kasu tuleb siis, kui <span class="ts-sig">töö ümber korraldatakse</span></h4>
          </div>
          <ul class="ts-vm">{vm}</ul>"""
MO = TK['moodmine']
ST = {'jah': 'Eestis olemas', 'osaliselt': 'Eestis osaliselt', 'ei': 'Eestis puudub'}
trep = ''.join(f"""<li class="ts-trep-{a['eesti']}"><span class="ts-trep-n">{i}</span><div><p class="ts-trep-q">{e(a['kusimus'])} <span class="ts-trep-st">{ST[a['eesti']]}</span></p><p class="ts-trep-t">{e(a['eesti_tekst'])}</p></div></li>""" for i, a in enumerate(MO['astmed'], 1))
trep_tabel = ''.join(f"<tr><td><span class=\"ts-t-name\">{i}. {e(a['kusimus'])}</span></td><td>{e(a['kuidas'])}</td><td>{e(a['naide'])}</td></tr>" for i, a in enumerate(MO['astmed'], 1))
gds = U['gds2025']
moodmine = f"""          <div class="ts-head-sm">
            <p class="ts-kicker">{e(MO["kirjeldus"])}</p>
            <h4 class="ts-ctitle ts-ctitle-sm">Eesti mõõdab täielikult <span class="ts-sig">ainult esimest astet</span></h4>
          </div>
          <ol class="ts-trep" aria-label="Töökorralduse muutuse mõõtmise astmed">{trep}</ol>
          <details class="ts-details">
            <summary>Kuidas iga astet mõõdetakse ja kes seda teeb</summary>
            <div class="ts-twbox ts-twbox-auto"><table class="ts-tw ts-tw-trep"><thead><tr><th>Aste</th><th>Kuidas</th><th>Kus seda tehakse</th></tr></thead><tbody>{trep_tabel}</tbody></table></div>
            <p class="ts-csub">MOPS-i 20%: <a href="{e(MO['mooduli_allikas'])}" target="_blank" rel="noopener">USA statistikaameti blogi 22.2.2019</a>. BTOS-i küsimused: Bonney jt 2026, lisa. Eesti: <a href="{e(MO['eesti_allikad']['laius'])}" target="_blank" rel="noopener">Eurostat isoc_eb_ai</a> (tehisaru kasutuse eesmärgid, 2025), <a href="{e(MO['eesti_allikad']['innovatsiooniuuring'])}" target="_blank" rel="noopener">Statistikaameti innovatsiooniuuringu käsiraamat</a> (küsimus F1).</p>
          </details>
          <div class="ts-pair">
            <div><p class="ts-kicker">Avaliku sektori lõks</p><span class="ts-big">26 min</span><p>päevas säästsid Suurbritannia ametnikud enda hinnangul tehisaruga. Mis selle ajaga tehti, jäi mõõtmata. <span class="ts-t-sub">GDS 2025, 20 000 ametnikku, küsitlus</span></p></div>
            <div><p class="ts-kicker">Mida siit õppida</p><p>{e(MO['avalik_sektor'])}</p></div>
          </div>
          <p class="ts-csub">Kõige odavam samm Eestile oleks teine aste: lisada olemasolevasse küsitlusse nimekiri, mida muudeti, ja siduda vastused registritega. Siis saaks vastata küsimusele, milline muutus tootlikkust tõstis. See on koostaja ettepanek, mitte ühegi asutuse otsus.</p>"""

# 6. Eesti takistused
# 6. Ettevõtete tehisaru kasutus: Eesti aegrida ja ELi riigid (Eurostat 2025, riikide 2026)
ES = json.load(open(LEHT + 'eurostat_isoc_eb_ai_2026-10-31.json'))
_g = ES['dimension']['geo']['category']['index']; _t = ES['dimension']['time']['category']['index']
def es(geo, aasta):
    k = str(_g[geo] * len(_t) + _t[aasta])
    return ES['value'].get(k), ES.get('status', {}).get(k, '')
EL27 = ['AT', 'BE', 'BG', 'CY', 'CZ', 'DE', 'DK', 'EE', 'EL', 'ES', 'FI', 'FR', 'HR', 'HU', 'IE', 'IT', 'LT', 'LU', 'LV', 'MT', 'NL', 'PL', 'PT', 'RO', 'SE', 'SI', 'SK']
NIMI = {'AT': 'Austria', 'BE': 'Belgia', 'BG': 'Bulgaaria', 'CY': 'Küpros', 'CZ': 'Tšehhi', 'DE': 'Saksamaa', 'DK': 'Taani', 'EE': 'Eesti', 'EL': 'Kreeka',
        'ES': 'Hispaania', 'FI': 'Soome', 'FR': 'Prantsusmaa', 'HR': 'Horvaatia', 'HU': 'Ungari', 'IE': 'Iirimaa', 'IT': 'Itaalia', 'LT': 'Leedu', 'LU': 'Luksemburg',
        'LV': 'Läti', 'MT': 'Malta', 'NL': 'Holland', 'PL': 'Poola', 'PT': 'Portugal', 'RO': 'Rumeenia', 'SE': 'Rootsi', 'SI': 'Sloveenia', 'SK': 'Slovakkia',
        'NO': 'Norra', 'EU27_2020': 'EL keskmine'}
# Riikide statistikaametite 2026. aasta arvud (tehisaru-seire/allikad/numbrid-2026.csv, kontrollitud 27.10.2026)
UUS = {'EE': (34.1, 'Statistikaamet IT1490, 16.9.2026'), 'DK': (59.0, 'Danmarks Statistik ITAV28, 15.9.2026'), 'NO': (48.0, 'SSB tabel 14942, 25.9.2026')}
riigid = sorted(EL27 + ['NO'], key=lambda g: -es(g, '2025')[0])
koht = [g for g in riigid if g in EL27].index('EE') + 1
riigid = sorted(riigid + ['EU27_2020'], key=lambda g: -es(g, '2025')[0])
li = []
for g in riigid:
    v, m = es(g, '2025')
    w = v / 85 * 100
    klass = 'is-fokus' if g == 'EE' else ('is-ink' if g == 'EU27_2020' else '')
    silt_ = f'{yks(v)}%' + (' <small>(aegrea katkestus)</small>' if m == 'b' else '')
    teine = ''
    if g in UUS:
        u = UUS[g][0]; w2 = u / 85 * 100
        teine = f'<span class="ts-hb-track ts-hb-2026"><span class="ts-hb-bar" style="width:{w2:.1f}%"></span><span class="ts-hb-v" style="left:{w2:.1f}%">2026: {arv(u)}%</span></span>'
        klass += ' ts-g-row'
    rida = f'<span class="ts-hb-track"><span class="ts-hb-bar" style="width:{w:.1f}%"></span><span class="ts-hb-v" style="left:{w:.1f}%">{silt_}</span></span>'
    li.append(f'<li class="{klass}"><span class="ts-hb-name">{NIMI[g]}</span>' + (f'<span class="ts-g-bars">{rida}{teine}</span>' if teine else rida) + '</li>')
el = es('EU27_2020', '2025')[0]
riigiread = ''.join(li)
eesti_rida = [('2021', es('EE', '2021')[0]), ('2023', es('EE', '2023')[0]), ('2024', es('EE', '2024')[0]), ('2025', es('EE', '2025')[0]), ('2026', 34.1)]
cols = ''.join(f'<div class="ts-col{" is-fokus" if a == "2025" else ""}{" ts-col-uus" if a == "2026" else ""}"><span class="ts-col-v">{yks(x)}%</span><span class="ts-col-bar" style="height:{x / 36 * 100:.1f}%"></span><span class="ts-col-y">{a}{"<small>Statistikaamet</small>" if a == "2026" else ""}</span></div>' for a, x in eesti_rida)
kordne = es('EE', '2025')[0] / es('EE', '2023')[0]
eesti2 = f'''          <div class="ts-head-sm">
            <p class="ts-kicker">Eesti ettevõtted, kus kasutati tehisaru, vähemalt 10 hõivatuga</p>
            <h4 class="ts-ctitle ts-ctitle-sm">Tehisaru kasutavate ettevõtete osa kasvas 2023–2025 <span class="ts-sig">üle {int(kordne)} korra</span></h4>
          </div>
          <div class="ts-cols ts-cols-sm" role="img" aria-label="Eesti ettevõtete tehisaru kasutus Eurostati järgi: 2021 2,8%, 2023 5,2%, 2024 13,9%, 2025 23,4%. 2026 Statistikaameti arv uue klassifikaatori järgi 34,1%, Eurostati arvudega ei ole võrreldav">{cols}</div>
          <p class="ts-csub">2021–2025 Eurostat. Viirutatud 2026. aasta tulp on Statistikaameti arv, mis on arvutatud uue tegevusalade klassifikaatori järgi (tabel IT1490). Seda ei saa Eurostati 2021–2025 arvudega võrrelda, seega 2025 ja 2026 vahet ei arvutata. Statistikaameti enda 2025. aasta arv vana klassifikaatori järgi on 22,2%.</p>
          <div class="ts-head-sm">
            <p class="ts-kicker">Sama näitaja ELi riikides ja Norras, 2025</p>
            <h4 class="ts-ctitle ts-ctitle-sm">Eesti on ELis <span class="ts-sig">{koht}. kohal</span>, EL keskmisest veidi eespool ({yks(el)}%)</h4>
            <p class="ts-csub">Tulp on 2025. aasta Eurostati arv. Kolm riiki on avaldanud juba 2026. aasta arvu: see on teise, tumeda tulbana.</p>
          </div>
          <ul class="ts-hb ts-hb-riigid">{riigiread}</ul>
          <p class="ts-source"><b>Allikas:</b> Eurostat isoc_eb_ai (uuendatud 15.6.2026, laaditud 31.10.2026), vähemalt 10 hõivatuga ettevõtted, v.a finantssektor ja põllumajandus. 2026: {'; '.join(f"{NIMI[k]} {u[1]}" for k, u in UUS.items())}. Ka Taanis ja Norras on 2026. aastal uus tegevusalade klassifikaator. Teiste riikide 2026. aasta arve me veel ei leidnud; Eurostat koondab need hiljem.</p>
          <p class="ts-csub">Mis takistab: OSKA ekspertide hinnangul ei teata ettevõtted sageli, millal ja milleks tehisaru kasutada. Takistab ka andmete ebaühtlane kvaliteet.</p>'''

vread = []
for v in L['vastuolud']:
    lingid = ', '.join(f'<a href="{e(U[i]["url"])}" target="_blank" rel="noopener">{e(U[i]["autorid"].split(",")[0].split(";")[0].split(" (")[0])} {U[i]["aasta"]}</a>' for i in v['uuringud'])
    vread.append(f'<tr><td><span class="ts-t-name">{e(v["mis"])}</span><span class="ts-t-sub">{lingid}</span></td><td><span class="ts-tag{' ts-tag-tugev' if v.get('staatus') == 'selgitatud' else ''}">{e(v.get('staatus', 'selgitamata'))}</span> {e(v["miks"])}</td></tr>')

meetodid = ''.join(f'<li><b>{K_NIMI[KINDLUS[m]]}, {M_NIMI[m]}.</b> {e(t)}</li>' for m, t in L['meetodid'].items())
kp = L['kontrollitud']
kp_ee = f'{int(kp[8:])}.{int(kp[5:7])}.{kp[:4]}'


# ---------- Vahekaart "Tulevik" ----------
T = L['tulevik']
# 1. Töö kaotanud: kaks arvu, mida ei võrrelda, ja tõendite tabel
KP = T['koondamise_pohjused']
_kr = [{'nimi': r['nimi'], 'protsent': round(r['teateid'] / KP['kokku'] * 100, 1)} for r in KP['read']]
_kr.append({'nimi': 'Muud põhjused (jääk)', 'protsent': round((KP['kokku'] - sum(r['teateid'] for r in KP['read'])) / KP['kokku'] * 100, 1)})
_kokku = f"{KP['kokku']:,}".replace(',', ' ')
pohjused = f'''          <div class="ts-head-sm">
            <p class="ts-kicker">USA koondamisteated põhjuse järgi, {KP['periood']}, % kõigist</p>
            <h4 class="ts-ctitle ts-ctitle-sm">Tehisaru on suurim üksikpõhjus, aga <span class="ts-sig">kolm neljandikku</span> teadetest on muudel põhjustel</h4>
          </div>
          <div class="ts-hb-pohj">{hb(_kr, 30, 'Tehisaru')}</div>
          <p class="ts-csub">Kokku {_kokku} teadet. {e(KP['markus'])} Väljaspool tehnoloogiasektorit on tehisaruga seotud koondamisi vähe.</p>'''
kaotus = f'''          <div class="ts-pair">
            <div><span class="ts-big">24%</span><p>USA koondamisteadetest nimetas 2026. aasta esimesel seitsmel kuul põhjuseks tehisaru <span class="ts-t-sub">112 713 teadet 477 033st, Challenger, Gray &amp; Christmas</span></p></div>
            <div><span class="ts-big">≈8%</span><p>ühe aasta palgast kaotasid viie aastaga inimesed, kelle ettevõte automatiseeris <span class="ts-t-sub">Holland 2000–2016, registriandmed, automatiseerimine üldiselt</span></p></div>
          </div>
          <p class="ts-csub">Need on eri mõõdikud ja neid ei liideta. Teade ei tähenda tegelikku koondamist ja tehisaru märkimine põhjuseks on ebamäärane. Eestis ega ELis ei loe keegi tehisaru tõttu koondatuid eraldi.</p>
{pohjused}'''

# 1b. Eesti koondamised ja tehisaru roll (käsitsi kogutud nimekiri)
KE = json.load(open(TS + 'koondamised_ee.json'))
ROLL = {'otsene': 'Otsene', 'osaline': 'Üks põhjustest', 'kaudne': 'Kaudne', 'tulevikus': 'Tulevikus võimalik', 'ei_mainita': 'Ei mainita'}
kr = []
for j in KE['juhtumid']:
    kp_ = j['kuupaev']; kpe = f'{int(kp_[8:])}.{int(kp_[5:7])}.{kp_[:4]}'
    arv_ = f"{j['arv_eestis']}" if j['arv_eestis'] else '?'
    kr.append(f"""<tr><td><a class="ts-t-name" href="{e(j['url'])}" target="_blank" rel="noopener">{e(j['ettevote'])}</a><span class="ts-t-sub">{kpe} · {e(j['sektor'])}</span></td>
<td class="ts-num"><span class="ts-t-name">{arv_}</span><span class="ts-t-sub">{e(j['arv_tekst'])}</span></td>
<td><span class="ts-tag ts-roll-{j['roll']}">{ROLL[j['roll']]}</span><p class="ts-leid">{e(j['pohjus'])}</p><span class="ts-t-sub">Ütles: {e(j['kes_utles'])}. Allikas: {e(j['allikas'])}</span></td></tr>""")
mainitud = sum(1 for j in KE['juhtumid'] if j['roll'] != 'ei_mainita')
LYH = {'otsene': 'otsene põhjus', 'osaline': 'üks põhjustest', 'kaudne': 'kaudne põhjus', 'tulevikus': 'tuleviku risk', 'ei_mainita': 'ei mainita'}
MAXK = 500
jrj = sorted(KE['juhtumid'], key=lambda j: -(j['arv_eestis'] or j.get('arv_ulem') or 0))
kb = []
for j in jrj:
    kp_ = j['kuupaev']; kpe = f'{int(kp_[8:])}.{int(kp_[5:7])}.'
    n = j['arv_eestis'] or j.get('arv_ulem')
    if n:
        w = n / MAXK * 100
        silt_ = f"{'kuni ' if not j['arv_eestis'] else ''}{n}"
        rida = f'<span class="ts-hb-track"><span class="ts-hb-bar ts-kb-{j["roll"]}{" ts-kb-ulem" if not j["arv_eestis"] else ""}" style="width:{w:.1f}%"></span><span class="ts-hb-v" style="left:{w:.1f}%">{silt_} <small>· {LYH[j["roll"]]}</small></span></span>'
    else:
        rida = f'<span class="ts-hb-track"><span class="ts-kb-puudu">Eesti arv teadmata ({e(j["arv_tekst"].split(",")[0])}) · {LYH[j["roll"]]}</span></span>'
    kb.append(f'<li><span class="ts-hb-name"><b>{e(j["ettevote"])}</b> <small>{kpe}</small></span>{rida}</li>')
legend = ''.join(f'<span class="ts-kb-leg"><i class="ts-kb-{k}"></i>{v}</span>' for k, v in (('osaline', 'tehisaru üks põhjustest'), ('kaudne', 'kaudne: tehisaru muutis turgu'), ('ei_mainita', 'tehisaru ei mainita')))
eesti_k = f'''          <div class="ts-head-sm">
            <p class="ts-kicker">Eesti suuremad koondamised 2026, koondatavaid Eestis</p>
            <h4 class="ts-ctitle ts-ctitle-sm">Suurimas, Pipedrive’i koondamises oli tehisaru <span class="ts-sig">kaudne põhjus</span>; otse nimetas seda ainult Telia</h4>
          </div>
          <p class="ts-kb-legend">{legend}</p>
          <ul class="ts-hb ts-kb" aria-label="Eesti koondamised 2026 ja tehisaru roll">{''.join(kb)}</ul>
          <p class="ts-csub">Tehisaru roll on see, mida ettevõte ise ütles, mitte meie hinnang. {mainitud} juhtumis {len(KE['juhtumid'])}-st mainiti tehisaru, aga üheski polnud see ainus põhjus. Arve ei liideta. Nimekiri ei ole täielik.</p>
          <details class="ts-details"><summary>Põhjused ettevõtete sõnul ({len(kr)})</summary>
          <div class="ts-twbox ts-twbox-auto"><table class="ts-tw ts-tw-koond"><thead><tr><th>Ettevõte</th><th class="ts-num">Eestis</th><th>Tehisaru roll ja põhjus ettevõtte sõnul</th></tr></thead><tbody>{''.join(kr)}</tbody></table></div>
          <ul>{''.join(f"<li><b>{ROLL[k]}.</b> {e(v)}</li>" for k, v in KE['rollid'].items())}</ul></details>'''

# 2. Ametid: hajuv tulpdiagramm (USA prognoos) ja Eesti suunad (OSKA)
MIN2, MAX2 = -6, 16
pos2 = lambda v: (v - MIN2) / (MAX2 - MIN2) * 100
nul2 = pos2(0)
li = []
for r in T['ametid']['read']:
    v = r['muutus']; neg = v < 0
    a_, b_ = sorted([nul2, pos2(v)])
    klass = 'is-fokus' if r['nimi'] == 'Kontori- ja haldustöö' else ('is-ink' if r.get('kokku') else '')
    märk = '−' if neg else '+'
    li.append(f'''<li class="{klass}"><span class="ts-hb-name">{e(r['nimi'])}</span>
<span class="ts-dv-track" style="--null:{nul2:.1f}%"><span class="ts-dv-bar" style="left:{a_:.1f}%;width:{b_ - a_:.1f}%"></span>
<span class="ts-dv-v" style="left:{nul2 if neg else b_:.1f}%">{märk}{arv(abs(v))}%</span></span></li>''')
ea = T['eesti_ametid']
ametid = f'''          <div class="ts-head-sm">
            <p class="ts-kicker">USA ametite pearühmad, töökohtade muutus 2025–2035, prognoos</p>
            <h4 class="ts-ctitle ts-ctitle-sm">Tervishoid kasvab kõige kiiremini, <span class="ts-sig">kontoritöö kahaneb</span> kõige rohkem</h4>
          </div>
          <ul class="ts-dv ts-dv-amet" aria-label="USA ametite pearühmade muutus 2025–2035">{''.join(li)}</ul>
          <p class="ts-csub">Üksikametitest kasvavad kõige kiiremini õendusspetsialistid (+41%), päikesepaneelide paigaldajad (+36,5%), andmeteadlased (+34,6%) ja tuuleturbiinide tehnikud (+29,5%). Kontori- ja haldustöös kaob 752 100 töökohta, USA tööstatistika amet seob selle osaliselt tehisaruga.</p>
          <div class="ts-head-sm">
            <p class="ts-kicker">Eesti, OSKA prognoos 2022–2031</p>
            <h4 class="ts-ctitle ts-ctitle-sm">Eestis on suund sama, aga <span class="ts-sig">inimesi on vaja rohkem</span>, kui koolist tuleb</h4>
          </div>
          <div class="ts-pair ts-suunad">
            <div><p class="ts-kicker">Töökohti lisandub</p><ul>{''.join(f'<li>{e(x)}</li>' for x in ea['kasvab'])}</ul></div>
            <div><p class="ts-kicker">Töökohti väheneb</p><ul>{''.join(f'<li>{e(x)}</li>' for x in ea['kahaneb'])}</ul></div>
          </div>
          <p class="ts-csub">Kõige rohkem inimesi on Eestis vaja pensionile jääjate asemele: müüjad, õpetajad, raamatupidajad, ehitajad, arstid, sõidukijuhid. Kokku 18 000 inimest aastas, koolist tuleb tööturule alla 16 000. OSKA prognoos on tehtud enne 2023. aastat; uuem trendiülevaade „Töö ja oskused 2035“ (29.10.2025) on kvalitatiivne ja arve ametite kaupa ei anna.</p>
          <p class="ts-csub">Maailmas ootavad suurtööandjad aastaks 2030 170 miljonit uut ja 92 miljonit kaduvat töökohta (WEF). ELis kasvab hõive 2023–2035 üle 4% (Cedefop). Need on eri prognoosid ja neid ei liideta.</p>'''

# 3. Töötus: Eesti tulbad, tegelik ja prognoos
rr = T['tootus_ee']['read']
cols_t = ''.join(f'<div class="ts-col{" is-ink" if r["tegelik"] else ""}{" is-fokus" if r is rr[-1] else ""}"><span class="ts-col-v">{arv(r["protsent"])}%</span><span class="ts-col-bar" style="height:{r["protsent"] / 8 * 100:.1f}%"></span><span class="ts-col-y">{r["aasta"]}{"" if r["tegelik"] else "*"}</span></div>' for r in rr)
tootus = f'''          <div class="ts-head-sm">
            <p class="ts-kicker">Eesti töötuse määr, %</p>
            <h4 class="ts-ctitle ts-ctitle-sm">Rahandusministeeriumi prognoosis langeb töötus <span class="ts-sig">2030. aastaks 6,1%-ni</span></h4>
          </div>
          <div class="ts-cols ts-cols-sm" role="img" aria-label="Eesti töötuse määr: 2025 tegelik 7,5%, prognoos 2026 6,7%, 2027 6,4%, 2028 6,3%, 2029 6,2%, 2030 6,1%">{cols_t}</div>
          <p class="ts-csub">2025 on tegelik arv, tärniga aastad on prognoos. Prognoos ei arvesta tehisaru mõju eraldi.</p>
          <div class="ts-pair">
            <div><span class="ts-big">4,9%</span><p>maailma töötus 2026. aastal <span class="ts-t-sub">ILO prognoos, jaanuar 2026</span></p></div>
            <div><span class="ts-big">+0,5 pp</span><p>lisatöötus USA-s tehisaru üleminekuajal, mis varasemate tehnoloogiate puhul kadus umbes kahe aastaga <span class="ts-t-sub">Goldman Sachs 2025, stsenaarium</span></p></div>
          </div>
          <p class="ts-csub">Need on eri mõõdikud eri riikidest ja neid ei liideta. Eesti kohta tehisaru töötuse stsenaariumi me ei leidnud.</p>'''

paneel_t = f'''  <div class="ts-panel" id="paneel-tulevik" role="tabpanel" aria-labelledby="tab-tulevik" hidden>
    <section class="ts-leiud-algus">
      <p class="ts-lead">Neli küsimust tuleviku kohta. Kahe esimese vastus põhineb andmetel ja ettevõtete endi sõnadel, kaks viimast on prognoosid: need näitavad suunda, mitte kindlat tulemust. Kontrollitud allikast {kp_ee}.</p>
    </section>
    <section class="ts-eesti" aria-label="Tulevik">
{kaart('Mis saab tehisaru tõttu töö kaotanud inimestest?', 'Keegi ei loe neid eraldi', 'Otsest mõõtmist pole. Varasema automatiseerimise järel kaotasid inimesed osa sissetulekust, enim vanemad ja kauaaegsed töötajad. Tehisaru mõju on seni näha eelkõige selles, et noori palgatakse vähem.', kaotus, T['kaotus'], 'Challenger, Gray &amp; Christmas juuli 2026; Bessen jt 2025 (REStat); Brynjolfsson jt 2026; Humlum, Vestergaard 2025; Goldman Sachs 2025.')}
{kaart('Kas tehisaru on Eesti koondamiste põhjus?', 'Pigem kaudselt', 'Põhjusena nimetab tehisaru ainult Telia ja ka seal koos kulude vähendamisega. Pipedrive’is muutis tehisaru turgu ja klientide ootusi, Swedbank peab seda tuleviku riskiks.', eesti_k, [], 'ERR, ERR News, Personaliuudised; kogutud käsitsi 31.10.2026. Täieliku arvu annaks Töötukassa kollektiivse koondamise teadete statistika, mida siin veel ei ole.')}
{kaart('Millised ametid 5–10 aastaga kasvavad?', 'Tervis, hooldus ja tehnoloogia', 'USA ametlik prognoos ja OSKA näevad sama suunda: kasvavad tervishoid, sotsiaaltöö, IT ja inseneriametid, kahanevad kontoritöö ja müük.', ametid, ['bls2026', 'oska2023', 'wef2025', 'cedefop2026'], 'USA tööstatistika amet 27.8.2026; OSKA üldprognoos 6.3.2023; WEF 2025; Cedefop EURESi kaudu 15.9.2026.')}
{kaart('Kui suur on töötus tulevikus?', 'Eestis umbes 6%', 'Prognoosid ei oota tehisaru tõttu suurt töötust. Eestis langeb töötus prognoosi järgi loomuliku taseme lähedale.', tootus, ['rm2026', 'ilo2026', 'goldman2025'], 'Rahandusministeeriumi suvine majandusprognoos 2026 (tabel 1); ILO Employment and Social Trends 2026; Goldman Sachs 2025.')}
    </section>
  </div>

'''

paneel = f'''  <div class="ts-panel" id="paneel-leiud" role="tabpanel" aria-labelledby="tab-leiud">
    <section class="ts-leiud-algus">
      <p class="ts-lead">Neli vastust maailma ja neli Eesti uuringute põhjal. Iga vastuse juures on, kui kindel see on ja millised uuringud selle taga on. Leiud on kontrollitud allikast {kp_ee}.</p>
    </section>

    <section class="ts-eesti" aria-labelledby="leiud-maailm">
      <h2 class="ts-ctitle" id="leiud-maailm">Maailm</h2>
{kaart('Kas tehisaru teeb töö kiiremaks?', 'Sageli jah', 'Katsetes tehti kirjutamis-, programmeerimis- ja konsultatsiooniülesandeid kiiremini. Tuttavas keerulises töös võib tehisaru ka aeglustada.', kiirus, ['peng2023', 'noy2023', 'dellacqua2023', 'metr2025', 'brynjolfsson2023'], 'juhuslikud katsed 2023–2025; klienditugi: Brynjolfsson, Li, Raymond 2023.')}
{kaart('Kas töökohti kaob?', 'Kogu tööturul veel mitte', 'Taanis ja USA-s ei ole tööhõive ega palk kokkuvõttes muutunud. USA noorte ja vabakutseliste juures on langus näha.', tookohad, ['humlum2025', 'yale2025', 'canaries2026', 'demirci2025', 'teutloff2025', 'hui2024'], 'Taani registriandmed, USA tööjõu-uuring ja palgaandmed, vabakutseliste platvormid; 2024–2026.')}
{kaart('Keda see puudutab?', 'Iga neljandat töötajat', 'Rikastes riikides ja kontoritöös rohkem, naisi rohkem kui mehi.', avatus, ['ilo2025', 'eloundou2023'], 'ILO töödokument 140, mai 2025. Avatus on hinnang ülesannete kohta, mitte mõõdetud muutus.')}
{kaart('Kas kasu jõuab majandusse?', 'Seni vähe', 'Ajasääst on kogu tööaja suhtes väike ja mudelid ennustavad tagasihoidlikku kasvu.', majandus, ['bick2024', 'acemoglu2024'], 'Bick, Blandin, Deming 2024 (küsitlus); Acemoglu 2024 (mudel).')}
    </section>

    <section class="ts-eesti" aria-labelledby="leiud-eesti">
      <h2 class="ts-ctitle" id="leiud-eesti">Eesti</h2>
{kaart('Kas tehisaru tõstab Eesti ettevõtete tootlikkust?', 'Ainult koos muutustega', 'Tehisaru üksi olulist mõju ei andnud. Koos töökorralduse muutmisega tõusis tootlikkus 19–23%.', eesti1, ['vahter2026', 'vahter2024'], 'konkurentsivõime eksperdikogu raport 2026 (ptk 9) ja Arenguseire lühiraport 18.6.2026, Tartu Ülikooli projekt MKM-POL15.')}
{kaart('Mida töökorralduse muutmine tähendab ja kus see mõjus?', 'Teenustes ja väikefirmades kõige rohkem', 'Muutus tähendab uut tööjaotust, vastutust ja otsustamist. Eesti andmetes andis see koos tehnoloogiaga suurima kasvu teadmusmahukates teenustes ja väikeettevõtetes. Milline muutus aitas kõige rohkem, uuring ei ütle.', tookorraldus, ['vahter2026', 'kim2026', 'bbh2002', 'calvino2023', 'dellacqua2026', 'gds2025'], 'konkurentsivõime eksperdikogu raport 2026, ptk 9 (tabelid 9.1, 9.2, tekstikastid 9.1–9.3, lisa 9.1); Kim, Kim, Koning 2026; välismaa uuringud tabelis.')}
{kaart('Kuidas töökorralduse muutust paremini mõõta?', 'Küsida, mida muudeti, ja siduda registritega', 'Eesti uuringud näitavad, kas töökorraldust muudeti, aga ei seo seda tehisaruga. USA statistikaamet küsib tehisaru kasutajatelt, mida muudeti. Eesti eelis on registrid, mis näitavad, mis päriselt juhtus.', moodmine, ['bonney2026', 'gds2025', 'kim2026', 'dellacqua2026'], 'USA statistikaamet (BTOS 2026, MOPS), Suurbritannia GDS 2025, katsed 2026; astmete järjestus ja Eesti hinnang on koostaja oma.')}
{kaart('Mis takistab?', 'Oskused ja andmed', 'Kasutajaid tuleb kiiresti juurde, aga OSKA ekspertide hinnangul ei tea paljud, milleks tehisaru kasutada.', eesti2, ['oska2025'], 'takistused: OSKA rakendusuuring 2025 (Leemet, Mets).')}
    </section>

    <section class="ts-chartcard" aria-labelledby="leiud-vastuolud">
      <div class="ts-head-sm">
        <p class="ts-kicker">Usaldus</p>
        <h2 class="ts-ctitle" id="leiud-vastuolud">Kus uuringud lahknevad</h2>
      </div>
      <table class="ts-tw"><thead><tr><th>Mis lahkneb</th><th>Selgitus</th></tr></thead><tbody>{''.join(vread)}</tbody></table>
      <details class="ts-details">
        <summary>Kuidas leiud valiti ja mida kindlus tähendab</summary>
        <ul>
          <li>Iga küsimuse kohta valisin tugevaima meetodiga ja enim viidatud uuringud ning lisasin uusimad (2025–2026). See ei ole süstemaatiline ülevaade.</li>
          <li>Arvud on võetud uuringu kokkuvõttest või asutuse enda teatest ja kontrollitud lingi kaudu {kp_ee}. Täisteksti ei ole loetud.</li>
          <li>Retsenseerimata töödokumendi tulemus võib hiljem muutuda.</li>
          {meetodid}
        </ul>
      </details>
    </section>
  </div>

'''

css = '''
  /* Mida leiti */
  .ts-leiu-sisu { display: grid; gap: var(--cds-gap-md); align-content: start; min-width: 0; }
  .ts-leiu-kaart .ts-verdict p.ts-v-big { color: var(--ts-signal); }
  .ts-tag { display: inline-block; font-size: 12px; font-weight: 700; letter-spacing: .04em; padding: 1px 8px; border-radius: 999px; border: 1px solid var(--ink-muted); color: var(--ink); white-space: nowrap; }
  .ts-tag-tugev { background: var(--ink); color: var(--surface); border-color: var(--ink); }
  .ts-tag-nork { border-style: dashed; color: var(--ink-muted); }
  .ts-inline { display: inline !important; }
  .ts-leid { margin: 0 0 6px; font-size: 14px; line-height: 1.45; }
  .ts-leid-meta { margin: 0; display: grid; gap: 4px; }
  .ts-tw-leiud td:first-child { width: 42%; }
  .ts-twbox-auto { max-height: none; }
  .ts-dv { display: grid; gap: 8px; margin: 0; padding: 0; list-style: none; }
  .ts-dv li { display: grid; grid-template-columns: minmax(5.5rem, 32%) minmax(0, 1fr); align-items: center; gap: var(--cds-gap-sm); font-size: 14px; }
  .ts-dv-track { position: relative; height: 1.6rem; }
  .ts-dv-track::before { content: ""; position: absolute; left: var(--null); top: -4px; bottom: -4px; width: 1px; background: var(--ink); }
  .ts-dv-bar { position: absolute; top: 3px; bottom: 3px; background: var(--ts-context); border-radius: 3px; }
  .ts-dv-v { position: absolute; top: 50%; transform: translateY(-50%); padding: 0 6px; white-space: nowrap; font-weight: 700; font-variant-numeric: tabular-nums; color: var(--ink-muted); }
  .ts-dv li.is-fokus .ts-dv-bar { background: var(--ts-signal); }
  .ts-dv li.is-fokus .ts-dv-v, .ts-dv li.is-fokus .ts-hb-name { color: var(--ts-signal); font-weight: 700; }
  .ts-pair { display: grid; align-items: start; gap: var(--cds-gap-md); grid-template-columns: repeat(auto-fit, minmax(min(100%, 13rem), 1fr)); }
  .ts-pair > div { display: grid; gap: 6px; align-content: start; padding: var(--cds-pad-md); border-radius: 12px; background: var(--surface); }
  .ts-pair p { margin: 0; font-size: var(--cds-font-size-body); line-height: 1.4; }
  .ts-pair .ts-t-sub { display: block; font-size: 13px; color: var(--ink-muted); margin-top: 4px; }
  .ts-g-row { align-items: start !important; }
  .ts-g-bars { display: grid; gap: 4px; }
  .ts-g-track { height: 1.25rem; }
  .ts-g-track .ts-hb-v small { font-weight: 400; color: var(--ink-muted); }
  .ts-g-puudu { font-size: 14px; color: var(--ink-muted); font-style: italic; border-left: 1px solid var(--ink); padding-left: 6px; }
  .ts-g .ts-hb-name { padding-top: 1px; }
  .ts-hb-2026 .ts-hb-bar { background: var(--ink) !important; }
  .ts-hb-2026 .ts-hb-v { color: var(--ink) !important; }
  .ts-hb-riigid li { font-size: 13px; }
  .ts-hb-riigid .ts-hb-track { height: 1.05rem; }
  .ts-hb-v small { font-weight: 400; }
  .ts-hb-v small b { font-weight: 700; color: var(--ink); }
  .ts-leiu-sisu > .ts-head-sm:not(:first-child) { margin-top: var(--cds-gap-md); }
  .ts-leiu-sisu > .ts-csub { margin-top: var(--cds-gap-xs); }
  /* Õhk graafiku ümber: tekst ei tohi olla visuaali vastas kinni (Kadri 31.10). */
  .ts-details > .ts-twbox { margin-top: var(--cds-gap-sm); }
  .ts-vk-head { margin-top: var(--cds-gap-lg); }
  .ts-hb-vk { margin-block: var(--cds-gap-sm); }
  @media (max-width: 40rem) { .ts-hb-vk li { grid-template-columns: 1fr; gap: 2px; } .ts-hb-vk .ts-hb-name { text-align: left; white-space: normal; overflow: visible; text-overflow: clip; } }
  .ts-details > .ts-twbox + * { margin-top: 12px; }
  .ts-leiu-sisu > :is(ul, ol, .ts-cols, .ts-dv, .ts-hd, .ts-hb, .ts-kb, .ts-trep, .ts-vm, .ts-chips, .ts-pair, .ts-twbox, table) { margin-block: var(--cds-gap-sm); }
  @media (max-width: 40rem) {
    .ts-dv li { grid-template-columns: 1fr; gap: 2px; }
    .ts-dv .ts-hb-name { text-align: left; }
    .ts-g li { grid-template-columns: 1fr; gap: 2px; }
    .ts-g .ts-hb-name { text-align: left; display: block; }
    .ts-tw-leiud thead { display: none; }
    .ts-tw-leiud td { display: block; width: auto !important; }
    .ts-tw-leiud td + td { border-top: 0; }
  }
  .ts-leiu-kaart .ts-verdict { order: 0; }
  .ts-tag-prognoos { border-style: dotted; color: var(--ink-muted); }
  .ts-dv li.is-ink .ts-dv-bar { background: var(--ink); }
  .ts-dv li.is-ink .ts-dv-v, .ts-dv li.is-ink .ts-hb-name { color: var(--ink); font-weight: 700; }
  .ts-col.is-ink .ts-col-bar { background: var(--ink); }
  .ts-col.is-ink .ts-col-v { color: var(--ink); }
  .ts-suunad ul { margin: 0; padding-left: 1.1rem; display: grid; gap: 4px; font-size: var(--cds-font-size-body); }
  .ts-suunad .ts-kicker { margin: 0; }
  .ts-chips { display: flex; flex-wrap: wrap; gap: 8px; margin: 0; padding: 0; list-style: none; }
  .ts-chips li { padding: 4px 12px; border-radius: 999px; background: var(--surface); border: 1px solid var(--ts-signal); color: var(--ink); font-size: 14px; }
  .ts-hd { display: grid; gap: 10px; margin: 0; padding: 0; list-style: none; }
  .ts-hd li { display: grid; grid-template-columns: minmax(7rem, 32%) minmax(0, 1fr); align-items: center; gap: var(--cds-gap-sm); font-size: 14px; }
  .ts-hd .ts-hb-name { text-align: right; color: var(--ink); }
  .ts-hd-track { position: relative; height: 2.6rem; border-left: 1px solid var(--ink); margin-right: 7rem; }
  .ts-hd-line { position: absolute; top: 0.8rem; height: 2px; background: var(--ts-context); }
  .ts-hd-a, .ts-hd-b { position: absolute; top: 0.8rem; width: 14px; height: 14px; border-radius: 50%; transform: translate(-50%, -6px); }
  .ts-hd-a { background: var(--ts-context); }
  .ts-hd-ns { background: var(--surface); border: 2px dashed var(--ink-muted); transform: translate(0, -6px); }
  .ts-hd-b { background: var(--ts-signal); }
  .ts-hd-v { position: absolute; top: 0.8rem; transform: translate(12px, -50%); white-space: nowrap; font-weight: 700; color: var(--ts-signal); font-variant-numeric: tabular-nums; }
  .ts-hd-av { position: absolute; left: 0; bottom: 0; padding-left: 4px; font-size: 12px; color: var(--ink-muted); white-space: nowrap; }
  .ts-pair ul { margin: 0; padding-left: 1.1rem; display: grid; gap: 4px; }
  @media (max-width: 40rem) { .ts-hd li { grid-template-columns: 1fr; gap: 2px; } .ts-hd .ts-hb-name { text-align: left; } .ts-hd-track { margin-right: 6.5rem; } }
  .ts-roll-otsene, .ts-roll-osaline { background: var(--ts-signal); border-color: var(--ts-signal); color: var(--surface); }
  .ts-roll-kaudne { border-color: var(--ts-signal); color: var(--ts-signal); }
  .ts-roll-tulevikus { border-style: dashed; }
  .ts-roll-ei_mainita { border-color: var(--ink-muted); color: var(--ink-muted); }
  .ts-tw-koond td .ts-tag { margin-bottom: 6px; }
  .ts-kb li { grid-template-columns: minmax(7rem, 26%) minmax(0, 1fr); }
  .ts-kb .ts-hb-name { color: var(--ink); }
  .ts-kb .ts-hb-name small { color: var(--ink-muted); font-weight: 400; }
  .ts-kb .ts-hb-track { height: 1.6rem; }
  .ts-kb .ts-hb-v small { font-weight: 400; }
  .ts-kb-osaline, .ts-kb-otsene { background: var(--ts-signal) !important; }
  .ts-kb-kaudne { background: color-mix(in srgb, var(--ts-signal) 28%, transparent) !important; box-shadow: inset 0 0 0 2px var(--ts-signal); }
  .ts-kb-tulevikus { background: transparent !important; box-shadow: inset 0 0 0 2px var(--ink); }
  .ts-kb-ei_mainita { background: var(--ts-context) !important; }
  .ts-kb-ulem { background-image: repeating-linear-gradient(135deg, transparent 0 5px, var(--surface) 5px 8px) !important; }
  .ts-kb-puudu { position: absolute; left: 6px; top: 50%; transform: translateY(-50%); font-size: 13px; color: var(--ink-muted); white-space: nowrap; }
  .ts-kb-legend { display: flex; flex-wrap: wrap; gap: 6px 16px; margin: 0 0 var(--cds-gap-sm); font-size: 13px; color: var(--ink-muted); }
  .ts-kb-leg { display: inline-flex; align-items: center; gap: 6px; }
  .ts-kb-leg i { display: inline-block; width: 14px; height: 14px; border-radius: 3px; }
  @media (max-width: 40rem) { .ts-kb li { grid-template-columns: 1fr; gap: 2px; } .ts-kb .ts-hb-name { text-align: left; } .ts-kb-puudu { white-space: normal; position: static; transform: none; display: block; padding: 2px 0 0 6px; } .ts-kb .ts-hb-track:has(.ts-kb-puudu) { height: auto; } }
  .ts-tw-koond td:first-child { width: 24%; }
  .ts-tw-koond td.ts-num .ts-t-sub { font-weight: 400; }
  @media (max-width: 40rem) { .ts-tw-koond thead { display: none; } .ts-tw-koond td { display: block; width: auto !important; text-align: left; } .ts-tw-koond td + td { border-top: 0; } .ts-tw-koond td.ts-num { text-align: left; padding-top: 0; } .ts-tw-koond td:first-child { padding-bottom: 2px; } }
  .ts-col-uus .ts-col-bar { background: repeating-linear-gradient(135deg, var(--ts-context) 0 4px, transparent 4px 8px) !important; border: 1px solid var(--ts-context); }
  .ts-col-uus .ts-col-v { color: var(--ink-muted); }
  .ts-col-uus .ts-col-y { position: relative; justify-self: stretch; text-align: center; }
  .ts-col-y small { position: absolute; right: 0; top: 100%; white-space: nowrap; font-size: 12px; color: var(--ink-muted); }
  .ts-cols:has(.ts-col-uus) { margin-bottom: 20px; }
  .ts-vm { list-style: none; margin: 0; padding: 0; display: grid; gap: 10px; }
  .ts-vm li { display: grid; grid-template-columns: 11rem 1fr; gap: 12px; align-items: baseline; padding-bottom: 10px; border-bottom: 1px solid var(--color-border-line); }
  .ts-vm-kes { font-weight: 700; color: var(--ink); }
  .ts-vm-lause { color: var(--ink); }
  .ts-vm .ts-inline { display: inline-block; margin-left: 4px; }
  .ts-trep { list-style: none; margin: 0; padding: 0; display: grid; gap: 0; }
  .ts-trep li { display: grid; grid-template-columns: 2.2rem 1fr; gap: 12px; padding: 10px 0; border-bottom: 1px solid var(--color-border-line); }
  .ts-trep-n { width: 2rem; height: 2rem; border-radius: 50%; display: grid; place-items: center; font-weight: 700; border: 2px solid var(--ink-muted); color: var(--ink-muted); background: var(--surface); }
  .ts-trep-jah .ts-trep-n { background: var(--ts-signal); border-color: var(--ts-signal); color: var(--surface); }
  .ts-trep-osaliselt .ts-trep-n { border-color: var(--ts-signal); color: var(--ts-signal); background: repeating-linear-gradient(135deg, transparent 0 4px, color-mix(in srgb, var(--ts-signal) 22%, transparent) 4px 7px); }
  .ts-trep-q { margin: 0; font-weight: 700; color: var(--ink); }
  .ts-trep-t { margin: 2px 0 0; color: var(--ink-muted); }
  .ts-trep-st { display: inline-block; margin-left: 6px; font-size: 12px; font-weight: 700; padding: 1px 8px; border-radius: 999px; border: 1px solid var(--ink-muted); color: var(--ink-muted); white-space: nowrap; }
  .ts-trep-jah .ts-trep-st { background: var(--ts-signal); border-color: var(--ts-signal); color: var(--surface); }
  .ts-trep-osaliselt .ts-trep-st { border-color: var(--ts-signal); color: var(--ts-signal); }
  @media (max-width: 40rem) { .ts-vm li { grid-template-columns: 1fr; gap: 2px; } }
  @media (max-width: 40rem) { .ts-hb-pohj .ts-hb li { grid-template-columns: 1fr; gap: 2px; } .ts-hb-pohj .ts-hb-name { text-align: left; white-space: normal; overflow: visible; text-overflow: clip; } }
'''


# Publikatsioonide jaotus valdkonniti (Kadri kommentaar 31.10 „Kui palju?“ juures). Andmed käivitusest töökaustas.
VALDKOND_ET = {'Economics, Econometrics and Finance': 'Majandus ja rahandus', 'Business, Management and Accounting': 'Ärijuhtimine',
               'Social Sciences': 'Sotsiaalteadused', 'Computer Science': 'Informaatika', 'Medicine': 'Meditsiin',
               'Decision Sciences': 'Otsustusteadus', 'Psychology': 'Psühholoogia', 'Health Professions': 'Tervishoiu kutsealad',
               'Engineering': 'Inseneeria', 'Mathematics': 'Matemaatika', 'Environmental Science': 'Keskkonnateadus',
               'Arts and Humanities': 'Humanitaaria', 'Agricultural and Biological Sciences': 'Põllumajandus ja bioloogia'}
valdkonnad_html = ''
try:
    VK = json.load(open(TOO + 'analyys/a_valdkonnad.json'))
except (OSError, ValueError):
    VK = None
if VK and VK.get('read'):
    k26 = sum(r['arv'] for r in VK['read']); k25 = sum(r['arv'] for r in VK['eelmine']) or None
    e25 = {r['voti']: r['arv'] for r in VK['eelmine']}
    suured = [r for r in VK['read'] if r['arv'] / k26 >= 0.01]
    vaiksed = [r for r in VK['read'] if r['arv'] / k26 < 0.01]
    read = [(VALDKOND_ET.get(r['nimi'], r['nimi']), r['arv'], e25.get(r['voti'], 0)) for r in suured]
    if vaiksed:
        read.append((f'Muud ({len(vaiksed)} valdkonda)', sum(r['arv'] for r in vaiksed),
                     sum(v for k, v in e25.items() if k not in {r['voti'] for r in suured})))
    vmax = max(max(a / k26, (b / k25 if k25 else 0)) for _, a, b in read) * 100 * 1.6
    li = []
    for i, (nm, a, b) in enumerate(read):
        o26 = 100 * a / k26; o25 = 100 * b / k25 if k25 else None
        tick = f'<span class="ts-hb-tick" style="left:{o25 / vmax * 100:.1f}%" title="{VK["aasta"] - 1}: {yks(o25)}%"></span>' if o25 is not None else ''
        li.append(f'<li class="{"is-fokus" if i == 0 else ""}"><span class="ts-hb-name">{e(nm)}</span><span class="ts-hb-track">'
                  f'<span class="ts-hb-bar" style="width:{o26 / vmax * 100:.1f}%"></span>{tick}'
                  f'<span class="ts-hb-v" style="left:{max(o26, o25 or 0) / vmax * 100:.1f}%">{yks(o26)}% · {a}</span></span></li>')
    kaks = 100 * (read[0][1] + read[1][1]) / k26
    kasv = max((r for r in read if r[2] >= 10 and not r[0].startswith('Muud')), key=lambda r: r[1] / r[2])
    valdkonnad_html = f"""        <div class="ts-head-sm ts-vk-head">
          <p class="ts-kicker">Millistest valdkondadest?</p>
          <h3 class="ts-ctitle ts-ctitle-sm">Üle poole publikatsioonidest ({yks(kaks)}%) on <span class="ts-sig">majanduse ja ärijuhtimise</span> valdkonnast</h3>
          <p class="ts-csub">Publikatsioonide osa {VK['aasta']}. aastal valdkonniti, %, ja nende arv. Kriips näitab {VK['aasta'] - 1}. aastat. Kõige kiiremini kasvas {e(kasv[0].lower())} ({kasv[2]} → {kasv[1]} publikatsiooni).</p>
        </div>
        <ul class="ts-hb ts-hb-vk" aria-label="Publikatsioonide osa valdkonniti">{''.join(li)}</ul>
        <p class="ts-source"><b>Valdkond</b> on OpenAlexi automaatne liigitus publikatsiooni peamise teema järgi. See näitab, kes uurib (näiteks majandusteadlased või meditsiin), mitte seda, millist majandusharu publikatsioon uurib. Päring {'.'.join(str(int(x)) for x in reversed(VK['aeg'][:10].split('-')))}: {VK['aasta']} {k26} publikatsiooni, {VK['aasta'] - 1} {k25} publikatsiooni.</p>
"""
s = open(LEHT + 'mall.html').read()


def rep(a, b):
    global s
    assert s.count(a) == 1, a[:80]
    s = s.replace(a, b)


if 'paneel-leiud' not in s:
    rep('<h1 class="ts-title">Mida uuritakse tehisaru ja <span class="ts-sig">töö</span> kohta</h1>',
        '<h1 class="ts-title">Tehisaru ja <span class="ts-sig">töö</span>: mida leiti ja mida uuritakse</h1>')
    rep('Arvud näitavad, mida uuritakse, mitte seda, mida uuringud leidsid.</p>',
        'Esimene vahekaart koondab tugevaimate uuringute leiud. Maailma ja Eesti vahekaart näitavad, mida ja kui palju uuritakse.</p>')
    rep('''    <button class="ts-tab" type="button" role="tab" id="tab-analyys" aria-controls="paneel-analyys" aria-selected="true">Maailm</button>''',
        '''    <button class="ts-tab" type="button" role="tab" id="tab-leiud" aria-controls="paneel-leiud" aria-selected="true">Mida leiti</button>
    <button class="ts-tab" type="button" role="tab" id="tab-analyys" aria-controls="paneel-analyys" aria-selected="false">Mida uuritakse: maailm</button>''')
    rep('id="tab-eesti" aria-controls="paneel-eesti" aria-selected="false">Eesti</button>', 'id="tab-eesti" aria-controls="paneel-eesti" aria-selected="false">Mida uuritakse: Eesti</button>')
    rep('''  <div class="ts-panel" id="paneel-analyys" role="tabpanel" aria-labelledby="tab-analyys">''',
        '<!--LEIUD-->' + '''  <div class="ts-panel" id="paneel-analyys" role="tabpanel" aria-labelledby="tab-analyys" hidden>''')
    rep('</style>', '/*LEIUD-CSS*/</style>')
if 'paneel-tulevik' not in s:
    rep('aria-controls="paneel-leiud" aria-selected="true">Mida leiti</button>',
        'aria-controls="paneel-leiud" aria-selected="true">Mida leiti</button>\n    <button class="ts-tab" type="button" role="tab" id="tab-tulevik" aria-controls="paneel-tulevik" aria-selected="false">Tulevik</button>')
    rep('  <div class="ts-panel" id="paneel-analyys"', '<!--TULEVIK--><!--/TULEVIK-->  <div class="ts-panel" id="paneel-analyys"')
import re
s = re.sub(r'<!--VALDKONNAD-->.*?<!--/VALDKONNAD-->', lambda m: '<!--VALDKONNAD-->' + valdkonnad_html + '<!--/VALDKONNAD-->', s, flags=re.S)
s = re.sub(r'<!--TULEVIK-->.*?<!--/TULEVIK-->', lambda m: '<!--TULEVIK-->' + paneel_t + '<!--/TULEVIK-->', s, flags=re.S)
s = re.sub(r'<!--LEIUD-->.*?(?=<!--TULEVIK-->)', lambda m: '<!--LEIUD-->' + paneel, s, flags=re.S)
s = re.sub(r'/\*LEIUD-CSS\*/.*?(?=</style>)', lambda m: '/*LEIUD-CSS*/' + css, s, count=1, flags=re.S)
os.makedirs(TOO, exist_ok=True)
open(TOO + 'leht-mall.html', 'w').write(s)
print('ok', len(s))
