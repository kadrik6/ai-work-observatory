# Lehtede igapäevane uuendus

Kadri 5.11.2026: seire sait, leht „Tehisaru ja töö“, selle leiud, uudised, koondamised ja AI-hanked peavad ise uuenema.
Selles kaustas on uuenduse kood. Andmed ja valmis lehed on repost väljas (projekti kaust, vaikimisi `/mnt/project-files`),
sest need muutuvad iga päev ja osa neist on GitHub Actionsi logidest tehtud vahefailid.

Uuenduse käivitab ajastatud töö (iga päev 7.23 ja andmete jaoks 17.53 Tallinna aja järgi). See loeb Actionsi logid
(`seire.yml`, `analyys.yml`, `hanked.yml`), ehitab lehed ja avaldab need. Repo faile ja `main` haru see ei muuda.

## Failid

| Fail | Mida teeb |
|---|---|
| `uuenda.py` | „Tehisaru ja töö“: logidest andmed (`seire_logist.py`, `../leht/*_logist.py`), leiud (`../leiud.json` + `leiud-lisa.json`), leht `../leht/ehita.py` abil |
| `seire_logist.py` | `seire.yml` töö „kogu“ logist `dash/*.json` |
| `uuenda_seire.sh` | seire sait: `main` haru kood, numbrid otse allikatest, `raportid/koosta.py`, fotod, „Tehisaru ja töö“, osa „Mis toimub“ |
| `lisalehed.py` | osa „Mis toimub“ (`toimub.html`): Eurostati töötus, koondamised, koondajate taust, tehisaru- ja andmehanked, uudised, väited |
| `hanked_logist.py` | `hanked.yml` logi `LEHT` ridadest `hanked/leht.json` |
| `ehita_leht.py`, `uudised-mall.html` | uudisteleht (uudised, Eesti koondamised, väited) |

## Andmekaustad (keskkonnamuutujad)

- `UUENDUS_ANDMED`: ühine juurkaust, vaikimisi `/mnt/project-files`.
- `TOOELU_TOO`: „Tehisaru ja töö“ andmed, vaikimisi `$UUENDUS_ANDMED/tooelu-leht-andmed`.
- `UUDISED`: uudised, väited, koondajate taust (`koondajad.json`), vaikimisi `$UUENDUS_ANDMED/tooelu-uudised`.
- `SEIRE_UUENDUS`: AI-hangete andmed ja `seis.json`, vaikimisi `$UUENDUS_ANDMED/seire-uuendus`.

## Käivitus

```
python3 tooelu-seire/uuendus/uuenda.py [--seire LOG RUN_ID] [--analyys LOG RUN_ID]
python3 tooelu-seire/uuendus/hanked_logist.py LOG RUN_ID
bash tooelu-seire/uuendus/uuenda_seire.sh TOOKAUST
python3 tooelu-seire/uuendus/ehita_leht.py
```

## Reeglid

- Ainult avalik info. Pimehindamise materjale (`kursus/projekt/margendus/`) ei loeta.
- Kui mõni samm annab `VIGA`, lehte ei avaldata.
- Uudistest hoitakse ainult pealkirja, linki, kuupäeva ja oma sõnadega lühikest põhjust.
- Koondajate „otsib“ tuleb firma enda tööpakkumiste lehelt; uuesti kontrollitakse esmaspäeviti.
