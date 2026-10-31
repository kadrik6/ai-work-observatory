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
(uudisvoog, ainult tehisaru sõnadega kirjed). Proovis veel ei tööta: ETIS (parameeter `Title` leiab ainult täpse
pealkirja), Tartu Ülikooli DSpace (ei vasta GitHubi serveritele), Praxis (voos pole kirjeid) ja TalTechi digikogu
(ainult HTML-leht): logis on olek ja vastuse algus. Uudisvoog näitab ainult viimaseid kirjeid,
seepärast koguneb uudiste ajalugu alles igapäevase seirega.
Riigikogu Toimetised (HTTP 403) ja Statistikaameti voog (HTTP 404) ei ole automaatselt loetavad (proov 30.10).

Lisaallikad: kolmas samm (`python3 tooelu-seire/lisaallikad.py --valjund valjund`) mõõdab tähelepanu ja toob raporteid:
GDELT (uudiste arv ja nimekiri, maailm ja Eesti, viimased 3 kuud), Vikipeedia vaatamised, Hacker Newsi enim hääli
saanud lood, Maailmapanga dokumendid ning uurimisasutuste uudisvood. Need on populaarsuse lähendid, mitte klikid.

## Kontrollitud leiud

`leiud.json` on eraldi kiht: käsitsi valitud ja kontrollitud leiud tehisaru mõjust tööle (17 uuringut, 31.10.2026).
Iga rida: autorid, kanal, link, kuupäev, meetod, valim ja leid oma sõnadega. Kindlus tuleneb meetodist
(katse ja registriandmed tugev, kirjeldav ja küsitlus keskmine, hinnang, mudel ja intervjuud nõrk). Artikli teksti ei hoita.
Kogujad seda faili ei muuda. Leht „Tehisaru ja töö“ (vahekaart „Mida leiti“) on ehitatud sellest. Testid: `tests/test_leiud.py`.

## Väljund

`olek.json`, `koik.jsonl`, `nahtud.jsonl` (kõik seni nähtud), `kirjed.jsonl` (uued), `versioonid.jsonl`, `duplikaadid.jsonl`, `vead.jsonl`,
`kokkuvote.md`. Väljumiskood on 0, kui vähemalt üks allikas töötas.

## Veel tegemata

Kandidaatide püsiv hoidmine repos ja inimese ülevaatus. Kandidaadid ei muuda kinnitatud andmeid ega avaldatud lehti.
