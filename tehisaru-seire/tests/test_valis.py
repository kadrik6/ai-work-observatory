"""Välisallikate lahtipakkimise testid. Võrku ei kasutata. NB: numbrid on väljamõeldud testandmed.

Erand: test_valis_vaatlused_on_kataloogis loeb päris faile kataloog/vaatlused-valis.csv ja moodikud.csv.
"""

import csv
import io
import zipfile
from pathlib import Path

import pytest

from seire import valis

JUUR = Path(__file__).resolve().parent.parent


def test_sdmx_vaatlused_filtreerib_ja_teisendab_riigikoodid():
    tekst = ("DATAFLOW,REF_AREA,FREQ,MEASURE,TIME_PERIOD,OBS_VALUE,OBS_STATUS\n"
             "X,EST,A,G14_B,2025,23.4026,A\n"
             "X,EST,A,G15A_B,2025,9,A\n"
             "X,KOR,A,G14_B,2022,27.99,B\n"
             "X,GRC,A,G14_B,2025,10,A\n"
             "X,XXX,A,G14_B,2025,1,A\n"
             "X,GBR,A,G14_B,2025,,A\n")
    read = valis.sdmx_vaatlused(valis.sdmx_csv_ridadeks(tekst.encode()), {"MEASURE": "G14_B"})
    assert [(r["riik"], r["aasta"], r["vaartus"], r["margend"]) for r in read] == [
        ("EE", 2025, 23.4026, ""), ("EL", 2025, 10.0, ""), ("KR", 2022, 27.99, "B")]


def test_sdmx_vaatlused_annab_vea_kui_filter_valib_mitu_rida():
    tekst = "REF_AREA,TIME_PERIOD,OBS_VALUE,AGE\nEST,2025,1,Y16T74\nEST,2025,2,Y16T24\n"
    with pytest.raises(ValueError):
        valis.sdmx_vaatlused(valis.sdmx_csv_ridadeks(tekst))


def test_osakaal_arvutab_ainult_kui_koik_osad_olemas():
    tekst = ("REF_AREA,TIME_PERIOD,OC2,OBS_VALUE,OBS_STATUS\n"
             "EST,2024,T,700,\nEST,2024,25,28,\nEST,2024,35,7,\n"
             "FIN,2024,T,2600,\nFIN,2024,25,100,\n"  # 35 puudub -> ei arvutata
             "USA,2025,T,1000,B\nUSA,2025,25,30,B\nUSA,2025,35,10,B\n")
    read = valis.osakaal(valis.sdmx_csv_ridadeks(tekst), ["25", "35"], "T", "OC2")
    assert [(r["riik"], r["aasta"], round(r["vaartus"], 2), r["margend"]) for r in read] == [
        ("EE", 2024, 5.0, ""), ("US", 2025, 4.0, "B")]


def test_ilo_uuendatud():
    xml = ("<common:AnnotationTitle>25/10/2026 09:29:51</common:AnnotationTitle>\n"
           "            <common:AnnotationType>LAST_UPDATE</common:AnnotationType>")
    assert valis.ilo_uuendatud(xml) == "2026-10-25"
    assert valis.ilo_uuendatud("<x/>") == ""


def test_pxweb_vaatlused_jsonstat2():
    andmed = {"id": ["Tid", "ContentsCode"], "size": [3, 1],
              "dimension": {"Tid": {"category": {"index": {"2024": 0, "2025": 1, "2026": 2}}},
                            "ContentsCode": {"category": {"index": {"X": 0}}}},
              "value": [38, None, 71]}
    read = valis.pxweb_vaatlused(andmed, "Tid", "NO")
    assert [(r["aasta"], r["vaartus"]) for r in read] == [(2024, 38.0), (2026, 71.0)]


def test_dst_vaatlused():
    tekst = "﻿VIRKSTRRDA;ANVEND;TID;INDHOLD\n1010;1680;2025;42\n1010;1680;2026;59\n1010;1680;2027;..\n"
    read = valis.dst_vaatlused(tekst.encode("utf-8"))
    assert [(r["riik"], r["aasta"], r["vaartus"]) for r in read] == [("DK", 2025, 42.0), ("DK", 2026, 59.0)]


