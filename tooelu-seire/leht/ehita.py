import json
import os
# Töökaust väljaspool repot: käivituste andmed (analyys/, dash/) ja väljund. Vt README.md.
B=os.environ.get('TOOELU_TOO','/mnt/project-files/tooelu-leht-andmed').rstrip('/')+'/'
s=open(B+'leht-mall.html').read()
s=s.replace('<meta name="dash-one-writer">\n','')
def rep(a,b,n=1):
    global s
    assert s.count(a)==n,(a,s.count(a))
    s=s.replace(a,b)
# Kadri disainisüsteemi järgi: värvid tokenitest, ei mingeid literaale
rep("  dash.onData(() => {\n    if (dash.colors && dash.colors[0]) document.querySelectorAll('.ts').forEach((t) => t.style.setProperty('--ts-signal', dash.colors[0]));\n  });\n","")
rep("  .ts { --ts-signal: #87139f; --ts-context: var(--cds-chart-muted); }","  .ts { --ts-signal: var(--signal); --ts-context: var(--context); }")
s=s.replace("color: #fff;","color: var(--on-signal);")
rep("  .ts-tile { display: grid; gap: var(--cds-gap-xs); align-content: start; padding: var(--cds-pad-md) var(--cds-pad-lg); border-radius: var(--cds-radius); background: var(--color-panel); border: 1px solid var(--color-border-line); }",
    "  .ts-tile { display: grid; gap: var(--cds-gap-xs); align-content: start; padding: var(--cds-pad-md) var(--cds-pad-lg); border-radius: var(--cds-radius); background: var(--color-panel); }")
rep("  .ts-card { position: relative; display: grid; gap: var(--cds-gap-sm); align-content: start; min-width: 0; padding: var(--cds-pad-lg); border-radius: var(--cds-radius); background: var(--color-panel); border: 1px solid var(--color-border-line); }",
    "  .ts-card { position: relative; display: grid; gap: var(--cds-gap-sm); align-content: start; min-width: 0; padding: var(--cds-pad-lg); border-radius: var(--cds-radius); background: var(--color-panel); }")
rep("  .ts-filter { font: inherit; font-size: var(--cds-font-size-caption); padding: var(--cds-pad-xs) var(--cds-pad-sm); border-radius: 999px; border: 1px solid var(--color-border-line); background: var(--color-bg); color: var(--color-fg); cursor: pointer; }\n  .ts-filter[aria-pressed=\"true\"] { background: var(--color-fg); color: var(--color-bg); border-color: var(--color-fg); }",
    "  .ts-filter { font: inherit; font-size: var(--cds-font-size-caption); padding: 6px 14px; border-radius: 999px; border: 1px solid var(--control-border); background: var(--surface); color: var(--ink); cursor: pointer; }\n  .ts-filter[aria-pressed=\"true\"] { background: var(--signal); color: var(--on-signal); border-color: var(--signal); }")
s=s.replace("outline: 3px solid var(--color-fg); outline-offset: 2px;","outline: 3px solid var(--signal); outline-offset: 2px;")
rep("  .ts-lead { margin: 0; font-size: var(--cds-font-size-body); line-height: 1.5; }","  .ts-lead { margin: 0; font-size: 18px; line-height: 1.6; max-width: 68ch; }")
rep("  .ts-title { margin: 0; font-family: var(--font-anthropic-serif); font-size: var(--cds-font-size-title); font-weight: 700; line-height: 1.1; text-wrap: balance; }",
    "  .ts-title { margin: 0; font-family: var(--font-anthropic-serif); font-size: clamp(30px, 6vw, 40px); font-weight: 700; line-height: 1.1; letter-spacing: -0.02em; text-wrap: balance; }")
rep("  .ts-kicker { margin: 0; font-size: var(--cds-font-size-caption);","  .ts-kicker { margin: 0; font-size: 13px;")

