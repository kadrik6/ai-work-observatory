"""Stack Overflow 2026 toorandmetest: tehisaru ja arendustööriistade kasutus tööstaaži järgi (Kadri 27.11.2026).

Kasutus: python3 lae_so_kogemus.py TEE/survey_results_public.csv
Toorandmed (122 MB, CC BY-SA/ODbL): https://github.com/StackExchange/Survey/tree/main/packages/archive/2026
Kirjutab sisu/so2026-kogemus.csv. Rühmad on tööstaaži järgi (WorkExp, aastad tööl): 1–5, 6–15, 16+.
Jagaja on igas küsimuses need, kes sellele küsimusele vastasid (sama mis Stack Overflow' tulemuste lehel):
AISelect: vastanud; tööriistad ja arenduskeskkonnad: kes vastasid mõnele sama küsimuse veerule (HaveWorkedWith,
WantTo…, Admired). Kaalumist pole, sest Stack Overflow ise ei kaalu.
"""
import csv
import sys
from pathlib import Path

VALJA = Path(__file__).resolve().parent / "sisu" / "so2026-kogemus.csv"
URL = "https://github.com/StackExchange/Survey/tree/main/packages/archive/2026"
RYHMAD = [("1–5", 1, 5), ("6–15", 6, 15), ("16+", 16, 999)]
NAITAJAD = [  # (küsimus, veerg, jagaja veerud, väärtus, silt)
    ("AISelect", "AISelect", ["AISelect"], "AI coding assistants or coding agents", "Kasutab koodiassistenti või koodiagenti"),
    ("AISelect", "AISelect", ["AISelect"], "AI agents or automated workflows", "Kasutab AI-agente või automatiseeritud töövooge"),
    ("AISelect", "AISelect", ["AISelect"], "I don’t use AI tools", "Ei kasuta tehisaru tööriistu"),
]
AGENT = ["AICodeAgentHaveWorkedWith", "AICodeAgentWantToUseNext6Months", "AICodeAgentAdmired"]
for t in ("Claude Code", "GitHub Copilot", "OpenAI Codex", "Cursor", "Open Code"):
    NAITAJAD.append(("AICodeAgent", "AICodeAgentHaveWorkedWith", AGENT, t, t))
IDE = ["DevIDEHaveWorkedWith", "DevIDEWantToWorkWith", "DevIDEAdmired"]
for t in ("Visual Studio Code", "Visual Studio", "IntelliJ IDEA", "Cursor", "Neovim", "Zed"):
    NAITAJAD.append(("DevIDE", "DevIDEHaveWorkedWith", IDE, t, t))


def _tais(v):
    return v not in ("", "NA")


def arvuta(read):
    out = []
    for kus, veerg, jag, vaartus, silt in NAITAJAD:
        for ryhm, lo, hi in [("kõik", 0, 999)] + RYHMAD:
            rr = read if ryhm == "kõik" else [r for r in read if _tais(r["WorkExp"]) and lo <= int(float(r["WorkExp"])) <= hi]
            alus = [r for r in rr if any(_tais(r[j]) for j in jag)]
            n = sum(1 for r in alus if vaartus in r[veerg].split(";"))
            out.append({"kusimus": kus, "naitaja": silt, "ryhm": ryhm, "osa": f"{100 * n / len(alus):.1f}",
                        "n": n, "valim": len(alus), "url": URL, "kogumine": "23.06.–05.08.2026"})
    return out


def main(tee):
    csv.field_size_limit(10**9)
    with open(tee, encoding="utf-8-sig", newline="") as f:
        read = list(csv.DictReader(f))
    out = arvuta(read)
    with open(VALJA, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0]))
        w.writeheader()
        w.writerows(out)
    print(f"{VALJA.name}: {len(out)} rida")


if __name__ == "__main__":
    main(sys.argv[1])
