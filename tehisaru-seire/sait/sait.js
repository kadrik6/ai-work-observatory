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
    // Järjestuse muutus (bump): Top N nupud ja klõps tegevusalale tõstab selle esile kõigis vaadetes (Kadri 7.11.2026)
    document.querySelectorAll('.bump-k').forEach(function (k) {
      var nupud = k.querySelectorAll('.bump-n button'), vaated = k.querySelectorAll('.bump-v');
      nupud.forEach(function (b) {
        b.addEventListener('click', function () {
          var n = b.getAttribute('data-n');
          nupud.forEach(function (x) { x.setAttribute('aria-pressed', x === b ? 'true' : 'false'); });
          vaated.forEach(function (v) { v.hidden = v.getAttribute('data-n') !== n; });
        });
      });
      function vali(id) {
        k.querySelectorAll('.bs').forEach(function (g) {
          var on = g.getAttribute('data-s') === id;
          g.classList.toggle('f', on);
          if (on) g.classList.remove('t');
          if (on && g.parentNode) g.parentNode.appendChild(g);  // esiletõstetud joon teiste peale
        });
      }
      k.querySelectorAll('.bs').forEach(function (g) {
        g.addEventListener('click', function () { vali(g.getAttribute('data-s')); });
        g.addEventListener('keydown', function (ev) { if (ev.key === 'Enter' || ev.key === ' ') { ev.preventDefault(); vali(g.getAttribute('data-s')); } });
      });
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
      var sisend = o.querySelector('input'), loe = o.querySelector('.h-loe'), ruhm = '', kus = '';
      var valik = o.querySelector('select[data-kus]'), uhik = o.getAttribute('data-uhik') || 'hanget';
      function riba() { var r = tabel.parentNode.nextElementSibling; return r && r.classList.contains('kogus') ? r : null; }
      function filtreeri() {
        var q = sisend.value.trim().toLowerCase(), k = riba();
        if (!q && !ruhm && !kus) {
          if (k) { k.hidden = false; k.querySelector('button').click(); } else { read.forEach(function (r) { r.hidden = false; }); }
          loe.textContent = '';
          return;
        }
        if (k) k.hidden = true;
        var n = 0;
        read.forEach(function (r) {
          var ok = (!q || r.getAttribute('data-otsi').indexOf(q) >= 0) &&
            (!ruhm || (ruhm === 'hea' ? r.getAttribute('data-hea') === '1' : r.getAttribute('data-ruhm') === ruhm)) &&
            (!kus || r.getAttribute('data-kus') === kus);
          r.hidden = !ok; if (ok) n++;
        });
        loe.textContent = n + ' ' + uhik;
      }
      sisend.addEventListener('input', filtreeri);
      if (valik) valik.addEventListener('change', function () { kus = valik.value; filtreeri(); });
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
    // Teemamall A (8.11.2026): vana ankur (nt too.html#vabad-kohad) võib olla peidetud saki sees; ava see sakk ja keri sinna.
    function avaAnkur(id, keri) {
      var el = id && document.getElementById(id);
      if (!el) return;
      var paneel = el.closest('[role="tabpanel"]'), oli = false;
      for (var p = paneel; p; p = p.parentElement && p.parentElement.closest('[role="tabpanel"]')) {
        if (p.hidden) {
          var nupp = document.querySelector('[role="tab"][aria-controls="' + p.id + '"]');
          if (nupp) { nupp.click(); oli = true; }
        }
      }
      if (keri && oli) el.scrollIntoView();
    }
    function hashId() { try { return decodeURIComponent(location.hash.slice(1)); } catch (e) { return ''; } }
    avaAnkur(hashId(), true);
    window.addEventListener('hashchange', function () { avaAnkur(hashId(), true); });
    document.addEventListener('click', function (ev) {
      var a = ev.target.closest && ev.target.closest('a[href^="#"]');
      if (a) avaAnkur(a.getAttribute('href').slice(1), false);
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
      if (v) nupud.forEach(function (b) {
        if (b.getAttribute(p[2]) !== v) return;
        b.click();
        var pn = b.closest('[role="tabpanel"]');
        if (pn && pn.hidden) { var n = document.querySelector('[role="tab"][aria-controls="' + pn.id + '"]'); if (n) n.click(); }
      });
    });
    document.querySelectorAll('.h-otsing input').forEach(function (i) {
      i.addEventListener('input', function () { sea('otsi', i.value.trim()); });
      var v = q.get('otsi');
      if (v) {
        i.value = v; i.dispatchEvent(new Event('input'));
        // Filter võib olla peidetud saki sees (teemamall A): ava see sakk, et lugeja näeks tulemust
        var p = i.closest('[role="tabpanel"]');
        if (p && p.hidden) { var n = document.querySelector('[role="tab"][aria-controls="' + p.id + '"]'); if (n) n.click(); }
      }
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

// Uudise kokkuvõte on kaks rida; klõps või Enter näitab kogu teksti (Kadri 7.11.2026: teksti on liiga palju).
(function () {
  document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('p.u-k').forEach(function (p) {
      p.classList.add('kinni');
      if (p.scrollHeight <= p.clientHeight + 2) { p.classList.remove('kinni'); return; }
      p.classList.add('voib');
      p.setAttribute('tabindex', '0');
      p.setAttribute('role', 'button');
      p.setAttribute('aria-expanded', 'false');
      p.setAttribute('title', 'Näita kogu kokkuvõtet');
      function vaheta() {
        var kinni = p.classList.toggle('kinni');
        p.setAttribute('aria-expanded', kinni ? 'false' : 'true');
      }
      p.addEventListener('click', function (ev) { if (!ev.target.closest('a')) vaheta(); });
      p.addEventListener('keydown', function (ev) { if (ev.key === 'Enter' || ev.key === ' ') { ev.preventDefault(); vaheta(); } });
    });
  });
})();

// Kadri kommentaar 8.11.2026: „suuna navigeerimisel alati lehe ülaossa, isegi kui olen eelmises vaates alla
// scrollinud“. Uus leht avaneb ülevalt; erand on #ankur (lugeja tahab kindlat kohta) ja tagasi-nupp (viib kohta, kust lugeja lahkus).
(function () {
  try { if ('scrollRestoration' in history) history.scrollRestoration = 'manual'; } catch (e) { /* sandbox */ }
  var VOTI = 'seire-keri:' + location.pathname;
  function tagasi() {
    try { var n = performance.getEntriesByType('navigation')[0]; return n && n.type === 'back_forward'; } catch (e) { return false; }
  }
  var liigutas = false; // lugeja hakkas ise kerima enne „load“ sündmust: ära kisu teda tagasi üles
  ['wheel', 'touchstart', 'keydown'].forEach(function (e) { window.addEventListener(e, function () { liigutas = true; }, { passive: true }); });
  function ules() {
    if (location.hash || liigutas) return;
    var y = 0;
    if (tagasi()) { try { y = parseInt(sessionStorage.getItem(VOTI), 10) || 0; } catch (e) { y = 0; } }
    window.scrollTo(0, y);
  }
  document.addEventListener('DOMContentLoaded', ules);
  window.addEventListener('load', ules);
  window.addEventListener('pageshow', function (ev) { if (!ev.persisted) ules(); });
  // Tagasi-nupp viib samasse kohta, kust lugeja lahkus (kasutusloogika: tagasi taastab oleku).
  var lahkus = false;
  function salvesta() { try { sessionStorage.setItem(VOTI, String(Math.round(window.scrollY))); } catch (e) { /* privaatne aken */ } }
  window.addEventListener('pagehide', function () { if (!lahkus) salvesta(); });
  // Link teisele lehele: keri enne lahkumist üles, et ka sama aknasse laaditud leht ei jätkaks vanast kohast.
  document.addEventListener('click', function (ev) {
    var a = ev.target.closest && ev.target.closest('a[href]');
    if (!a || ev.button || ev.metaKey || ev.ctrlKey || ev.shiftKey || ev.altKey) return;
    var h = a.getAttribute('href');
    if (!h || h.charAt(0) === '#' || /^[a-z]+:/i.test(h) || a.target === '_blank') return;
    if (h.indexOf('#') < 0) { salvesta(); lahkus = true; window.scrollTo(0, 0); }
  }, true); // püüdefaasis: claude.ai kest võib lingiklõpsu ise käsitleda
})();

// Kopeeritav fakt (sisuloogika 8.11.2026, idee 2): nupp numbriplaadil kopeerib lause koos allika ja lingiga.
// Kui lõikelauale kirjutada ei saa (nt artefakti raam keelab), näidatakse lause plaadi all valituna, et saaks ise kopeerida.
(function () {
  function naita(nupp, tekst) {
    var plaat = nupp.closest('.plaat');
    var p = plaat.querySelector('.fakt-tekst');
    if (!p) { p = document.createElement('textarea'); p.className = 'fakt-tekst'; p.readOnly = true; p.rows = 3; plaat.appendChild(p); }
    p.value = tekst; p.focus(); p.select();
    nupp.setAttribute('data-silt', 'Vali tekst ja kopeeri');
  }
  function vana(tekst) {
    var t = document.createElement('textarea');
    t.value = tekst; t.setAttribute('readonly', ''); t.style.position = 'fixed'; t.style.opacity = '0';
    document.body.appendChild(t); t.select();
    var ok = false;
    try { ok = document.execCommand('copy'); } catch (e) { ok = false; }
    document.body.removeChild(t);
    return ok;
  }
  function tehtud(nupp) {
    var vaike = 'Kopeeri fakt koos allikaga';
    nupp.classList.add('ok'); nupp.setAttribute('data-silt', 'Kopeeritud'); nupp.setAttribute('aria-label', 'Kopeeritud');
    setTimeout(function () {
      nupp.classList.remove('ok'); nupp.setAttribute('data-silt', vaike); nupp.setAttribute('aria-label', vaike);
    }, 2000);
  }
  document.addEventListener('click', function (ev) {
    var nupp = ev.target.closest && ev.target.closest('button.kopeeri');
    if (!nupp) return;
    var tekst = nupp.getAttribute('data-fakt') || '';
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(tekst).then(function () { tehtud(nupp); }, function () {
        if (vana(tekst)) tehtud(nupp); else naita(nupp, tekst);
      });
    } else if (vana(tekst)) tehtud(nupp); else naita(nupp, tekst);
  });
})();