data={}
for n,f in [('a_aastad','analyys/a_aastad.json'),('a_teemad','analyys/a_teemad.json'),('a_tood','analyys/a_tood.json'),('a_jaotused','analyys/a_jaotused.json'),('a_eesti_allikad','analyys/a_eesti_allikad.json'),('a_lisa','analyys/a_lisa.json'),
            ('kandidaadid','dash/kandidaadid.json'),('allikad','dash/allikad.json'),('eurostat','dash/eurostat.json'),('kaivitus','dash/kaivitus.json')]:
    data[n]=json.load(open(B+f))
andmed=json.dumps(data,ensure_ascii=False).replace('</','<\\/')

head='''<title>TOOELU · Tehisaru ja töö</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&family=Space+Grotesk:wght@700&display=swap">
<style>
  /* Kadri disainisüsteem (MJzwWQ2BkkCvLAQNYxXJXk): üks fookus (signal), hall kontekst, pealkiri ütleb leiu. */
  :root {
    --surface: #ffffff; --surface-raised: #f5f5f7; --surface-note: #f3ede1;
    --ink: #141414; --ink-muted: #555555; --ink-faded: #767676;
    --signal: #87139f; --signal-tint: #f3e4f7; --on-signal: #ffffff;
    --context: #bdbdbd; --context-strong: #3d3d3d; --counter: #e0561b; --counter-text: #9a3208;
    --hairline: #e2e2e2; --grid: #ededed; --control-border: #767676;
    --display: "Space Grotesk", "Segoe UI", system-ui, sans-serif;
    --body: Inter, "Segoe UI", system-ui, sans-serif;

    --color-fg: var(--ink); --color-fg-muted: var(--ink-muted); --color-bg: var(--surface); --color-panel: var(--surface-raised);
    --color-border-line: var(--hairline); --color-ok: var(--context-strong); --color-warn: var(--counter); --color-bad: var(--counter);
    --cds-chart-muted: var(--context); --cds-chart-grid: var(--grid); --cds-chart-axis: var(--ink-muted); --cds-chart-reference: var(--ink);
    --cds-surface-popover: var(--surface); --cds-border: var(--hairline); --cds-text-secondary: var(--ink-muted); --cds-shadow-popover: 0 6px 20px rgb(0 0 0 / 0.14);
    --cds-gap-xs: 4px; --cds-gap-sm: 8px; --cds-gap-md: 16px; --cds-gap-lg: 24px; --cds-gap-xl: 48px;
    --cds-pad-xs: 4px; --cds-pad-sm: 8px; --cds-pad-md: 16px; --cds-pad-lg: 24px; --cds-radius: 16px;
    --cds-font-size-caption: 14px; --cds-font-size-body: 16px; --cds-font-size-heading: 22px; --cds-font-size-title: 40px; --cds-dur-slow: .3s;
    --font-anthropic-sans: var(--body); --font-anthropic-serif: var(--display);
  }
  @media (prefers-color-scheme: dark) {
    :root:not([data-theme="light"]) {
      --surface: #141414; --surface-raised: #1e1e22; --surface-note: #2a2620;
      --ink: #f2f2f2; --ink-muted: #b3b3b3; --ink-faded: #8c8c8c;
      --signal: #df8cf5; --signal-tint: #3a1a45; --on-signal: #141414;
      --context: #505050; --context-strong: #d6d6d6; --counter: #ff8a55; --counter-text: #ff8a55;
      --hairline: #2e2e2e; --grid: #262626; --control-border: #8c8c8c; color-scheme: dark;
    }
  }
  :root[data-theme="dark"] {
    --surface: #141414; --surface-raised: #1e1e22; --surface-note: #2a2620;
    --ink: #f2f2f2; --ink-muted: #b3b3b3; --ink-faded: #8c8c8c;
    --signal: #df8cf5; --signal-tint: #3a1a45; --on-signal: #141414;
    --context: #505050; --context-strong: #d6d6d6; --counter: #ff8a55; --counter-text: #ff8a55;
    --hairline: #2e2e2e; --grid: #262626; --control-border: #8c8c8c; color-scheme: dark;
  }
  body { margin: 0; background: var(--surface); color: var(--ink); font-family: var(--body); font-size: 16px; line-height: 1.5;
    padding-block: 8px 64px; padding-left: max(clamp(20px, 4vw, 64px), env(safe-area-inset-left, 0px)); padding-right: max(clamp(20px, 4vw, 64px), env(safe-area-inset-right, 0px)); }
  a { color: var(--signal); }
  @media (prefers-reduced-motion: reduce) { * { transition: none !important; } }
</style>
<script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.9.0/d3.min.js"></script>
<script type="application/json" id="andmed">''' + andmed + '''</script>
<script>
  // Väike käituskiht: andmed on lehes, joonised joonistatakse uuesti teema vahetusel.
  window.dash = (() => {
    const D = JSON.parse(document.getElementById('andmed').textContent);
    const joonised = {};
    const kuulajad = [];
    const v = (n) => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
    const api = {
      data: (n) => (D[n] ? { status: 'ok', data: D[n] } : { status: 'error' }),
      draw(n, f) {
        if (f) joonised[n] = f;
        const g = joonised[n];
        if (g) document.querySelectorAll('[data-draw="' + n + '"]').forEach((e) => g(e));
      },
      onData(c) { kuulajad.push(c); setTimeout(c, 0); },
    };
    Object.defineProperty(api, 'colors', { get: () => [v('--signal'), v('--context-strong'), v('--counter')] });
    const koik = () => { Object.keys(joonised).forEach((n) => api.draw(n)); kuulajad.forEach((c) => c()); };
    try { matchMedia('(prefers-color-scheme: dark)').addEventListener('change', koik); } catch (e) {}
    new MutationObserver(koik).observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });
    let t;
    addEventListener('resize', () => { clearTimeout(t); t = setTimeout(() => ['a-teemad', 'a-riigid', 'a-asutused', 'a-kanalid', 'a-eesti-moodused', 'a-eesti-asutused', 'a-ea-allikad', 'nadalad', 'euro'].forEach((n) => api.draw(n)), 150); });
    return api;
  })();
</script>
'''
# eemalda armatuuri reeglid, mida siin pole
for a in ["  [data-dash-source-state=empty] { color: transparent; }\n","  [data-dash-source-state=refreshing] { opacity: .5; transition: opacity var(--cds-dur-slow); }\n"]:
    s=s.replace(a,'')
