"""Uuendab lehe „Tehisaru ja töö“ andmed GitHub Actionsi logidest ja ehitab lehe uuesti.

Kasutus (logid on GitHubi get_job_logs vastused, salvestatud failiks):
  python3 uuenda.py --seire SEIRE_LOG SEIRE_RUN_ID [--analyys ANALYYS_LOG ANALYYS_RUN_ID]

Seire (seire.yml, iga päev): uued uurimused, ERR-i tabamused, allikate seis, Eurostati uuendused.
Analüüs (analyys.yml, käivitatakse kord nädalas): vahekaardid „Mida uuritakse“ (OpenAlex, Eesti allikad, lisaallikad).
Kureeritud leiud: repo tooelu-seire/leiud.json + selle kausta leiud-lisa.json (igapäevase ülevaatuse lisad), liidetakse
faili leiud-koos.json; repo faile see skript ei muuda. Lisad näidatakse vahekaardil „Mida leiti“ plokis „Uued leiud“.
Väljund: tehisaru-ja-too.html (artefakt KJZJV6t17ddPTzU8sUXjZH) ja tehisaru-ja-too-uhine.html (ühine sait MKUSmw6WrrQFoidzARqsyd).
Lisatud 5.11.2026 (Kadri: leht peab ise uuenema).
"""
import json
import os
import re
import subprocess
import sys
from datetime import date

SIIN = os.path.dirname(os.path.abspath(__file__))
# Andmed (logidest tehtud JSON, leiud-lisa.json, valmis lehed) on repost väljas; kood on repos.
TOO = os.environ.get("TOOELU_TOO", os.path.join(os.environ.get("UUENDUS_ANDMED", "/mnt/project-files"), "tooelu-leht-andmed"))
REPO = os.environ.get("TOOELU_REPO", os.path.dirname(os.path.dirname(SIIN)))
LEHT = os.path.join(REPO, "tooelu-seire", "leht")
URL = "https://github.com/kadrik6/ai-work-observatory/actions/runs/"


def jooksuta(*k, cwd=None):
    env = dict(os.environ, TOOELU_TOO=TOO)
    r = subprocess.run([sys.executable, *k], cwd=cwd, env=env, capture_output=True, text=True)
    print(r.stdout.strip()[-600:])
    if r.returncode:
        sys.exit(f"VIGA {' '.join(k)}:\n{r.stderr[-1500:]}")


