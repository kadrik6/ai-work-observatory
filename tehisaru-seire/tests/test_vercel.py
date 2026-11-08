"""Veebisait Verceli kaudu (Kadri 8.11.2026): ehitus repo failidest, ainult saidi kaust, otsingumootoritele keelatud."""
import importlib.util
import json
import re
import sys
from pathlib import Path

JUUR = Path(__file__).resolve().parent.parent
REPO = JUUR.parent
sys.path.insert(0, str(JUUR / "sait"))
_spec = importlib.util.spec_from_file_location("sait_ehita_v", JUUR / "sait" / "ehita.py")
ehita = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ehita)


def test_vercel_ehitab_ainult_saidi_kausta_ja_keelab_indekseerimise():
    v = json.loads((REPO / "vercel.json").read_text(encoding="utf-8"))
    assert v["outputDirectory"] == "tehisaru-seire/valjund/sait"
    assert (REPO / v["outputDirectory"]).resolve() == ehita.VALJUND.resolve()
    assert v["buildCommand"] == "cd tehisaru-seire && python3 sait/ehita.py"
    assert "main" in v["ignoreCommand"]  # eelvaateid teistest harudest ei ehitata
    pais = {h["key"]: h["value"] for r in v["headers"] for h in r["headers"]}
    assert "noindex" in pais["X-Robots-Tag"]


def test_robots_keelab_koik(tmp_path):
    ehita.ehita(tmp_path)
    assert (tmp_path / "robots.txt").read_text(encoding="utf-8") == "User-agent: *\nDisallow: /\n"
    # väljundis on ainult saidi failid: html, stiil, skript ja robots.txt
    lubatud = re.compile(r".+\.html$|^stiil\.css$|^sait\.js$|^robots\.txt$")
    assert all(lubatud.match(p.name) for p in tmp_path.iterdir()), sorted(p.name for p in tmp_path.iterdir())
