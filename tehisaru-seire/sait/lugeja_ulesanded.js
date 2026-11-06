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
  {nimi: 'Analüütik: kas Eurostat ja Statistikaamet lahknevad', klikid: ['css:main a:has-text("lahknevust")'], siht: '#lahknevused'},
  {nimi: 'Hankija: hea näide tehisaruhankest', klikid: ['Avalik sektor', 'Hanked (katseline)', 'Leia hea näide'], siht: '#loend'},
  {nimi: 'Otsustaja: ettevõtete siht ja kaugus', klikid: ['Ettevõtted', 'Siht'], siht: '#siht-ettevotted'},
  {nimi: 'Kadri: mis täna muutus', klikid: ['Mis muutus'], siht: '#muutus'},
];
(async () => {
  const b = await chromium.launch();
  for (const w of [1280, 390]) {
    const p = await b.newPage({viewport: {width: w, height: w > 500 ? 800 : 844}});
    for (const u of U) {
      await p.goto(D + 'index.html');
      let ok = true, klikke = 0; const puudu = [];
      for (const k of u.klikid) {
        const l = k.startsWith('css:') ? p.locator(k.slice(4)).first() : p.locator(`header a:text-is("${k}"), nav a:text-is("${k}")`).first();
        if (!(await l.count()) || !(await l.isVisible())) { puudu.push(k); continue; }
        await l.click().catch(() => { ok = false; });
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
      console.log(`${w}px | ${u.nimi} | klikke ${klikke} | ${ok && y !== null ? 'leitud, ekraane siht ' + ekraan : 'EI LEIDNUD'} ${puudu.length ? ' (nuppu pole nähtaval: ' + puudu.join(', ') + ', tuleb kerida)' : ''} | horisontaalne üle ${ylevool}px | ${p.url().split('/').pop()}`);
    }
    // menüü telefonis: kas kõik 6 teemat nähtaval
    await p.goto(D + 'index.html');
    const menu = await p.$$eval('ul.menu a', as => as.map(a => { const r = a.getBoundingClientRect(); return [a.textContent, Math.round(r.right), r.width > 0]; }));
    const peidus = menu.filter(m => m[1] > w).map(m => m[0]);
    console.log(`${w}px | menüü: ${peidus.length ? 'ekraanilt väljas ' + peidus.join(', ') : 'kõik teemad nähtaval'}`);

    // Kasutusloogika (oskus kasutusloogika 6.11.2026): väikesed sihtmärgid ja tagasi-nupp
    const vaiksed = {};
    for (const f of ['index.html', 'too.html', 'hanked.html', 'uudised.html', 'ettevotted-voimekus.html']) {
      await p.goto(D + f);
      const v = await p.evaluate(() => [...document.querySelectorAll('a[href], button, summary')]
        .filter(e => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0; })
        .filter(e => !(getComputedStyle(e).display === 'inline' && e.closest('p,li,td,small,.allikas,.src')))
        .map(e => { const r = e.getBoundingClientRect(); return [e.tagName + (e.className ? '.' + String(e.className).split(' ')[0] : ''), Math.round(Math.min(r.width, r.height))]; })
        .filter(x => x[1] < 24));
      v.forEach(([k, m]) => { vaiksed[k] = Math.min(vaiksed[k] ?? 99, m); });
    }
    console.log(`${w}px | alla 24 px sihtmärgid: ${Object.keys(vaiksed).length ? Object.entries(vaiksed).map(([k, m]) => k + ' ' + m + 'px').join(', ') : 'pole'}`);
    await p.goto(D + 'index.html'); await p.evaluate(() => window.scrollTo(0, 1200)); await p.waitForTimeout(150);
    const y0 = await p.evaluate(() => scrollY);
    await p.locator('ul.menu a:text-is("Töö")').click(); await p.waitForTimeout(150);
    await p.goBack(); await p.waitForTimeout(300);
    console.log(`${w}px | tagasi-nupp: avalehelt (kerimine ${y0}) Töö lehele ja tagasi → ${p.url().split('/').pop()}, kerimine ${await p.evaluate(() => scrollY)}`);
    if (PILDID) await p.screenshot({path: path.join(PILDID, `index-${w}.png`)});
    await p.close();
  }
  await b.close();
})();
