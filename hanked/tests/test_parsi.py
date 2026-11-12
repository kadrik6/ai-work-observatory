"""Parseri testid sünteetiliste (väljamõeldud) teadetega. Struktuur järgib registri avaandmeid (4.11.2026)."""
from parsi import parsi_fail

NS = ('xmlns="urn:oasis:names:specification:ubl:schema:xsd:ContractNotice-2" '
      'xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2" '
      'xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2" '
      'xmlns:efac="http://data.europa.eu/p27/eforms-ubl-extension-aggregate-components/1" '
      'xmlns:efbc="http://data.europa.eu/p27/eforms-ubl-extension-basic-components/1" '
      'xmlns:efext="http://data.europa.eu/p27/eforms-ubl-extensions/1" '
      'xmlns:ext="urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2"')

CN = f"""<?xml version="1.0" encoding="UTF-8"?><OPEN-DATA><ContractNotice {NS}>
<ext:UBLExtensions><ext:UBLExtension><ext:ExtensionContent><efext:EformsExtension>
<efac:NoticeSubType><cbc:SubTypeCode listName="notice-subtype">16</cbc:SubTypeCode></efac:NoticeSubType>
<efac:Organizations><efac:Organization><efac:Company>
<cac:PartyIdentification><cbc:ID schemeName="organization">ORG-0001</cbc:ID></cac:PartyIdentification>
<cac:PartyName><cbc:Name languageID="EST">Näidisamet</cbc:Name></cac:PartyName>
<cac:PartyLegalEntity><cbc:CompanyID>70000000</cbc:CompanyID></cac:PartyLegalEntity>
</efac:Company></efac:Organization></efac:Organizations>
</efext:EformsExtension></ext:ExtensionContent></ext:UBLExtension></ext:UBLExtensions>
<cbc:ID schemeName="notice-id">n-1</cbc:ID><cbc:IssueDate>2024-03-05+02:00</cbc:IssueDate><cbc:VersionID>01</cbc:VersionID>
<cac:ContractingParty><cac:ContractingPartyType><cbc:PartyTypeCode listName="buyer-legal-type">cga</cbc:PartyTypeCode></cac:ContractingPartyType>
<cac:Party><cac:PartyIdentification><cbc:ID schemeName="organization">ORG-0001</cbc:ID></cac:PartyIdentification></cac:Party></cac:ContractingParty>
<cac:TenderingTerms><cac:TendererQualificationRequest><cac:SpecificTendererRequirement><cbc:Description languageID="EST">https://riigihanked.riik.ee/rhr-web/#/procurement/6900001/procurement-passport</cbc:Description></cac:SpecificTendererRequirement></cac:TendererQualificationRequest></cac:TenderingTerms>
<cac:TenderingProcess><cbc:Description languageID="EST">Avatud hankemenetlus</cbc:Description><cbc:ProcedureCode listName="procurement-procedure-type">open</cbc:ProcedureCode></cac:TenderingProcess>
<cac:ProcurementProject><cbc:ID>270001</cbc:ID><cbc:Name languageID="EST">Tehisintellektil põhinev kõnetuvastus</cbc:Name>
<cbc:Description languageID="EST">Kõnest teksti teenuse arendus.</cbc:Description>
<cbc:ProcurementTypeCode listName="contract-nature">services</cbc:ProcurementTypeCode>
<cac:RequestedTenderTotal><cbc:EstimatedOverallContractAmount currencyID="EUR">120000.00</cbc:EstimatedOverallContractAmount></cac:RequestedTenderTotal>
<cac:MainCommodityClassification><cbc:ItemClassificationCode listName="cpv">72212000</cbc:ItemClassificationCode></cac:MainCommodityClassification>
</cac:ProcurementProject>
<cac:ProcurementProjectLot><cbc:ID schemeName="Lot">LOT-0001</cbc:ID>
<cac:TenderingTerms><cac:AwardingTerms><cac:AwardingCriterion>
<cac:SubordinateAwardingCriterion><ext:UBLExtensions><ext:UBLExtension><ext:ExtensionContent><efext:EformsExtension>
<efac:AwardCriterionParameter><efbc:ParameterCode listName="number-weight">per-exa</efbc:ParameterCode><efbc:ParameterNumeric>60</efbc:ParameterNumeric></efac:AwardCriterionParameter>
</efext:EformsExtension></ext:ExtensionContent></ext:UBLExtension></ext:UBLExtensions>
<cbc:AwardingCriterionTypeCode listName="award-criterion-type">price</cbc:AwardingCriterionTypeCode></cac:SubordinateAwardingCriterion>
<cac:SubordinateAwardingCriterion><ext:UBLExtensions><ext:UBLExtension><ext:ExtensionContent><efext:EformsExtension>
<efac:AwardCriterionParameter><efbc:ParameterCode listName="number-weight">per-exa</efbc:ParameterCode><efbc:ParameterNumeric>40</efbc:ParameterNumeric></efac:AwardCriterionParameter>
</efext:EformsExtension></ext:ExtensionContent></ext:UBLExtension></ext:UBLExtensions>
<cbc:AwardingCriterionTypeCode listName="award-criterion-type">quality</cbc:AwardingCriterionTypeCode></cac:SubordinateAwardingCriterion>
</cac:AwardingCriterion></cac:AwardingTerms></cac:TenderingTerms>
<cac:ProcurementProject><cbc:Name languageID="EST">Osa 1: kõnetuvastuse mudel</cbc:Name>
<cac:ProcurementAdditionalType><cbc:ProcurementTypeCode listName="strategic-procurement">inn-pur</cbc:ProcurementTypeCode></cac:ProcurementAdditionalType>
<cac:MainCommodityClassification><cbc:ItemClassificationCode listName="cpv">72212000</cbc:ItemClassificationCode></cac:MainCommodityClassification>
</cac:ProcurementProject></cac:ProcurementProjectLot>
</ContractNotice></OPEN-DATA>"""