def test_cbs_aastatabelid_ja_vaartus():
    kataloog = {"value": [
        {"Identifier": "86118NED", "Title": "ICT-gebruik bij bedrijven; bedrijfsgrootte, 2025", "Modified": "2025-12-12T06:30:00"},
        {"Identifier": "86117NED", "Title": "ICT-gebruik bij kleine bedrijven; bedrijfsgrootte, 2025", "Modified": ""},
        {"Identifier": "86119NED", "Title": "ICT-gebruik bij bedrijven; bedrijfstak en bedrijfsgrootte, 2025", "Modified": ""},
    ]}
    assert valis.cbs_aastatabelid(kataloog, "ICT-gebruik bij bedrijven; bedrijfsgrootte") == {2025: ("86118NED", "2025-12-12")}
    andmed = {"value": [{"Bedrijfsgrootte": "WP19089   ", "AIGebruikt_53": 20},
                        {"Bedrijfsgrootte": "WP19088   ", "AIGebruikt_53": 33}]}
    assert valis.cbs_vaartus(andmed, "AIGebruikt_", {"Bedrijfsgrootte": "WP19088"}) == 33
    with pytest.raises(ValueError):
        valis.cbs_vaartus(andmed, "Puudub_", {"Bedrijfsgrootte": "WP19088"})


def test_statcan_vaatlused():
    vastus = [{"status": "SUCCESS", "object": {"productId": 33101167, "vectorId": 1, "vectorDataPoint": [
        {"refPer": "2026-01-01", "value": 19.2, "releaseTime": "2026-05-27T08:30"}]}}]
    r = valis.statcan_vaatlused(vastus)[0]
    assert (r["riik"], r["aasta"], r["vaartus"], r["avaldatud"]) == ("CA", 2026, 19.2, "2026-05-27")
    with pytest.raises(ValueError):
        valis.statcan_vaatlused([{"status": "FAILED", "object": "x"}])


def test_bics_failid_kuupaevad():
    html = ('<div class="meta__term">Release date:</div> <div>22 October 2026</div>'
            '<a href="/file?uri=/x/bicswave166/a.xlsx">'
            '<h3>BICS Wave 165 edition of this dataset 8 October 2026 </h3><a href="/file?uri=/x/bicswave165/b.xlsx">')
    assert valis.bics_failid(html) == [("https://www.ons.gov.uk/file?uri=/x/bicswave166/a.xlsx", "2026-10-22"),
                                       ("https://www.ons.gov.uk/file?uri=/x/bicswave165/b.xlsx", "2026-10-08")]


def _xlsx(lehed):
    """Väike xlsx mälus: {lehe nimi: [[lahtrid]]}. Tekst jagatud stringidena, arvud otse."""
    jagatud, raamat, seosed = [], [], []
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w") as z:
        for i, (nimi, read) in enumerate(lehed.items(), 1):
            raamat.append(f'<sheet name="{nimi}" sheetId="{i}" r:id="rId{i}"/>')
            seosed.append(f'<Relationship Id="rId{i}" Target="worksheets/sheet{i}.xml" Type="x"/>')
            xml_read = []
            for ri, rida in enumerate(read, 1):
                lahtrid = []
                for ci, v in enumerate(rida):
                    ref = f"{chr(65 + ci)}{ri}"
                    if v == "":
                        continue  # tühi lahter puudub failist, nagu Excelis
                    if isinstance(v, str):
                        jagatud.append(v)
                        lahtrid.append(f'<c r="{ref}" t="s"><v>{len(jagatud) - 1}</v></c>')
                    else:
                        lahtrid.append(f'<c r="{ref}"><v>{v}</v></c>')
                xml_read.append(f'<row r="{ri}">{"".join(lahtrid)}</row>')
            z.writestr(f"xl/worksheets/sheet{i}.xml",
                       f'<worksheet xmlns="{valis._X[1:-1]}"><sheetData>{"".join(xml_read)}</sheetData></worksheet>')
        z.writestr("xl/workbook.xml", f'<workbook xmlns="{valis._X[1:-1]}" xmlns:r="{valis._R[1:-1]}"><sheets>'
                                      f'{"".join(raamat)}</sheets></workbook>')
        z.writestr("xl/_rels/workbook.xml.rels", '<Relationships xmlns="http://schemas.openxmlformats.org/package/'
                                                 f'2006/relationships">{"".join(seosed)}</Relationships>')
        z.writestr("xl/sharedStrings.xml", f'<sst xmlns="{valis._X[1:-1]}">'
                                           + "".join(f"<si><t>{s}</t></si>" for s in jagatud) + "</sst>")
    return b.getvalue()


