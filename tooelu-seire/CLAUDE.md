# tooelu-seire (suund 2: tehisaru ja tööelu)

Ühised reeglid on juurkausta `CLAUDE.md`-s. Inimesele mõeldud juhend on `README.md`.

## Käivitus
```
python3 -m pytest -q                              # testid ilma võrguta, ~1 s
python3 proov.py --valjund /tmp/proov             # proovikäivitus (vajab võrku)
```

## Reeglid
- Kogujad toovad ainult KONTROLLIMATA kandidaate. Kogumine ei tee järeldusi ega muuda kinnitatud andmeid,
  prognoose, avaldatud lehti ega `main` haru.
- Väljund (`valjund/`) ei lähe repo. Actionsis läheb see ainult artefaktiks.
- Uudistest salvestame ainult pealkirja, lingi, kuupäeva ja märksõna, mis kirje leidis. Mitte artikli teksti.
- Märksõnad on kahepoolsed: töökohtade kadu, ümberkorraldus ja loomine. Ainult kao otsimine moonutab pilti.
- Võti (`OPENALEX_API_KEY`) tuleb keskkonnast. Vigade logis on võtmed peidetud (`yhine.peida_votmed`).
- Ära sea võltsitud ega kohandatud User-Agenti.
- Uus allikas: aadress + lahtipakkimine `kogujad/allikad.py`-s, sünteetiline vastus ja test `tests/`-is.
