# Seireraport

Mitmeleheline HTML-raport seire andmetest, Kadri disainisüsteemis.

## Uuendamine

Kaustast `tehisaru-seire`, pärast `python run.py`:

```
python raportid/koosta.py
```

Lehed tekivad kausta `raportid/html/`. Avalehe päisefoto on kaustas `raportid/fotod/` ja kopeeritakse koos lehtedega (`html/fotod/`); avaldamisel pane ka need failid `files` alla. Avaleht on `index.html` (ilma `<html>`-raamita, sest artefakt lisab selle ise), alamlehed on täisdokumendid.

## Kust sisu tuleb

- Numbrid: `../naitajad.json`, `../andmed/<id>.csv`, `../andmed/<id>.meta.json`, `../andmed/muutused.csv`. Käsitsi numbreid ei kirjutata.
- Käsitsi peetav: `sundmused.csv` (allikate uuendused ja seire arendus), `lahknevused.csv` (lahknevuse olek ja järgmine samm), `riskid.csv` (eksitavad väited, hüpoteesid, seire riskid).
- Raport tuletab ise: koha võrdlusriikide seas, kasvu protsendipunktides, ebatavalised langused ilma Eurostati katkestusmärgendita ja „uuem riiklik number olemas“ (kui `meta.json` väli `uuem_allikas` puudub).
- Lehtede ülesehitus (27.10.2026) on kolmetasandiline:
  1. `index.html` Ülevaade: vastus, iga näitaja kaart (uusim Eesti number, ELi võrdlus, kolm usaldusmärki), meelespea ja uudised.
  2. `<näitaja id>.html`: number, „nii on õige öelda“, riikide võrdlus, uuemad riiklikud numbrid, aegrida ja viis usaldusrida (värskus, allikate kooskõla, meetodi muutused, piirangud, avalikud väited), mis avanevad klõpsuga.
  3. `teemad.html` (kataloog teemade kaupa) ja `kuidas.html` (allikad, uuenduste kalender, sarnased mõisted, kellele mis number vastab, märkide tähendus, seire riskid, logi, failide kooskõla).
  4. `kaart.html` (3.11.2026): ELi kaart, iga näitaja viimane aasta kõigi 27 riigi kohta.
- Sihid: `../naitajad.json` väli `sihid` (riik, aasta, väärtus, allikas, url, märkus, kontrollitud). Siht on näitaja lehel faktina, riikide joonisel katkendjoonega tulbana ja aegreal katkendjoonena. Siht näitab ametlikku eesmärki, mitte prognoosi.
- ELi kaart: andmed `../andmed/el27.csv` (teeb `run.py`), riigipiirid `euroopa.json` (teeb `tee_euroopa_kaart.py` npm-paketi world-atlas@2.0.2 failist countries-50m.json; Natural Earth, avalik omand). Kaardi värvid jagavad riigid viide võrdsesse vahemikku.
- Käsitsi peetavad tabelid lehel Kuidas see töötab: `sarnased.csv` (mõisted, mis kõlavad sarnaselt, aga mõõdavad eri asja) ja `lugejad.csv` (kellele mis number vastab). Neis numbreid pole.
- `riskid.csv` veerud `naitaja` (mis näitaja lehel kirje on) ja `reegel` (lühike meelespea ülevaatesse).
- Kataloog ja allikate võrdlus tulevad kaustast `../kataloog/` mooduli `seire/kataloog.py` kaudu. Vt `../kataloog/README.md`.
