"""Veebisait Verceli kaudu (Kadri 8.11.2026): ehitus repo failidest, ainult saidi kaust.
Otsingumootoritele avatud alates 21.11.2026 (Kadri: „Remove this no index“); vercel.app jääb noindex."""
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


def test_vercel_ehitab_ainult_saidi_kausta_ja_noindex_ainult_vercel_app():
    v = json.loads((REPO / "vercel.json").read_text(encoding="utf-8"))
    assert v["outputDirectory"] == "tehisaru-seire/valjund/sait"
    assert (REPO / v["outputDirectory"]).resolve() == ehita.VALJUND.resolve()
    assert v["buildCommand"] == "cd tehisaru-seire && python3 sait/ehita.py"
    assert "main" in v["ignoreCommand"]  # eelvaateid teistest harudest ei ehitata
    koik = [r for r in v["headers"] if "has" not in r]
    assert all(h["key"] != "X-Robots-Tag" for r in koik for h in r["headers"])  # põhidomeen on indekseeritav
    vercel = [r for r in v["headers"] if r.get("has") == [{"type": "host", "value": ".*\\.vercel\\.app"}]]
    assert len(vercel) == 1 and {h["key"]: h["value"] for h in vercel[0]["headers"]}["X-Robots-Tag"] == "noindex, nofollow"


def test_robots_lubab_ja_sisukaart_on_parisleheed(tmp_path):
    lehed = ehita.ehita(tmp_path)
    assert (tmp_path / "robots.txt").read_text(encoding="utf-8") == "User-agent: *\nAllow: /\nSitemap: https://www.tehisaruseire.ee/sitemap.xml\n"
    kaart = (tmp_path / "sitemap.xml").read_text(encoding="utf-8")
    loc = re.findall(r"<loc>(.*?)</loc>", kaart)
    assert loc[0] == "https://www.tehisaruseire.ee/" and len(loc) == len(lehed)
    assert all(f"https://www.tehisaruseire.ee/{v}" not in loc for v in ehita.VANAD_AADRESSID)  # suunajad pole sisukaardis
    for f in lehed:  # igal lehel on oma põhiaadress ja kirjeldus
        h = (tmp_path / f).read_text(encoding="utf-8")
        assert f'<link rel="canonical" href="https://www.tehisaruseire.ee/{"" if f == "index.html" else f}">' in h, f
        assert '<meta name="description" content="' in h and 'name="robots"' not in h, f
    for vana in ehita.VANAD_AADRESSID:
        assert '<meta name="robots" content="noindex">' in (tmp_path / vana).read_text(encoding="utf-8")
    # väljundis on ainult saidi failid: html, stiil, skript, robots.txt, sisukaart ja avalehe päise pilt
    lubatud = re.compile(r".+\.html$|^stiil\.css$|^sait\.js$|^robots\.txt$|^sitemap\.xml$|^pilt$")
    assert all(lubatud.match(p.name) for p in tmp_path.iterdir()), sorted(p.name for p in tmp_path.iterdir())
    assert sorted(p.name for p in (tmp_path / "pilt").iterdir() if p.name != "logod") == ["avaleht-tume.jpg", "avaleht.jpg"]
    # uudiste allikate logod (sait/lae_logod.py): ainult pildid, nimekiri logod.json jääb väljundist välja
    lubatud_logo = re.compile(r"^[a-z0-9.-]+\.(png|ico|gif|webp)$")
    logod = tmp_path / "pilt" / "logod"
    assert not logod.exists() or all(lubatud_logo.match(p.name) for p in logod.iterdir())


def test_kulastusloendur_ainult_vercelis():
    """Verceli Web Analytics (Kadri 8.11.2026): skript laaditakse ainult *.vercel.app ja oma domeeni aadressil."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "sait"))
    import kest
    assert "/_vercel/insights/script.js" in kest.ANALYYTIKA_JS
    assert "h.slice(-11)==='.vercel.app'" in kest.ANALYYTIKA_JS and "if(!ok)return" in kest.ANALYYTIKA_JS
    # 21.11.2026: oma domeen tehisaruseire.ee ja www; mitte sama lõpuga võõras nimi (nt xtehisaruseire.ee)
    assert "h==='tehisaruseire.ee'||h.slice(-17)==='.tehisaruseire.ee'" in kest.ANALYYTIKA_JS
    assert "h.slice(-16)==='tehisaruseire.ee'" not in kest.ANALYYTIKA_JS
    d = Path(__file__).resolve().parents[1] / "valjund" / "sait"
    if d.exists():
        for f in d.glob("*.html"):
            h = f.read_text(encoding="utf-8")
            if "<header" in h:
                assert kest.ANALYYTIKA_JS in h, f.name


def test_igapaevased_commitid_ehitatakse_deploy_hookiga():
    # 8.11.2026: Vercel Hobby blokeeris seire-igapaevane commit'i 0802a39 („Deployment was blocked“)
    w = (Path(__file__).resolve().parents[2] / ".github" / "workflows" / "vercel-ehita.yml").read_text(encoding="utf-8")
    assert "secrets.VERCEL_DEPLOY_HOOK" in w and "workflows: [sait-andmed, logod]" in w
    assert "https://api.vercel.com" not in w  # hooki URL on ainult saladuses
