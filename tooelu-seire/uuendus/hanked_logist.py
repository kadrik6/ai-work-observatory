"""Hangete tuvastuse (hanked.yml, haru hanked/tuvastus) logist leht.json: LEHT i n <base64 gzip> read kokku.

Kasutus: python3 hanked_logist.py LOGIFAIL RUN_ID   -> SEIRE_UUENDUS/hanked/leht.json ja seis.json
(SEIRE_UUENDUS vaikimisi /mnt/project-files/seire-uuendus)
LOGIFAIL = GitHubi get_job_logs vastus (JSON väljaga logs_content või tavaline tekst).
Lisatud 5.11.2026 (Kadri: AI-hanked ka seire saidile). Pimehindamise materjale see ei puuduta.
"""
import base64, gzip, json, os, re, sys, datetime
from pathlib import Path

VALJA = Path(os.environ.get("SEIRE_UUENDUS", os.path.join(os.environ.get("UUENDUS_ANDMED", "/mnt/project-files"), "seire-uuendus"))) / "hanked"
t = open(sys.argv[1], encoding="utf-8").read()
try:
    t = json.loads(t)["logs_content"]
except Exception:
    pass
tykid = {}
for m in re.finditer(r"LEHT (\d+) (\d+) ([A-Za-z0-9+/=]+)", t):
    tykid[int(m.group(1))] = (int(m.group(2)), m.group(3))
if not tykid:
    sys.exit("VIGA: logis pole LEHT ridu")
n = next(iter(tykid.values()))[0]
puudu = [i for i in range(n) if i not in tykid]
if puudu:
    sys.exit(f"VIGA: logist puuduvad LEHT tükid {puudu[:5]} (suurenda tail_lines)")
leht = json.loads(gzip.decompress(base64.b64decode("".join(tykid[i][1] for i in range(n)))))
VALJA.mkdir(parents=True, exist_ok=True)
(VALJA / "leht.json").write_text(json.dumps(leht, ensure_ascii=False), encoding="utf-8")
(VALJA / "seis.json").write_text(json.dumps({"run": sys.argv[2], "kuupaev": datetime.date.today().isoformat()}), encoding="utf-8")
print("leht.json:", list(leht), "loend", len(leht.get("loend", [])))
