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
  {nimi: 'Analüütik: kas Eurostat ja Statistikaamet lahknevad', klikid: ['Usaldus', 'Lahknevused'], siht: '#lahknevused'},
  {nimi: 'Hankija: hea näide tehisaruhankest', klikid: ['Hanked', 'Leia hea näide'], siht: '#loend'},
  {nimi: 'Otsustaja: ettevõtete siht ja kaugus', klikid: ['Ettevõtted'], siht: '#kasutus .siht-rida'},
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
        // Päise link enne lehe sisu linke (avalehe „Sellel lehel“ reas on samanimelised ankrud). Telefonis on teemad
        // „Menüü“ taga (navigatsioon B, 6.11.2026): kui teema on menüüs, ava menüü ja klõpsa seal.
        let l;
        if (k.startsWith('css:')) l = p.locator(k.slice(4)).first();
        else {
          l = p.locator(`header a:text-is("${k}"):visible`).first();
          if (!(await l.count()) && await p.locator(`.mega-paneel a.mega-nimi:text-is("${k}")`).count() && await p.locator('details.mega > summary').isVisible()) {
            await p.click('details.mega > summary'); klikke++; await p.waitForTimeout(150);
            l = p.locator(`header a:text-is("${k}"):visible`).first();
          }
          if (!(await l.count())) l = p.locator(`nav a:text-is("${k}"):visible`).first();
        }
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
    // menüü: kas kõik teemad on nähtaval (telefonis pärast „Menüü“ avamist)
    await p.goto(D + 'index.html');
    if (!(await p.locator('ul.menu').isVisible())) await p.click('details.mega > summary');
    const sel = (await p.locator('ul.menu').isVisible()) ? 'ul.menu a' : '.mega-paneel a.mega-nimi';
    const menu = await p.$$eval(sel, as => as.map(a => { const r = a.getBoundingClientRect(); return [a.textContent, Math.round(r.right), r.width > 0 && r.bottom <= innerHeight]; }));
    const peidus = menu.filter(m => m[1] > w || !m[2]).map(m => m[0]);
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
    // „Sellel lehel“: klõpsatud link on pärast klõpsu märgitud (Kadri kommentaar 7.11.2026: kõrvuti plokkidel värvus vale link)
    const valesti = [];
    for (const f of ['index.html', 'too.html', 'ettevotted.html', 'inimesed.html']) {
      await p.goto(D + f); await p.waitForTimeout(200);
      const hrefid = await p.$$eval('.lehel .sellel a[href^="#"]', as => [...new Set(as.map(a => a.getAttribute('href')))]);
      for (const h of hrefid) {
        const l = p.locator(`.lehel .sellel a[href="${h}"]:visible`).first();
        if (!(await l.count())) continue;
        await l.click(); await p.waitForTimeout(400);
        const cur = await p.$$eval('.lehel .sellel a[aria-current]', as => [...new Set(as.map(a => a.getAttribute('href')))]);
        if (cur.length !== 1 || cur[0] !== h) valesti.push(`${f}${h}→${cur.join(',') || '-'}`);
      }
    }
    console.log(`${w}px | „Sellel lehel“ märge pärast klõpsu: ${valesti.length ? 'VALE ' + valesti.join(', ') : 'õige'}`);
    await p.goto(D + 'index.html'); await p.evaluate(() => window.scrollTo(0, 1200)); await p.waitForTimeout(150);
    const y0 = await p.evaluate(() => scrollY);
    // hiireklõps koordinaadile: locator.click() kerib enne klõpsu ja rikuks tagasi-nupu mõõtmise
    if (!(await p.locator('ul.menu').isVisible())) { const sb = await p.locator('details.mega > summary').boundingBox(); await p.mouse.click(sb.x + 5, sb.y + 5); await p.waitForTimeout(150); }
    const bx = await p.locator('ul.menu a:text-is("Töö"):visible, .mega-paneel a:text-is("Töö"):visible').first().boundingBox();
    await p.mouse.click(bx.x + bx.width / 2, bx.y + bx.height / 2); await p.waitForTimeout(250);
    await p.goBack(); await p.waitForTimeout(300);
    console.log(`${w}px | tagasi-nupp: avalehelt (kerimine ${y0}) Töö lehele ja tagasi → ${p.url().split('/').pop()}, kerimine ${await p.evaluate(() => scrollY)}`);
    if (PILDID) await p.screenshot({path: path.join(PILDID, `index-${w}.png`)});
    await p.close();
  }
  await b.close();
})();
