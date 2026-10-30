"""Valdkonna ülevaade OpenAlexist: kui palju uuritakse, mis teemad kasvavad, mida tsiteeritakse, kes avaldab.

    python tooelu-seire/analyys.py --valjund valjund

Kasutab sama päringut nagu koguja (tehisaru JA tööturg pealkirjas). Loeb ainult OpenAlexi koondarve ja
enim tsiteeritud töid; repo faile, avaldatud lehti ega prognoose ei muuda.

Piirid:
    Tsitaadid on ainoke vaba populaarsuse mõõt. Klikke ega allalaadimisi OpenAlex ei avalda.
    Värske töö on vähe tsiteeritud lihtsalt sellepärast, et ta on värske.
    Jooksva aasta arv on poolik ja OpenAlex indekseerib töid hilinemisega.
    Liik "article" ei tähenda, et töö on eelretsenseeritud.

Väljund: valjund/analyys.json ja iga osa rida logis kujul "ANALYYS <osa> {json}".
Väljumiskood on 0, kui vähemalt üks osa õnnestus.
"""

import argparse
import datetime as dt
import json
import os
import sys
import time
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kogujad import allikad, yhine  # noqa: E402

PARING = allikad.OPENALEX_PARING
LIIGID = "type:article|preprint|report"
# Lai päring pealkirjast ja kokkuvõttest. Kasutame Eesti ja uusimate tööde jaoks, kus pealkirja päring jätab
# liiga palju välja (30.10: Eesti kohta leidis pealkirja päring vaid 4 tööd).
PARING_LAI = ('("artificial intelligence" OR "generative AI" OR "large language model" OR ChatGPT OR automation '
              'OR "machine learning" OR robots) AND ("labor market" OR "labour market" OR employment OR jobs '
              'OR workforce OR workers OR skills OR wages OR occupations OR "future of work") '
              'AND NOT ("job shop" OR scheduling)')
# Eestikeelsed tööd: OpenAlexi tüvestamine on inglise keele oma, seepärast mitu sõnavormi.
PARING_ET = ('(tehisintellekt OR tehisintellekti OR tehisaru OR masinõpe OR automatiseerimine OR "suur keelemudel") AND '
             '(tööturg OR tööturu OR tööturul OR töötajad OR töötajate OR tööjõud OR tööjõu OR oskused OR oskuste '
             'OR töökohad OR töökohtade OR töö)')
EESTI = "authorships.countries:EE"
LIIGID_LAI = "type:article|preprint|report|dissertation|book-chapter|book"

# Viis hüpoteeside suunda (kirjeldused/tooelu-observatoorium-arhitektuur.md) ja generatiivne tehisaru eraldi.
TEEMAD = {
    "kadu": ("Töökohtade kadu", '"job loss" OR displacement OR unemployment OR layoffs'),
    "varbamine": ("Värbamine ja vabad töökohad", 'hiring OR recruitment OR vacancies OR "job postings"'),
    "umberkorraldus": ("Töö ja organisatsiooni ümberkorraldus", 'tasks OR organizational OR organisational '
                       'OR restructuring OR management'),
    "majandus": ("Majanduslik mõju", 'productivity OR growth OR "economic impact"'),
    "tootajad": ("Töötajate olukord", 'wages OR inequality OR skills OR reskilling OR "well-being"'),
    "genai": ("Generatiivne tehisaru", '"generative AI" OR ChatGPT OR "large language model" OR LLM'),
}


def url(filt, **param):
    param = {"filter": filt, **param}
    if os.environ.get("OPENALEX_API_KEY"):
        param["api_key"] = os.environ["OPENALEX_API_KEY"]
    return allikad.OPENALEX_URL + "?" + urllib.parse.urlencode(param)


def paring(teema=None):
    return f"({PARING}) AND ({teema})" if teema else PARING


def grupid(sisu, mitu=None):
    rida = [{"voti": str(g.get("key", "")).rsplit("/", 1)[-1], "nimi": g.get("key_display_name") or g.get("key"),
             "arv": g.get("count", 0)} for g in json.loads(sisu).get("group_by", [])]
    rida = [r for r in rida if r["nimi"] not in (None, "", "unknown")]
    return rida[:mitu] if mitu else rida


def arv(sisu):
    return json.loads(sisu).get("meta", {}).get("count", 0)


