# Tehisaru seire sait (uus, nullist)

Üks generaator kogu saidile. Sisu: sisuloogika hinnang (Kadri kinnitas 4.11.2026). Arhitektuur: „SEIRE · Uue saidi arhitektuur“.

```
cd tehisaru-seire
python3 sait/ehita.py                 # kirjutab valjund/sait/ (ei lähe repo)
python3 -m pytest -q tests/test_sait.py
node sait/kontroll/kontroll.js valjund/sait PILDIKAUST ettevotted.html saidikaart.html   # renderkontroll kohapeal
```

| Fail | Vastutab |
|---|---|
| `vaated.json` | saidikaart: vaated, küsimused, `h1` mallid, olek (valmis / kavas) |
| `andmekiht.py` | loeb andmed, annab igale vaatlusele võrreldavusklassi kataloogist, kukub puuduva lingi või klassi korral |
| `pealkiri.py` | `h1` mallid `{näitaja\|riik\|aasta\|vorm}`; kukub, kui vaatlust pole |
| `komponendid.py` | tulbad, hantlid, kaart, muutuse tulbad, aastatulbad, osad, kohariba, ajajoon, sihiriba, tabel, allikarida; skaala keeldub eri klassidest („alus“ ja „sama“ on üks klass) |
| `kest.py` | üks päis, üks teemalüliti, menüü, jalus |
| `abi.py` | vaate algus (pealkiri, sissejuhatus, kolm numbrit), vaatelink ainult valmis vaatele ja `kontrolli()`: pealkirja osad, mida mall ei kata (loendid, kuupäevad), arvutatakse andmetest ja ehitus kukub, kui need ei klapi |
| `lehed.py` | Ettevõtted ja saidikaart; `EHITAJAD` seob vaate id ehitajaga |
| `lehed_teemad.py` | Inimesed, Töö, Avalik sektor, Reeglid ja sihid |
| `lehed_usaldus.py` | Avaleht, Kas see on tõsi?, Kuidas lugeda |
| `sisu/` | käsitsi kontrollitud sisu: leiud, leidude numbrid, sihid, 2026. aasta numbrite mõõdikud, OECD avaliku raporti numbrid (`avalik-sektor.csv`, iga rida peatüki või joonisega) ja OECD 8 soovitust |
| `stiil.css`, `sait.js` | Sinine Fookus tokenitest; teemalüliti ja „12 / 24 / 48 / kõik“ |

Graafikud on ehitamise ajal tehtud staatiline HTML (div-tulbad), mitte JS. Arhitektuur nimetab SVG-d; HTML valiti,
sest siis jääb tekst ka 390 px laiusel päris suuruseks. Moodul on `andmekiht.py`, mitte `andmed.py`, sest kaust
`andmed/` varjaks samanimelise mooduli.
