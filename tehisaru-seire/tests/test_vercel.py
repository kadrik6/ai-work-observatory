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
    # väljundis on ainult saidi failid: html, stiil, skript, robots.txt ja avalehe päise pilt
    lubatud = re.compile(r".+\.html$|^stiil\.css$|^sait\.js$|^robots\.txt$|^pilt$")
    assert all(lubatud.match(p.name) for p in tmp_path.iterdir()), sorted(p.name for p in tmp_path.iterdir())
    assert sorted(p.name for p in (tmp_path / "pilt").iterdir()) == ["avaleht.jpg"]


def test_kulastusloendur_ainult_vercelis():
    """Verceli Web Analytics (Kadri 8.11.2026): skript laaditakse ainult *.vercel.app aadressil."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "sait"))
    import kest
    assert "/_vercel/insights/script.js" in kest.ANALYYTIKA_JS
    assert "h.slice(-11)==='.vercel.app'" in kest.ANALYYTIKA_JS and "if(!ok)return" in kest.ANALYYTIKA_JS
    d = Path(__file__).resolve().parents[1] / "valjund" / "sait"
    if d.exists():
        for f in d.glob("*.html"):
            h = f.read_text(encoding="utf-8")
            if "<header" in h:
                assert kest.ANALYYTIKA_JS in h, f.name


def test_igapaevased_commitid_ehitatakse_deploy_hookiga():
    # 8.11.2026: Vercel Hobby blokeeris seire-igapaevane commit'i 0802a39 („Deployment was blocked“)
    w = (Path(__file__).resolve().parents[2] / ".github" / "workflows" / "vercel-ehita.yml").read_text(encoding="utf-8")
    assert "secrets.VERCEL_DEPLOY_HOOK" in w and "workflows: [sait-andmed]" in w
    assert "https://api.vercel.com" not in w  # hooki URL on ainult saladuses