def tood(sisu):
    tulem = []
    for t in json.loads(sisu).get("results", []):
        koht = t.get("primary_location") or {}
        allikas = koht.get("source") or {}
        tulem.append({
            "voti": str(t.get("id", "")).rsplit("/", 1)[-1],
            "pealkiri": " ".join((t.get("display_name") or "").split()),
            "avaldatud": t.get("publication_date"),
            "viiteid": t.get("cited_by_count", 0),
            "liik": t.get("type"),
            "doi": (t.get("doi") or "").removeprefix("https://doi.org/") or None,
            "kanal": allikas.get("display_name"),
            "kanali_liik": allikas.get("type"),
            "url": t.get("doi") or koht.get("landing_page_url") or t.get("id"),
            "tagasi_voetud": bool(t.get("is_retracted")),
        })
    return tulem


def osad(tana):
    """Iga osa: nimi -> (url, töötleja). Ajavahemikud on arvutatud tänase kuupäeva järgi."""
    aasta = tana.year
    aasta_tagasi = (tana - dt.timedelta(days=365)).isoformat()
    alates = f"{aasta - 3}-01-01"
    valik = "id,display_name,publication_date,cited_by_count,type,doi,primary_location,is_retracted"
    tulem = {"aastad": (url(f"title.search:{PARING},publication_year:{aasta - 10}-{aasta},{LIIGID}",
                            group_by="publication_year"), grupid)}
    for voti, (_, teema) in TEEMAD.items():
        tulem[f"teema_{voti}"] = (url(f"title.search:{paring(teema)},publication_year:{aasta - 6}-{aasta},{LIIGID}",
                                      group_by="publication_year"), grupid)
    tulem.update({
        "enim_tsiteeritud": (url(f"title.search:{PARING},from_publication_date:{alates},{LIIGID}",
                                 sort="cited_by_count:desc", select=valik, **{"per-page": 25}), tood),
        "enim_tsiteeritud_aasta": (url(f"title.search:{PARING},from_publication_date:{aasta_tagasi},{LIIGID}",
                                       sort="cited_by_count:desc", select=valik, **{"per-page": 25}), tood),
        "liigid": (url(f"title.search:{PARING},from_publication_date:{alates},{LIIGID}", group_by="type"), grupid),
        "kanali_liigid": (url(f"title.search:{PARING},from_publication_date:{alates},{LIIGID}",
                              group_by="primary_location.source.type"), grupid),
        "kanalid": (url(f"title.search:{PARING},from_publication_date:{alates},{LIIGID}",
                        group_by="primary_location.source.id"), lambda s: grupid(s, 15)),
        "asutused": (url(f"title.search:{PARING},from_publication_date:{alates},{LIIGID}",
                         group_by="authorships.institutions.lineage"), lambda s: grupid(s, 15)),
        "riigid": (url(f"title.search:{PARING},from_publication_date:{alates},{LIIGID}",
                       group_by="authorships.countries"), lambda s: grupid(s, 20)),
        # CWTS Leideni "core" kanal: rahvusvaheliselt nähtav teadusajakiri. Usaldusväärsuse jämedad lähendid.
        "tuumkanal": (url(f"title.search:{PARING},from_publication_date:{alates},{LIIGID}",
                          group_by="primary_location.source.is_core"), grupid),
        "enim_tsiteeritud_tuum": (url(f"title.search:{PARING},from_publication_date:{alates},{LIIGID},"
                                      "primary_location.source.is_core:true",
                                      sort="cited_by_count:desc", select=valik, **{"per-page": 15}), tood),
        "avatud": (url(f"title.search:{PARING},from_publication_date:{alates},{LIIGID}",
                       group_by="open_access.is_oa"), grupid),
        "tagasi_voetud": (url(f"title.search:{PARING},from_publication_date:{alates},{LIIGID},is_retracted:true",
                              **{"per-page": 1}), arv),
        # Vähemalt aasta vana töö ilma ühegi viiteta: mida keegi pole kasutanud.
        "vanad_koik": (url(f"title.search:{PARING},from_publication_date:{alates},"
                           f"to_publication_date:{aasta_tagasi},{LIIGID}", **{"per-page": 1}), arv),
        "vanad_viiteta": (url(f"title.search:{PARING},from_publication_date:{alates},"
                              f"to_publication_date:{aasta_tagasi},{LIIGID},cited_by_count:0", **{"per-page": 1}), arv),
        "eesti": (url(f"title.search:{PARING},abstract.search:Estonia OR Estonian,{LIIGID}",
                      sort="cited_by_count:desc", select=valik, **{"per-page": 10}), tood),
        # Uusimad: viimase 60 päeva tööd avaldamise järjekorras (pealkirja päring, et jääks teema juurde).
        "uusimad": (url(f"title.search:{PARING},from_publication_date:{(tana - dt.timedelta(days=60)).isoformat()},"
                        f"to_publication_date:{tana.isoformat()},{LIIGID}",
                        sort="publication_date:desc", select=valik, **{"per-page": 50}), tood),
        "lai_aastad": (url(f"title_and_abstract.search:{PARING_LAI},publication_year:{aasta - 10}-{aasta},{LIIGID}",
                           group_by="publication_year"), grupid),
        # Eesti kolmel moel: Eesti autorid, Eesti mainimine kokkuvõttes, eestikeelsed tööd.
        "eesti_autorid_aastad": (url(f"title_and_abstract.search:{PARING_LAI},{EESTI},{LIIGID_LAI}",
                                     group_by="publication_year"), grupid),
        "eesti_autorid_liigid": (url(f"title_and_abstract.search:{PARING_LAI},{EESTI},{LIIGID_LAI}",
                                     group_by="type"), grupid),
        "eesti_autorid_asutused": (url(f"title_and_abstract.search:{PARING_LAI},{EESTI},{LIIGID_LAI}",
                                       group_by="authorships.institutions.lineage"), lambda s: grupid(s, 15)),
        "eesti_autorid_uusimad": (url(f"title_and_abstract.search:{PARING_LAI},{EESTI},{LIIGID_LAI},"
                                      f"to_publication_date:{tana.isoformat()}",
                                      sort="publication_date:desc", select=valik, **{"per-page": 50}), tood),
        "eesti_autorid_tsiteeritud": (url(f"title_and_abstract.search:{PARING_LAI},{EESTI},{LIIGID_LAI}",
                                          sort="cited_by_count:desc", select=valik, **{"per-page": 25}), tood),
        "eesti_mainitud_aastad": (url(f"title_and_abstract.search:({PARING_LAI}) AND (Estonia OR Estonian),{LIIGID_LAI}",
                                      group_by="publication_year"), grupid),
        "eesti_mainitud_uusimad": (url(f"title_and_abstract.search:({PARING_LAI}) AND (Estonia OR Estonian),{LIIGID_LAI},"
                                       f"to_publication_date:{tana.isoformat()}",
                                       sort="publication_date:desc", select=valik, **{"per-page": 50}), tood),
        "eesti_keeles_aastad": (url(f"title_and_abstract.search:{PARING_ET},language:et",
                                    group_by="publication_year"), grupid),
        "eesti_keeles": (url(f"title_and_abstract.search:{PARING_ET},language:et",
                             sort="publication_date:desc", select=valik, **{"per-page": 50}), tood),
    })
    return tulem


