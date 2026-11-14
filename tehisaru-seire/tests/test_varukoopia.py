"""ADR-2 (14.11.2026): käsitsi hoitud failidest päevane koopia projekti kausta, 14 päeva."""
import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "sait"))
import vota_kaasa as vk  # noqa: E402


def _proj(tmp_path):
    for rel in ("seire-uks-sait/ettekanded.json", "tooelu-leht-andmed/leiud-lisa.json"):
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / rel).write_text('{"a": 1}', encoding="utf-8")
    return tmp_path


def test_koopia_tekib_paeva_kausta(tmp_path):
    p = _proj(tmp_path)
    tehtud = vk.varukoopia(p, dt.date(2026, 11, 14))
    paev = p / vk.VARUKOOPIAD / "2026-11-14"
    assert tehtud == ["seire-uks-sait/ettekanded.json", "tooelu-leht-andmed/leiud-lisa.json"]
    assert (paev / "seire-uks-sait__ettekanded.json").read_text(encoding="utf-8") == '{"a": 1}'
    assert (paev / "tooelu-leht-andmed__leiud-lisa.json").exists()


def test_vanad_kaovad_uued_ja_muud_jaavad(tmp_path):
    p = _proj(tmp_path)
    juur = p / vk.VARUKOOPIAD
    for nimi in ("2026-10-30", "2026-10-31", "markmed"):
        (juur / nimi).mkdir(parents=True)
    vk.varukoopia(p, dt.date(2026, 11, 14))
    alles = sorted(k.name for k in juur.iterdir())
    assert alles == ["2026-10-31", "2026-11-14", "markmed"]


def test_puuduv_fail_ei_peata(tmp_path):
    assert vk.varukoopia(tmp_path, dt.date(2026, 11, 14)) == []
    assert not (tmp_path / vk.VARUKOOPIAD).exists()


def test_koopiad_ei_lahe_repo():
    assert vk.VARUKOOPIAD.startswith("seire-uks-sait/") and "sisu" not in vk.VARUKOOPIAD
