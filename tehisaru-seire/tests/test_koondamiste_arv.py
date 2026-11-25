"""Koondatute arv uueneb jätku-uudisest ise (Kadri 25.11.2026: Pipedrive'i ja Eesti Energia lõplikud arvud olid
uudistes olemas, aga Töö vaade näitas esimest teadet)."""
import copy
import re
import sys
from pathlib import Path

import pytest

JUUR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(JUUR / "sait"))
import andmekiht  # noqa: E402
import komponendid  # noqa: E402
import lehed_ulevaade  # noqa: E402

import importlib.util  # noqa: E402

_spec = importlib.util.spec_from_file_location("sait_ehita_koond", JUUR / "sait" / "ehita.py")
ehita = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ehita)


def _juhtum(nimi="Firma", kuupaev="2026-10-29", arv=267, **lisa):
    return dict({"id": nimi.lower() + "-" + kuupaev, "kuupaev": kuupaev, "ettevote": nimi, "arv_eestis": arv,
                 "arv_tekst": "esimene teade", "roll": "kaudne"}, **lisa)


def _uudis(kuupaev, arv, nimi="Firma", tekst="jätkulugu: uus arv", **lisa):
    return dict({"kuupaev": kuupaev, "piirkond": "EE", "teema": "koondamine", "ettevote": nimi, "arv_eestis": arv,
                 "arv_tekst": tekst, "ai_roll": "ei_mainita", "pealkiri": f"{nimi} {arv}", "url": f"https://n.ee/{kuupaev}",
                 "allikas": "ERR", "lisatud": kuupaev}, **lisa)


def _uuenda(juhtumid, uudised):
    A = {"koondamised": {"juhtumid": copy.deepcopy(juhtumid)}, "uudised": uudised}
    andmekiht.uuenda_koondamiste_arvud(A)
    return A["koondamised"]["juhtumid"]


def test_hilisem_uudis_uue_arvuga_asendab_esimese_teate_arvu():
    (j,) = _uuenda([_juhtum(arv_vahemalt=True)], [_uudis("2026-11-24", 236)])
    assert j["arv_eestis"] == 236 and j["arv_tekst"] == "uus arv"  # eesliide „jätkulugu:“ võetakse ära
    assert j["arv_varem"] == {"arv_eestis": 267, "arv_vahemalt": True, "arv_ulem": None, "arv_tekst": "esimene teade"}
    assert j["arv_uuendus"] == {"kuupaev": "2026-11-24", "url": "https://n.ee/2026-11-24", "allikas": "ERR", "pealkiri": "Firma 236"}
    assert "arv_vahemalt" not in j  # täpsustatud arv ei ole enam alampiir
    assert j["roll"] == "kaudne" and j["kuupaev"] == "2026-10-29"  # roll ja kuupäev tulevad esimesest teatest


def test_varem_nahtud_arvu_kordamine_ei_muuda_midagi():
    # arvamuslugu nimetab pärast täpsustust jälle esialgset arvu; jätkulugu ilma arvuta ei loe
    (j,) = _uuenda([_juhtum(arv=390)], [_uudis("2026-11-06", 390), _uudis("2026-11-23", 343), _uudis("2026-11-25", 390),
                                        _uudis("2026-11-26", None)])
    assert j["arv_eestis"] == 343 and j["arv_uuendus"]["kuupaev"] == "2026-11-23"
    (j,) = _uuenda([_juhtum(arv=390)], [_uudis("2026-11-06", 390), _uudis("2026-11-07", None)])
    assert j["arv_eestis"] == 390 and "arv_uuendus" not in j and "arv_varem" not in j


def test_mitu_tapsustust_voidab_uusim_ja_samal_paeval_hiljem_lisatu():
    (j,) = _uuenda([_juhtum()], [_uudis("2026-11-24", 236, lisatud="2026-11-25"), _uudis("2026-11-10", 250),
                                 _uudis("2026-11-24", 240, lisatud="2026-11-24")])
    assert j["arv_eestis"] == 236 and j["arv_varem"]["arv_eestis"] == 267


