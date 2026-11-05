# Märgendusjuhend: kas hange on AI- või andmehange?

Üks lehekülg, et kaks märgendajat otsustaksid ühtemoodi (CRISP-DM etapp 3, samm 8). Märgendaja loeb hanke
pealkirja, lühikirjelduse, osade nimed ja CPV-koodi. Hanke dokumente ei avata.

## Sildid

| Silt | Millal | Näited |
|---|---|---|
| **AI** | Hanke põhiese või selge osa on tehisintellekti või masinõppe lahendus, selle arendus, kasutuselevõtt või sellega seotud teenus. | kõnetuvastus, masintõlge, juturobot, pildi- või objektituvastus, ennustusmudel, dokumentide automaatne liigitamine, keelemudeli kasutuselevõtt, AI-nõustamine |
| **ANDMED** | Põhiese on andmete analüüs või andmelahendus, mis ei ole AI: andmeladu, andmeplatvorm, analüütika- või BI-lahendus, andmekvaliteet ja -haldus, statistiline modelleerimine, andmeanalüüsi teenus. | andmelao arendus, Power BI aruandluslahendus, registriandmete analüüs ja mudel, andmehaldusplatvorm |
| **EI** | Kõik muu. | tavaline tarkvaraarendus ilma andme- või AI-fookuseta, infosüsteemi hooldus, litsentsid, riistvara, küsitlusuuring, sotsioloogiline uuring, ehitus |

## Piirijuhud

- **Infosüsteemi arendus, kus AI on üks mitmest funktsioonist:** AI, kui AI-funktsioon on kirjelduses nimeliselt
  välja toodud (nt „sh tekstituvastus“). Muidu EI.
- **Uuring:** küsitlus- või intervjuuuuring on EI. Uuring, mille põhiosa on olemasolevate andmete modelleerimine
  või analüüs (nt registriandmete ühendamine ja mõjuhinnang), on ANDMED.
- **„Andmebaasi hooldus“, „andmesideteenus“, „andmekandja“:** EI. Sõna „andmed“ üksi ei tee hanget andmehankeks.
- **Liikluse või hoonete automaatika „algoritm“:** EI, kui ei ole masinõpet või andmeanalüüsi.
- **Kaardistus, GIS, aerofotod:** EI, välja arvatud kui põhiese on andmete analüüs või automaatne tuvastus (nt
  „ortofotodelt hoonete automaatne tuvastus“ on AI).
- **AI-koolitus, AI-nõustamine, uuring tehisintellekti kohta:** AI.
- **Riistvara AI jaoks (serverid, graafikakaardid):** EI. Hange ostab rauda, mitte lahendust.
- **AI-funktsioon seadme lisana** (nt alkomeetri näotuvastuse litsents): EI, kui hanke põhiese on seade.
- **BI- ja analüütikalitsentsid** (Tableau, Power BI, SAP BusinessObjects, SAS, Snowflake): ANDMED.
- **Kaheldes:** vali EI ja kirjuta märkus. Kahtlased read vaatab teine märgendaja üle.

## Kvaliteet

- Esimese ringi märgendas Claude (märgendaja `claude-2026-11-04`). See on **inimese poolt kontrollimata**
  märgendus ja seda tuleb tõlgendada nii.
- Valimi kihid on tehtud märksõnaloendi järgi ja märgendaja nägi märksõnu. See soosib märksõnaloendit
  hindamisel. Inimese kontroll peab olema pime: märgendaja ei näe kihti ega märksõnu.
- Kontrolliks märgendab inimene vähemalt 100 rida uuesti teadmata Claude'i silti. Kokkulangevust mõõdetakse
  Coheni kappaga; siht on vähemalt 0,6.
- Lahknevused arutatakse läbi ja juhendit täpsustatakse. Muudatus kirjutatakse faili `UUENDUSED.md`.