TED = """<?xml version="1.0" encoding="UTF-8"?><OPEN-DATA><TED_ESENDERS xmlns="http://publications.europa.eu/resource/schema/ted/R2.0.9/reception">
<FORM_SECTION><F02_2014><CONTRACTING_BODY><ADDRESS_CONTRACTING_BODY><OFFICIALNAME>Näidisvald</OFFICIALNAME><NATIONALID>75000000</NATIONALID></ADDRESS_CONTRACTING_BODY></CONTRACTING_BODY>
<OBJECT_CONTRACT><TITLE><P>Andmelao arendus</P></TITLE><REFERENCE_NUMBER>190001</REFERENCE_NUMBER>
<CPV_MAIN><CPV_CODE CODE="72000000"/></CPV_MAIN><TYPE_CONTRACT CTYPE="SERVICES"/><SHORT_DESCR><P>Analüütika.</P></SHORT_DESCR>
<OBJECT_DESCR><SHORT_DESCR><P>Osa kirjeldus</P></SHORT_DESCR><AC><AC_QUALITY><AC_CRITERION>Kvaliteet</AC_CRITERION><AC_WEIGHTING>30</AC_WEIGHTING></AC_QUALITY><AC_PRICE><AC_WEIGHTING>70</AC_WEIGHTING></AC_PRICE></AC></OBJECT_DESCR>
</OBJECT_CONTRACT><PROCEDURE><PT_OPEN/></PROCEDURE></F02_2014><NOTICE_UUID>u-1</NOTICE_UUID></FORM_SECTION></TED_ESENDERS>
<TED_ESENDERS xmlns="http://publications.europa.eu/resource/schema/ted/R2.0.9/reception"><FORM_SECTION><F03_2014>
<OBJECT_CONTRACT><TITLE><P>Andmelao arendus</P></TITLE><REFERENCE_NUMBER>190001</REFERENCE_NUMBER></OBJECT_CONTRACT>
<AWARD_CONTRACT><AWARDED_CONTRACT><TENDERS><NB_TENDERS_RECEIVED>3</NB_TENDERS_RECEIVED></TENDERS>
<CONTRACTORS><CONTRACTOR><ADDRESS_CONTRACTOR><OFFICIALNAME>Näide OÜ</OFFICIALNAME></ADDRESS_CONTRACTOR></CONTRACTOR></CONTRACTORS>
<VALUES><VAL_TOTAL>50000</VAL_TOTAL></VALUES></AWARDED_CONTRACT></AWARD_CONTRACT></F03_2014></FORM_SECTION></TED_ESENDERS>
<TED_ESENDERS xmlns="http://publications.europa.eu/resource/schema/ted/R2.0.9/reception"><FORM_SECTION><F14_2014/></FORM_SECTION></TED_ESENDERS>
</OPEN-DATA>"""


