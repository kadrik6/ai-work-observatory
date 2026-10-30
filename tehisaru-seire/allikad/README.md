# Allikate register

Uuendatud: 27.10.2026 08:30 (Taani, Norra, UK ja Kanada API-d töötavad nüüd)

Siin on ametlikud statistikaametid ja rahvusvahelised andmeallikad, mida seire kasutab või võiks kasutada. Iga rea juures on kirjas, kas API töötab siit keskkonnast ja mida ma tegelikult kontrollisin.

| Fail | Mis seal on |
|---|---|
| `allikad.csv` | 21 allikat: 12 riiklikku ametit, 7 rahvusvahelist allikat või raamistikku, 2 naaberriiki |
| `numbrid-2026.csv` | Juba avaldatud 2026. aasta tehisaru numbrid koos võrreldavuse märkusega |

## Veerg „mida_kontrollisin“

- **API testitud**: tegin siit päringu ja sain andmed kätte.
- **leht avatud**: lugesin ametlikku lehte, aga API-t siit ei saanud proovida.
- **otsingutulemus**: nägin numbrit ainult otsingu kokkuvõttes. Seda ei tohi raportis kasutada enne, kui allikas on avatud.
- **Claude'i teadmine**: aadress või litsents on minu teadmistest ja vajab kontrolli.

Litsentsid on kõik märgitud „kontrollimata“, sest ühtegi litsentsilehte ma ei avanud.

## Peamised leiud 27.10.2026

1. **Eesti inimeste tehisaru kasutus 2026: 65,0%** (16–74-aastased, Statistikaameti tabel IT71). Tööalaselt kasutas 36,9%. Eurostatis on seni ainult 2025. aasta (EE 46,64%), mis klapib Statistikaameti 46,6%-ga. Seda näitajat seires veel pole.
2. **UK 2026: 38%** ettevõtetest, kus on vähemalt 10 töötajat (ONS BICS, september 2026, avaldatud 08.10.2026).
3. **Kanada 2026: 19,2%** ettevõtetest (Statistics Canada, II kvartal 2026, avaldatud 11.06.2026).
4. **USA**: Census'e BTOS annab tehisaru kasutuse iga kahe nädala tagant ja API töötab ilma võtmeta. Numbrit 17–20% (kuni mai 2026) nägin ainult otsingus.
5. **OECD andmestik** kordab ELi riikide jaoks Eurostati numbrit (EE 2025 = 23,40 mõlemas). See lisab Koread, Jaapanit ja Türgit, aga USA, UK ja Kanada 2024–2025 andmed puuduvad.
6. **Soome, Rootsi, Saksamaa ja Holland** pole 2026. aasta numbrit veel avaldanud. Eelmisel aastal avaldasid Soome ja Rootsi oma numbri novembris–detsembris.

## Teine kontroll 27.10.2026 08:30, pärast uute aadresside lisamist

| Allikas | Kas töötab | Mida sain |
|---|---|---|
| Taani (api.statbank.dk) | töötab | ITAV28: 2023 15%, 2024 28%, 2025 42%, 2026 59% |
| Norra (data.ssb.no) | töötab | ettevõtted 2026 48% (tabel 14942); inimesed 16–74 2026 71% (tabel 14365; 2025 57%, 2024 38%) |
| UK (www.ons.gov.uk) | töötab | BICS laine 165 andmefail: 10+ töötajaga ettevõtetest 38,1%; 11,1% vastas „ei tea“ |
| Kanada (www150.statcan.gc.ca) | töötab | tabel 33-10-1167-01: 19,2% |
| USA (www.census.gov) | ei vasta | ühendus avaneb, aga server ei vasta 90 sekundi jooksul; põhjus teadmata |

Inimeste tehisaru kasutus 2026: **Norra 71%, Eesti 65,0%**. Mõlemad kasutavad Eurostati ühist küsimustikku, nii et neid saab võrrelda. Eurostatis on alles 2025. aasta numbrid.

## Tähtis: UK, Kanada ja USA numbreid ei saa ELi numbritega otse võrrelda

| Mis erineb | EL (Eurostat) | UK (BICS) | Kanada (CSBC) | USA (BTOS) |
|---|---|---|---|---|
| Ettevõtted | 10+ hõivatut | 10+ (ka kõik) | kõik tööandjad | kõik tööandjad |
| Periood | aasta jooksul | praegu | viimased 12 kuud | viimased 2 nädalat |
| Mida loetakse | üks 7–11 tehnoloogiast | üks tehnoloogiatest | tehisaru tootmises või teenustes | mis tahes äritegevuses (alates nov 2025) |

Seepärast on need failis `numbrid-2026.csv` eraldi näitajatena (`-bics`, `-csbc`, `-btos`), mitte sama näitaja all kui ELi riigid.

## Võrgu lubatud aadressid

Eurostat, ESCO, Statistikaamet, OECD ja ILO töötavad juba. Teiste API-de jaoks tuleb lisada need aadressid (Project settings → environment → Allowed domains).

**Esmalt, sest neil on juba 2026. aasta numbrid:**
- api.statbank.dk
- data.ssb.no
- www.ons.gov.uk
- www150.statcan.gc.ca
- www.census.gov

**Siis, kui nad avaldavad 2026. aasta numbrid (nov–dets):**
- pxdata.stat.fi
- statistikdatabasen.scb.se
- opendata.cbs.nl

**Hiljem, oskuste ja hariduse jaoks:**
- api.uis.unesco.org
- api.bls.gov
- api.census.gov

Destatise API (www-genesis.destatis.de) vajab registreerimist ja tunnust. See kuulub Claude Code CLI-sse, mitte siia. Saksamaa ELi number tuleb võtmeta Eurostatist.
