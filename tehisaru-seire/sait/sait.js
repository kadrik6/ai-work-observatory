// Tehisaru seire: teemalüliti ja pikkade tabelite valik „12 / 24 / 48 / kõik“. Ilma selleta töötab leht samuti.
(function () {
  var VOTI = 'seire-teema';
  var juur = document.documentElement;
  function loe() { try { return localStorage.getItem(VOTI); } catch (e) { return null; } }
  function kirjuta(v) { try { localStorage.setItem(VOTI, v); } catch (e) { /* privaatne aken */ } }
  // Kolm teemat: Hele → Pehme → Tume → Hele (Kadri 5.11.2026). Ilma valikuta järgib süsteemi heledat või tumedat.
  var JARG = ['light', 'soft', 'dark'];
  var NIMI = { light: 'Hele', soft: 'Pehme', dark: 'Tume' };
  function praegune() {
    var t = juur.getAttribute('data-theme');
    if (JARG.indexOf(t) >= 0) return t;
    return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  }
  var salvestatud = loe();
  if (JARG.indexOf(salvestatud) >= 0) juur.setAttribute('data-theme', salvestatud);

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
        juur.setAttribute('data-theme', uus);
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
    // Koondamised: üks kaart korraga, all mininavigatsioon; tulbal klõps valib sama ettevõtte (Kadri 5.11 23:12).
    var kk = document.querySelector('#koondamised .kk-v');
    if (kk) {
      var kaardid = [].slice.call(kk.querySelectorAll('.kk[data-k]'));
      var nav = document.querySelector('#koondamised .kk-nav');
      var tapid = nav.querySelector('.kk-tapid');
      var loe = nav.querySelector('.kk-loe');
      var ribad = [].slice.call(document.querySelectorAll('#koondamised-visuaal .kr[data-k]'));
      // sama järjekord kui tulpadel, nii et nooled liiguvad tulbalt tulbale
      var jrk = ribad.map(function (r) { return r.getAttribute('data-k'); });
      kaardid.sort(function (a, b) { return jrk.indexOf(a.getAttribute('data-k')) - jrk.indexOf(b.getAttribute('data-k')); });
      var i = 0;
      kaardid.forEach(function (k, j) {
        var b = document.createElement('button');
        b.type = 'button'; b.className = 'kk-tapp';
        b.setAttribute('aria-label', k.querySelector('b').textContent);
        b.addEventListener('click', function () { nayta(j); });
        tapid.appendChild(b);
      });
      function nayta(j) {
        i = (j + kaardid.length) % kaardid.length;
        var kood = kaardid[i].getAttribute('data-k');
        kaardid.forEach(function (k, n) { k.hidden = n !== i; });
        [].forEach.call(tapid.children, function (b, n) { b.setAttribute('aria-current', n === i ? 'true' : 'false'); });
        ribad.forEach(function (r) {
          var on = r.getAttribute('data-k') === kood;
          r.classList.toggle('on', on);
          r.setAttribute('aria-pressed', on ? 'true' : 'false');
        });
        loe.textContent = (i + 1) + ' / ' + kaardid.length;
      }
      kk.classList.add('yks');
      nav.hidden = false;
      nav.querySelector('.kk-e').addEventListener('click', function () { nayta(i - 1); });
      nav.querySelector('.kk-j').addEventListener('click', function () { nayta(i + 1); });
      ribad.forEach(function (r) {
        r.tabIndex = 0;
        r.setAttribute('role', 'button');
        function vali() {
          var j = kaardid.findIndex(function (k) { return k.getAttribute('data-k') === r.getAttribute('data-k'); });
          if (j >= 0) nayta(j);
        }
        r.addEventListener('click', vali);
        r.addEventListener('keydown', function (ev) { if (ev.key === 'Enter' || ev.key === ' ') { ev.preventDefault(); vali(); } });
      });
      nayta(0);
    }
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
    var lingid = Array.prototype.slice.call(document.querySelectorAll('.top .sellel a[href^="#"]'));
    if (!lingid.length) return;
    var sihid = lingid.map(function (a) { return document.getElementById(a.getAttribute('href').slice(1)); });
    function margi() {
      var piir = (parseInt(getComputedStyle(document.documentElement).getPropertyValue('--top-h'), 10) || 110) + 24;
      var k = -1;
      sihid.forEach(function (t, i) { if (t && t.getBoundingClientRect().top <= piir) k = i; });
      lingid.forEach(function (a, i) { if (i === k) a.setAttribute('aria-current', 'true'); else a.removeAttribute('aria-current'); });
      var akt = lingid[k];
      if (akt && akt.parentNode.parentNode.scrollWidth > akt.parentNode.parentNode.clientWidth) {
        var ul = akt.parentNode.parentNode, l = akt.parentNode;
        if (l.offsetLeft < ul.scrollLeft || l.offsetLeft + l.offsetWidth > ul.scrollLeft + ul.clientWidth) ul.scrollLeft = l.offsetLeft - 16;
      }
    }
    window.addEventListener('scroll', margi, { passive: true });
    margi();
  });
})();
