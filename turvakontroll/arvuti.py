"""Kontrollib, kas see arvuti on repo jaoks õigesti seadistatud. Käivita repo juurkaustast igas uues arvutis.

    python3 turvakontroll/arvuti.py

Ei muuda midagi. OK = korras, HOIATUS = vaata üle, VIGA = paranda enne commit'i (kood 1).
"""

import locale
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

JUUR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
import kontrolli  # noqa: E402


def git(*args):
    r = subprocess.run(["git", "-C", str(JUUR), *args], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else ""


def kontrollid():
    """Tagastab loendi (tase, tekst)."""
    tulem = []
    v = sys.version_info
    tulem.append(("OK" if v >= (3, 10) else "VIGA", f"Python {v.major}.{v.minor} (vaja vähemalt 3.10)"))
    kodeering = locale.getpreferredencoding(False).lower().replace("-", "")
    tulem.append(("OK" if kodeering == "utf8" else "HOIATUS",
                  f"vaikekodeering {kodeering} (kood määrab utf-8 ise; utf8 on kindlam: PYTHONUTF8=1)"))
    tulem.append(("OK" if shutil.which("curl") else "HOIATUS", "curl (välisallikate laadija vajab)"))
    wsl = "microsoft" in platform.release().lower()
    if sys.platform == "win32":
        tulem.append(("HOIATUS", "Windowsi Python: kasuta WSL2-d (liivakast ja reavahetused)"))
    if wsl and str(JUUR).startswith("/mnt/"):
        tulem.append(("HOIATUS", f"repo on Windowsi kettal ({JUUR}); kiirem ja kindlam on WSL-i kodukaust"))
    if not shutil.which("git"):
        tulem.append(("VIGA", "git puudub"))
        return tulem
    if not (JUUR / ".git").exists():
        tulem.append(("HOIATUS", "see kaust pole Giti repo (veel)"))
        return tulem
    autocrlf = git("config", "core.autocrlf") or "pole seatud"
    tulem.append(("OK" if autocrlf in ("false", "input", "pole seatud") else "HOIATUS",
                  f"core.autocrlf = {autocrlf} (.gitattributes hoiab LF-i, aga 'true' võib Windowsis segada)"))
    konks = git("config", "core.hooksPath")
    tulem.append(("OK" if konks == ".githooks" else "VIGA",
                  f"core.hooksPath = {konks or 'pole seatud'} (paranda: git config core.hooksPath .githooks)"))
    for nimi, muutuja in [("keelatud-sonad.txt", "KEELATUD_SONAD"), ("keelatud-kaustad.txt", "KEELATUD_KAUSTAD")]:
        leitud = kontrolli.loe_loend(nimi, muutuja)[1]
        tulem.append(("OK" if leitud else "HOIATUS",
                      f"privaatne loend {nimi} " + ("olemas" if leitud else "puudub (~/.config/ai-work-observatory/)")))
    crlf = [t for t in kontrolli.git_failid(JUUR)
            if Path(t).suffix in {".py", ".md", ".html", ".css", ".json"} and b"\r\n" in (JUUR / t).read_bytes()]
    tulem.append(("OK" if not crlf else "HOIATUS", f"Windowsi reavahetustega tekstifaile: {len(crlf)}"
                  + (f" (nt {crlf[0]})" if crlf else "")))
    if os.environ.get("CLAUDECODE"):
        tulem.append(("OK", "töötab Claude Code'i sees; liivakasti seisu vaata käsuga /status"))
    return tulem


def main():
    tulem = kontrollid()
    for tase, tekst in tulem:
        print(f"{tase:8} {tekst}")
    return 1 if any(t == "VIGA" for t, _ in tulem) else 0


if __name__ == "__main__":
    sys.exit(main())
