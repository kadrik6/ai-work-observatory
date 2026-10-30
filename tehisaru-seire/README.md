# Tehisaru ja andmete seire

Kogub avalikku statistikat tehisaru kasutuse ja oskuste kohta, võrdleb Eestit teiste riikidega ja näitab iga numbri juures, kui värske see on, kas allikad on omavahel kooskõlas ja mis on numbri piirangud.


## Käivitamine

Vaja on Python 3.10 või uuemat. Andmete laadimiseks ei ole vaja lisapakette, testide jaoks on vaja `pytest`i. Välisallikate laadija (`kataloog/lae_valis.py`) kasutab süsteemi `curl`i, mis on macOS-is ja Windows 10+ olemas.

```
pip install -r requirements.txt
python -m pytest          # testid, umbes 1 sekund
python run.py --uuri isoc_eb_ai   # vaata andmestiku koode enne filtrite kinnitamist
python run.py             # laadi andmed ja koosta kaardid
```

Pärast käivitamist ava `kaardid/README.md`.

### Kuldfailitest (30.10.2026)

`tests/test_raport_kuld.py` ehitab raporti ajutises koopias külmutatud sisendist (`tests/kuld/sisend/`, kuupäev 27.10.2026) ja võrdleb tulemust salvestatud viitega (`tests/kuld/viited.json`). Test kukub, kui raporti **kood** muudab lehti. Uued andmed testi ei kuku. Kui koodimuudatus on teadlik, uuenda viide: `python tests/kuld/ehita.py --uuenda` ja kirjuta põhjus muudatuste logisse.

Fotode asemel kasutab test sünteetilisi testpilte (`tests/kuld/sisend/raportid/fotod/`). Isiklikud fotod ei ole repos. Raport ehitub ka ilma nendeta, ainult avalehe päisepilt jääb puudu. Avaldamiseks pane fotod kohapeal kausta `raportid/fotod/`.

### Liidesetest

Üks leht väljaspool seda repot loeb osa selle kausta failidest lukustatud koopiast. `tests/test_liides.py` kontrollib, et need failid on alles ja nende veerud ei muutunud (`tests/liides.json`). Kui muudad neid teadlikult, uuenda `liides.json` ja anna lehe hooldajale teada.

## Kuidas see töötab

1. `naitajad.json`: iga näitaja kirjeldus, sealhulgas allikas, filtrid, sagedus, piirangud, teised allikad ja selgitus „mida see tähendab“. Uue näitaja lisamiseks lisa siia uus plokk.
2. `seire/eurostat.py`: laadib andmed Eurostati API-st ja teeb JSON-stat vastusest tabeli.
3. `seire/kontrollid.py`: kontrollib, et andmeid tuli, et kordusi pole, et ükski riik ega aasta pole puudu, et väärtused jäävad vahemikku 0–100 ja millised märgendid andmetel on.
4. `seire/usaldus.py`: arvutab värskuse (ajakohane, aegumas või aegunud) ja võrdleb numbrit teiste allikatega.
5. `seire/kaart.py`: koostab numbrikaardi ja graafiku.
6. `run.py`: paneb kõik kokku ja logib iga muutunud väärtuse faili `andmed/muutused.csv`.

## Uue näitaja lisamine

Iga uue näitaja filtrid kontrolli enne kasutamist. Käivita `python run.py --uuri <andmestik>` ja vaata, et iga filter valib õige koodi ning vastuses jääb igas mõõtmes peale riigi ja aasta alles ainult üks kood. Siis märgi `naitajad.json` failis `"filtrid_kontrollitud": true`. Seni on kaardil hoiatus.

`isoc_eb_ai` filtrid on kontrollitud 27.10.2026. Esialgne `size_emp` kood oli vale, õige kood on `GE10`.

## Uuem number teisest allikast

Statistikaamet avaldab Eesti numbri sageli enne Eurostati. Kui mõni `teised_allikad` kirje annab Eesti kohta uuema aasta kui Eurostat, lisab seire kaardile hoiatuse „Uuem number on juba olemas“. Meta-failis on see väljal `uuem_allikas` (kirje või `null`), kokkuvõttes tõeväärtusena.

Statistikaameti numbri saab lasta ka automaatselt laadida. Selleks lisa näitajale `riiklik_allikas`:

```json
"riiklik_allikas": {
  "tabel": "majandus/infotehnoloogia/infotehnoloogia-ettevettes/IT1490",
  "aasta_moode": "Aasta",
  "valikud": {"<muutuja kood>": ["<väärtuse kood>"]}
}
```

Muutujate ja koodide leidmiseks käivita `python run.py --uuri-sa <tabel>`. Päring peab andma iga aasta kohta täpselt ühe väärtuse, muidu annab seire vea. Kui laadimine ebaõnnestub, jätkab seire Eurostati andmetega ja lisab kaardile hoiatuse.

## Allikate register

Kaustas `allikad/` on kõik ametlikud statistikaametid ja andmeallikad (`allikad.csv`): API aadress, litsents, tehisaru tabelid, uuendamise sagedus ja kas API töötab siit keskkonnast. Juba avaldatud 2026. aasta numbrid on failis `allikad/numbrid-2026.csv`.

## Kataloog ja allikate võrdlus

`python kataloog/lae_valis.py` laeb OECD, ILOSTATi ning Taani, Norra, Soome, Rootsi, Hollandi, Ühendkuningriigi ja Kanada statistikaametite numbrid kataloogi (`kataloog/vaatlused-valis.csv`, olek failis `kataloog/valis-olek.csv`).

Kaustas `kataloog/` on kõigi küsimuste teemapuu (tehisaru kasutus, andmed, oskused, tööturg, haridus ja teadus, investeeringud), iga küsimuse allikad koos määratlusega ja numbrid eri allikatest. `python -m seire.kataloog` kontrollib kataloogi ja võrdleb allikaid. Täpsemalt: `kataloog/README.md`.
