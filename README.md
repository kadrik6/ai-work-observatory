# ai-work-observatory

Tehisaru kasutuse, oskuste ja tööturu mõju seire. Andmed tulevad avalikest allikatest. Iga numbri juures on näha, kui värske see on, kas allikad lahknevad ja millised on piirangud.

| Kaust | Mis |
|---|---|
| `tehisaru-seire/` | Suund 1: tehisaru kasutus ja oskused. Siin on ka **ühine kiht**: allikate register, näitajate kataloog, laadijad ja kontrollid. Vt `tehisaru-seire/README.md`. |
| `tooelu-seire/` | Suund 2 (tuleb): tehisaru mõju tööturule |
| `turvakontroll/` | Mis tohib repo minna; arvuti kontroll |
| `CLAUDE.md` | Claude Code'i ühised reeglid |
| `UUENDUSED.md` | Muudatuste logi |

See repo on alates 30.10.2026 seire ja turvakontrolli põhikoht. Muudatused tehakse siin, mitte algses projekti kaustas.

## Uus arvuti (Windows 11 + WSL2 Ubuntu)

Tee kõik WSL-i terminalis ja hoia repo WSL-i failisüsteemis (`~/...`), mitte `/mnt/c/` all.

```
git config --global core.autocrlf input
git clone <repo-aadress> ~/projektid/ai-work-observatory
cd ~/projektid/ai-work-observatory
git config core.hooksPath .githooks
python3 -m venv .venv && . .venv/bin/activate
pip install -r tehisaru-seire/requirements.txt
mkdir -p ~/.config/ai-work-observatory     # pane siia privaatsed loendid (need ei ole repos)
python3 turvakontroll/arvuti.py
python3 -m pytest -q -p no:cacheprovider turvakontroll/tests
cd tehisaru-seire && python3 -m pytest -q
```

Claude Code'is kontrolli käsuga `/status`, et projekti seaded (`.claude/settings.json`) on laaditud ja liivakast töötab.

## Turvalisus

Kaitse on viiekihiline:

1. Tundlikku sisu selles kaustas pole.
2. Claude Code'i õigused ja liivakast piiravad lugemist väljaspool kausta.
3. `.gitignore` lubab ainult nimetatud kaustad.
4. Konks kontrollib iga commit'i.
5. GitHub Actions kordab kontrolli.

Täpsemalt: `turvakontroll/README.md`.

## Testid

| Testid | Kus jooksevad |
|---|---|
| `tehisaru-seire/tests` (sh kuldfailitest ja liidesetest) | kohapeal ja GitHub Actionsis |
| `turvakontroll/tests` | kohapeal ja GitHub Actionsis |
| Välise lehe testid | ainult selle lehe juures, mitte siin. Siinne liidesetest kontrollib faile, mida see leht loeb. |
