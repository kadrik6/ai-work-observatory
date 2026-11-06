const { chromium } = require('playwright');
// Lugeja ülesanded renderdatud saidil 1280 ja 390 px (oskus andmesaidi-ulesehitus, samm 7). Ekspertkontroll, mitte kasutajatest.
// Käivita: node sait/lugeja_ulesanded.js [valjund/sait] [kaust ekraanipiltidele]
const path = require('path');
const D = 'file://' + path.resolve(process.argv[2] || path.join(__dirname, '..', 'valjund', 'sait')) + '/';
const PILDID = process.argv[3] || null;
// Iga ülesanne: algus, klikid (lingi tekst päises/sisus), siht (CSS), mida peab nägema
const U = [
  {nimi: 'Ajakirjanik: Eesti inimeste tehisaru kasutus ja allikas', klikid: [], siht: '.plaat, .vastus div', tekst: /65/},
  {nimi: 'Kodanik: kas tehisaru võtab töökohti', klikid: ['Töö'], siht: 'h1'},
  {nimi: 'Analüütik: kas Eurostat ja Statistikaamet lahknevad', klikid: ['Uudised ja väited', 'Väited', 'Lahknevused'], siht: '#lahknevused'},
  {nimi: 'Hankija: hea näide tehisaruhankest', klikid: ['Avalik sektor', 'Hanked (katseline)', 'Leia hea näide'], siht: '#loend'},
  {nimi: 'Otsustaja: ettevõtete siht ja kaugus', klikid: ['Ettevõtted', 'Siht'], siht: '#siht-ettevotted'},
  {nimi: 'Kadri: mis täna muutus', klikid: [], siht: '#muutus'},
];
(async () => {
  const b = await chromium.launch();
  for (const w of [1280, 390]) {
    const p = await b.newPage({viewport: {width: w, height: w > 500 ? 800 : 844}});
    for (const u of U) {
      await p.goto(D + 'index.html');
      let ok = true, klikke = 0;
      for (const k of u.klikid) {
        const l = p.locator(`header a:text-is("${k}"), nav a:text-is("${k}")`).first();
        if (!(await l.count())) { ok = false; break; }
        const vis = await l.isVisible();
        await l.click({force: !vis}).catch(() => { ok = false; });
        klikke++; await p.waitForTimeout(250);
      }
      const el = p.locator(u.siht).first();
      let y = null;
      if (ok && await el.count()) {
        const r = await el.evaluate(e => { const b = e.getBoundingClientRect(); return b.top + window.scrollY; });
        const sy = await p.evaluate(() => window.scrollY);
        y = r; var ekraan = ((r - sy) / (w > 500 ? 800 : 844)).toFixed(1);
      }
      const ylevool = await p.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
      console.log(`${w}px | ${u.nimi} | klikke ${klikke} | ${ok && y !== null ? 'leitud, ekraane siht ' + ekraan : 'EI LEIDNUD'} | horisontaalne üle ${ylevool}px | ${p.url().split('/').pop()}`);
    }
    // menüü telefonis: kas kõik 6 teemat nähtaval
    await p.goto(D + 'index.html');
    const menu = await p.$$eval('ul.menu a', as => as.map(a => { const r = a.getBoundingClientRect(); return [a.textContent, Math.round(r.right), r.width > 0]; }));
    const peidus = menu.filter(m => m[1] > w).map(m => m[0]);
    console.log(`${w}px | menüü: ${peidus.length ? 'ekraanilt väljas ' + peidus.join(', ') : 'kõik teemad nähtaval'}`);
    if (PILDID) await p.screenshot({path: path.join(PILDID, `index-${w}.png`)});
    await p.close();
  }
  await b.close();
})();
