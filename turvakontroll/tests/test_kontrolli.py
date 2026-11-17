"""Turvakontrolli testid. Võtmed, sõnad ja kaustad siin on väljamõeldud näited.

Näited on kokku liidetud tükkidest, et see fail ise läbiks turvakontrolli.
"""

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

SIIN = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SIIN))
import kontrolli  # noqa: E402

PROJEKT = SIIN.parent
ON_GIT = (PROJEKT / ".git").exists()


def fail(juur, tee, sisu):
    p = juur / tee
    p.parent.mkdir(parents=True, exist_ok=True)
    (p.write_bytes if isinstance(sisu, bytes) else lambda s: p.write_text(s, encoding="utf-8"))(sisu)
    return tee


def test_puhas_fail_laheb_labi(tmp_path):
    tee = fail(tmp_path, "tehisaru-seire/a.py", "x = 1\n")
    assert kontrolli.kontrolli_faili(tmp_path, tee, ["salajane"]) == ([], [])


def test_leiab_votme(tmp_path):
    tee = fail(tmp_path, "tehisaru-seire/a.py", 'API_KEY = "' + "abcdefghijklmnop" + '1234"\n')
    vead, _ = kontrolli.kontrolli_faili(tmp_path, tee, [])
    assert vead and "võti" in vead[0]


def test_leiab_votme_urlist(tmp_path):
    tee = fail(tmp_path, "tehisaru-seire/a.md", "https://api.openalex.org/works?api_key=" + "ABCDEF1234567890\n")
    assert kontrolli.kontrolli_faili(tmp_path, tee, [])[0]


def test_leiab_keelatud_sona_tostutundetult(tmp_path):
    tee = fail(tmp_path, "tehisaru-seire/a.md", "Siin on SALAJANE tekst.\n")
    vead, _ = kontrolli.kontrolli_faili(tmp_path, tee, ["muu", "salajane"])
    assert vead == ["keelatud sõna nr 2 privaatsest loendist"]


def test_veateade_ei_naita_keelatud_sona(tmp_path):
    """Actionsi logid võivad olla avalikud, seega veateade ei tohi sõna ennast sisaldada."""
    tee = fail(tmp_path, "tehisaru-seire/a.md", "Siin on SALAJANE tekst.\n")
    vead, _ = kontrolli.kontrolli_faili(tmp_path, tee, ["salajane"])
    assert vead and not any("salajane" in v.lower() for v in vead)


def test_keelatud_kaust_ja_tuup(tmp_path):
    tee = fail(tmp_path, "uploads/tabel.xlsx", b"PK\x03\x04")
    vead, _ = kontrolli.kontrolli_faili(tmp_path, tee, [])
    assert len(vead) == 2


def test_pilt_on_lubatud_ainult_testides(tmp_path):
    foto = fail(tmp_path, "tehisaru-seire/raportid/pilt.jpg", b"\xff\xd8")
    test = fail(tmp_path, "tehisaru-seire/tests/kuld/sisend/pilt.jpg", b"\xff\xd8")
    assert kontrolli.kontrolli_faili(tmp_path, foto, [])[0]
    assert not kontrolli.kontrolli_faili(tmp_path, test, [])[0]


def test_saidi_paisepilt_on_ainus_erand(tmp_path):
    """Kadri luba 8.11.2026: ainult see üks failitee, mitte kogu kaust."""
    luba = fail(tmp_path, "tehisaru-seire/sait/pilt/avaleht.jpg", b"\xff\xd8")
    teine = fail(tmp_path, "tehisaru-seire/sait/pilt/teine.jpg", b"\xff\xd8")
    assert not kontrolli.kontrolli_faili(tmp_path, luba, [])[0]
    assert kontrolli.kontrolli_faili(tmp_path, teine, [])[0]


def test_isiklikud_fotod_on_keelatud_ka_testikaustas_valjas(tmp_path):
    tee = fail(tmp_path, "tehisaru-seire/raportid/html/fotod/p.jpg", b"\xff\xd8")
    vead, _ = kontrolli.kontrolli_faili(tmp_path, tee, [])
    assert any("keelatud kaust" in v for v in vead)


