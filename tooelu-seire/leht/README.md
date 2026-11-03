# Leht „Tehisaru ja töö“ (TOOELU)

Avaldatud: https://claude.ai/artifact/KJZJV6t17ddPTzU8sUXjZH. Lisatud repo 31.10.2026, sest seni oli generaator
ainult ühe sessiooni ajutises kaustas (saitide ülevaatus 31.10, leid Ü7).

## Mis on kus

| Fail | Mis see on |
|---|---|
| `mall.html` | Lehe HTML, CSS ja JS. Vahekaartide „Mida leiti“ ja „Tulevik“ sisu on märgendite `<!--LEIUD-->` ja `<!--TULEVIK-->…<!--/TULEVIK-->` vahel ja tehakse iga kord uuesti. |
| `tee_leiud.py` | Loeb `../leiud.json`, `../koondamised_ee.json` ja `eurostat_isoc_eb_ai_2026-10-31.json`, täidab malli ja kirjutab `leht-mall.html` töökausta. |
| `ehita.py` | Lisab töökausta andmed (vt allpool) ja disainisüsteemi, kirjutab `tehisaru-ja-too.html` (üksik leht oma artefaktis), `tehisaru-ja-too-uhine.html` (täisdokument ühise saidi jaoks) ja `eelvaade.html` (kohaliku d3-ga). |
| `andmed_logist.py`, `eesti_logist.py`, `lisa_logist.py` | Teevad analüüsi käivituse logist (GitHub Actions) vahekaartide „Mida uuritakse“ andmed `a_*.json`. Käivita töökausta `analyys/` kaustas. |
| `eurostat_isoc_eb_ai_2026-10-31.json` | Eurostati väljavõte (avalik), mille põhjal on ELi riikide graafik. |

## Töökaust (ei ole repos)

Vaikimisi `/mnt/project-files/tooelu-leht-andmed/`, muudetav keskkonnamuutujaga `TOOELU_TOO`. Seal on:

- `analyys/a_*.json`: käivituste koondandmed ja tööde pealkirjad;
- `dash/*.json`: kogujate kandidaadid ja allikate seis;
- `d3.min.js`: eelvaate jaoks.

Need ei lähe repo, sest kandidaadid jäävad käivituse artefakti (Kadri otsus 30.10.2026) ja on kontrollimata.

## Ehitamine

```
python3 tooelu-seire/leht/tee_leiud.py
python3 tooelu-seire/leht/ehita.py
python3 -m pytest -q -p no:cacheprovider tooelu-seire/tests
```

Siis vaata `eelvaade.html` üle (1200 ja 390 px, tume režiim) ja avalda `tehisaru-ja-too.html` sama lingiga.
Avaldatud lehe sisu muudetakse ainult Kadri loal.

Ümardus: riikide protsendid ja ELi keskmine on ühe kohaga, pool üles (`yks()`), nagu seire ja „Tehisaru 2027“ lehel.

## Ühine sait (Kadri otsus 3.11.2026)

Seire („Mida mõõdetakse“) ja see leht („Mida uuritakse“) on üks sait. Ühises artefaktis on seire lehed ja see leht kõrvuti; `tehisaru-ja-too-uhine.html` avaldatakse seal nimega `tehisaru-ja-too.html`. Ühises versioonis on lehe kohal osade riba (kolm osa: mõõdetakse, uuritakse, väidetakse) ja uuringu juures link „Eesti number: …“, kui sama küsimuse kohta on seire näitaja (seos: `tehisaru-seire/kataloog/uuringud.csv`). Üksikus versioonis neid pole, sest seire lehti seal ei ole. Numbrid ja uuringud ei ole kunagi samal joonisel.
