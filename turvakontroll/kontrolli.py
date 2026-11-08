"""Kontrollib enne GitHubi viimist, et repo läheksid ainult lubatud failid ja et neis poleks tundlikku sisu.

    python3 turvakontroll/kontrolli.py               kõik failid, mis läheksid repo (vt allpool)
    python3 turvakontroll/kontrolli.py --nimekiri    prindib ainult failide nimekirja
    python3 turvakontroll/kontrolli.py --staged      ainult commit'iks lisatud failid, sisu Giti indeksist (konks)
    python3 turvakontroll/kontrolli.py FAIL ...      ainult antud failid

Millised failid: Giti repos need, mida Git jälgiks (.gitignore järgi); väljaspool repot lubatud.txt järgi.
Viga (lõpetab koodiga 1): keelatud kaust, keelatud failitüüp, isiklik pilt, võtmetaoline string, keelatud sõna.
Hoiatus: suur fail, e-posti aadress, masina absoluutne tee, puuduv privaatne loend. Hoiatused vaatab inimene üle.

Privaatsed loendid (ei lähe repo): keelatud-sonad.txt ja keelatud-kaustad.txt. Neid otsitakse järjekorras:
kaust muutujas TURVAKONTROLL_PRIVAATNE, see kaust, ~/.config/ai-work-observatory/. GitHub Actionsis võib
loendi sisu anda saladusena muutujates KEELATUD_SONAD ja KEELATUD_KAUSTAD (üks rida = üks kirje).
"""

import argparse
import fnmatch
import os
import re
import subprocess
import sys
from pathlib import Path

SIIN = Path(__file__).resolve().parent
# Need ei lähe välisesse hoidlasse kunagi, isegi kui .gitignore või lubatud.txt neid kogemata lubaks.
# Sisemiste projektide kaustade nimed on privaatses loendis keelatud-kaustad.txt, mitte siin.
YLDISED_KAUSTAD = ["uploads/*", "fotod/*", "Photos*", "arhiiv/*", "*/work/*", "*.env", "*/.env*", ".env*",
                   "tehisaru-seire/raportid/fotod/*", "tehisaru-seire/raportid/html/fotod/*",
                   "turvakontroll/keelatud-*.txt", "turvakontroll/KLASSID.md", ".claude/settings.local.json"]
KEELATUD_TUUBID = {".xlsx", ".xls", ".xlsm", ".csv.gz", ".pkl", ".pickle", ".zip", ".docx", ".pptx", ".pdf",
                   ".db", ".sqlite", ".env", ".pem", ".key"}
# Pildid on lubatud ainult testide sünteetilise sisendina; muud pildid võivad olla isiklikud fotod.
PILDID = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".heic", ".cr3", ".tif", ".tiff"}
# Erand (Kadri luba 8.11.2026): seire saidi avalehe päise pilt, Kadri antud töölaua foto, mitte isiklik.
PILDID_LUBATUD = ["*/tests/*", "tehisaru-seire/sait/pilt/avaleht.jpg"]
TEKST = {".py", ".md", ".csv", ".json", ".txt", ".html", ".css", ".js", ".ini", ".toml", ".yml", ".yaml", ".svg", ""}
SUUR = 1_000_000
VOTMED = [
    (re.compile(r"(?i)(api[_-]?key|secret|token|password|passwd|parool)\s*[:=]\s*['\"][^'\"\s]{12,}['\"]"), "võti või parool"),
    (re.compile(r"ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}"), "GitHubi võti"),
    (re.compile(r"sk-ant-[A-Za-z0-9_-]{20,}"), "Anthropicu võti"),
    (re.compile(r"AKIA[0-9A-Z]{16}"), "AWS võti"),
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), "privaatvõti"),
    (re.compile(r"(?i)[?&]api_key=[A-Za-z0-9]{12,}"), "võti URL-is"),
]
EPOST = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
ABS_TEE = re.compile(r"/mnt/project[-]files|/home/[a-z]+/|C:\\\\Users\\\\")


def loe_mustrid(p):
    lubatud, valja = [], []
    for rida in p.read_text(encoding="utf-8").splitlines():
        rida = rida.strip()
        if not rida or rida.startswith("#"):
            continue
        (valja if rida.startswith("!") else lubatud).append(rida.lstrip("!"))
    return lubatud, valja


def sobib(tee, mustrid):
    return any(fnmatch.fnmatchcase(tee, m) for m in mustrid)


def nimekiri(juur, lubatud_fail=SIIN / "lubatud.txt"):
    """Kõik failid kaustas juur, mis lubatud.txt järgi lähevad repo (suhtelised teed)."""
    lubatud, valja = loe_mustrid(lubatud_fail)
    failid = []
    for p in sorted(juur.rglob("*")):
        if not p.is_file():
            continue
        tee = p.relative_to(juur).as_posix()
        if sobib(tee, lubatud) and not sobib(tee, valja):
            failid.append(tee)
    return failid


def _git(juur, *args):
    r = subprocess.run(["git", "-C", str(juur), *args], capture_output=True)
    if r.returncode:
        raise SystemExit(f"git {' '.join(args[:2])} ebaõnnestus: {r.stderr.decode('utf-8', 'replace').strip()}")
    return r.stdout


def git_failid(juur):
    """Failid, mida Git jälgib või jälgiks (.gitignore järgi). Kettalt kustutatud failid jäävad välja."""
    valjund = _git(juur, "ls-files", "-z", "--cached", "--others", "--exclude-standard")
    return sorted({t for t in valjund.decode("utf-8").split("\0") if t and (juur / t).exists()})


