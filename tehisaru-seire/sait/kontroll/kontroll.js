// Renderkontroll enne avaldamist (kohapeal, mitte CI-s):
//   node sait/kontroll/kontroll.js KAUST PILDID leht.html …
// Kontrollib konsooli vigu, ülevoolu 1280 ja 390 px juures, kõrgeid vaateid 1366 × 768 juures ja nuppe üle 36 px.
// Teeb kuvatõmmised heledas ja tumedas teemas. Välised fondid võivad võrguta jääda laadimata.
const { chromium } = require('playwright');
const path = require('path');
(async () => {
  const [kaust, pildid, ...lehed] = process.argv.slice(2);
  const b = await chromium.launch();
  let vigu = 0;
  for (const f of lehed) {
    for (const [w, h, nimi] of [[1366, 768, 'sylearvuti'], [1280, 720, 'projektor'], [390, 844, 'telefon']]) {
      for (const teema of ['light', 'dark']) {
        const p = await b.newPage({ viewport: { width: w, height: h }, colorScheme: teema });
        const vead = [];
        p.on('console', (m) => { if (m.type() === 'error' && !/fonts\.g/.test(m.text())) vead.push(m.text()); });
        p.on('pageerror', (er) => vead.push(String(er)));
        await p.goto('file://' + path.resolve(kaust, f));
        await p.waitForTimeout(300);
        const m = await p.evaluate((vh) => {
          const lai = document.documentElement.scrollWidth > window.innerWidth + 1;
          const yle = [...document.querySelectorAll('body *')].filter((e) => {
            const r = e.getBoundingClientRect();
            return r.width > 0 && r.right > window.innerWidth + 1 && !e.closest('.tbl, .menu, .kaart');
          }).map((e) => e.tagName.toLowerCase() + '.' + String(e.className).split(' ')[0]).slice(0, 5);
          const riba = document.querySelector('.top').getBoundingClientRect().height;
          const korged = [...document.querySelectorAll('figure')].filter((e) => e.getBoundingClientRect().height > vh - riba)
            .map((e) => (e.getAttribute('aria-labelledby') || 'figure') + ' ' + Math.round(e.getBoundingClientRect().height) + 'px');
          const nupud = [...document.querySelectorAll('button, .menu a')].filter((e) => e.getBoundingClientRect().height > 36 && innerWidth > 680).length;
          const g = document.querySelector('figure .ribad');
          const t = document.querySelector('figure .gt');
          return { lai, yle, korged, nupud, riba: Math.round(riba),
            graafiku_pealkiri_y: t ? Math.round(t.getBoundingClientRect().top + scrollY) : null,
            graafik_algab_y: g ? Math.round(g.getBoundingClientRect().top + scrollY) : null };
        }, h);
        const probleem = m.lai || m.yle.length || vead.length || (w > 680 && m.nupud);
        if (probleem) vigu++;
        console.log(`${f} ${w}x${h} ${teema}: ${JSON.stringify(m)}${vead.length ? ' VEAD ' + vead.join(' | ') : ''}`);
        if (pildid) {
          await p.screenshot({ path: path.join(pildid, `${f.replace('.html', '')}-${nimi}-${teema}.png`), fullPage: w === 390 });
          if (w === 1366) await p.screenshot({ path: path.join(pildid, `${f.replace('.html', '')}-${nimi}-${teema}-terve.png`), fullPage: true });
        }
        await p.close();
      }
    }
  }
  await b.close();
  process.exit(vigu ? 1 : 0);
})();
