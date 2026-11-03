"""Lehe „Tehisaru ja töö“ generaator: ehitub repo failidest ja näitab parandatud kohti õigesti."""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

LEHT = Path(__file__).resolve().parents[1] / "leht"


def ehita(tmp_path):
    env = dict(os.environ, TOOELU_TOO=str(tmp_path))
    subprocess.run([sys.executable, str(LEHT / "tee_leiud.py")], check=True, env=env, capture_output=True)
    return (tmp_path / "leht-mall.html").read_text(encoding="utf-8")


def test_leht_ehitub_ja_koik_kaardid_on_olemas(tmp_path):
    s = ehita(tmp_path)
    for kysimus in ("Kas tehisaru teeb töö kiiremaks?", "Kas töökohti kaob?", "Mida töökorralduse muutmine tähendab",
                    "Kuidas töökorralduse muutust paremini mõõta?", "Kas tehisaru on Eesti koondamiste põhjus?",
                    "Kui suur on töötus tulevikus?"):
        assert kysimus in s, kysimus


def test_eli_keskmine_on_umardatud_pool_yles(tmp_path):
    # Eurostati väärtus 19,95 näidatakse 20,0, nagu seire ja „Tehisaru 2027“ lehel.
    s = ehita(tmp_path)
    assert "EL keskmisest veidi eespool (20,0%)" in s
    assert "(19,9%)" not in s


def test_2026_tulp_on_eraldi_reana(tmp_path):
    s = ehita(tmp_path)
    assert "ts-col-uus" in s and "Seda ei saa Eurostati 2021–2025 arvudega võrrelda" in s
    assert "uus rida" not in s  # Kadri 31.10: silt tekitas segadust
    assert "kaks aastat varem iga seitsmes" not in s


def test_mallis_ja_eurostati_failis_pole_kandidaate():
    # Kandidaatide pealkirjad jäävad käivituse artefakti (Kadri otsus 30.10), mitte repo.
    for f in ("mall.html", "eurostat_isoc_eb_ai_2026-10-31.json"):
        assert "openalex.org/W" not in (LEHT / f).read_text(encoding="utf-8"), f


def test_valdkondade_jaotus_tuleb_tookausta_andmetest(tmp_path):
    import json
    (tmp_path / "analyys").mkdir()
    rida = lambda v, n, a: {"voti": v, "nimi": n, "arv": a}
    (tmp_path / "analyys" / "a_valdkonnad.json").write_text(json.dumps({
        "aeg": "2026-10-31T19:25:00Z", "aasta": 2026,
        "read": [rida("20", "Economics, Econometrics and Finance", 60), rida("14", "Business, Management and Accounting", 30),
                 rida("27", "Medicine", 10)],
        "eelmine": [rida("20", "Economics, Econometrics and Finance", 40), rida("27", "Medicine", 10)]}), encoding="utf-8")
    s = ehita(tmp_path)
    assert "Millistest valdkondadest?" in s and "Majandus ja rahandus" in s
    assert "60,0% · 60" in s and "(90,0%)" in s  # kaks suurimat kokku
    assert "Päring 31.10.2026: 2026 100 publikatsiooni, 2025 50 publikatsiooni." in s


def test_ilma_valdkondade_andmeteta_plokki_pole(tmp_path):
    assert "Millistest valdkondadest?" not in ehita(tmp_path)


def test_pikkadel_tabelitel_on_ridade_valik():
    # Kadri 31.10.2026: vaikimisi 12 rida, valik 12 / 24 / 48 / kõik.
    s = (LEHT / "mall.html").read_text(encoding="utf-8")
    assert "const LK_VALIKUD = [12, 24, 48];" in s
    for nimi in ("a-tood", "a-hn", "a-raportid", "a-tood-eesti", "a-rk", "a-ea-tabel", "tabel"):
        assert f"'{nimi}'" in s.split("const LK_VALIKUD")[1].split("forEach")[0], nimi
        assert f'data-draw="{nimi}"' in s, nimi


def test_publikatsioon_ei_ole_too():
    # Kadri 31.10.2026: „töö“ tähendab lehel ainult palgatööd.
    s = (LEHT / "mall.html").read_text(encoding="utf-8")
    for vale in (">Töö</th>", "Teadustöid", "Teadustööd", "Uusimad ja enim tsiteeritud tööd", "Eesti autorite töid"):
        assert vale not in s, vale


def test_peamised_leiud_viitavad_olemasolevatele_kaartidele(tmp_path):
    # Kadri 31.10.2026: sissejuhatuses kolm peamist leidu, igaüks link oma kaardile.
    import re
    s = ehita(tmp_path)
    lingid = re.findall(r'data-kaart="([\w-]+)"', s)
    assert len(lingid) == 3
    for k in lingid + ["kindlus"]:
        assert f'id="{k}"' in s, k


def test_uuringute_lingid_viitavad_otse_allikale():
    import json
    leiud = json.loads((Path(__file__).resolve().parents[1] / 'leiud.json').read_text(encoding='utf-8'))
    for u in leiud['uuringud']:
        for vaali in ('url', 'lisa_url'):
            url = u.get(vaali)
            if not url:
                continue
            assert url.startswith('https://'), (u['id'], url)
            assert 'consensus.app' not in url, (u['id'], url)


def test_uuringult_viide_seire_naitajale_ja_osade_riba(tmp_path):
    """Ühine sait (3.11.2026): uuring viitab sama küsimuse seire näitajale, mõlemal osal on sama riba."""
    s = ehita(tmp_path)
    naitajad = {n["id"] for n in json.loads((LEHT.parent.parent / "tehisaru-seire" / "naitajad.json").read_text(encoding="utf-8"))["naitajad"]}
    viited = re.findall(r'href="([a-z-]+)\.html#uuringud">Eesti number: ', s)
    assert viited and set(viited) <= naitajad
    assert '<nav class="osad"' in s and 'href="index.html"><b>Mida mõõdetakse</b>' in s
