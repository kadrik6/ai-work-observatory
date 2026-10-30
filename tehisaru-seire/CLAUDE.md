# tehisaru-seire (suund 1 + ühine kiht)

Ühised reeglid on juurkausta `CLAUDE.md`-s. Inimesele mõeldud juhend on `README.md`.

## Käivitus
```
python3 -m pytest -q          # testid, ~1 s
python3 run.py                # laadi andmed (vajab võrku)
python3 raportid/koosta.py    # ehita raport kausta raportid/html/
```

## Andmed
- Iga number: allikas, URL ja avaldamise kuupäev. Allikata väide on anonüümne arvamus, mitte fakt.
- Näita iga riigi uusimat avaldatud aastat, mitte ainult Eurostati viimast aastat.
- Filtrid on kontrollitud (nt `size_emp=GE10`, `PC_IND`). Ära muuda neid ilma allika metaandmeid kontrollimata.
- Lahknevus allikate vahel ei ole viga: logi see (`raportid/lahknevused.csv`), ära silu.
- Ühine kiht (`seire/`, `allikad/`, `kataloog/`) on ka teise suuna sisend. Uus mõõdik saab kataloogis
  võrreldavusklassi enne, kui seda kuskil võrreldakse.

## Raport
- Visuaal enne teksti: graafik ja üks lause, detailid lahti klõpsates. Leht peab olema 5 minutiga mõistetav.
- Fotosid repos pole. Raport ehitub ilma nendeta; avaldamiseks pane fotod kohapeal kausta `raportid/fotod/`.
- `tests/test_raport_kuld.py` kukub, kui raporti KOOD muudab lehti. Andmete muutus seda testi ei kuku.