def git_lisatud(juur):
    """Commit'iks lisatud (muudetud või uued) failid."""
    valjund = _git(juur, "diff", "--cached", "--name-only", "-z", "--diff-filter=ACMR")
    return sorted(t for t in valjund.decode("utf-8").split("\0") if t)


def loe_loend(nimi, muutuja):
    """Privaatne loend: Actionsi saladus (muutuja) või fail. Tagastab (kirjed, kas leiti)."""
    if os.environ.get(muutuja):
        return [r.strip() for r in os.environ[muutuja].splitlines() if r.strip()], True
    kohad = [Path(os.environ["TURVAKONTROLL_PRIVAATNE"])] if os.environ.get("TURVAKONTROLL_PRIVAATNE") else []
    kohad += [SIIN, Path.home() / ".config" / "ai-work-observatory"]
    for kaust in kohad:
        p = kaust / nimi
        if p.exists():
            read = p.read_text(encoding="utf-8").splitlines()
            return [r.strip() for r in read if r.strip() and not r.startswith("#")], True
    return [], False


def loe_sonad():
    return loe_loend("keelatud-sonad.txt", "KEELATUD_SONAD")[0]


def keelatud_kaustad():
    return YLDISED_KAUSTAD + loe_loend("keelatud-kaustad.txt", "KEELATUD_KAUSTAD")[0]


KEELATUD_KAUSTAD = keelatud_kaustad()


def kontrolli_faili(juur, tee, sonad, sisu=None):
    """Tagastab (vead, hoiatused) ühe faili kohta. sisu (baidid) antakse, kui fail tuleb Giti indeksist."""
    vead, hoiatused = [], []
    if sisu is None:
        sisu = (juur / tee).read_bytes()
    laiend = Path(tee).suffix.lower()
    if sobib(tee, KEELATUD_KAUSTAD):
        vead.append("keelatud kaust: ei lähe välisesse hoidlasse ilma eraldi loata")
    if any(tee.lower().endswith(t) for t in KEELATUD_TUUBID if t):
        vead.append("keelatud failitüüp")
    if laiend in PILDID and not sobib(tee, PILDID_LUBATUD):
        vead.append("pilt väljaspool teste (võib olla isiklik foto)")
    if len(sisu) > SUUR:
        hoiatused.append(f"suur fail ({len(sisu) // 1000} kB)")
    if laiend not in TEKST:
        return vead, hoiatused
    tekst = sisu.decode("utf-8", errors="replace")
    for muster, nimi in VOTMED:
        if muster.search(tekst):
            vead.append(f"{nimi} (muster: {muster.pattern[:30]}…)")
    madal = tekst.lower()
    for s in sonad:
        if s.lower() in madal:
            vead.append(f"keelatud sõna: „{s}“")
    aadressid = sorted(set(EPOST.findall(tekst)))
    if aadressid:
        hoiatused.append(f"e-posti aadress: {', '.join(aadressid[:3])}")
    if ABS_TEE.search(tekst):
        hoiatused.append("masina absoluutne tee")
    return vead, hoiatused


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("failid", nargs="*", help="kontrolli ainult neid (suhtelised teed)")
    ap.add_argument("--juur", default=".", help="projekti või repo kaust (vaikimisi praegune)")
    ap.add_argument("--nimekiri", action="store_true", help="prindi ainult repo minevate failide nimekiri")
    ap.add_argument("--staged", action="store_true", help="kontrolli commit'iks lisatud faile (Giti konks)")
    args = ap.parse_args(argv)
    juur = Path(args.juur).resolve()
    on_git = (juur / ".git").exists()

    if args.staged:
        failid = git_lisatud(juur)
    elif args.failid:
        failid = args.failid
    else:
        failid = git_failid(juur) if on_git else nimekiri(juur)
    if args.nimekiri:
        print("\n".join(failid))
        return 0

    sonad, leitud = loe_loend("keelatud-sonad.txt", "KEELATUD_SONAD")
    hoiatusi = 0
    if not leitud:
        print("HOIATUS  keelatud sõnade privaatne loend puudub: sisemisi termineid ei kontrollita", file=sys.stderr)
        hoiatusi += 1
    if not loe_loend("keelatud-kaustad.txt", "KEELATUD_KAUSTAD")[1]:
        print("HOIATUS  keelatud kaustade privaatne loend puudub: kehtivad ainult üldised keelud", file=sys.stderr)
        hoiatusi += 1
    lubatud, valja = loe_mustrid(SIIN / "lubatud.txt")
    vigu = 0
    for tee in failid:
        sisu = _git(juur, "show", f":{tee}") if args.staged else None
        vead, hoiatused = kontrolli_faili(juur, tee, sonad, sisu)
        if args.failid and not on_git and not (sobib(tee, lubatud) and not sobib(tee, valja)):
            vead.insert(0, "pole lubatud.txt nimekirjas")
        for v in vead:
            print(f"VIGA     {tee}: {v}")
        for h in hoiatused:
            print(f"HOIATUS  {tee}: {h}")
        vigu += len(vead)
        hoiatusi += len(hoiatused)
    print(f"\nKontrollitud {len(failid)} faili: {vigu} viga, {hoiatusi} hoiatust.")
    return 1 if vigu else 0


if __name__ == "__main__":
    sys.exit(main())
