# Ettekanded: igapäevane otsing ja kokkuvõtte mustand

Kadri otsus 8.11.2026: lehel Uudised › Ettekanded on usaldatud seminaride ja konverentside ettekannete kokkuvõtted.
Kanalite loend on failis `kataloog/ettekannete-kanalid.json` (Kadri valik „jah 1-4, 6-8“).

## 1. Otsing (GitHub Actions, iga päev 06:17 Tallinna aja järgi)

`.github/workflows/ettekanded.yml` käivitab `sait/lae_ettekanded.py`:
- loeb iga kanali YouTube'i RSS-voo (TÜ seminari puhul seminarilehe lingid);
- jätab kandidaadiks videod, mis on alla 120 päeva vanad ja räägivad tehisarust, andmetest või tööst;
  TÜ seminari uued salvestised lähevad kandidaadiks alati;
- kirjutab `sait/sisu/ettekannete-kandidaadid.json` (olek `uus`, `teemaväline` või `vana`) ja teeb commit'i main'i;
- proovib uutele kandidaatidele automaatsubtiitreid (`yt-dlp`). Need jäävad 7 päevaks töö artefaktiks `subtiitrid`
  ega lähe repo ega saidile.

## 2. Mustand (igapäevane töö, 07:23)

1. `git pull` ja vaata failist `sait/sisu/ettekannete-kandidaadid.json` kirjeid olekuga `uus`.
   Jäta vahele need, mille video on juba failis `/mnt/project-files/seire-uks-sait/ettekanded.json`.
2. Subtiitrid: `gh run download -R kadrik6/ai-work-observatory -n subtiitrid -D /tmp/subt`
   (viimane `ettekanded` jooks). Kui subtiitreid pole, kirjuta päeva aruandesse rida
   „subtiitrid puuduvad: <link>“. Kadri saab need oma arvutis võtta käsuga `yt-dlp --write-auto-subs --skip-download`.
3. Kirjuta iga sobiva ettekande kohta kirje faili `/mnt/project-files/seire-uks-sait/ettekanded.json`
   **ilma** väljata `seire_olek` (= ootab kinnitust). Väljad: `id`, `esineja`, `amet`, `pealkiri`, `allikas`
   (kanali id), `uritus`, `uritus_url`, `kuupaev`, `video` (link koos `?t=` ettekande algusega), `keel`, `teemad`,
   `kokkuvote` (2 lauset oma sõnadega), `mottes` (3 punkti), `kontroll` (millised väited kontrolliti subtiitrite vastu),
   `liik: "ettekanne"`.
   Transkripti teksti saidile ega repo ei kopeeri. Esineja kogemus on arvamus, mitte mõõtmistulemus.
4. Kui kanal on uus, lisa see ka faili `ettekanded.json` `allikad` loendisse.
5. `python3 sait/ootel.py /mnt/project-files/` näitab Kadrile ootel kirjeid. Kadri vastab „jah ID“ või „jah kõik“.
