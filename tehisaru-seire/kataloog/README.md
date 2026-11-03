# Näitajate kataloog ja allikate võrdlus

Uuendatud: 27.10.2026

Kataloog jagab kogu seire statistika teemadeks ja paneb sama küsimuse kohta eri allikate numbrid kõrvuti, ilma et ühildumatuid numbreid kokku segataks.

## Neli tasandit

| Fail | Tasand | Näide |
|---|---|---|
| `kategooriad.csv` | teema ja alateema | TA Tehisaru kasutus › TA.ETT Ettevõtted |
| `moisted.csv` | küsimus (mõiste) ja selle võrdlusalus | „Mitu protsenti ettevõtetest kasutab tehisaru?“, alus Eurostat |
| `moodikud.csv` | üks allikas oma määratlusega: populatsioon, ühik, periood, klassifikaator, võrreldavus, olek | Statistikaamet IT149, „sama mõõdik“ |
| `vaatlused-api.csv`, `vaatlused-muud.csv` | number riigi ja aasta kohta | sa-it149, EE, 2025, 22.2 |

## Uuringud küsimuste juures

`uuringud.csv` seob küsimuse (`moisted.csv` id) uuringuga failist `tooelu-seire/leiud.json` (uuringu id). Veerg `seos` ütleb ühe lausega, mida uuring numbrile lisab. Uuringu andmeid (autor, aasta, meetod, leid) siia ei kopeerita, need loetakse failist `leiud.json`.

Uuring on väide, mitte mõõdik: seda ei panda kunagi samale joonisele ega samasse tabelisse kui ametlikku numbrit. Seireraportis on see näitaja lehel eraldi kastis „Mida uuringud ütlevad“. Ühe küsimuse juures on kuni 3 uuringut, faili järjekorras. Test `tests/test_uuringud.py` kontrollib, et iga id on olemas.

Seire põhinäitaja (Eurostat `isoc_eb_ai`) numbreid kataloogi ei kopeerita. Need loetakse otse failist `andmed/<näitaja>.csv` (mõõdiku veerg `naitaja`).

Teemad: tehisaru kasutus, andmed ja digitaristu, oskused, tööturg, haridus ja teadus, investeeringud.

## Avalike lausete kontroll

Fail `vaited.csv` (3.11.2026) hoiab avalikke lauseid tehisaru, töö ja oskuste kohta, mis on kontrollitud algallika vastu. Leht on `raportid/html/vaited.html` („Mida väidetakse“, saidi kolmas osa). Lehel on ka `raportid/riskid.csv` read liigiga `vaide`: need käivad ühe seire näitaja kohta ja on näha ka selle näitaja lehel.

Iga rida vajab ütleja linki (`url`), algallika linki (`algallika_url`) ja algallika täpset sõnastust (`algallikas_utleb`). Ilma algallikata hinnangut ei tehta. `hinnang` peab olema loendis `HINNANGUD` failis `raportid/koosta.py`; seal on ka iga hinnangu tähendus. Veerus `uuringud` on tühikuga eraldatud uuringute id-d failist `tooelu-seire/leiud.json`. Veerus `kusimus` on kataloogi küsimuse id, kui lause käib selle küsimuse kohta. Hinnang on lause kohta, mitte inimese kohta. Testid: `tests/test_vaited.py`.

## Otsused ja sihid ajajoonel

Fail `otsused.csv` (3.11.2026) hoiab seaduste tähtaegu, praegu ELi tehisintellekti määruse omi. Leht on `raportid/html/otsused.html` („Mida otsustatakse“, saidi neljas osa). Sihid tulevad registri `naitajad.json` väljalt `sihid`, neid siia ei kopeerita. Veerg `tapsus` on `paev`, `kuu` või `aasta`: kui allikas annab ainult kuu, ei kirjutata päeva juurde. Lehel ei ole sihti ja praegust numbrit kõrvuti, sest sihti mõõdetakse sageli teise allikaga; sihi juures on link näitaja lehele. Testid: `tests/test_otsused.py`.

## Võrreldavuse klassid

Iga küsimuse juures on üks **võrdlusalus** (tavaliselt Eurostat, sest see on kõigi ELi riikide kohta sama meetodiga). Iga teine mõõdik on selle suhtes ühes klassis:

- **sama**: sama küsitlus ja määratlus. Number peab klappima ümardamise täpsusega. Kui ei klapi, on see lahknevus.
- **osaliselt**: sama küsitlus, aga erinev kogum, klassifikaator või nimetaja. Näidatakse eraldi veerus, kasvu ei arvutata.
- **erinev**: teine küsitlus või määratlus. Näidatakse eraldi tabelis, samasse ritta ei panda.
- **kontrollimata**: määratlust pole metaandmetest kontrollitud. Käsitle nagu „erinev“.

Vahe hinnang (`seire/kataloog.py`, `hinda_vahe`): lubatud vahe on pool vähem täpse numbri viimasest kohast (22,2 → 0,05; 59 → 0,5). Kui vahe ületab seda, on see „väike vahe“. Kui ületab vähemalt 0,5 protsendipunkti võrra (sama piir mis `usaldus.VASTUOLU_PIIR`), on see „lahknevus“.

## Mõõdiku olek

- `seires`: seire laeb automaatselt (`run.py`)
- `andmed`: numbrid on vaatluste failis
- `kavandatud`: andmestik on teada ja Eurostati API-st kontrollitud, et see on olemas, aga numbreid pole laaditud
- `allikas_leidmata`: küsimus on oluline, aga sobivat ametlikku allikat pole leitud

## Käivitamine

Kaustast `tehisaru-seire`:

