// Tehisaru seire: teemalüliti ja pikkade tabelite valik „12 / 24 / 48 / kõik“. Ilma selleta töötab leht samuti.
(function () {
  var VOTI = 'seire-teema-2'; // uus võti 6.11.2026: varem salvestatud „Hele“ ei kata enam vaikimisi Pehmet
  var juur = document.documentElement;
  function loe() { try { return localStorage.getItem(VOTI); } catch (e) { return null; } }
  function kirjuta(v) { try { localStorage.setItem(VOTI, v); } catch (e) { /* privaatne aken */ } }
  // Kolm teemat: Hele → Pehme → Tume → Hele (Kadri 5.11.2026). Oma atribuut data-seire-teema, sest claude.ai artefakti kest kirjutab juure data-theme üle (alamlehel tuli Hele, 6.11.2026). Ilma valikuta Pehme, süsteemi tumeda korral Tume.
  var JARG = ['light', 'soft', 'dark'];
  var NIMI = { light: 'Hele', soft: 'Pehme', dark: 'Tume' };
  function praegune() {
    var t = juur.getAttribute('data-seire-teema');
    if (JARG.indexOf(t) >= 0) return t;
    return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  }
  var salvestatud = loe();
  // Vaikimisi Pehme (Kadri 6.11.2026); süsteemi tumeda teema korral jääb Tume.
  if (JARG.indexOf(salvestatud) >= 0) juur.setAttribute('data-seire-teema', salvestatud);
  else if (!(window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches)) juur.setAttribute('data-seire-teema', 'soft');

  function uuendaNupp(nupp) {
    var t = praegune(), j = JARG[(JARG.indexOf(t) + 1) % 3];
    var silt = 'Teema: ' + NIMI[t] + '. Vaheta: ' + NIMI[j];
    nupp.setAttribute('aria-label', silt);
    nupp.setAttribute('title', silt);
    nupp.setAttribute('data-t', t);
  }
  document.addEventListener('DOMContentLoaded', function () {
    var nupp = document.querySelector('.teema');
    if (nupp) {
      uuendaNupp(nupp);
      nupp.addEventListener('click', function () {
        var uus = JARG[(JARG.indexOf(praegune()) + 1) % 3];
        juur.setAttribute('data-seire-teema', uus);
        kirjuta(uus);
        uuendaNupp(nupp);
      });
    }
    // Kaart: hõljudes riik ette, teised tuhmiks, silt hiire juurde. Puutel sama koputusega.
    document.querySelectorAll('.kaart').forEach(function (k) {
      var vihje = k.querySelector('.kaart-vihje');
      var svg = k.querySelector('svg');
      var fookus = svg && svg.querySelector('path.fookus');
      var praegu = null;
      function peida() {
        if (praegu) praegu.classList.remove('on');
        praegu = null;
        k.classList.remove('hoiab');
        if (vihje) vihje.hidden = true;
        if (fookus) svg.appendChild(fookus); // Eesti piirjoon jääb jälle pealmiseks
      }
      function naita(p, x, y) {
        if (praegu !== p) {
          if (praegu) praegu.classList.remove('on');
          praegu = p;
          p.classList.add('on');
          svg.appendChild(p);
          k.classList.add('hoiab');
          vihje.innerHTML = '';
          var b = document.createElement('b');
          b.textContent = p.getAttribute('data-n');
          var v = document.createElement('span');
          v.textContent = p.getAttribute('data-v');
          b.appendChild(v);
          vihje.appendChild(b);
          if (p.getAttribute('data-a')) {
            var a = document.createElement('small');
            a.textContent = p.getAttribute('data-a');
            vihje.appendChild(a);
          }
          vihje.hidden = false;
        }
        var r = k.getBoundingClientRect();
        var lx = x - r.left + 14, ly = y - r.top + 14;
        if (lx + vihje.offsetWidth > r.width) lx = x - r.left - vihje.offsetWidth - 14;
        if (ly + vihje.offsetHeight > r.height) ly = y - r.top - vihje.offsetHeight - 14;
        vihje.style.left = Math.max(0, lx) + 'px';
        vihje.style.top = Math.max(0, ly) + 'px';
      }
      if (!svg || !vihje) return;
      svg.addEventListener('pointermove', function (ev) {
        var p = ev.target.closest && ev.target.closest('path[data-n]');
        if (p) naita(p, ev.clientX, ev.clientY); else peida();
      });
      svg.addEventListener('pointerleave', peida);
    });
    // Kaart ja järjestus: üks riik esile mõlemas (data-n on sama nimi).
    document.querySelectorAll('.el-rida').forEach(function (rida) {
      var read = rida.querySelectorAll('.jrj-r[data-n]');
      var svg = rida.querySelector('.kaart svg');
      function vali(n) {
        read.forEach(function (r) { r.classList.toggle('on', r.getAttribute('data-n') === n); });
      }
      if (svg) {
        svg.addEventListener('pointermove', function (ev) {
          var p = ev.target.closest && ev.target.closest('path[data-n]');
          vali(p ? p.getAttribute('data-n') : null);
        });
        svg.addEventListener('pointerleave', function () { vali(null); });
      }
      read.forEach(function (r) {
        r.addEventListener('pointerenter', function () {
          var n = r.getAttribute('data-n');
          vali(n);
          if (!svg) return;
          svg.querySelectorAll('path[data-n]').forEach(function (p) { p.classList.toggle('on', p.getAttribute('data-n') === n); });
          svg.parentNode.classList.add('hoiab');
        });
        r.addEventListener('pointerleave', function () {
          vali(null);
          if (!svg) return;
          svg.querySelectorAll('path.on').forEach(function (p) { p.classList.remove('on'); });
          svg.parentNode.classList.remove('hoiab');
        });
      });
    });
    // Pikk tabel: vaikimisi 12 rida.
    document.querySelectorAll('table[data-piir]').forEach(function (tabel) {
      var read = Array.prototype.slice.call(tabel.tBodies[0].rows);
      if (read.length <= 12) return;
      var riba = document.createElement('div');
      riba.className = 'kogus';
      riba.appendChild(document.createTextNode('Näita'));
      [12, 24, 48, 0].forEach(function (n) {
        if (n && n >= read.length && n !== 12) return;
        var b = document.createElement('button');
        b.type = 'button';
        b.textContent = n ? String(n) : 'kõik (' + read.length + ')';
        b.addEventListener('click', function () { naita(n); });
        riba.appendChild(b);
      });
      function naita(n) {
        read.forEach(function (r, i) { r.hidden = n !== 0 && i >= n; });
        riba.querySelectorAll('button').forEach(function (b) {
          var m = b.textContent.indexOf('kõik') === 0 ? 0 : parseInt(b.textContent, 10);
          b.setAttribute('aria-pressed', m === n ? 'true' : 'false');
        });
      }
      tabel.parentNode.insertAdjacentElement('afterend', riba);
      naita(12);
    });
    // ELi riikide järjestus: vaikimisi esimesed 10, ülejäänud nupust (Kadri 7.11.2026). Fookusriik jääb alati näha.
    document.querySelectorAll('.jrj[data-piir]').forEach(function (j) {
      var piir = parseInt(j.getAttribute('data-piir'), 10) || 10;
      var read = Array.prototype.slice.call(j.querySelectorAll('.jrj-r[data-n]'));
      if (read.length <= piir) return;
      var riba = document.createElement('div');
      riba.className = 'kogus';
      riba.appendChild(document.createTextNode('Näita'));
      [piir, 0].forEach(function (n) {
        var b = document.createElement('button');
        b.type = 'button';
        b.setAttribute('data-n', String(n));
        b.textContent = n ? 'esimesed ' + n : 'kõik (' + read.length + ')';
        b.addEventListener('click', function () { naita(n); });
        riba.appendChild(b);
      });
      function naita(n) {
        read.forEach(function (r, i) { r.hidden = n !== 0 && i >= n && !r.classList.contains('fookus'); });
        riba.querySelectorAll('button').forEach(function (b) {
          b.setAttribute('aria-pressed', b.getAttribute('data-n') === String(n) ? 'true' : 'false');
        });
      }
      j.insertAdjacentElement('afterend', riba);
      naita(piir);
    });
    // Uudiste teemafilter
    document.querySelectorAll('.pn .u-f[aria-label="Vali teema"]').forEach(function (f) {
      var li = f.parentNode.querySelectorAll('.u-voog li');
      f.querySelectorAll('button').forEach(function (b) {
        b.addEventListener('click', function () {
          var t = b.getAttribute('data-f');
          f.querySelectorAll('button').forEach(function (x) { x.setAttribute('aria-pressed', x === b ? 'true' : 'false'); });
          li.forEach(function (l) { l.hidden = !!t && l.getAttribute('data-teema') !== t; });
        });
      });
    });
    // Hangete otsing ja rühmafilter; otsingu ajal näidatakse kõik sobivad read
    document.querySelectorAll('.h-otsing').forEach(function (o) {
      var tabel = o.parentNode.querySelector('table.h-tabel');
      var read = Array.prototype.slice.call(tabel.tBodies[0].rows);
      var sisend = o.querySelector('input'), loe = o.querySelector('.h-loe'), ruhm = '';
      function riba() { var r = tabel.parentNode.nextElementSibling; return r && r.classList.contains('kogus') ? r : null; }
      function filtreeri() {
        var q = sisend.value.trim().toLowerCase(), k = riba();
        if (!q && !ruhm) {
          if (k) { k.hidden = false; k.querySelector('button').click(); } else { read.forEach(function (r) { r.hidden = false; }); }
          loe.textContent = '';
          return;
        }
        if (k) k.hidden = true;
        var n = 0;
        read.forEach(function (r) {
          var ok = (!q || r.getAttribute('data-otsi').indexOf(q) >= 0) &&
            (!ruhm || (ruhm === 'hea' ? r.getAttribute('data-hea') === '1' : r.getAttribute('data-ruhm') === ruhm));
          r.hidden = !ok; if (ok) n++;
        });
        loe.textContent = n + ' hanget';
      }
      sisend.addEventListener('input', filtreeri);
      o.querySelectorAll('button[data-r]').forEach(function (b) {
        b.addEventListener('click', function () {
          ruhm = b.getAttribute('data-r');
          o.querySelectorAll('button[data-r]').forEach(function (x) { x.setAttribute('aria-pressed', x === b ? 'true' : 'false'); });
          filtreeri();
        });
      });
    });
    // Publikatsioonide sakid
    document.querySelectorAll('.p-tabs').forEach(function (t) {
      var nupud = t.querySelectorAll('[role="tab"]');
      nupud.forEach(function (b) {
        b.addEventListener('click', function () {
          nupud.forEach(function (x) {
            var on = x === b;
            x.setAttribute('aria-selected', on ? 'true' : 'false');
            document.getElementById(x.getAttribute('aria-controls')).hidden = !on;
          });
        });
      });
    });
  });
})();

