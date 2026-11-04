// Tehisaru seire: teemalüliti ja pikkade tabelite valik „12 / 24 / 48 / kõik“. Ilma selleta töötab leht samuti.
(function () {
  var VOTI = 'seire-teema';
  var juur = document.documentElement;
  function loe() { try { return localStorage.getItem(VOTI); } catch (e) { return null; } }
  function kirjuta(v) { try { localStorage.setItem(VOTI, v); } catch (e) { /* privaatne aken */ } }
  function tume() {
    var t = juur.getAttribute('data-theme');
    if (t) return t === 'dark';
    return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
  }
  var salvestatud = loe();
  if (salvestatud === 'dark' || salvestatud === 'light') juur.setAttribute('data-theme', salvestatud);

  function uuendaNupp(nupp) {
    var on = tume();
    nupp.setAttribute('aria-pressed', on ? 'true' : 'false');
    nupp.textContent = on ? 'Hele teema' : 'Tume teema';
  }
  document.addEventListener('DOMContentLoaded', function () {
    var nupp = document.querySelector('.teema');
    if (nupp) {
      uuendaNupp(nupp);
      nupp.addEventListener('click', function () {
        var uus = tume() ? 'light' : 'dark';
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
  });
})();
