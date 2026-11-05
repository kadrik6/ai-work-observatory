import tellija as T

NIMED = T.asutused(["Riigi Tugiteenuste Keskus", "Eesti Töötukassa"])


def test_sulgudes_ja_kaandes():
    assert T.kelle_jaoks("Eesti.ai koolitajate tellimine (Riigikantselei)", "Riigi Tugiteenuste Keskus", NIMED) == \
        ("Riigikantselei", "pealkiri")
    assert T.kelle_jaoks("Meediamonitooringu tellimine Riigikantseleile", "Riigi Tugiteenuste Keskus", NIMED)[0] == \
        "Riigikantselei"
    assert T.kelle_jaoks("Kohanemisvaldkonna analüüs Kultuuriministeeriumile", "Riigi Tugiteenuste Keskus",
                         NIMED)[0] == "Kultuuriministeerium"


def test_luhend():
    assert T.kelle_jaoks("PPA teenindussaalide kliendiarvutite teenus",
                         "Siseministeeriumi infotehnoloogia- ja arenduskeskus", NIMED)[0] == "Politsei- ja Piirivalveamet"


def test_keskne_hankija_ei_ole_ise_tellija():
    kj, allikas = T.kelle_jaoks("Nutipoide võrgustiku piloteerimine", "Riigi Tugiteenuste Keskus", NIMED)
    assert allikas == "keskne" and "Tugiteenuste" not in kj


def test_tavaline_hankija_on_ise_tellija():
    assert T.kelle_jaoks("E-töötukassa arendustööd", "Eesti Töötukassa", NIMED) == ("Eesti Töötukassa", "sama")