// Päise kõrgus ankurlinkide jaoks ja „Sellel lehel“ praeguse jaotise märge (Kadri 6.11.2026).
(function () {
  function korgus() {
    var p = document.querySelector('header.top');
    if (p) document.documentElement.style.setProperty('--top-h', p.offsetHeight + 'px');
  }
  document.addEventListener('DOMContentLoaded', function () {
    korgus();
    window.addEventListener('resize', korgus);
    // „Sellel lehel“ on kaks koopiat (laial ekraanil parem veerg, kitsal rida sakkide all); märge käib mõlemas.
    var lingid = Array.prototype.slice.call(document.querySelectorAll('.lehel .sellel a[href^="#"]'));
    if (!lingid.length) return;
    var hrefid = [];
    lingid.forEach(function (a) { var h = a.getAttribute('href'); if (hrefid.indexOf(h) < 0) hrefid.push(h); });
    var sihid = hrefid.map(function (h) { return document.getElementById(h.slice(1)); });
    // Kõrvuti jaotistel (nt sp5 + sp7 ühes reas) on sama ülaserv. Seepärast: klõpsatud link jääb märgituks, kuni
    // lugeja ise kerib (ratas, puude, klahv). Ilma klõpsuta võidab suurima ülaservaga jaotis; viigi korral see,
    // mis on menüüs eespool (Kadri kommentaar 7.11.2026: „valikul värvub vale koht siniseks“).
    var valitud = null;
    function sea(h) {
      lingid.forEach(function (a) {
        if (h && a.getAttribute('href') === h) a.setAttribute('aria-current', 'true'); else a.removeAttribute('aria-current');
      });
    }
    function margi() {
      if (valitud) { sea(valitud); return; }
      var piir = (parseInt(getComputedStyle(document.documentElement).getPropertyValue('--top-h'), 10) || 110) + 24;
      var k = -1, parim = -Infinity;
      sihid.forEach(function (t, i) {
        if (!t) return;
        var y = Math.round(t.getBoundingClientRect().top);
        if (y <= piir && y > parim + 1) { parim = y; k = i; }
      });
      sea(k >= 0 ? hrefid[k] : null);
    }
    lingid.forEach(function (a) {
      a.addEventListener('click', function () { valitud = a.getAttribute('href'); sea(valitud); });
    });
    function vabasta() { valitud = null; }
    ['wheel', 'touchstart', 'keydown'].forEach(function (e) { window.addEventListener(e, vabasta, { passive: true }); });
    if (location.hash && hrefid.indexOf(location.hash) >= 0) valitud = location.hash;
    window.addEventListener('scroll', margi, { passive: true });
    margi();
  });
})();

