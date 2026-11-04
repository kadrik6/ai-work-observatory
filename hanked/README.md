# AI- ja andmehangete tuvastus

Kursuse projekt (CRISP-DM, TÜ, 2026). Autor: Kadri Kungla. Kood leiab riigihangete registrist hanked, mille
põhiese on tehisintellekti- või andmelahendus. Kood mõõdab, kuidas neid hangitakse, ja aitab leida häid näiteid.
Innovatsioonihangete siht (2% arvult aastaks 2027) tuleb raportist OECD (2026), doi 10.1787/c2c09a06-en.

Ainult avalikud andmed: riigihangete registri avaandmed (CC BY-SA 3.0 EE). Isikuandmeid ega võtmeid ei ole.

## Kuidas see töötab

| Samm | Fail | Mida teeb |
|---|---|---|
| 1 | `lae.py`, `parsi.py` | Laeb registri kuufailid (2017-09 →), loeb eVormid (alates 09/2023) ja vana TED eSenderi vormingu ning teeb põhitabeli: üks rida hanke kohta, viimane versioon. Tulemuse teade lisab pakkumuste arvu ja tulemuse. |
| 2 | `reeglid.py` | Märksõnaloend (AI, andmed, lai), CPV-rühmad, hindamiskriteeriumid ja innovatsioonimärge. |
| 3 | `kirjelda.py` | Väljade täidetus ja kihistatud valim märgendamiseks (märksõna, IT-CPV, muu). |
| 4 | `margendid.csv`, `MARGENDUSJUHEND.md` | 782 märgendatud hanget. Esimese ringi märgendas Claude; inimene pole seda veel üle vaadanud. |
| 5 | `mudel.py` | TF-IDF ja logistiline regressioon. Ajapõhine test (treening kuni 2023, test 2024–2026). Kaalutud täpsus ja saagis bootstrap-vahemikuga. Võrdleb nelja reeglit ja valib lehe reegli. Annab ka levimuse hinnangu valimi põhjal. |
| 6 | `koonda.py` | Aastanäitajad, hankimise viis, hankijate koondumine ja otsingu loend (`leht.json`). |
| 7 | `leht/ehita.py`, `leht/mall.html` | Tulemuste leht Sinine Fookus stiilis: ülevaade, sarnaste hangete otsing, hankimise viis ja täpsus. |

Andmed laaditakse GitHub Actionsis (`.github/workflows/hanked.yml`), sest registri aadress ei ole igast
keskkonnast kättesaadav. Töövoog käivitub haru `hanked/**` tõukega. Tulemused jäävad 30 päevaks artefakti ja
logisse (`HANKED ...`, `LEHT ...`).

```
pip install -r hanked/requirements.txt
python hanked/lae.py --valjund valjund
python hanked/kirjelda.py --valjund valjund
python hanked/mudel.py --valjund valjund
python hanked/koonda.py --valjund valjund
python hanked/leht/ehita.py valjund/leht.json valjund/ai-hanked.html
cd hanked && python -m pytest -q -p no:cacheprovider
```

## Piirid

- Alla 30 000 euro hankeid registris ei ole (OECD 2026, lisa 2.B).
- Märgendus on Claude'i oma ja inimese poolt kontrollimata. Kontroll on kavas: vähemalt 100 rida pimesi, Coheni kappa ≥ 0,6.
- Valim on kihistatud märksõnaloendi järgi ja märgendaja nägi märksõnu. See soosib märksõnaloendit hindamisel.
- Innovatsioonimärge on ainult eVormides. Meie näitaja loeb hankeid, millel on mõni neljast märkest. Rahandusministeerium ja OECD loendavad teisiti, seega pole numbrid üks-ühele võrreldavad.