s=s.replace('</div>\n\n<script>','  <p class="ts-source" style="margin-top:var(--cds-gap-lg)">Kujundus: Kadri disainisüsteem. Leiud: uuringute kokkuvõtted, kontrollitud käsitsi. Muud andmed: OpenAlex, arXiv, Riigikogu, Hacker News, Maailmapank, NBER, ERR, OSKA, Arenguseire, Eurostat; seire töövood GitHubis.</p>\n</div>\n\n<script>',1)
s=s.replace("Iga allika vastus viimases käivituses. Roheline täpp: allikas vastas.","Iga allika vastus viimases käivituses. Oranž täpp tähendab, et allikas ei vastanud.")
# Numbrid Interis (disainisüsteem: Space Grotesk ainult pealkirjades)
s=s.replace("</style>","  .ts-tile-value, .ts-num, .ts-tw .ts-num, .ts-block-box, .ts-big { font-family: var(--body) !important; letter-spacing: -0.01em; }\n</style>",1)
out="<script>document.documentElement.lang=\"et\"</script>\n"+head+s
open(B+'tehisaru-ja-too.html','w').write(out)
# Ühise saidi versioon (seire artefaktis kõrvalfail): täisdokument, sest ainult avaleht saab raami avaldamisel.
open(B+'tehisaru-ja-too-uhine.html','w').write('<!doctype html>\n<html lang="et">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'+head+'</head>\n<body>\n'+s+'</body>\n</html>\n')
# eelvaade kohaliku d3-ga
open(B+'eelvaade.html','w').write('<!doctype html><html lang="et"><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">'+out.replace('https://cdnjs.cloudflare.com/ajax/libs/d3/7.9.0/d3.min.js','d3.min.js'))
print(len(out))
