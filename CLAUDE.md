# ai-work-observatory

Kaks uurimissuunda, ühine andmekiht (arhitektuur C, kinnitatud 30.10.2026):
- `tehisaru-seire/`: tehisaru kasutus ja oskused + ÜHINE KIHT (`seire/`, `allikad/`, `kataloog/`)
- `tooelu-seire/`: tehisaru mõju tööturule. Praegu kogujate proovirežiim; kõik kirjed on kontrollimata kandidaadid
- `turvakontroll/`: mis tohib repo minna

Suuna oma reeglid on selle kausta `CLAUDE.md`-s. Siin on ainult ühised reeglid; neid seal ei korrata.

## Keel
Kirjuta eesti keeles, lihtsalt ja täislausetega. Koodi nimed jäävad nagu on.

## Turvalisus (kõige tähtsam)
- Selles kaustas on ainult avalik või lubatud sisu. Tundlikud materjalid on mujal: ära otsi, loe ega kopeeri
  midagi väljastpoolt seda kausta. Kui ülesanne seda vajab, küsi Kadrilt.
- Ära lisa repo isiklikke fotosid, dokumente, tabeleid (`.xlsx`) ega võtmeid. API-võtmed on keskkonnamuutujates
  või GitHubi saladustes, mitte failides ega vestluses.
- Uus kaust läheb repo ainult siis, kui see lisatakse `.gitignore` lubatud nimekirja. Ära kasuta `git add -f`.
- Enne commit'i: `python3 turvakontroll/kontrolli.py`. Viga = ära commit'i. Konksu ei lülitata välja.
- Ära loo GitHubi repot, ära muuda selle seadeid ega tee push'i ilma Kadri selge loata.

## Muutmine
- Failiteid ära muuda ilma testideta, mis muutust kontrollivad.
- Ühine kiht: pärast muutmist jooksuta kõik testid. Kuldfailitesti viidet uuenda ainult teadlikult
  (`python tests/kuld/ehita.py --uuenda`) ja kirjuta põhjus faili `UUENDUSED.md`.
- `tehisaru-seire/tests/liides.json` kirjeldab faile, mida loeb väline leht. Ära muuda neid veerge märkamatult.
- Avaldatud lehtede sisu ei muudeta ega avaldata uuesti ilma Kadri loata.
- Ära liida ega võrdle võrreldamatuid mõõdikuid (võrreldavusklassid: `tehisaru-seire/kataloog/README.md`).
- Iga muudatus, mis muudab seisu: rida faili `UUENDUSED.md` (uuemad üleval).

## Testid
```
python3 turvakontroll/arvuti.py                       # kas arvuti on korras
python3 -m pytest -q -p no:cacheprovider turvakontroll/tests
python3 -m pytest -q -p no:cacheprovider tooelu-seire/tests
cd tehisaru-seire && python3 -m pytest -q
```
Samad testid jooksevad GitHub Actionsis (`.github/workflows/testid.yml`).
