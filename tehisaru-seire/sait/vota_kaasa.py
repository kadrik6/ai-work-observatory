"""Võtab projekti kaustast saidi jaoks avaliku hetkeseisu: uudised, uudiste väited, hanked, publikatsioonid ja
Kadri kinnitatud uued uuringud (vt sait/ootel.py).

Neid andmeid uuendavad igapäevased tööd väljaspool repot (uudiste kogumine, hangete Actionsi käik, OpenAlexi
analüüs). Sait ehitab ainult repo failidest. Repo reegli järgi kopeeritakse siia midagi väljastpoolt ainult Kadri loal.
Kopeeritakse ainult avalik sisu: pealkiri, link, kuupäev ja oma sõnadega lühikokkuvõte (mitte artikli tekst),
riigihangete registri avalikud väljad (kirjeldus lühendatud) ja publikatsioonide metaandmed.

Käivitus: python3 sait/vota_kaasa.py PROJEKTI_KAUST   (või keskkonnamuutuja PROJEKTI_KAUST)
Uudistest jäetakse välja, kes ütles (väide kuulub väljaandele, mitte inimesele).
"""
import datetime as dt
import json
import os
import re
import shutil
import sys
from pathlib import Path

SISU = Path(__file__).resolve().parent / "sisu"
KIRJELDUS_MAX = 300  # hanke kirjelduse pikkus; täistekst jääb registrisse
NAITA = {"kinnitatud", "varasem"}  # väite olekud, mis lähevad saidile
UURINGU_VALJAD = ("id", "autorid", "aasta", "pealkiri", "kanal", "retsenseeritud", "url", "avaldatud", "meetod",
                  "kus", "valim", "leid", "lisatud", "seire_kinnitatud")


