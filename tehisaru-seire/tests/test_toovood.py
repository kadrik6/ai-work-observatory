"""Töövood, mis lükkavad main harule, ei tohi kukkuda selle peale, et main vahepeal liikus.

12.11.2026 kukkus sait-andmed (push ilma rebase'ita) ja 13.11 logod (rebase ilma git'i nimeta).
"""
from pathlib import Path

TOOVOOD = Path(__file__).resolve().parents[2] / ".github" / "workflows"


def _kirjutajad():
    return [p for p in sorted(TOOVOOD.glob("*.yml")) if "git push" in p.read_text(encoding="utf-8")]


def test_kirjutajad_leitud():
    nimed = {p.name for p in _kirjutajad()}
    assert {"sait-andmed.yml", "logod.yml", "ettekanded.yml"} <= nimed


def test_push_enne_rebase_ja_nimi_enne_commiti():
    for p in _kirjutajad():
        s = p.read_text(encoding="utf-8")
        for rida in (r for r in s.splitlines() if "git push" in r):
            assert "git pull --rebase" in rida, f"{p.name}: push ilma rebase'ita: {rida.strip()}"
        nimi = s.find("git config user.name")
        assert nimi != -1, f"{p.name}: git'i nimi seadmata (rebase vajab seda)"
        assert nimi < s.find("git commit") and nimi < s.find("git pull --rebase"), p.name
