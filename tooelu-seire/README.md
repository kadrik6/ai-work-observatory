# tooelu-seire

Tehisaru ja tööelu seire teine suund. Praegu on siin ainult **proovirežiim**: kogujad, mis kontrollivad, kas
allikad on kättesaadavad, kas duplikaadid ja versioonid tuvastatakse ning kas vead logitakse.

Kõik kogutud kirjed on **kontrollimata kandidaadid**. Need ei muuda kinnitatud andmeid ega avaldatud lehti.

## Allikad

| Allikas | Mida toob | Duplikaat / versioon |
|---|---|---|
| arXiv | eeltrükid tehisaru ja tööturu kohta | arXiv id; versioon v1, v2 … |
| OpenAlex | teadustööd (ajakirjad, eeltrükid, raportid) | DOI ja pealkiri; `updated_date` |
| ERR RSS | uudised: töökohtade kadu, ümberkorraldus, loomine | GUID |
| Eurostat | tööturu ja tehisaru andmestike viimane uuendus | andmestiku kood; `updated` (vintage) |

Sama töö eri allikates (nt arXiv ja OpenAlex) tuvastatakse DOI või normaliseeritud pealkirja järgi.

## Käivitus

```
python3 tooelu-seire/proov.py --valjund /tmp/proov1
python3 tooelu-seire/proov.py --valjund /tmp/proov2 --eelmine /tmp/proov1/nahtud.jsonl
```

GitHubis: Actions → **proov** → Run workflow. Tulemus on käivituse artefaktis (14 päeva).

Ajastatud seire: töövoog **seire** käivitub iga päev ja on käivitatav ka käsitsi. Kandidaadid on artefaktis
`seire-kandidaadid` (90 päeva). Fail `nahtud.jsonl` kogub kõik seni nähtud kirjed ja on järgmise käivituse võrdlus.

Valdkonna ülevaade: töövoog **analyys** (ainult käsitsi) loeb OpenAlexist koondarvud: tööde arv aastate ja
teemade kaupa, enim tsiteeritud tööd, kanalid, asutused, riigid ja Eesti kohta käivad tööd
(`python3 tooelu-seire/analyys.py --valjund valjund`). Tsitaadid on ainus vaba populaarsuse mõõt; klikke ei avaldata.

Eesti allikad: sama töövoo teine samm (`python3 tooelu-seire/eesti.py --valjund valjund`) loeb allikaid, mida
OpenAlexis pole: Arenguseire Keskus, Praxis ja OSKA (WordPressi otsinguvoog), ERR ja Novaator
(uudisvoog, ainult tehisaru sõnadega kirjed), ETIS-e publikatsioonid (pealkirja otsing) ning Tartu Ülikooli
lõputööd (DSpace). TalTechi digikogu on proovirežiimis: logis on olek ja vastuse algus. Uudisvoog näitab ainult viimaseid kirjeid,
seepärast koguneb uudiste ajalugu alles igapäevase seirega.
Riigikogu Toimetised (HTTP 403) ja Statistikaameti voog (HTTP 404) ei ole automaatselt loetavad (proov 30.10).

## Väljund

`olek.json`, `koik.jsonl`, `nahtud.jsonl` (kõik seni nähtud), `kirjed.jsonl` (uued), `versioonid.jsonl`, `duplikaadid.jsonl`, `vead.jsonl`,
`kokkuvote.md`. Väljumiskood on 0, kui vähemalt üks allikas töötas.

## Veel tegemata

Kandidaatide püsiv hoidmine repos ja inimese ülevaatus. Kandidaadid ei muuda kinnitatud andmeid ega avaldatud lehti.