def test_hoiatus_eposti_ja_absoluutse_tee_kohta(tmp_path):
    tee = fail(tmp_path, "tehisaru-seire/a.md", "Kirjuta nimi" + "@example.com, fail /home/" + "kasutaja/x\n")
    vead, hoiatused = kontrolli.kontrolli_faili(tmp_path, tee, [])
    assert not vead and len(hoiatused) == 2


def test_nimekiri_jargib_lubatud_ja_valja_mustreid(tmp_path):
    fail(tmp_path, "tehisaru-seire/a.py", "")
    fail(tmp_path, "tehisaru-seire/raportid/fotod/p.jpg", b"\xff\xd8")
    fail(tmp_path, "privaatne/b.py", "")
    lub = tmp_path / "lubatud.txt"
    lub.write_text("tehisaru-seire/*\n!tehisaru-seire/raportid/fotod/*\n", encoding="utf-8")
    assert kontrolli.nimekiri(tmp_path, lub) == ["tehisaru-seire/a.py"]


def test_privaatne_loend_tuleb_muutujast(monkeypatch):
    monkeypatch.setenv("KEELATUD_SONAD", "esimene\n\nteine\n")
    assert kontrolli.loe_loend("keelatud-sonad.txt", "KEELATUD_SONAD") == (["esimene", "teine"], True)


def test_privaatne_loend_tuleb_kaustast(tmp_path, monkeypatch):
    monkeypatch.delenv("KEELATUD_KAUSTAD", raising=False)
    monkeypatch.setenv("TURVAKONTROLL_PRIVAATNE", str(tmp_path))
    (tmp_path / "keelatud-kaustad.txt").write_text("# kommentaar\nsala/*\n", encoding="utf-8")
    assert kontrolli.loe_loend("keelatud-kaustad.txt", "KEELATUD_KAUSTAD") == (["sala/*"], True)


@pytest.mark.skipif(not shutil.which("git"), reason="git puudub")
def test_giti_rezhiim_jargib_gitignorei_ja_indeksit(tmp_path):
    def git(*a):
        subprocess.run(["git", "-C", str(tmp_path), *a], check=True, capture_output=True)
    git("init", "-q")
    fail(tmp_path, ".gitignore", "*\n!.gitignore\n!lubatud/\n!lubatud/**\n")
    fail(tmp_path, "lubatud/a.md", "puhas\n")
    fail(tmp_path, "peidus/b.md", "ei tohi näha\n")
    assert kontrolli.git_failid(tmp_path) == [".gitignore", "lubatud/a.md"]
    git("add", "lubatud/a.md")
    fail(tmp_path, "lubatud/a.md", "kettal muudetud, aga indeksis puhas\n")
    assert kontrolli.git_lisatud(tmp_path) == ["lubatud/a.md"]
    assert kontrolli.main(["--juur", str(tmp_path), "--staged"]) == 0
    fail(tmp_path, "lubatud/a.md", "Siin on SALAJANE sõna\n")
    git("add", "lubatud/a.md")
    sonad = ["salajane"]
    sisu = kontrolli._git(tmp_path, "show", ":lubatud/a.md")
    assert kontrolli.kontrolli_faili(tmp_path, "lubatud/a.md", sonad, sisu)[0]


def test_paris_nimekiri_ei_sisalda_keelatud_kaustu():
    """Repos: Git ei jälgi ühtegi keelatud faili. Algses kaustas: lubatud.txt ei luba ühtegi keelatud kausta."""
    failid = kontrolli.git_failid(PROJEKT) if ON_GIT else kontrolli.nimekiri(PROJEKT)
    assert failid, "nimekiri on tühi"
    keelatud = [f for f in failid if kontrolli.sobib(f, kontrolli.KEELATUD_KAUSTAD)]
    assert not keelatud, keelatud


def test_paris_failid_on_puhtad():
    """Kõik praegu lubatud failid läbivad kontrolli ilma veata."""
    failid = kontrolli.git_failid(PROJEKT) if ON_GIT else kontrolli.nimekiri(PROJEKT)
    sonad = kontrolli.loe_sonad()
    vead = {f: v for f in failid if (v := kontrolli.kontrolli_faili(PROJEKT, f, sonad)[0])}
    assert not vead, vead