```
python kataloog/lae.py        # uuendab vaatlused-api.csv (Statistikaamet ja Eurostat)
python kataloog/lae_valis.py  # uuendab vaatlused-valis.csv (OECD, ILOSTAT, UNESCO UIS, DK, NO, FI, SE, NL, UK, CA)
python -m seire.kataloog      # kontrollib kataloogi ja prindib võrdluse kokkuvõtte
python raportid/koosta.py     # raporti lehed: Teemad ja allikad (teemad.html) ja iga näitaja leht
```

`vaatlused-valis.csv` teeb `lae_valis.py` (25 mõõdikut, kõik API-st või ametlikust andmefailist). Kui mõni allikas ei vasta, jäävad selle eelmised read alles ja failis `valis-olek.csv` on viga kirjas; teised allikad laaditakse ikka. Päringud teeb süsteemi `curl`, sest OECD ja ILO keelduvad Pythoni vaikimisi kliendist. `vaatlused-muud.csv` on käsitsi peetav: numbrid, mida ükski laadija ei too. 27.10.2026 seisuga on see tühi, sest kõik varem käsitsi kantud numbrid (Taani, Norra, UK, Kanada, OECD) laaditakse nüüd automaatselt.

## Kooskõlakontroll

Sama number on mõnikord mitmes failis: `allikad/numbrid-2026.csv`, `raportid/riiklikud.csv` ja seire meta-failis. `kataloog.kooskola()` võrdleb neid kataloogiga. Erinev number on viga (test kukub läbi). Kui number on teises failis, aga kataloogis puudub, näidatakse seda lehel Allikate võrdlus tööna, mis vajab tegemist.

## Uue allika lisamine

1. Kui küsimust veel pole, lisa rida faili `moisted.csv` (kategooria peab olema alateema, näiteks `TT.HOI`).
2. Lisa mõõdik faili `moodikud.csv`. `allikas` on id failist `allikad/allikad.csv`. Vali võrreldavuse klass ja kirjuta veergu `erinevused`, mis täpselt erineb.
3. Lisa numbrid: API kaudu faili `lae.py` (Statistikaamet, Eurostat) või `lae_valis.py` (teised allikad, sõnastik `MOODIKUD`) või käsitsi faili `vaatlused-muud.csv` koos URL-i ja kontrollimise kuupäevaga.
4. Käivita `python -m seire.kataloog` ja `python -m pytest`.

## Leiud 27.10.2026

- Ettevõtete tehisaru kasutus: sama mõõdikuga allikad klapivad 30 korral 32-st. OECD kordab ELi riikide puhul täpselt Eurostati numbrit (28/28), nii et see ei ole sõltumatu kinnitus. Statistikaameti IT149 erineb 2023. aastal 0,09 protsendipunkti (väike vahe) ja 2025. aastal 1,2 protsendipunkti (lahknevus C5).
- Inimeste tehisaru kasutus: Statistikaameti 65,0% (2026) on protsent kõigist 16–74-aastastest. Sama tabeli 69,0% on protsent ainult internetikasutajatest. Neid ei tohi segi ajada.
- Norra inimeste 2025. aasta number: SSB 57 ja Eurostat 56,32. Vahe on 0,68 protsendipunkti, mida täisarvuni ümardamine ei seleta (56,32 ümardub 56-ks). Väike vahe, põhjus kontrollimata. SSB number on kantud allikate lõimest, ma ei näinud seda ise.
- ELi-väliste riikide OECD numbrid (USA, Kanada, Jaapan, Korea) on klassis „kontrollimata“. Korea hüppab 2021–2022 2,7%-lt 28%-le.

## Leiud 27.10.2026, välisallikad

- Soome, Rootsi ja Hollandi statistikaametite ettevõtete numbrid klapivad Eurostatiga (täisarvuni ümardatud). Hollandi uudise „üks kuuest“ ei ole 10+ töötajaga ettevõtete number: CBS-i enda tabelis on 2025. aastal 33%, sama mis Eurostatis.
- Rootsi inimeste generatiivse tehisaru kasutus 2026 = 53% (SCB TAB6388, 16–74). Eesti 65,0%, Norra 71%.
- Soome enda inimeste number (2025: 41%) on väiksem kui Eurostati (46,3%), sest Soome koguarv hõlmab 16–89-aastaseid.
- OECD Norra 2024. aasta tööalane kasutus (59,5%) on suurem kui sama aasta üldine kasutus (37,6%). Tõenäoliselt on OECD võtnud protsendi tehisaru kasutajatest, mitte kõigist elanikest (SSB tabelis 60%). Kinnitamata.
- OECD märgib Korea ettevõtete 2022. aasta väärtuse aegrea katkestuseks (B). See seletab hüppe 2,7%-lt 28%-le.
- IKT-spetsialistid: Eurostati määratlus (EE 2025: 6,8%) on laiem kui ILO ametirühmad ISCO-08 25 ja 35 (EE 2024: 5,0%). Mõlemad tulevad samast tööjõu-uuringust, aga neid ei tohi kõrvutada kui sama numbrit.
- UNESCO UIS (lisatud 27.10.2026 13:10): teadlased miljoni elaniku kohta (EE 2023: 4800; FI 8315, SE 8911), IKT eriala lõpetajate osakaal (EE 2024: 9,4%, DE 6,2%) ja T&A kulud % SKPst. UIS-i T&A kulud erinevad Eurostatist kuni 0,08 protsendipunkti (Norra), sest UIS pole kõiki hilisemaid parandusi üle võtnud. Lahknevuseks see ei küüni.
- US BLS (palgad): host on lubatud, aga võtmeta päringute päevalimiit on täis. Tasuta võtmega päring käib Claude Code CLI-s.
