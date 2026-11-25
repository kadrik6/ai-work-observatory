# Seire sait veebis (Vercel)

Kadri 8.11.2026: sait peab olema kolleegidele avatav link, mis ehitub GitHubist ja uueneb ise.

## Kuidas see töötab

1. Vercel ehitab saidi `main` harust: `cd tehisaru-seire && python3 sait/ehita.py` (ainult Pythoni standardteek).
   Veebi läheb ainult kaust `tehisaru-seire/valjund/sait`. Teisi repo faile Vercel ei serveeri.
2. Teiste harude eelvaateid ei ehitata (`ignoreCommand` failis `vercel.json`).
3. Otsingumootorid indekseerivad saiti alates 21.11.2026 (Kadri otsus). Põhiaadress on `https://www.tehisaruseire.ee/`:
   igal lehel on sinna canonical-link, `robots.txt` lubab kõike ja näitab `sitemap.xml`-i. `*.vercel.app` aadressil jääb
   päis `X-Robots-Tag: noindex, nofollow`, et sama sisu ei oleks otsingus kahe aadressiga.
4. Ametlik statistika uueneb iga päev: töö `.github/workflows/sait-andmed.yml` laeb numbrid allikatest,
   ehitab saidi, jooksutab testid ja turvakontrolli ning teeb commit'i `main` harule ainult siis, kui mõni number muutus.
   Iga selline commit käivitab Verceli uue ehituse. Kui uus number ei klapi lehe pealkirjaga, töö kukub ja
   GitHub saadab teate; sait jääb eelmise seisuga.
   Sama töö laeb ka töötuse kuurea (`sait/lae_tootus.py`, Eurostat une_rt_m): uus kuu jõuab lehele samal päeval,
   kui Eurostat avaldab nii Eesti kui ka ELi numbri.
   Registreeritud töötute arvu laeb `sait/lae_reg_tootud.py` (Statistikaamet TT065, Töötukassa andmed); see on
   eraldi plokis ja töötuse määraga seda ei võrrelda.
5. Uudised, koondajad, AI-kuulutused, hanked ja publikatsioonid tulevad projekti igapäevastest töödest
   (7.23 ja 17.53 Tallinna aja järgi). Iga töö viimane samm on `bash tehisaru-seire/sait/sisu_maini.sh`
   puhtas koopias: see võtab hetkeseisu (`sait/vota_kaasa.py`), ehitab saidi, jooksutab testid ja turvakontrolli
   ning push'ib `main` harusse ainult kausta `sait/sisu/` (Kadri otsus 8.11.2026). Kui midagi kukub, push'i ei tule.

## Ühekordne seadistus (Kadri)

1. vercel.com → Add New → Project → Import Git Repository → `kadrik6/ai-work-observatory`
   (esimesel korral küsib Vercel luba GitHubi rakendusele; anna ligipääs ainult sellele repole).
2. Framework Preset: Other. Root Directory: jäta tühjaks (repo juur). Muud seaded tulevad failist `vercel.json`.
3. Deploy. Aadress on kujul `<projekt>.vercel.app`.

## Igapäevased andmed ja Deploy Hook (8.11.2026)

Vercel Hobby ehitab `main`-i git-push'ist ainult siis, kui commit'i autor on Kadri. Igapäevaste andmete
commit'id (`seire-igapaevane`, `github-actions[bot]`) saavad Vercelis oleku „Deployment was blocked“.
Seepärast käivitab töövoog `.github/workflows/vercel-ehita.yml` ehituse Deploy Hookiga. Ühekordne seadistus:

1. Vercelis: projekt → Settings → Git → Deploy Hooks. Nimi `igapaevane`, haru `main` → Create Hook. Kopeeri URL.
2. GitHubis: repo → Settings → Secrets and variables → Actions → New repository secret.
   Nimi `VERCEL_DEPLOY_HOOK`, väärtus on see URL. URL-i ära kopeeri vestlusesse ega faili.

Kui saladust pole, töövoog jätab ehituse vahele ja sait jääb viimase Kadri commit'i seisu.