def test_eforms_hanketeade():
    cn, can, vahele = parsi_fail(CN.encode(), "2024-03")
    assert vahele == 0 and not can and len(cn) == 1
    r = cn[0]
    assert r["viitenumber"] == "270001" and r["rhr_id"] == "6900001"
    assert r["pealkiri"].startswith("Tehisintellektil") and r["hankija"] == "Näidisamet"
    assert r["hankija_kood"] == "70000000" and r["hankija_liik"] == "cga"
    assert r["kuupaev"] == "2024-03-05" and r["alamtyyp"] == "16"
    assert r["cpv"] == ["72212000"] and r["eeldatav_maksumus"] == 120000.0
    assert r["kriteeriumid"] == [("price", 60.0), ("quality", 40.0)]
    assert r["strateegiline"] == ["inn-pur"] and r["osade_nimed"] == ["Osa 1: kõnetuvastuse mudel"]


def test_ted_vana_vorming():
    cn, can, vahele = parsi_fail(TED.encode(), "2019-05")
    assert vahele == 1  # F14 (parandusteade) jäetakse vahele
    assert len(cn) == 1 and len(can) == 1
    assert cn[0]["pealkiri"] == "Andmelao arendus" and cn[0]["viitenumber"] == "190001"
    assert cn[0]["kriteeriumid"] == [("quality", 30.0), ("price", 70.0)]
    assert cn[0]["liik"] == "services" and cn[0]["menetlus"] == "PT_OPEN"
    assert can[0]["pakkumusi"] == 3 and can[0]["voitjad"] == ["Näide OÜ"] and can[0]["lepingu_summa"] == 50000


def test_ted_vorm_ei_ole_esimene_laps():
    """Päris failides võib FORM_SECTION-i esimene laps olla muu element; vorm leitakse nime järgi."""
    sisu = TED.replace("<FORM_SECTION><F02_2014>", "<FORM_SECTION><NOTICE_UUID>u-0</NOTICE_UUID><F02_2014>", 1)
    cn, can, vahele = parsi_fail(sisu.encode(), "2019-05")
    assert len(cn) == 1 and cn[0]["pealkiri"] == "Andmelao arendus"


CAN = f"""<?xml version="1.0" encoding="UTF-8"?><OPEN-DATA><ContractAwardNotice {NS.replace('ContractNotice-2', 'ContractAwardNotice-2')}>
<ext:UBLExtensions><ext:UBLExtension><ext:ExtensionContent><efext:EformsExtension><efac:NoticeResult>
<efac:LotResult><cbc:TenderResultCode listName="winner-selection-status">selec-w</cbc:TenderResultCode>
<efac:ReceivedSubmissionsStatistics><efbc:StatisticsCode listName="received-submission-type">tenders</efbc:StatisticsCode><efbc:StatisticsNumeric>1</efbc:StatisticsNumeric></efac:ReceivedSubmissionsStatistics>
<efac:TenderLot><cbc:ID schemeName="Lot">LOT-0001</cbc:ID></efac:TenderLot></efac:LotResult>
<efac:LotResult><cbc:TenderResultCode listName="winner-selection-status">selec-w</cbc:TenderResultCode>
<efac:ReceivedSubmissionsStatistics><efbc:StatisticsCode listName="received-submission-type">tenders</efbc:StatisticsCode><efbc:StatisticsNumeric>4</efbc:StatisticsNumeric></efac:ReceivedSubmissionsStatistics>
<efac:TenderLot><cbc:ID schemeName="Lot">LOT-0002</cbc:ID></efac:TenderLot></efac:LotResult>
</efac:NoticeResult></efext:EformsExtension></ext:ExtensionContent></ext:UBLExtension></ext:UBLExtensions>
<cbc:ID schemeName="notice-id">a-1</cbc:ID><cbc:IssueDate>2025-05-05+02:00</cbc:IssueDate>
<cac:ProcurementProject><cbc:ID>270001</cbc:ID></cac:ProcurementProject>
</ContractAwardNotice></OPEN-DATA>"""


def test_eforms_osade_pakkumused():
    """Hanke tase võtab suurima osa pakkumuste arvu; osade tase hoiab iga osa eraldi."""
    cn, can, vahele = parsi_fail(CAN.encode(), "2025-05")
    assert vahele == 0 and len(can) == 1
    assert can[0]["pakkumusi"] == 4
    assert can[0]["osade_pakkumusi"] == {"LOT-0001": 1, "LOT-0002": 4}