// Kasutusloogika 6.11.2026: filtri, rühma, saki ja otsingu valik jääb aadressi (?teema=…, ?ruhm=…, ?sakk=…, ?otsi=…),
// et filtreeritud vaadet saaks saata ja värskendamisel valik ei kaoks. replaceState: tagasi-nupp viib eelmisele lehele,
// mitte iga filtriklõpsu juurde tagasi.
(function () {
  function sea(k, v) {
    try {
      var u = new URL(location.href);
      if (v) u.searchParams.set(k, v); else u.searchParams.delete(k);
      history.replaceState(history.state, '', u.pathname + u.search + u.hash);
    } catch (e) { /* nt sandbox ei luba: valik töötab ikka, ainult aadressi ei jää */ }
  }
  document.addEventListener('DOMContentLoaded', function () {
    var q;
    try { q = new URLSearchParams(location.search); } catch (e) { q = { get: function () { return null; } }; }
    var paarid = [
      ['teema', '.u-f[aria-label="Vali teema"] button[data-f]', 'data-f'],
      ['ruhm', 'button[data-r]', 'data-r'],
      ['sakk', '.p-tabs [role="tab"]', 'aria-controls'],
    ];
    paarid.forEach(function (p) {
      var nupud = document.querySelectorAll(p[1]);
      nupud.forEach(function (b) { b.addEventListener('click', function () { sea(p[0], b.getAttribute(p[2])); }); });
      var v = q.get(p[0]);
      if (v) nupud.forEach(function (b) { if (b.getAttribute(p[2]) === v) b.click(); });
    });
    document.querySelectorAll('.h-otsing input').forEach(function (i) {
      i.addEventListener('input', function () { sea('otsi', i.value.trim()); });
      var v = q.get('otsi');
      if (v) { i.value = v; i.dispatchEvent(new Event('input')); }
    });
  });
})();

// „Kõik teemad“ / telefonis „Menüü“ (navigatsioon B, Kadri 6.11.2026): sulgub Esc-iga, klõpsuga mujale ja lingi valimisel.
(function () {
  document.addEventListener('DOMContentLoaded', function () {
    var m = document.querySelector('details.mega');
    if (!m) return;
    var s = m.querySelector('summary');
    function uuenda() { s.setAttribute('aria-expanded', m.open ? 'true' : 'false'); }
    m.addEventListener('toggle', uuenda); uuenda();
    document.addEventListener('keydown', function (ev) { if (ev.key === 'Escape' && m.open) { m.open = false; s.focus(); } });
    document.addEventListener('click', function (ev) { if (m.open && !m.contains(ev.target)) m.open = false; });
    m.querySelectorAll('a').forEach(function (a) { a.addEventListener('click', function () { m.open = false; }); });
  });
})();
