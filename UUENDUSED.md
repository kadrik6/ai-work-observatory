# Muudatuste logi

Uuemad üleval. Varasem ajalugu (26.–30.10.2026) on algses projekti kaustas.

| Aeg | Mis muutus |
|---|---|
| 30.10.2026 | Seire parandused: OpenAlexi uuendusaeg ei loe enam uueks versiooniks (tekitas valesid versioone); OpenAlexi liik "article" on nüüd "artikkel", mitte "eelretsenseeritud". Kirjed lähevad ka käivituse logisse ülevaatelehe jaoks. Uut versiooni võrreldakse nüüd viimase, mitte esimese nähtud seisuga (muidu oleks sama Eurostati uuendus iga päev "uus"), ja `nahtud.jsonl` hoiab iga tööd üks kord. Esimene päris uus versioon: Eurostat `lfsa_egai2d` uuendati 30.10.2026. |
| 30.10.2026 | Lisandus ajastatud seire (`seire.yml`, Kadri valik 30.10): kord päevas, ainult lugemisõigus. Kandidaadid jäävad käivituse artefakti 90 päevaks ja võrreldakse eelmise eduka käivituse kirjetega. Repo ega avaldatud lehti see ei muuda. |
| 30.10.2026 | Esimene proovikäivitus GitHubis: kõik 8 kogujate allikat ja 25 statistika allikat töötasid, duplikaatide tuvastus töötas. Kontrollis selgus, et arXivi päring tõi peamiselt teemaväliseid masinõppe töid: päring kitsendati majanduse ja ühiskonna kategooriatele. ERR-i voo kirjete arv on nüüd olekus näha (0 sobivat uudist ei ole viga, tühi voog on). Kokkuvõttes on näited iga allika kohta. |
| 30.10.2026 | Lisandus `tooelu-seire/`: kogujate proovirežiim (arXiv, OpenAlex, ERR RSS, Eurostati andmestike uuendused), duplikaatide ja versioonide tuvastus, vigade logi, 13 testi ilma võrguta. Töövoog `proov` käivitub ainult käsitsi ja annab tulemuse artefaktina. Eurostati vabade töökohtade andmestik `jvs_q_nace2` on suletud; kogujas on asendaja `jvs_q_r21`. |
| 30.10.2026 | Enne esimest push'i puhastatud: privaatsed claude.ai lingid eemaldatud, isiklikud märkused kommentaaridest eemaldatud (autorlus ja fotoviide jäävad), SVG-de ja testpiltide päritolu metaandmed (C2PA) eemaldatud. Kuldfailitesti viites muutusid `stiil.css` ja 2 testpilti. Sellest hetkest on see repo seire ja turvakontrolli põhikoht. |
| 30.10.2026 | Repo töökoopia loodud. Sisu: `tehisaru-seire/` ilma isiklike fotodeta ja `turvakontroll/` ilma privaatsete loenditeta. Lisatud: CLAUDE.md failid, Claude Code'i õigused ja liivakast, lubatud nimekirjaga `.gitignore`, LF-reavahetused, commit'i konks, GitHub Actionsi testid. Kuldfailitest kasutab sünteetilisi testpilte ja ühtlustab reavahetused. Lisandus liidesetest välisele lehele. |
