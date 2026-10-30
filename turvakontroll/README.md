# Turvakontroll

Kontrollib, et repo läheksid ainult lubatud failid ja et neis poleks tundlikku sisu. Kaitse on mitmekihiline. Ükski kiht üksi ei piisa:

1. **Füüsiline eraldus.** Repo töökoopias pole tundlikke kaustu üldse.
2. **Claude Code'i õigused ja liivakast** (`.claude/settings.json`). Piiravad lugemist väljaspool töökausta.
3. **`.gitignore` lubatud nimekirjaga.** Kõik on keelatud, välja arvatud nimetatud kaustad.
4. **Giti konks** (`.githooks/pre-commit`). Käivitab `kontrolli.py --staged` iga commit'i eel.
5. **GitHub Actions.** Kordab kontrolli ja testid iga push'i peale, ka siis, kui konks oli välja lülitatud.

## Klassid

- **AVALIK**: avalik statistika, avalikud allikad, kood. Võib minna repo.
- **PRIVAATNE**: isiklik või kontrollimata sisu. Läheb repo ainult eraldi loaga.
- **PIIRATUD**: tööandja reeglitega piiratud sisu. **Ei lähe välisesse hoidlasse ilma vastava loata.** Täpne klass sõltub sisust ja tööandja reeglitest.
- **VAJAB OTSUST**: kuni otsuseni jääb repost välja.

Algse projekti kaustade klassid on privaatses failis `KLASSID.md`, mis repo ei lähe.

## Failid

| Fail | Mis see on |
|---|---|
| `kontrolli.py` | Kontrollib keelatud kaustu, failitüüpe, pilte väljaspool teste, võtmetaolisi stringe ja keelatud sõnu. Annab hoiatuse suurte failide, e-posti aadresside ja absoluutsete teede kohta. Giti repos kontrollib faile, mida Git jälgiks. |
| `arvuti.py` | Kontrollib, kas arvuti on õigesti seadistatud: Python, kodeering, WSL, `core.autocrlf`, konks, privaatsed loendid, reavahetused. Midagi ei muuda. |
| `lubatud.txt` | Lubatud failid väljaspool Giti repot. Repos otsustab `.gitignore`. |
| `tests/test_kontrolli.py` | Testid, sh Giti režiim ja see, et päris failid on puhtad. |

**Privaatsed loendid** on `keelatud-sonad.txt` ja `keelatud-kaustad.txt`. Need ei lähe repo. Kontroll otsib neid kolmest kohast:

1. kaustast, mille annab muutuja `TURVAKONTROLL_PRIVAATNE`;
2. sellest kaustast;
3. kaustast `~/.config/ai-work-observatory/`.

GitHub Actionsis võib loendi sisu anda saladusena (`KEELATUD_SONAD`, `KEELATUD_KAUSTAD`). Ilma loenditeta kehtivad üldised keelud ja kontroll annab hoiatuse.

## Kasutamine

```
python3 turvakontroll/kontrolli.py --nimekiri   # mis läheks repo
python3 turvakontroll/kontrolli.py              # kontrolli kõik
python3 turvakontroll/kontrolli.py --staged     # commit'iks lisatud failid (konks teeb seda ise)
python3 turvakontroll/arvuti.py                 # uue arvuti kontroll
python3 -m pytest -p no:cacheprovider turvakontroll/tests
```

## Mida kontroll ei leia

- piltide ja PDF-ide sisu;
- nimesid ilma e-postita;
- sisemist sisu, mida keelatud sõnade loend ei tunne.

Seepärast on peamine kaitse füüsiline eraldus ja lubatud nimekiri, mitte otsing.