def _loe(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


STRATEEGIA_VALJAD = ("id", "riik", "riik_kood", "pealkiri", "asutus", "kuupaev", "url", "tahtaeg", "sihid", "markus",
                     "kontrollitud", "lisatud")


def strateegiad_saidile(d):
    """Ainult saidil näidatavad väljad; kogumise sisemised märkmed jäävad projekti kausta."""
    return {"strateegiad": [{k: s[k] for k in STRATEEGIA_VALJAD if k in s} for s in d.get("strateegiad", [])]}


def _kirjuta(nimi, andmed):
    (SISU / nimi).write_text(json.dumps(andmed, ensure_ascii=False, indent=0) + "\n", encoding="utf-8")


def ilma_nimedeta(kes):
    """„ERR News 3.11.2026 (Sinisalu, Hiiemaa, Töötukassa)“ → „ERR News 3.11.2026“. Sulud, kus on number
    (nt „sarnaselt ERR News 3.11“), jäävad alles."""
    return re.sub(r"\s*\([^()\d]*\)", "", kes).strip()


def naidatavad_vaited(read):
    return [r for r in read if r.get("seire_olek") in NAITA]


def kinnitatud_uuringud(read):
    """Ainult kinnitatud uuringud ja ainult avalikud väljad (kandidaadi sisemine viide jääb välja)."""
    return [{k: u[k] for k in UURINGU_VALJAD if k in u} for u in read if u.get("seire_olek") == "kinnitatud"]


ETTEKANDE_VALJAD = ("id", "esineja", "amet", "pealkiri", "allikas", "uritus", "uritus_url", "kuupaev", "video", "algus", "keel",
                    "teemad", "ruhm", "kokkuvote", "mottes", "kontroll", "seire_kinnitatud", "tegija")


def kinnitatud_ettekanded(d):
    """Usaldatud ürituste ettekanded (Kadri 8.11.2026): saidile ainult kinnitatud kirjed ja avalikud väljad."""
    return {"allikad": d.get("allikad", []),
            "ettekanded": [{k: r[k] for k in ETTEKANDE_VALJAD if k in r} for r in d.get("ettekanded", [])
                           if r.get("seire_olek") == "kinnitatud"]}


LIGIPAAS = ("avab_koigile", "avab_ehitamise_piirab_avaldamise", "piirab_rolliga", "keelab")


def ligipaasu_sundmused(uudised, tagasivaade):
    """Ettevõtete otsused, kes tohib tehisaru tööriistu kasutada (Kadri 9.11.2026: saidile kohe, märkega „töös“).
    Uudiste read, millel on `ligipaas`, ja vanemad juhtumid failist ligipaas-tagasivaade.jsonl. Sisemine kontrollimärge
    (`kontroll`) ja nimed (`kes_utles`) saidile ei lähe; põhjus on ettevõtte enda sõnadega."""
    out = []
    for kust, read, tekst in (("uudis", uudised, "arv_tekst"), ("tagasivaade", tagasivaade, "tekst")):
        for r in read:
            if not r.get("ligipaas") or r.get("kontrollitud") is False:
                continue
            out.append({"kuupaev": r["kuupaev"], "kuupaev_tapsus": r.get("kuupaev_tapsus", ""), "piirkond": r.get("piirkond", ""),
                        "ettevote": r["ettevote"], "sektor": r.get("sektor", ""), "ligipaas": r["ligipaas"],
                        "pohjus": r.get("ligipaas_pohjus", ""), "tekst": r.get(tekst) or r.get("pealkiri", ""),
                        "url": r.get("url", ""), "allikas": r.get("allikas", ""), "lisaallikas": r.get("lisaallikas", ""), "kust": kust})
    return sorted(out, key=lambda r: r["kuupaev"], reverse=True)


# ADR-2 (Kadri „jah ADR-2“ 14.11.2026): käsitsi hoitud failidel projekti kaustas pole ajalugu ja viimane kirjutaja
# võidab. Enne kopeerimist läheb nendest päevane koopia projekti kausta (mitte repo), alles 14 päeva.
KASITSI_FAILID = ("seire-uks-sait/ettekanded.json", "seire-uks-sait/saidi-ettepanekud.json",
                  "tooelu-leht-andmed/leiud-lisa.json")
VARUKOOPIAD = "seire-uks-sait/varukoopiad"
HOIA_PAEVI = 14


def varukoopia(proj, tana=None, hoia=HOIA_PAEVI):
    """Kopeerib käsitsi hoitud failid kausta varukoopiad/AAAA-KK-PP/ ja kustutab üle `hoia` päeva vanad."""
    proj, tana = Path(proj), tana or dt.date.today()
    juur = proj / VARUKOOPIAD
    paev = juur / tana.isoformat()
    tehtud = []
    for rel in KASITSI_FAILID:
        if (proj / rel).exists():
            paev.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(proj / rel, paev / rel.replace("/", "__"))
            tehtud.append(rel)
    piir = (tana - dt.timedelta(days=hoia)).isoformat()
    for k in juur.iterdir() if juur.exists() else []:
        if k.is_dir() and re.fullmatch(r"\d{4}-\d{2}-\d{2}", k.name) and k.name < piir:
            shutil.rmtree(k)
    return tehtud


def vota(proj):
    proj = Path(proj)
    varukoopia(proj)
    uu = proj / "tooelu-uudised"
    read = [json.loads(r) for r in (uu / "uudised.jsonl").read_text(encoding="utf-8").splitlines() if r.strip()]
    for r in read:
        r.pop("kes_utles", None)
    (SISU / "uudised.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in read), encoding="utf-8")
    tv_p = uu / "ligipaas-tagasivaade.jsonl"
    tv = [json.loads(r) for r in tv_p.read_text(encoding="utf-8").splitlines() if r.strip()] if tv_p.exists() else []
    _kirjuta("ligipaas.json", {"sundmused": ligipaasu_sundmused(read, tv)})
    # Kinnituskord (Kadri 8.11.2026 21:36): automaatsed mustandid lähevad saidile alles pärast Kadri „jah“-i.
    # Ilma olekuta kirje on ootel. „varasem“ = oli saidil enne kinnituskorda.
    koik_vaited = _loe(uu / "vaited.json")
    vaited = naidatavad_vaited(koik_vaited)
    for r in vaited:  # väide kuulub väljaandele: sulgudes nimed (ilma kuupäevata) jäävad välja
        r["kes"] = ilma_nimedeta(r.get("kes", ""))
    (SISU / "uudiste-vaited.json").write_text(json.dumps(vaited, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    shutil.copyfile(uu / "olek.json", SISU / "uudiste-olek.json")
    shutil.copyfile(uu / "koondajad.json", SISU / "koondajad.json")  # keda koondajad ise tööle otsivad
    if (uu / "avatus" / "ametiliigid-isco.json").exists():  # ametiliikide seos ISCO-ga (Kadri valik A 27.11.2026, Minu amet)
        shutil.copyfile(uu / "avatus" / "ametiliigid-isco.json", SISU / "ametiliigid-isco.json")
    if (uu / "toopakkumised.json").exists():  # tööportaalide kuulutuste arv ja jaotused (Kadri 7.11.2026)
        shutil.copyfile(uu / "toopakkumised.json", SISU / "toopakkumised.json")
    if (uu / "ai_tookuulutused.json").exists():  # tehisaru- ja andmetööde kuulutused (Kadri 8.11.2026)
        k = _loe(uu / "ai_tookuulutused.json")
        k.pop("nahtud_id", None)  # kogumise sisemine olek, saidil pole vaja
        _kirjuta("ai-tookuulutused.json", k)
    if (uu / "strateegiad.json").exists():  # riikide tehisarustrateegiad ja sihid (Kadri „jah kõik“ 12.11.2026)
        _kirjuta("strateegiad.json", strateegiad_saidile(_loe(uu / "strateegiad.json")))

    lisa_p = proj / "tooelu-leht-andmed" / "leiud-lisa.json"
    koik_uu = _loe(lisa_p).get("uuringud", []) if lisa_p.exists() else []
    _kirjuta("uuringud-lisa.json", kinnitatud_uuringud(koik_uu))
    ek_p = proj / "seire-uks-sait" / "ettekanded.json"
    ek = _loe(ek_p) if ek_p.exists() else {}
    _kirjuta("ettekanded.json", kinnitatud_ettekanded(ek))
    _kirjuta("ootel.json", {"uuringud": sum(1 for u in koik_uu if not u.get("seire_olek")),
                            "vaited": sum(1 for r in koik_vaited if not r.get("seire_olek")),
                            "ettekanded": sum(1 for r in ek.get("ettekanded", []) if not r.get("seire_olek"))})

    h = _loe(proj / "seire-uuendus" / "hanked" / "leht.json")
    for r in h["loend"]:
        if r.get("k") and len(r["k"]) > KIRJELDUS_MAX:
            r["k"] = r["k"][:KIRJELDUS_MAX].rstrip() + "…"
    h.get("hindamine", {}).pop("margenda_jargmiseks", None)
    h["seis"] = _loe(proj / "seire-uuendus" / "hanked" / "seis.json")
    _kirjuta("hanked-leht.json", h)

    an = proj / "tooelu-leht-andmed" / "analyys"
    meta = _loe(an / "osad.json")["meta"]
    _kirjuta("publikatsioonid.json", {
        "meta": {"aeg": meta["aeg"], "paring": meta["paring"], "teemad": meta["teemad"]},
        "aastad": _loe(an / "a_aastad.json"),
        "teemad": _loe(an / "a_teemad.json"),
        "tood": _loe(an / "a_tood.json"),
        "eesti_allikad": _loe(an / "a_eesti_allikad.json"),
        # Eesti tööde põhinumbrid, kontrollitud allika lehelt (Kadri MKUS-i kommentaar 7.11.2026 08:53)
        "eesti_kpi": _loe(an / "a_eesti_kpi.json") if (an / "a_eesti_kpi.json").exists() else None,
    })


if __name__ == "__main__":
    kaust = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("PROJEKTI_KAUST")
    if not kaust:
        sys.exit("Anna projekti kaust: python3 sait/vota_kaasa.py KAUST")
    vota(kaust)
    print("sisu/ uuendatud")