def liida_leiud():
    """Repo leiud.json + leiud-lisa.json -> leiud-koos.json. Lisa kirje sama id-ga asendab repo kirje."""
    repo = json.load(open(os.path.join(REPO, "tooelu-seire", "leiud.json"), encoding="utf-8"))
    p = os.path.join(TOO, "leiud-lisa.json")
    lisa = json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {"uuringud": [], "ulevaatused": []}
    ids = {u["id"] for u in lisa["uuringud"]}
    for u in lisa["uuringud"]:
        if u["meetod"] not in {m for ms in repo["kindlus"].values() for m in ms}:
            sys.exit(f"VIGA leiud-lisa.json: tundmatu meetod {u['meetod']} ({u['id']})")
    repo["uuringud"] = [u for u in repo["uuringud"] if u["id"] not in ids] + lisa["uuringud"]
    koos = os.path.join(TOO, "leiud-koos.json")
    json.dump(repo, open(koos, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return koos, lisa


def lisa_uued_leiud(lisa):
    """Plokk „Uued leiud“ vahekaardi „Mida leiti“ algusesse (leht-mall.html, enne ehita.py-d)."""
    import html
    e = html.escape
    repo = json.load(open(os.path.join(REPO, "tooelu-seire", "leiud.json"), encoding="utf-8"))
    kindlus = {m: k for k, ms in repo["kindlus"].items() for m in ms}
    k_nimi = {"tugev": "Tugev tõend", "keskmine": "Keskmine tõend", "nork": "Nõrk tõend", "prognoos": "Prognoos"}
    m_nimi = {"katse": "juhuslik katse", "loomulik_katse": "loomulik katse", "registriandmed": "registri- või platvormiandmed",
              "kirjeldav": "kirjeldav analüüs", "kusitlus": "küsitlus", "hinnang": "hinnang ülesannete kohta", "mudel": "majandusmudel",
              "ekspertintervjuud": "ekspertintervjuud", "prognoos": "prognoos või ootus, mitte mõõtmine"}
    kp = lambda s: "{}.{}.{}".format(int(s[8:10]), int(s[5:7]), s[:4])
    ul = sorted(lisa.get("ulevaatused") or [], key=lambda u: u["kuupaev"])
    if not ul:
        return
    viim = ul[-1]
    uued = sorted(lisa["uuringud"], key=lambda u: u["lisatud"], reverse=True)
    read = []
    for u in uued:
        k = kindlus[u["meetod"]]
        r = "" if u["retsenseeritud"] or u["meetod"] == "prognoos" else " · retsenseerimata"
        read.append(f'''<tr><td><a class="ts-t-name" href="{e(u['url'])}" target="_blank" rel="noopener">{e(u['pealkiri'])}</a>
<span class="ts-t-sub">{e(u['autorid'])} · {e(u['kanal'])} · {e(u['avaldatud'])} · lisatud {kp(u['lisatud'])}</span></td>
<td><p class="ts-leid">{e(u['leid'])}</p><p class="ts-leid-meta"><span class="ts-tag ts-tag-{k}">{k_nimi[k]}</span> <span class="ts-t-sub ts-inline">{m_nimi[u['meetod']]}{r}</span><span class="ts-t-sub">{e(u['kus'])}: {e(u['valim'])}</span></p></td></tr>''')
    pealkiri = (f"{len(uued)} uut uuringut lisatud pärast {kp(repo['kontrollitud'])}" if uued
                else f"Pärast {kp(repo['kontrollitud'])} uusi kontrollitud leide ei lisandunud")
    tabel = (f'''<div class="ts-twbox ts-twbox-auto"><table class="ts-tw ts-tw-leiud ts-tw-pinu"><thead><tr><th>Uuring</th><th>Mida leiti ja kui kindel</th></tr></thead><tbody>
{"".join(read)}
          </tbody></table></div>''' if uued else "")
    plokk = f'''<!--UUED-LEIUD-->    <section class="ts-chartcard" id="uued-leiud" aria-labelledby="uued-leiud-h">
      <div class="ts-head-sm">
        <p class="ts-kicker">Uued leiud · viimati üle vaadatud {kp(viim['kuupaev'])}</p>
        <h2 class="ts-ctitle ts-ctitle-sm" id="uued-leiud-h">{e(pealkiri)}</h2>
        <p class="ts-csub">Iga päev vaadatakse läbi teadustööde seire uued kandidaadid. Leiuks saab uuring, mille arvud on kontrollitud kokkuvõttest. Viimases ülevaatuses vaadati läbi {viim['vaadatud']} kandidaati ja lisati {viim['lisatud']}.</p>
      </div>
      {tabel}
      <details class="ts-details"><summary>Mida jäeti välja ja miks</summary><p class="ts-source">{e(viim.get('markus', ''))}</p></details>
    </section>
<!--/UUED-LEIUD-->'''
    p = os.path.join(TOO, "leht-mall.html")
    s = open(p, encoding="utf-8").read()
    s = re.sub(r"<!--UUED-LEIUD-->.*?<!--/UUED-LEIUD-->", "", s, flags=re.S)
    ankur = '    <section class="ts-leiud-algus">\n      <p class="ts-lead">Neli vastust maailma'
    if s.count(ankur) != 1:
        sys.exit("VIGA: „Uued leiud“ ploki koht lehel puudub (tee_leiud.py muutus?)")
    s = s.replace(ankur, plokk + "\n" + ankur)
    s = s.replace("<dd>leiud käsitsi (", "<dd>leiud iga päev üle vaadatud (" + kp(viim["kuupaev"]) + "; põhileiud ", 1)
    open(p, "w", encoding="utf-8").write(s)


def main(a):
    seis = json.load(open(os.path.join(TOO, "uuendus.json"))) if os.path.exists(os.path.join(TOO, "uuendus.json")) else {}
    if "--seire" in a:
        i = a.index("--seire")
        jooksuta(os.path.join(SIIN, "seire_logist.py"), a[i + 1], URL + a[i + 2])
        seis["seire"] = {"run": a[i + 2], "kuupaev": date.today().isoformat()}
    if "--analyys" in a:
        i = a.index("--analyys")
        log, run = os.path.abspath(a[i + 1]), a[i + 2]
        ad = os.path.join(TOO, "analyys")
        osad = os.path.join(ad, "osad.json")
        if not os.path.exists(osad):
            json.dump({}, open(osad, "w"))
        jooksuta(os.path.join(LEHT, "andmed_logist.py"), log, run, osad, cwd=ad)
        os.replace(os.path.join(ad, "osad3.json"), osad)
        jooksuta(os.path.join(LEHT, "eesti_logist.py"), log, cwd=ad)
        jooksuta(os.path.join(LEHT, "lisa_logist.py"), log, cwd=ad)
        seis["analyys"] = {"run": run, "kuupaev": date.today().isoformat()}
    koos, lisa = liida_leiud()
    jooksuta(os.path.join(LEHT, "tee_leiud.py"), koos, cwd=REPO)
    lisa_uued_leiud(lisa)
    jooksuta(os.path.join(LEHT, "ehita.py"), cwd=REPO)
    # Päis: kureeritud leidude kuupäev eraldi andmete kuupäevast, et lugeja näeks, et leht uueneb.
    kp = lambda s: "{}.{}.{}".format(int(s[8:10]), int(s[5:7]), s[:4])
    andmed = max(v["kuupaev"] for v in seis.values()) if seis else date.today().isoformat()
    ul = lisa.get("ulevaatused") or []
    leiud_kp = kp(max(u["kuupaev"] for u in ul)) if ul else None
    for f in ("tehisaru-ja-too.html", "tehisaru-ja-too-uhine.html", "eelvaade.html"):
        p = os.path.join(TOO, f)
        s = open(p).read()
        s = re.sub(r'<span class="ts-seis">Seis ([^<]*)</span>',
                   lambda m: f'<span class="ts-seis">Leiud {leiud_kp or m.group(1)} · uudised ja uurimused {kp(andmed)}</span>', s)
        open(p, "w").write(s)
    json.dump(seis, open(os.path.join(TOO, "uuendus.json"), "w"), ensure_ascii=False, indent=1)
    print("valmis:", seis)


if __name__ == "__main__":
    main(sys.argv[1:])
