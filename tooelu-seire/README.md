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

## Väljund

`olek.json`, `koik.jsonl`, `nahtud.jsonl` (kõik seni nähtud), `kirjed.jsonl` (uued), `versioonid.jsonl`, `duplikaadid.jsonl`, `vead.jsonl`,
`kokkuvote.md`. Väljumiskood on 0, kui vähemalt üks allikas töötas.

## Veel tegemata

Kandidaatide püsiv hoidmine repos ja inimese ülevaatus. Kandidaadid ei muuda kinnitatud andmeid ega avaldatud lehti.
