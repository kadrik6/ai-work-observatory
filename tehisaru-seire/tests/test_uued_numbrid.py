"""kataloog/uued_numbrid.py testid. NB: numbrid on väljamõeldud testandmed, mitte päris statistika."""

import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "uued_numbrid", Path(__file__).resolve().parent.parent / "kataloog" / "uued_numbrid.py")
un = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(un)

PAIS = "moodik,riik,aasta,vaartus,avaldatud,kontrollitud,kuidas,url,markus,margend\n"


def test_uus_aasta_ja_muutus_leitakse_umardamine_ja_kuupaev_mitte(tmp_path, monkeypatch):
    vana = PAIS + ("m,EE,2024,1.98,2026-09-29,2026-10-27,,,,\n"
                   "m,FI,2024,3.1126,,2026-10-27,,,,\n"
                   "m,SE,2024,3.5,,2026-10-27,,,,\n")
    uus = PAIS + ("m,EE,2024,1.98,2026-11-03,2026-11-03,,,,\n"   # ainult kuupäevad muutusid
                  "m,FI,2024,3.11,,2026-11-03,,,,\n"            # ümardamine
                  "m,SE,2024,3.6,,2026-11-03,,,,\n"             # päris muutus
                  "m,EE,2025,2.08,2026-11-03,2026-11-03,,,,p\n")  # uus aasta
    (tmp_path / "kataloog").mkdir()
    (tmp_path / "kataloog" / "vaatlused-valis.csv").write_text(uus, encoding="utf-8")
    monkeypatch.setattr(un, "SIIN", tmp_path)
    monkeypatch.setattr(un, "FAILID", {"kataloog/vaatlused-valis.csv": ("moodik", "riik", "aasta")})
    monkeypatch.setattr(un, "vana_tekst", lambda nimi, viide: vana)
    leiud = un.vorrdle(0.006, "HEAD")
    assert [(l["voti"], l["liik"]) for l in leiud] == [(["m", "SE", "2024"], "muutus"), (["m", "EE", "2025"], "uus")]
    md = un.markdown(leiud)
    assert "Lehe riikide kohta 2 uut" in md and "| 2.08 | uus | p |" in md


def test_teised_riigid_eraldi_ja_tuhi_tulemus():
    l = {"fail": "kataloog/vaatlused-valis.csv", "voti": ["m", "KR", "2025"], "vana": None, "uus": "1",
         "liik": "uus", "avaldatud": "", "margend": ""}
    assert "teiste riikide kohta 1" in un.markdown([l])
    assert "ei ole" in un.markdown([])
