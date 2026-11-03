"""Näitajate kataloog ja allikate võrdlus.

Kataloog on neljatasandiline:
  kategooria (teema ja alateema)  -> kataloog/kategooriad.csv
  mõiste (üks küsimus)            -> kataloog/moisted.csv
  mõõdik (konkreetne allikas ja   -> kataloog/moodikud.csv
          definitsioon)
  vaatlus (riik, aasta, väärtus)  -> kataloog/vaatlused-*.csv (api, valis, muud)
                                     ja seire põhiandmed andmed/<näitaja>.csv

Iga mõiste juures on üks võrdlusalus (tavaliselt Eurostat). Teised mõõdikud on
selle suhtes ühes viiest võrreldavusklassist. Võrdlus arvutab vahed ainult nende
mõõdikute vahel, mida tohib kõrvutada, ega pane kunagi eri mõõdikute numbreid
ühte ritta.

Käivitamine kaustast tehisaru-seire:  python -m seire.kataloog
"""

import csv
import json
import re
from pathlib import Path

from seire.usaldus import VASTUOLU_PIIR

JUUR = Path(__file__).resolve().parent.parent

VORREDAVUS = {
    "alus": "Võrdlusalus",
    "sama": "Sama mõõdik",
    "osaliselt": "Osaliselt võrreldav",
    "erinev": "Ei ole võrreldav",
    "kontrollimata": "Võrreldavus kontrollimata",
}
VORREDAVUS_SELGITUS = {
    "alus": "Selle mõiste peamine allikas. Kõigi riikide kohta sama meetodiga, nii et riike saab omavahel järjestada.",
    "sama": "Sama küsitlus ja sama määratlus. Number peab klappima võrdlusalusega ümardamise täpsusega. Kui ei klapi, on see lahknevus, mida tuleb uurida.",
    "osaliselt": "Sama küsitlus, aga erinev kogum, klassifikaator või nimetaja. Erinevus on oodatav. Numbrit võib näidata kõrval, aga mitte arvutada sellest kasvu ega järjestada koos võrdlusalusega.",
    "erinev": "Teine küsitlus või teine määratlus (periood, ettevõtete suurus, küsimus). Näidatakse eraldi ja ei panda võrdlusalusega samasse ritta.",
    "kontrollimata": "Ma ei ole metaandmetest kontrollinud, kas määratlus on sama. Kuni seda pole tehtud, käsitle seda nagu „ei ole võrreldav“.",
}
OLEKUD = {
    "seires": "Seire laeb automaatselt",
    "andmed": "Andmed kataloogis",
    "kavandatud": "Andmestik teada, andmed laadimata",
    "allikas_leidmata": "Allikas leidmata",
}
JARJEKORD = list(VORREDAVUS)
STAATUSED = {"kooskolas": "kooskõlas", "vaike_vahe": "väike vahe", "lahknevus": "lahknevus"}

# Otsuskriitilised lahtrid: Eesti ja ELi viimane aasta võrdlusaluses. Just neid numbreid lugeja kasutab,
# nii et nende kooskõla näidatakse eraldi. Üldine klappimise määr võib kõrge olla ja peita vea selles lahtris.
KRIITILISED_RIIGID = ("EE", "EU27_2020")

# Eurostat avaldab protsendid kahe komakohaga. Seire CSV kaotab lõpunullid (23.40 -> 23.4).
EUROSTATI_TAPSUS = 2


