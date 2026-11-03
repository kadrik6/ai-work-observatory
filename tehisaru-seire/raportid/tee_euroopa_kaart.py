"""Teeb Euroopa riikide kaardi kujud (SVG teed) faili raportid/euroopa.json.

Käivita ainult siis, kui kaardi kuju on vaja muuta. Raport loeb valmis faili, võrku ei vaja.

    python raportid/tee_euroopa_kaart.py <tee>/countries-50m.json

Sisend on npm-paketi world-atlas@2.0.2 fail countries-50m.json (litsents ISC, Mike Bostock).
Piirid pärinevad Natural Earthist (avalik omand). Ainult standardteek.
"""

import json
import math
import sys
from pathlib import Path

VALJA = Path(__file__).resolve().parent / "euroopa.json"

# ISO 3166 numbrikood -> Eurostati riigikood (Kreeka on EL, mitte GR).
EL27 = {
    "040": "AT", "056": "BE", "100": "BG", "191": "HR", "196": "CY", "203": "CZ", "208": "DK", "233": "EE",
    "246": "FI", "250": "FR", "276": "DE", "300": "EL", "348": "HU", "372": "IE", "380": "IT", "428": "LV",
    "440": "LT", "442": "LU", "470": "MT", "528": "NL", "616": "PL", "620": "PT", "642": "RO", "703": "SK",
    "705": "SI", "724": "ES", "752": "SE",
}
# Naaberriigid hallis taustana. Norra on seire võrdlusriik, aga ELi kaardil ainult taust.
TAUST = {
    "578": "NO", "352": "IS", "756": "CH", "826": "UK", "008": "AL", "070": "BA", "499": "ME", "807": "MK",
    "688": "RS", "498": "MD", "804": "UA", "112": "BY", "643": "RU", "792": "TR", "438": "LI", "020": "AD",
    "492": "MC", "674": "SM", "336": "VA", "-99": "XK", "012": "DZ", "504": "MA", "788": "TN", "760": "SY",
    "368": "IQ", "364": "IR", "268": "GE", "051": "AM", "031": "AZ", "398": "KZ", "422": "LB", "376": "IL",
    "818": "EG", "434": "LY", "400": "JO", "682": "SA",
}
# Kaardi ala (pikkus, laius) ja projektsioon: Lamberti pindalatruu asimutaalprojektsioon, nagu Eurostati kaartidel.
ALA = (-25.0, 33.5, 45.0, 72.0)
KESKE = (10.0, 52.0)
W = 560


def lambert(lon, lat):
    l0, f0 = math.radians(KESKE[0]), math.radians(KESKE[1])
    l, f = math.radians(lon), math.radians(lat)
    k = math.sqrt(2 / (1 + math.sin(f0) * math.sin(f) + math.cos(f0) * math.cos(f) * math.cos(l - l0)))
    return k * math.cos(f) * math.sin(l - l0), k * (math.cos(f0) * math.sin(f) - math.sin(f0) * math.cos(f) * math.cos(l - l0))


def kaared(topo):
    """TopoJSONi kaared pikkus-laius-punktideks (delta-kodeering lahti)."""
    (sx, sy), (tx, ty) = topo["transform"]["scale"], topo["transform"]["translate"]
    tulem = []
    for kaar in topo["arcs"]:
        x = y = 0
        punktid = []
        for dx, dy in kaar:
            x, y = x + dx, y + dy
            punktid.append((x * sx + tx, y * sy + ty))
        tulem.append(punktid)
    return tulem


def rõngas(K, indeksid):
    punktid = []
    for i in indeksid:
        kaar = K[i] if i >= 0 else list(reversed(K[~i]))
        punktid.extend(kaar[1:] if punktid else kaar)
    return punktid


def hulknurgad(geom, K):
    if geom["type"] == "Polygon":
        return [[rõngas(K, r) for r in geom["arcs"]]]
    if geom["type"] == "MultiPolygon":
        return [[rõngas(K, r) for r in p] for p in geom["arcs"]]
    return []


def ala_sees(r):
    lon = sum(p[0] for p in r) / len(r)
    lat = sum(p[1] for p in r) / len(r)
    return ALA[0] <= lon <= ALA[2] and ALA[1] <= lat <= ALA[3]


def main(sisend):
    topo = json.loads(Path(sisend).read_text(encoding="utf-8"))
    K = kaared(topo)
    # Kaardi raam = ELi riikide (ilma ülemeremaadeta) ümbritsev ristkülik + väike vahe.
    xs, ys = [], []
    for g in topo["objects"]["countries"]["geometries"]:
        if g.get("id") in EL27:
            for hulk in hulknurgad(g, K):
                if ala_sees(hulk[0]):
                    for lon_, lat_ in hulk[0]:
                        x, y = lambert(lon_, lat_)
                        xs.append(x)
                        ys.append(y)
    vahe = 0.02 * (max(xs) - min(xs))
    x0, x1, y0, y1 = min(xs) - vahe, max(xs) + vahe, min(ys) - vahe, max(ys) + vahe
    mõõt = W / (x1 - x0)
    korgus = round((y1 - y0) * mõõt)

    def ekraan(lon, lat):
        x, y = lambert(lon, lat)
        return round((x - x0) * mõõt, 1), round((y1 - y) * mõõt, 1)

    riigid, taust = {}, {}
    for g in topo["objects"]["countries"]["geometries"]:
        kood = EL27.get(g.get("id")) or TAUST.get(g.get("id"))
        if not kood:
            continue
        osad = []
        for hulk in hulknurgad(g, K):
            if kood in EL27.values() and not ala_sees(hulk[0]):
                continue
            if kood not in EL27.values() and sum(p[1] for p in hulk[0]) / len(hulk[0]) > 74:
                continue  # Arktika saared jääksid servale moonutatud kolmnurgana  # ülemeremaad (nt Prantsuse Guajaana, Kanaari saared) jäävad välja
            for r in hulk:
                pp = []
                for lon_, lat_ in r:
                    # Taustariigid (nt Venemaa) lõigatakse kaardi servast veidi kaugemal, et projektsioon ei läheks katki.
                    if lon_ < -40:
                        lon_ += 360  # Venemaa idaosa üle 180. meridiaani: ida poole, mitte kaardi vasakusse serva
                    p = ekraan(max(min(lon_, 60), -30), max(min(lat_, 80), 25))
                    if not pp or abs(p[0] - pp[-1][0]) + abs(p[1] - pp[-1][1]) >= 0.6:
                        pp.append(p)
                if len(pp) >= 3:
                    osad.append("M" + "L".join(f"{x:g},{y:g}" for x, y in pp) + "Z")
        if osad:
            (riigid if kood in EL27.values() else taust)[kood] = "".join(osad)
    VALJA.write_text(json.dumps({
        "selgitus": "Euroopa riikide SVG teed seireraporti ELi kaardi jaoks. Tehtud skriptiga tee_euroopa_kaart.py.",
        "allikas": "Natural Earth (avalik omand), world-atlas@2.0.2 countries-50m (ISC)",
        "viewBox": f"0 0 {W} {korgus}", "el": riigid, "taust": taust}, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8")
    print(f"{VALJA.name}: {len(riigid)} ELi riiki, {len(taust)} taustariiki, {VALJA.stat().st_size // 1024} kB")


if __name__ == "__main__":
    main(sys.argv[1])
