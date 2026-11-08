# Seire sait veebis (Vercel)

Kadri 8.11.2026: sait peab olema kolleegidele avatav link, mis ehitub GitHubist ja uueneb ise.

## Kuidas see töötab

1. Vercel ehitab saidi `main` harust: `cd tehisaru-seire && python3 sait/ehita.py` (ainult Pythoni standardteek).
   Veebi läheb ainult kaust `tehisaru-seire/valjund/sait`. Teisi repo faile Vercel ei serveeri.
2. Teiste harude eelvaateid ei ehitata (`ignoreCommand` failis `vercel.json`).
3. Otsingumootorid saiti ei indekseeri: päis `X-Robots-Tag: noindex, nofollow` ja `robots.txt`.
   Kes lingi saab, see näeb. Avalikuks tegemine (indekseerimise lubamine) on Kadri otsus.
4. Ametlik statistika uueneb iga päev: töö `.github/workflows/sait-andmed.yml` laeb numbrid allikatest,
   ehitab saidi, jooksutab testid ja turvakontrolli ning teeb commit'i `main` harule ainult siis, kui mõni number muutus.
   Iga selline commit käivitab Verceli uue ehituse. Kui uus number ei klapi lehe pealkirjaga, töö kukub ja
   GitHub saadab teate; sait jääb eelmise seisuga.
5. Uudised, koondajad, AI-kuulutused, hanked ja publikatsioonid tulevad projekti igapäevastest töödest
   (`sait/vota_kaasa.py`). Need jõuavad veebi, kui nende hetkeseis (`sait/sisu/`) on `main` harus.

## Ühekordne seadistus (Kadri)

1. vercel.com → Add New → Project → Import Git Repository → `kadrik6/ai-work-observatory`
   (esimesel korral küsib Vercel luba GitHubi rakendusele; anna ligipääs ainult sellele repole).
2. Framework Preset: Other. Root Directory: jäta tühjaks (repo juur). Muud seaded tulevad failist `vercel.json`.
3. Deploy. Aadress on kujul `<projekt>.vercel.app`.