def _loe_csv(p):
    if not p.exists():
        return []
    with open(p, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def tapsus(s):
    """Komakohtade arv numbri kirjapildis: "22.2" -> 1, "59" -> 0."""
    s = str(s).strip()
    return len(s.split(".")[1]) if "." in s else 0


def _vaatlus(rida, **lisa):
    return {
        "moodik": rida["moodik"], "riik": rida["riik"], "aasta": int(rida["aasta"]),
        "vaartus": float(rida["vaartus"]), "tapsus": tapsus(rida["vaartus"]),
        "avaldatud": rida.get("avaldatud", ""), "kontrollitud": rida.get("kontrollitud", ""),
        "kuidas": rida.get("kuidas", ""), "url": rida.get("url", ""), "markus": rida.get("markus", ""),
        "margend": rida.get("margend", ""), **lisa,
    }


def lae(juur=JUUR):
    k = juur / "kataloog"
    kategooriad = {r["kood"]: r for r in _loe_csv(k / "kategooriad.csv")}
    moisted = {r["id"]: r for r in _loe_csv(k / "moisted.csv")}
    moodikud = {r["id"]: r for r in _loe_csv(k / "moodikud.csv")}
    allikad = {r["id"]: r for r in _loe_csv(juur / "allikad" / "allikad.csv")}

    vaatlused = []
    # Kui mõõdik on seire põhinäitaja ja selle andmefail on olemas, loetakse numbrid ainult sealt. Kataloogi
    # failides võib sama mõõdik alles olla (nt T&A kulu failis vaatlused-valis.csv), sest seda loeb väline leht.
    seires = {m["id"] for m in moodikud.values() if m["naitaja"] and (juur / "andmed" / f"{m['naitaja']}.csv").exists()}
    for p in sorted(k.glob("vaatlused-*.csv")):  # api (lae.py), valis (lae_valis.py), muud (käsitsi)
        vaatlused += [_vaatlus(r, fail=f"kataloog/{p.name}") for r in _loe_csv(p) if r["vaartus"] and r["moodik"] not in seires]
    # Seire põhinäitajad: numbrid tulevad otse seire andmefailist, mitte koopiast.
    for m in moodikud.values():
        if not m["naitaja"]:
            continue
        andmed = juur / "andmed" / f"{m['naitaja']}.csv"
        meta_p = juur / "andmed" / f"{m['naitaja']}.meta.json"
        meta = json.loads(meta_p.read_text(encoding="utf-8")) if meta_p.exists() else {}
        for r in _loe_csv(andmed):
            if r["vaartus"] == "":
                continue
            v = _vaatlus({"moodik": m["id"], "riik": r["geo"], "aasta": r["time"], "vaartus": r["vaartus"],
                          "avaldatud": meta.get("allikas_uuendas", ""), "kontrollitud": meta.get("kontrollitud", ""),
                          "kuidas": "seire põhiandmed", "url": meta.get("url", m["url"]), "margend": r.get("margend", "")},
                         fail=f"andmed/{m['naitaja']}.csv")
            v["tapsus"] = EUROSTATI_TAPSUS if m["allikas"] == "INT-EUROSTAT" else v["tapsus"]
            vaatlused.append(v)
    return {"kategooriad": kategooriad, "moisted": moisted, "moodikud": moodikud, "allikad": allikad,
            "vaatlused": vaatlused}


def kontrolli(K):
    """Kataloogi sisemine kooskõla. Tagastab vigade loendi (tühi = korras)."""
    vead = []
    kat, moi, mod = K["kategooriad"], K["moisted"], K["moodikud"]
    for kood, r in kat.items():
        if r["ulem"] and r["ulem"] not in kat:
            vead.append(f"Kategooria {kood}: ülemkategooriat {r['ulem']} pole.")
    for mid, r in moi.items():
        if r["kategooria"] not in kat:
            vead.append(f"Mõiste {mid}: kategooriat {r['kategooria']} pole.")
        elif not kat[r["kategooria"]]["ulem"]:
            vead.append(f"Mõiste {mid}: kategooria {r['kategooria']} on teema, mõiste peab olema alateema all.")
        alus = mod.get(r["vordlusalus"])
        if alus is None:
            vead.append(f"Mõiste {mid}: võrdlusalust {r['vordlusalus']} pole mõõdikute seas.")
        elif alus["moiste"] != mid:
            vead.append(f"Mõiste {mid}: võrdlusalus {alus['id']} kuulub teise mõiste alla.")
    for mid, r in mod.items():
        if r["moiste"] not in moi:
            vead.append(f"Mõõdik {mid}: mõistet {r['moiste']} pole.")
        if r["vorreldavus"] not in VORREDAVUS:
            vead.append(f"Mõõdik {mid}: tundmatu võrreldavus „{r['vorreldavus']}“.")
        if r["olek"] not in OLEKUD:
            vead.append(f"Mõõdik {mid}: tundmatu olek „{r['olek']}“.")
        if r["allikas"] and K["allikad"] and r["allikas"] not in K["allikad"]:
            vead.append(f"Mõõdik {mid}: allikat {r['allikas']} pole registris allikad/allikad.csv.")
        on_alus = r["moiste"] in moi and moi[r["moiste"]]["vordlusalus"] == mid
        if (r["vorreldavus"] == "alus") != on_alus and r["vorreldavus"] in VORREDAVUS and r["moiste"] in moi:
            vead.append(f"Mõõdik {mid}: võrreldavus „alus“ peab olema täpselt mõiste võrdlusalusel.")
    nahtud = {}
    for v in K["vaatlused"]:
        if v["moodik"] not in mod:
            vead.append(f"Vaatlus {v['fail']}: mõõdikut {v['moodik']} pole.")
            continue
        votm = (v["moodik"], v["riik"], v["aasta"])
        if votm in nahtud:
            vead.append(f"Vaatlus {v['moodik']} {v['riik']} {v['aasta']} on kaks korda ({nahtud[votm]} ja {v['fail']}).")
        nahtud[votm] = v["fail"]
    andmetega = {v["moodik"] for v in K["vaatlused"]}
    for mid, r in mod.items():
        if r["olek"] in ("seires", "andmed") and mid not in andmetega:
            vead.append(f"Mõõdik {mid}: olek on „{r['olek']}“, aga vaatlusi pole.")
        if r["olek"] in ("kavandatud", "allikas_leidmata") and mid in andmetega:
            vead.append(f"Mõõdik {mid}: olek on „{r['olek']}“, aga vaatlused on olemas. Muuda olekuks „andmed“.")
    return vead


def hinda_vahe(a, b):
    """Kahe sama asja mõõtva numbri vahe ja hinnang.

    kooskõlas:  vahe mahub ümardamise sisse (vähem täpse numbri pool viimasest kohast)
    väike vahe: vahe on suurem kui ümardamine, aga alla VASTUOLU_PIIR protsendipunkti üle selle
    lahknevus:  vahe on vähemalt VASTUOLU_PIIR protsendipunkti üle ümardamise
    """
    vahe = round(b["vaartus"] - a["vaartus"], 4)
    lubatud = 0.5 * 10 ** -min(a["tapsus"], b["tapsus"])
    ule = abs(vahe) - lubatud
    if ule <= 1e-9:
        staatus = "kooskolas"
    elif ule < VASTUOLU_PIIR:
        staatus = "vaike_vahe"
    else:
        staatus = "lahknevus"
    return {"vahe": vahe, "lubatud": lubatud, "staatus": staatus}


def vordle(K, moiste_id):
    """Ühe mõiste kõik allikad kõrvuti.

    Tagastab mõõdikud võrreldavuse järjekorras, nende vaatlused, paarikaupa vahed
    võrdlusalusega (ainult klassidele "sama" ja "osaliselt") ja riikide viimase aasta
    tabeli, kus eri klasside numbrid on eri veergudes.
    """
    moiste = K["moisted"][moiste_id]
    alus_id = moiste["vordlusalus"]
    mood = sorted((m for m in K["moodikud"].values() if m["moiste"] == moiste_id),
                  key=lambda m: (JARJEKORD.index(m["vorreldavus"]), m["id"]))
    vaat = {m["id"]: {} for m in mood}
    for v in K["vaatlused"]:
        if v["moodik"] in vaat:
            vaat[v["moodik"]][(v["riik"], v["aasta"])] = v
    alus = vaat.get(alus_id, {})

    alus_viimane = {}
    for riik_, aasta in alus:
        alus_viimane[riik_] = max(aasta, alus_viimane.get(riik_, aasta))
    paarid = []
    for m in mood:
        if m["vorreldavus"] not in ("sama", "osaliselt"):
            continue
        for votm, v in sorted(vaat[m["id"]].items()):
            if votm in alus:
                paarid.append({"moodik": m["id"], "klass": m["vorreldavus"], "riik": votm[0], "aasta": votm[1],
                               "alus": alus[votm]["vaartus"], "teine": v["vaartus"], **hinda_vahe(alus[votm], v),
                               # koopia: allikas kordab võrdlusaluse numbrit (nt OECD ELi riikide kohta), see ei kinnita
                               "koopia": m.get("koopia") == "jah",
                               "kriitiline": votm[0] in KRIITILISED_RIIGID and votm[1] == alus_viimane[votm[0]]})

    riigid = {}
    for m in mood:
        for (riik, aasta), v in vaat[m["id"]].items():
            r = riigid.setdefault(riik, {"alus": None, "uuem": None, "muud": []})
            if m["vorreldavus"] == "alus":
                if r["alus"] is None or aasta > r["alus"]["aasta"]:
                    r["alus"] = v
            elif m["vorreldavus"] in ("sama", "osaliselt"):
                if r["uuem"] is None or aasta > r["uuem"]["aasta"]:
                    r["uuem"] = v
            else:
                r["muud"].append(v)
    for r in riigid.values():
        # "Uuem" näidatakse ainult siis, kui see on tõesti uuem kui võrdlusalus.
        if r["uuem"] and r["alus"] and r["uuem"]["aasta"] <= r["alus"]["aasta"]:
            r["uuem"] = None
        viimased = {}
        for v in r["muud"]:
            if v["moodik"] not in viimased or v["aasta"] > viimased[v["moodik"]]["aasta"]:
                viimased[v["moodik"]] = v
        r["muud"] = list(viimased.values())

    return {"moiste": moiste, "alus_id": alus_id, "moodikud": mood, "vaatlused": vaat,
            "paarid": paarid, "riigid": riigid}


def klappimine(paarid):
    """Kaks klappimise numbrit sama mõõdikuga allikate kohta: kõik sõltumatud võrdlused ja kriitilised lahtrid.

    Koopiaid (allikas kordab võrdlusalust) ei loeta, sest nende kokkulangemine ei ole sõltumatu kinnitus.
    """
    sama = [p for p in paarid if p["klass"] == "sama"]
    soltumatud = [p for p in sama if not p["koopia"]]
    kriitilised = [p for p in soltumatud if p["kriitiline"]]

    def loe(pp):
        return {"klapib": sum(1 for p in pp if p["staatus"] == "kooskolas"), "kokku": len(pp),
                "lahknevused": [p for p in pp if p["staatus"] == "lahknevus"],
                "vaikesed": [p for p in pp if p["staatus"] == "vaike_vahe"]}

    return {"koik": loe(soltumatud), "kriitilised": loe(kriitilised), "koopiaid": len(sama) - len(soltumatud)}


def vorreldavad_moisted(K):
    """Mõisted, kus vähemalt kahel mõõdikul on andmed. Ainult neid saab kõrvutada."""
    andmetega = {v["moodik"] for v in K["vaatlused"]}
    tulem = []
    for mid in K["moisted"]:
        n = sum(1 for m in K["moodikud"].values() if m["moiste"] == mid and m["id"] in andmetega)
        if n >= 2:
            tulem.append(mid)
    return tulem


def _registri_vaatlus(K, naitaja, riik, aasta):
    for v in K["vaatlused"]:
        m = K["moodikud"].get(v["moodik"])
        if m and m["registri_naitaja"] == naitaja and v["riik"] == riik and v["aasta"] == aasta:
            return v
    return None


def kooskola(K, juur=JUUR):
    """Kontrollib, et sama number on igas käsitsi peetavas failis sama.

    Võrdleb kataloogi vaatlusi failidega allikad/numbrid-2026.csv, raportid/riiklikud.csv
    ja seire meta-failide teiste allikate kirjetega (andmed/<näitaja>.meta.json).
    """
    tulem = []

    def lisa(fail, kirje, teine, v):
        if v is None:
            tulem.append({"fail": fail, "kirje": kirje, "teine": teine, "kataloog": None, "staatus": "kataloogis puudub"})
            return
        h = hinda_vahe(v, {"vaartus": float(teine), "tapsus": tapsus(teine)})
        tulem.append({"fail": fail, "kirje": kirje, "teine": float(teine), "kataloog": v["vaartus"],
                      "staatus": "klapib" if h["staatus"] == "kooskolas" else "erineb"})

    for fail in ("allikad/numbrid-2026.csv", "raportid/riiklikud.csv"):
        for r in _loe_csv(juur / fail):
            if not r.get("vaartus"):
                continue
            v = _registri_vaatlus(K, r["naitaja"], r["riik"], int(r["aasta"]))
            lisa(fail, f"{r['naitaja']} {r['riik']} {r['aasta']} ({r['allikas']})", r["vaartus"], v)

    sa_mood = [m for m in K["moodikud"].values() if m["allikas"] == "EE-SA" and m["andmestik"]]
    for meta_p in sorted((juur / "andmed").glob("*.meta.json")):
        meta = json.loads(meta_p.read_text(encoding="utf-8"))
        for t in meta.get("vordlus", []):
            # Kui kirjes on mõõdik kirjas (automaatselt laaditud riiklik allikas), seo selle järgi.
            # Muidu otsi tabeli nime järgi; sama tabeli mitme mõõdiku korral oleks see mitmetähenduslik.
            kandidaadid = [K["moodikud"][t["moodik"]]] if t.get("moodik") in K["moodikud"] else sa_mood
            for m in kandidaadid:
                if t.get("moodik") or re.search(rf"\b{re.escape(m['andmestik'])}\b", t["allikas"]) and "uudis" not in t["allikas"]:
                    v = next((x for x in K["vaatlused"] if x["moodik"] == m["id"] and x["riik"] == t["riik"]
                              and x["aasta"] == int(t["aasta"])), None)
                    lisa(f"andmed/{meta_p.name}", f"{t['allikas']} {t['riik']} {t['aasta']}", str(t["vaartus"]), v)
    return tulem


def kokkuvote(K):
    andmetega = {v["moodik"] for v in K["vaatlused"]}
    olekud = {}
    for m in K["moodikud"].values():
        olekud[m["olek"]] = olekud.get(m["olek"], 0) + 1
    teemad = [k for k, r in K["kategooriad"].items() if not r["ulem"]]
    moisted_andmetega = {K["moodikud"][m]["moiste"] for m in andmetega if m in K["moodikud"]}
    return {
        "teemasid": len(teemad),
        "alateemasid": len(K["kategooriad"]) - len(teemad),
        "moisteid": len(K["moisted"]),
        "moisteid_andmetega": len(moisted_andmetega),
        "moodikuid": len(K["moodikud"]),
        "vaatlusi": len(K["vaatlused"]),
        "olekud": olekud,
    }


def main():
    K = lae()
    vead = kontrolli(K)
    kk = kokkuvote(K)
    print(f"Kataloog: {kk['teemasid']} teemat, {kk['alateemasid']} alateemat, {kk['moisteid']} mõistet "
          f"({kk['moisteid_andmetega']} andmetega), {kk['moodikuid']} mõõdikut, {kk['vaatlusi']} vaatlust.")
    for olek, n in kk["olekud"].items():
        print(f"  {OLEKUD[olek]}: {n}")
    print("Vead:" if vead else "Kataloog on sisemiselt kooskõlas.")
    for v in vead:
        print(f"  {v}")
    for mid in vorreldavad_moisted(K):
        V = vordle(K, mid)
        loend = {}
        for p in V["paarid"]:
            if p["klass"] == "sama":
                loend[p["staatus"]] = loend.get(p["staatus"], 0) + 1
        osad = ", ".join(f"{STAATUSED[s]} {n}" for s, n in sorted(loend.items()))
        print(f"{V['moiste']['nimi']}: {len(V['moodikud'])} mõõdikut. Sama mõõdiku kontrollid: {osad or 'pole'}.")
        for p in V["paarid"]:
            if p["staatus"] != "kooskolas" and p["klass"] == "sama":
                print(f"  {p['moodik']} {p['riik']} {p['aasta']}: {p['teine']} vs {p['alus']} ({STAATUSED[p['staatus']]})")
    erinevad = [r for r in kooskola(K) if r["staatus"] != "klapib"]
    print("Käsitsi failid klapivad kataloogiga." if not erinevad else "Käsitsi failide erinevused:")
    for r in erinevad:
        print(f"  {r['fail']}: {r['kirje']} = {r['teine']}, kataloogis {r['kataloog']} ({r['staatus']})")
    return 1 if vead else 0


if __name__ == "__main__":
    raise SystemExit(main())