def test_xlsx_ja_bics_arvutus():
    leht = [
        ["Question: ..."],
        ["Dates", "Wave", "Industry/Size Band", "Robotics", "Not sure", "Business does not currently use artificial intelligence technologies"],
        ["21 September 2026 to 4 October 2026", "Wave 165", "All size bands excluding 0 - 9", 0.01, 0.111, 0.508],
        ["21 September 2026 to 4 October 2026", "Wave 165", "All businesses", 0.01, 0.062, 0.641],
        ["15 June 2026 to 28 June 2026", "Wave 159", "All size bands excluding 0 - 9", "", 0.1, 0.6],
        ["11 December 2023 to 24 December 2023", "Wave 98", "All size bands excluding 0 - 9", 0.01, "[c]", 0.8],
    ]
    sisu = _xlsx({"Muu": [["x"]], valis.BICS_LEHT_AI: leht})
    assert valis.xlsx_leht(sisu, "Puudub") is None
    read = valis.xlsx_leht(sisu, valis.BICS_LEHT_AI)
    assert read[4][3] == ""  # tühi lahter jääb oma kohale
    lained = valis.bics_vaatlused(read)
    assert [(l["laine"], round(l["vaartus"], 1)) for l in lained] == [("Wave 165", 38.1), ("Wave 159", 30.0)]
    aastad = valis.bics_aastate_kaupa(lained)
    assert [(r["aasta"], round(r["vaartus"], 1)) for r in aastad] == [(2026, 38.1)]


def test_valis_vaatlused_on_kataloogis():
    """Iga vaatlused-valis.csv mõõdik peab olema moodikud.csv-s ja iga laadija mõõdik samuti."""
    k = JUUR / "kataloog"
    with open(k / "moodikud.csv", encoding="utf-8") as f:
        moodikud = {r["id"] for r in csv.DictReader(f)}
    with open(k / "vaatlused-valis.csv", encoding="utf-8") as f:
        vaatlused = {r["moodik"] for r in csv.DictReader(f)}
    assert vaatlused <= moodikud
    import importlib.util
    spec = importlib.util.spec_from_file_location("lae_valis", k / "lae_valis.py")
    lae_valis = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(lae_valis)
    assert set(lae_valis.MOODIKUD) <= moodikud
    assert lae_valis.arv(4.7) == "4.7" and lae_valis.arv(59.0) == "59" and lae_valis.arv(23.40261) == "23.4026"
    assert {m for m, _ in lae_valis.AVALDATUD} <= set(lae_valis.MOODIKUD)


def test_uis_vaatlused_ja_uuendatud():
    vastus = {"records": [{"indicatorId": "X", "geoUnit": "EST", "year": 2023, "value": 1.83878, "qualifier": None},
                          {"indicatorId": "X", "geoUnit": "USA", "year": 2023, "value": None, "qualifier": None},
                          {"indicatorId": "X", "geoUnit": "WLD", "year": 2023, "value": 2.0, "qualifier": None}]}
    assert [(r["riik"], r["aasta"], r["vaartus"]) for r in valis.uis_vaatlused(vastus)] == [("EE", 2023, 1.83878)]
    versioonid = [{"publicationDate": "2025-09-01", "themeDataStatus": [{"theme": "EDUCATION", "lastUpdate": "09/01/2025"}]},
                  {"publicationDate": "2026-05-08", "themeDataStatus": [{"theme": "EDUCATION", "lastUpdate": "02/09/2026"}]}]
    assert valis.uis_uuendatud(versioonid, "EDUCATION") == "2026-02-09"
    assert valis.uis_uuendatud(versioonid, "CULTURE") == ""


def test_uksiku_allika_viga_ei_kukuta_sammu():
    import importlib.util
    k = Path(__file__).resolve().parents[1] / "kataloog"
    spec = importlib.util.spec_from_file_location("lae_valis", k / "lae_valis.py")
    lae_valis = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(lae_valis)
    ok, viga = {"olek": "ok", "viga": ""}, {"olek": "viga", "viga": "HTTP 403"}
    assert lae_valis.lopukood(["a", "b"], {"a": ok, "b": viga}) == 0
    assert lae_valis.lopukood(["a", "b"], {"a": ok, "b": ok}) == 0
    assert lae_valis.lopukood(["a", "b"], {"a": viga, "b": viga}) == 1