def test_ted_osade_pakkumused():
    teine = ("<AWARD_CONTRACT><LOT_NO>2</LOT_NO><AWARDED_CONTRACT><TENDERS><NB_TENDERS_RECEIVED>1</NB_TENDERS_RECEIVED>"
             "</TENDERS></AWARDED_CONTRACT></AWARD_CONTRACT></F03_2014>")
    sisu = TED.replace("<AWARD_CONTRACT><AWARDED", "<AWARD_CONTRACT><LOT_NO>1</LOT_NO><AWARDED", 1).replace("</F03_2014>", teine, 1)
    cn, can, vahele = parsi_fail(sisu.encode(), "2019-05")
    assert can[0]["pakkumusi"] == 3 and can[0]["osade_pakkumusi"] == {"1": 3, "2": 1}


def test_osade_koond():
    from lae import osade_koond
    rid = [{"aasta": 2025, "allikas": "eforms", "osade_arv": 2, "pakkumusi": 4, "osade_pakkumusi": {"A": 1, "B": 4}},
           {"aasta": 2025, "allikas": "eforms", "osade_arv": 1, "pakkumusi": 1, "osade_pakkumusi": {"A": 1}},
           {"aasta": 2025, "allikas": "eforms", "osade_arv": 1, "pakkumusi": None, "osade_pakkumusi": {}}]
    c = osade_koond(rid)[(2025, "eforms")]
    assert c["hankeid"] == 3 and c["mitme_osaga"] == 1 and c["osi"] == 4
    assert c["osi_pakkumustega"] == 3 and c["osi_1_pakkumus"] == 2
    assert c["hankeid_pakkumustega"] == 2 and c["hankeid_1_pakkumus"] == 1


def test_eforms_osade_info():
    """Hanketeate iga osa: tunnus, CPV, eeldatav maksumus, kriteeriumid ja pakkumuste esitamise tähtaeg."""
    osa = ('<cac:TenderingProcess><cac:TenderSubmissionDeadlinePeriod><cbc:EndDate>2024-04-04+03:00</cbc:EndDate>'
           '</cac:TenderSubmissionDeadlinePeriod></cac:TenderingProcess>'
           '<cac:ProcurementProject><cbc:Name languageID="EST">Osa 1')
    lisa = ('<cac:RequestedTenderTotal><cbc:EstimatedOverallContractAmount currencyID="EUR">80000</cbc:EstimatedOverallContractAmount>'
            '</cac:RequestedTenderTotal><cac:MainCommodityClassification><cbc:ItemClassificationCode listName="cpv">72212000')
    sisu = CN.replace('<cac:ProcurementProject><cbc:Name languageID="EST">Osa 1', osa, 1)
    sisu = sisu.replace('</cac:ProcurementAdditionalType>\n<cac:MainCommodityClassification><cbc:ItemClassificationCode listName="cpv">72212000',
                        '</cac:ProcurementAdditionalType>\n' + lisa, 1)
    cn, can, vahele = parsi_fail(sisu.encode(), "2024-03")
    o = cn[0]["osade_info"]
    assert o == [{"osa": "LOT-0001", "cpv": "72212000", "maksumus": 80000.0,
                  "kriteeriumid": [("price", 60.0), ("quality", 40.0)], "tahtaeg": "2024-04-04"}]


def test_ted_osade_info():
    sisu = TED.replace("<OBJECT_DESCR><SHORT_DESCR>", '<OBJECT_DESCR><LOT_NO>1</LOT_NO><CPV_ADDITIONAL><CPV_CODE CODE="72300000"/>'
                       '</CPV_ADDITIONAL><VAL_OBJECT CURRENCY="EUR">40000</VAL_OBJECT><SHORT_DESCR>', 1)
    sisu = sisu.replace("<PROCEDURE><PT_OPEN/></PROCEDURE>",
                        "<PROCEDURE><PT_OPEN/><DATE_RECEIPT_TENDERS>2019-06-10</DATE_RECEIPT_TENDERS></PROCEDURE>", 1)
    cn, can, vahele = parsi_fail(sisu.encode(), "2019-05")
    assert cn[0]["osade_info"] == [{"osa": "1", "cpv": "72300000", "maksumus": 40000.0,
                                    "kriteeriumid": [("quality", 30.0), ("price", 70.0)], "tahtaeg": "2019-06-10"}]
