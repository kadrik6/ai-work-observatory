// Tehisaru seire: teemalüliti ja pikkade tabelite valik „12 / 24 / 48 / kõik“. Ilma selleta töötab leht samuti.
(function () {
  var VOTI = 'seire-teema-2'; // uus võti 6.11.2026: varem salvestatud „Hele“ ei kata enam vaikimisi Pehmet
  var juur = document.documentElement;
  function loe() { try { return localStorage.getItem(VOTI); } catch (e) { return null; } }
  function kirjuta(v) { try { localStorage.setItem(VOTI, v); } catch (e) { /* privaatne aken */ } }
  // Kaks teemat: Hele (endine Pehme, väärtus 'soft') ja Tume (Kadri 8.11.2026: valge Hele eemaldati). Oma atribuut data-seire-teema,
  // sest claude.ai artefakti kest kirjutab juure data-theme üle. Ilma valikuta Hele; varem salvestatud valge Hele ('light') = Hele.
  var JARG = ['soft', 'dark'];
  var NIMI = { soft: 'Hele', dark: 'Tume' };
  function praegune() {
    var t = juur.getAttribute('data-seire-teema');
    if (JARG.indexOf(t) >= 0) return t;
    return 'soft';
  }
  var salvestatud = loe();
  juur.setAttribute('data-seire-teema', salvestatud === 'dark' ? 'dark' : 'soft');

  function uuendaNupp(nupp) {
    var t = praegune(), j = JARG[(JARG.indexOf(t) + 1) % JARG.length];
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
        var uus = JARG[(JARG.indexOf(praegune()) + 1) % JARG.length];
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
      function teata(n) { k.dispatchEvent(new CustomEvent('seire-riik', {detail: n})); }
      function peida() {
        if (praegu) teata(null);
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
          if (x !== null) teata(p.getAttribute('data-n'));
        }
        var r = k.getBoundingClientRect();
        if (x === null) { var pb = p.getBoundingClientRect(); x = pb.right - 4; y = pb.top + pb.height / 2; }  // tabelist: silt riigi juurde
        var lx = x - r.left + 14, ly = y - r.top + 14;
        if (lx + vihje.offsetWidth > r.width) lx = x - r.left - vihje.offsetWidth - 14;
        if (ly + vihje.offsetHeight > r.height) ly = y - r.top - vihje.offsetHeight - 14;
        vihje.style.left = Math.max(0, lx) + 'px';
        vihje.style.top = Math.max(0, ly) + 'px';
      }
      if (!svg || !vihje) return;
      // Kõrvaltabel või -graafik kutsub seda: riik esile ja tema silt kaardile (null peidab).
      k.seireRiik = function (n) {
        var p = null;
        if (n) svg.querySelectorAll('path[data-n]').forEach(function (x) { if (x.getAttribute('data-n') === n) p = x; });
        if (p) naita(p, null, null); else if (praegu) { praegu.classList.remove('on'); praegu = null; k.classList.remove('hoiab'); vihje.hidden = true; if (fookus) svg.appendChild(fookus); }
      };
      svg.addEventListener('pointermove', function (ev) {
        var p = ev.target.closest && ev.target.closest('path[data-n]');
        if (p) naita(p, ev.clientX, ev.clientY); else peida();
      });
      svg.addEventListener('pointerleave', peida);
      // Puutel pointermove ei tule (kasutusloogika 11.11.2026: koputus kaardil ei näidanud midagi): koputus = sama mis hõljumine.
      svg.addEventListener('click', function (ev) {
        var p = ev.target.closest && ev.target.closest('path[data-n]');
        if (p) naita(p, ev.clientX, ev.clientY); else peida();
      });
    });
    // Kaart ja kõrvaltabel (Kadri 11.11.2026): riigi peal hõljudes ükskõik kummal pool tuleb sama riik esile ka teisel pool.
    // Partnerid on sama jaotise read .jrj-r[data-n] ja järjestusgraafiku jooned .bs (aria-label = riigi nimi).
    document.querySelectorAll('.kaart').forEach(function (k) {
      var jaotis = k.closest('section') || k.parentNode;
      var read = jaotis.querySelectorAll('.jrj-r[data-n]');
      var jooned = jaotis.querySelectorAll('.bs[aria-label]');
      if (!read.length && !jooned.length) return;
      function esile(n) {  // ainult partnerid; kaart teeb enda osa ise
        read.forEach(function (r) { r.classList.toggle('on', r.getAttribute('data-n') === n); });
        jooned.forEach(function (g) {
          var on = g.getAttribute('aria-label') === n;
          g.classList.toggle('hv', on);
          if (on) g.parentNode.appendChild(g);
        });
        jaotis.querySelectorAll('svg.bump').forEach(function (sv) {
          sv.classList.toggle('hoiab', !!n && !!sv.querySelector('.bs.hv'));
          if (!n) { var f = sv.querySelector('.bs.f'); if (f) sv.appendChild(f); }  // Eesti jälle peale
        });
      }
      k.addEventListener('seire-riik', function (ev) { esile(ev.detail); });
      function seo(el, n) {
        function sisse() { esile(n); if (k.seireRiik) k.seireRiik(n); }
        function valja() { esile(null); if (k.seireRiik) k.seireRiik(null); }
        el.addEventListener('pointerenter', sisse);
        el.addEventListener('pointerleave', valja);
        el.addEventListener('focus', sisse);
        el.addEventListener('blur', valja);
      }
      read.forEach(function (r) { seo(r, r.getAttribute('data-n')); });
      // Graafiku joon tõstetakse teiste peale (DOM-is ümber), seepärast kuulab hõljumist SVG ise, mitte joon:
      // ümber tõstetud elemendi pointerleave võib muidu kaduma minna ja esiletõst jääks külge.
      jaotis.querySelectorAll('svg.bump').forEach(function (sv) {
        var praegu = null;
        sv.addEventListener('pointermove', function (ev) {
          var g = ev.target.closest && ev.target.closest('.bs[aria-label]');
          var n = g ? g.getAttribute('aria-label') : null;
          if (n === praegu) return;
          praegu = n; esile(n); if (k.seireRiik) k.seireRiik(n);
        });
        sv.addEventListener('pointerleave', function () { praegu = null; esile(null); if (k.seireRiik) k.seireRiik(null); });
      });
      jooned.forEach(function (g) {  // klaviatuur
        var n = g.getAttribute('aria-label');
        g.addEventListener('focus', function () { esile(n); if (k.seireRiik) k.seireRiik(n); });
        g.addEventListener('blur', function () { esile(null); if (k.seireRiik) k.seireRiik(null); });
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
    document.querySelectorAll('.jrj[data-piir], .ar[data-piir]').forEach(function (j) {
      var piir = parseInt(j.getAttribute('data-piir'), 10) || 10;
      var read = Array.prototype.slice.call(j.querySelectorAll('.jrj-r[data-n], .ar-r'));
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
      // Kasutusloogika 11.11.2026: varem oli iga joon eraldi Tab-peatus (avalehel 76, Töö lehel 148), klaviatuuriga
      // lugeja pidi kõik läbi käima. Nüüd on igas vaates üks peatus ja nooled liiguvad joonte vahel (roving tabindex).
      k.querySelectorAll('svg.bump').forEach(function (sv) {  // igas SVG-s (lai ja kitsas) oma peatus
        sv.querySelectorAll('.bs').forEach(function (g, i) { g.setAttribute('tabindex', i ? '-1' : '0'); });
      });
      k.querySelectorAll('.bs').forEach(function (g) {
        g.addEventListener('click', function () { vali(g.getAttribute('data-s')); });
        g.addEventListener('keydown', function (ev) {
          if (ev.key === 'Enter' || ev.key === ' ') { ev.preventDefault(); vali(g.getAttribute('data-s')); g.focus(); return; }
          var samm = { ArrowDown: 1, ArrowRight: 1, ArrowUp: -1, ArrowLeft: -1 }[ev.key];
          if (!samm) return;
          ev.preventDefault();
          var koik = Array.prototype.slice.call(g.parentNode.querySelectorAll('.bs')).sort(function (a, b) {
            return a.getBBox().y - b.getBBox().y; });
          var j = (koik.indexOf(g) + samm + koik.length) % koik.length;
          koik.forEach(function (x) { x.setAttribute('tabindex', x === koik[j] ? '0' : '-1'); });
          koik[j].focus();
        });
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
    // Tööportaalide valdkonna filter (Kadri 11.11.2026): valitud valdkonna linnad ja tööandjad
    document.querySelectorAll('.tp-vk').forEach(function (f) {
      var paneel = f.parentNode;
      f.querySelectorAll('button[data-vk]').forEach(function (b) {
        b.addEventListener('click', function () {
          var v = b.getAttribute('data-vk');
          f.querySelectorAll('button[data-vk]').forEach(function (x) { x.setAttribute('aria-pressed', x === b ? 'true' : 'false'); });
          paneel.querySelectorAll('[data-vk-sisu]').forEach(function (d) { d.hidden = d.getAttribute('data-vk-sisu') !== v; });
        });
      });
    });
    // Ettekannete filter liigi ja allika järgi (Kadri 11.11.2026). Valikud kehtivad koos; rühm, kuhu ühtki rida ei jää,
    // peidetakse ja rühmade arvud näitavad valikule vastavat arvu.
    document.querySelectorAll('#ettekanded').forEach(function (pn) {
      var ridu = pn.querySelectorAll('.ek-r li[data-liik]');
      if (!ridu.length) return;
      var valik = { liik: '', allikas: '' };
      function rakenda() {
        ridu.forEach(function (l) {
          l.hidden = (!!valik.liik && l.getAttribute('data-liik') !== valik.liik) ||
            (!!valik.allikas && l.getAttribute('data-allikas') !== valik.allikas);
        });
        var kokku = 0;
        pn.querySelectorAll('.ek-r').forEach(function (r) {
          var n = r.querySelectorAll('li[data-liik]:not([hidden])').length;
          kokku += n;
          r.hidden = n === 0;
          var a = r.querySelector('h3 .arv'); if (a) a.textContent = n;
          var v = pn.querySelector('.ek-valik a[data-ruhm="' + r.id.slice(3) + '"]');
          if (v) { v.hidden = n === 0; v.querySelector('.arv').textContent = n; }
        });
        var t = pn.querySelector('.ek-tyhi'); if (t) t.hidden = kokku > 0;
        // Kadri 11.11.2026: kombinatsiooni, millega tulemusi pole, ei saa valida. Nupu arv näitab, mitu jääb
        // teise filtri praeguse valikuga; null arvuga nupp on keelatud.
        pn.querySelectorAll('.ek-f').forEach(function (f) {
          var k = f.getAttribute('data-k'), teine = k === 'liik' ? 'allikas' : 'liik';
          f.querySelectorAll('button[data-v]').forEach(function (b) {
            var v = b.getAttribute('data-v'), n = 0;
            ridu.forEach(function (l) {
              if ((!valik[teine] || l.getAttribute('data-' + teine) === valik[teine]) && (!v || l.getAttribute('data-' + k) === v)) n++;
            });
            var a = b.querySelector('.arv'); if (a) a.textContent = n;
            b.disabled = !!v && n === 0;
          });
        });
      }
      pn.querySelectorAll('.ek-f').forEach(function (f) {
        var k = f.getAttribute('data-k');
        f.querySelectorAll('button[data-v]').forEach(function (b) {
          b.addEventListener('click', function () {
            valik[k] = b.getAttribute('data-v');
            f.querySelectorAll('button[data-v]').forEach(function (x) { x.setAttribute('aria-pressed', x === b ? 'true' : 'false'); });
            rakenda();
          });
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
      function sobib(r, q_, ruhm_, kus_) {
        return (!q_ || r.getAttribute('data-otsi').indexOf(q_) >= 0) &&
          (!ruhm_ || (ruhm_ === 'hea' ? r.getAttribute('data-hea') === '1' : r.getAttribute('data-ruhm') === ruhm_)) &&
          (!kus_ || r.getAttribute('data-kus') === kus_);
      }
      // Filtri all näitavad rühmanupud ja maakonnad, mitu rida on teiste valikute juures (Kadri 8.11.2026 21:45).
      var nupud = Array.prototype.slice.call(o.querySelectorAll('button[data-r]'));
      var valikud = valik ? Array.prototype.slice.call(valik.options) : [];
      function alus(el) {
        if (!el.hasAttribute('data-alg')) el.setAttribute('data-alg', el.textContent);
        return el.getAttribute('data-alg').replace(/ \(\d+\)$/, '');
      }
      function loenda(q) {
        var filter = !!(q || ruhm || kus);
        nupud.forEach(function (b) {
          var r_ = b.getAttribute('data-r');
          if (!filter) { b.textContent = b.getAttribute('data-alg') || b.textContent; return; }
          var m = read.filter(function (r) { return sobib(r, q, r_, kus); }).length;
          b.textContent = alus(b) + ' (' + m + ')';
        });
        valikud.forEach(function (op) {
          if (!filter) { op.textContent = op.getAttribute('data-alg') || op.textContent; return; }
          var m = read.filter(function (r) { return sobib(r, q, ruhm, op.value); }).length;
          op.textContent = alus(op) + ' (' + m + ')';
        });
      }
      nupud.forEach(alus); valikud.forEach(alus);
      function filtreeri() {
        var q = sisend.value.trim().toLowerCase(), k = riba();
        loenda(q);
        if (!q && !ruhm && !kus) {
          if (k) { k.hidden = false; k.querySelector('button').click(); } else { read.forEach(function (r) { r.hidden = false; }); }
          loe.textContent = '';
          return;
        }
        if (k) k.hidden = true;
        var n = 0;
        read.forEach(function (r) { var ok = sobib(r, q, ruhm, kus); r.hidden = !ok; if (ok) n++; });
        loe.textContent = n ? n + ' ' + uhik + (n < read.length ? ' ' + read.length + '-st' : '')
          : 'Ei leitud ühtegi. Proovi lühemat sõna või vali rühmaks „kõik“.';  // tühi olek (kasutusloogika 11.11.2026)
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
    // R1 (Kadri 8.11.2026): „Sellel lehel“ rida kleepub päise alla; ankur peab jääma ka selle rea alla.
    var r = document.querySelector('.lehel-rida');
    document.documentElement.style.setProperty('--lehel-h', (r ? r.offsetHeight : 0) + 'px');
  }
  document.addEventListener('DOMContentLoaded', function () {
    korgus();
    window.addEventListener('resize', korgus);
    // „Sellel lehel“ on üks kleepuv rida sakkide all (R1). Kui see on päise all kinni, saab rida peene alajoone.
    var rida = document.querySelector('.lehel-rida');
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
        if (h && a.getAttribute('href') === h) {
          if (a.getAttribute('aria-current') === 'true') return;
          a.setAttribute('aria-current', 'true');
          // Telefonis on rida külgsuunas keritav: märgitud kiip tuuakse nähtavale.
          var ul = a.closest('.sellel');
          if (ul && ul.scrollWidth > ul.clientWidth) {
            var ar = a.getBoundingClientRect(), ur = ul.getBoundingClientRect();
            if (ar.left < ur.left || ar.right > ur.right) ul.scrollLeft += ar.left - ur.left - 16;
          }
        } else a.removeAttribute('aria-current');
      });
    }
    function margi() {
      if (valitud) { sea(valitud); return; }
      var st = getComputedStyle(document.documentElement);
      var piir = (parseInt(st.getPropertyValue('--top-h'), 10) || 110) + (parseInt(st.getPropertyValue('--lehel-h'), 10) || 0) + 24;
      if (rida) rida.classList.toggle('kleepub', rida.getBoundingClientRect().top <= (parseInt(st.getPropertyValue('--top-h'), 10) || 0) + 1);
      var k = -1, parim = -Infinity;
      sihid.forEach(function (t, i) {
        if (!t) return;
        var y = Math.round(t.getBoundingClientRect().top);
        if (y <= piir && y > parim + 1) { parim = y; k = i; }
      });
      // Lehe lõpus ei jõua viimased jaotised piirini: siis märgitakse esimene nähtav jaotis, mis jäi piirist allapoole.
      if (window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 2) {
        sihid.forEach(function (t, i) {
          if (!t) return;
          var y = Math.round(t.getBoundingClientRect().top);
          if (y > piir && y < window.innerHeight && (k < 0 || y > parim + 1)) { parim = y; k = i; }
        });
      }
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
  // Kasutusloogika 11.11.2026 (uus nurk: lingiga saabuja): filtri valik lisab aadressi ka jaotise ankru (#loend jne),
  // et saadetud link avaneks filtri juures, mitte lehe alguses 1–3 ekraani kõrgemal.
  function jaotis(el) { var j = el && el.closest('section[id], .pn[id], .jaotis[id]'); return j ? j.id : ''; }
  function sea(k, v, el) {
    try {
      var u = new URL(location.href);
      if (v) u.searchParams.set(k, v); else u.searchParams.delete(k);
      if (v && !u.hash && jaotis(el)) u.hash = '#' + jaotis(el);
      history.replaceState(history.state, '', u.pathname + u.search + u.hash);
    } catch (e) { /* nt sandbox ei luba: valik töötab ikka, ainult aadressi ei jää */ }
  }
  document.addEventListener('DOMContentLoaded', function () {
    var q;
    try { q = new URLSearchParams(location.search); } catch (e) { q = { get: function () { return null; } }; }
    var paarid = [
      ['teema', '.u-f[aria-label="Vali teema"] button[data-f]', 'data-f'],
      ['ruhm', 'button[data-r]', 'data-r'],
      ['valdkond', '.tp-vk button[data-vk]', 'data-vk'],
      ['liik', '.ek-f[data-k="liik"] button[data-v]', 'data-v'],
      ['allikas', '.ek-f[data-k="allikas"] button[data-v]', 'data-v'],
      ['sakk', '.p-tabs [role="tab"]', 'aria-controls'],
    ];
    paarid.forEach(function (p) {
      var nupud = document.querySelectorAll(p[1]);
      nupud.forEach(function (b) { b.addEventListener('click', function () { sea(p[0], b.getAttribute(p[2]), b); }); });
      var v = q.get(p[0]);
      if (v) nupud.forEach(function (b) {
        if (b.getAttribute(p[2]) !== v) return;
        b.click();
        var pn = b.closest('[role="tabpanel"]');
        if (pn && pn.hidden) { var n = document.querySelector('[role="tab"][aria-controls="' + pn.id + '"]'); if (n) n.click(); }
      });
    });
    document.querySelectorAll('.h-otsing input').forEach(function (i) {
      i.addEventListener('input', function () { sea('otsi', i.value.trim(), i); });
      var v = q.get('otsi');
      if (v) {
        i.value = v; i.dispatchEvent(new Event('input'));
        // Filter võib olla peidetud saki sees (teemamall A): ava see sakk, et lugeja näeks tulemust
        var p = i.closest('[role="tabpanel"]');
        if (p && p.hidden) { var n = document.querySelector('[role="tab"][aria-controls="' + p.id + '"]'); if (n) n.click(); }
      }
    });
    // Vana jagatud link ilma ankruta (?otsi=… või ?ruhm=…): keri filtri juurde ja lisa ankur aadressi.
    if (!location.hash) {
      var el = null;
      if (q.get('otsi')) el = document.querySelector('.h-otsing input');
      else paarid.some(function (p) { var v = q.get(p[0]); if (!v) return false;
        el = Array.prototype.slice.call(document.querySelectorAll(p[1])).filter(function (b) { return b.getAttribute(p[2]) === v; })[0] || null; return !!el; });
      var j = jaotis(el);
      if (j) { try { history.replaceState(history.state, '', location.pathname + location.search + '#' + j); } catch (e) { /* sandbox */ }
        document.getElementById(j).scrollIntoView(); }
    }
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
    document.addEventListener('click', function (ev) { if (m.open && (!m.contains(ev.target) || ev.target === m)) m.open = false; });  // ev.target === m: klõps tumendatud kattele
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