def kaivita(valjund, hae=None, tana=None, paus=1.0):
    hae = hae or yhine.hae
    tana = tana or dt.date.today()
    valjund = Path(valjund)
    valjund.mkdir(parents=True, exist_ok=True)
    tulem = {"aeg": yhine.nuud(), "paring": PARING, "teemad": {k: v[0] for k, v in TEEMAD.items()},
             "osad": {}, "vead": {}}
    for nimi, (aadress, tootle) in osad(tana).items():
        try:
            tulem["osad"][nimi] = tootle(hae(aadress))
        except (yhine.KogujaViga, ValueError, KeyError) as e:
            tulem["vead"][nimi] = str(e)
        if paus:
            time.sleep(paus)
    (valjund / "analyys.json").write_text(json.dumps(tulem, ensure_ascii=False, indent=1), encoding="utf-8")
    return tulem


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--valjund", required=True)
    a = p.parse_args(argv)
    tulem = kaivita(a.valjund)
    print("ANALYYS meta " + json.dumps({k: tulem[k] for k in ("aeg", "paring", "teemad", "vead")}, ensure_ascii=False))
    for nimi, sisu in tulem["osad"].items():
        print(f"ANALYYS {nimi} " + json.dumps(sisu, ensure_ascii=False))
    for nimi, viga in tulem["vead"].items():
        print(f"VIGA {nimi}: {viga}", file=sys.stderr)
    return 0 if tulem["osad"] else 1


if __name__ == "__main__":
    sys.exit(main())