def test_teadmata_arv_saab_arvu_ja_ulempiir_kaob():
    (j,) = _uuenda([_juhtum(arv=None, arv_ulem=50)], [_uudis("2026-11-01", 42)])
    assert j["arv_eestis"] == 42 and "arv_ulem" not in j and j["arv_varem"]["arv_ulem"] == 50


def test_uudis_laheb_oige_juhtumi_juurde():
    juhtumid = [_juhtum(kuupaev="2026-01-09", arv=40), _juhtum(kuupaev="2026-10-12", arv=100), _juhtum("Teine", arv=10)]
    uudised = [_uudis("2026-01-05", 99),             # enne esimest teadet
               _uudis("2026-02-01", 45),             # jaanuari juhtumi täpsustus
               _uudis("2026-11-01", 90),             # oktoobri juhtumi täpsustus, mitte jaanuari oma
               _uudis("2026-11-02", 7, nimi="Kolmas"),
               _uudis("2026-11-03", 12, nimi="Teine", piirkond="US"),
               _uudis("2026-11-03", 12, nimi="Teine", teema="ai_too"),
               _uudis("2026-11-03", True, nimi="Teine")]
    jaan, okt, teine = _uuenda(juhtumid, uudised)
    assert (jaan["arv_eestis"], okt["arv_eestis"], teine["arv_eestis"]) == (45, 90, 10) and "arv_uuendus" not in teine
    (j,) = _uuenda([_juhtum(kuupaev="2026-01-09", arv=40)], [_uudis("2026-09-01", 45)])
    assert j["arv_eestis"] == 40  # üle poole aasta hilisem uudis on juba uus lugu


@pytest.fixture(scope="module")
def A():
    return andmekiht.lae()


@pytest.fixture(scope="module")
def too(A, tmp_path_factory):
    kaust = tmp_path_factory.mktemp("sait-koond")
    ehita.ehita(kaust, A)
    return (kaust / "too.html").read_text(encoding="utf-8")


def _tekst(h):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", h))


def test_too_vaade_naitab_uut_arvu_esimest_teadet_ja_allikat(A, too):
    """Kui andmetes on täpsustatud arv, peab leht ütlema uue arvu, esimese teate arvu ja andma uue arvu allika lingi."""
    for j in A["koondamised"]["juhtumid"]:
        if not j.get("arv_uuendus"):
            continue
        uus, varem = lehed_ulevaade.koondamise_arv(j), lehed_ulevaade.koondamise_arv(j["arv_varem"])
        lause = _tekst(too[too.index('id="koondamised-uuendused"'):].split("</p>")[0])
        assert f'{j["ettevote"]} {uus} (esimeses teates {varem}; {j["arv_uuendus"]["allikas"]}, {komponendid.kp(j["arv_uuendus"]["kuupaev"])})' in lause
        rida = too[too.index(f'id="pk-{j["id"]}"'):]
        rida = rida[:rida.index("</tr>")]
        assert f"<b>{uus}</b>" in rida and f"esimeses teates {varem}" in _tekst(rida)
        assert f'href="{j["arv_uuendus"]["url"]}"' in rida and f'href="{j["arv_uuendus"]["url"]}"' in too[too.index('id="koondamised-uuendused"'):]
        riba = too[too.index(f'data-k="{j["id"]}"'):]
        assert f'<span class="kr-a">{j["arv_eestis"]}</span>' in riba[:riba.index("</div>")]


def test_ilma_tapsustusteta_lauset_ei_ole():
    assert lehed_ulevaade.arvu_uuendused([_juhtum()]) == ""


def test_viimane_kuupaev_arvestab_arvu_tapsustust():
    (j,) = _uuenda([_juhtum()], [_uudis("2026-11-24", 236)])
    assert lehed_ulevaade.koondamiste_viimane({"juhtumid": [j]}) == "2026-11-24"
    assert lehed_ulevaade.koondamiste_viimane({"juhtumid": [_juhtum()]}) == "2026-10-29"
