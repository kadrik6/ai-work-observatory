"""Uudiste allikate logod (Kadri 11.11.2026: „allikad võiks olla seal kõrval logodena nähtavad, hoveril võiks nime näha“).

Loeb sait/sisu/uudised.jsonl linkidest domeenid ja laeb igale domeenile, millel logot veel pole, selle saidi enda
ikooni (favicon) DuckDuckGo ikooniteenusest või otse saidilt. Fail läheb kausta sait/pilt/logod/ ja nimekiri faili
sait/pilt/logod/logod.json ({domeen: failinimi}). Leht kasutab logot, kui see on olemas; muidu jääb allika nimi tekstina.

Pilvekeskkonnas (Claude) on välisvõrk suletud, seepärast jookseb see GitHub Actionsis (.github/workflows/logod.yml).
Käivitus: python sait/lae_logod.py
"""
import json
import sys
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

SIIN = Path(__file__).resolve().parent
KAUST = SIIN / "pilt" / "logod"
NIMEKIRI = KAUST / "logod.json"
UUDISED = SIIN / "sisu" / "uudised.jsonl"
ETTEKANDED = SIIN / "sisu" / "ettekanded.json"
# Podcastide kaanepildid (Kadri 12.11.2026: „lisa podcastidele ka logod, otsi veebist“). Saidi favicon ei ole see pilt,
# mida kuulaja tunneb; kaas on saate ametlikust RSS-voost (itunes:image), vähendatakse 64 px PNG-ks.
KAANED = {
    "lexfridman.com": "https://lexfridman.com/wordpress/wp-content/uploads/powerpress/lex_fridman_podcast_cover_3000.jpg",
    "preposterousuniverse.com": "https://static.libsyn.com/p/assets/b/0/6/d/b06d098337897af116c3140a3186d450/"
                                "21d641ef836c48dff270cbede4360d187bdd6c56cb126be7d6f51078db34d4675527fa72e13c86bb573ec42c5d4fc493e18e7d95fec734ec77168fc379baefcf.jpeg",
}
KAANE_SUURIM = 8_000_000
# Vahendajad, mille logo ei ütleks, kes allikas on (nt DOI viib ülikooli repositooriumi)
VAHELE = {"doi.org", "t.co", "bit.ly", "news.google.com"}
KAHE_OSAGA = {"gov.au", "com.au", "co.uk", "gov.uk", "org.uk", "ac.uk", "gc.ca", "gov.cy", "co.in", "gov.in"}
SUURIM = 60_000  # baiti; favicon on väike, suurem fail pole ikoon
AEG = 15


def domeen(url):
    d = (urlparse(url).hostname or "").lower()
    return d[4:] if d.startswith("www.") else d


def baas(d):
    osad = d.split(".")
    n = 3 if ".".join(osad[-2:]) in KAHE_OSAGA else 2
    return ".".join(osad[-n:])


def logo_fail(logod, url):
    """Failinimi lehe jaoks või None. Enne täpne domeen (news.err.ee), siis põhidomeen (err.ee)."""
    d = domeen(url)
    if not d or d in VAHELE:
        return None
    return logod.get(d) or logod.get(baas(d))


def tuup(sisu):
    if sisu[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if sisu[:4] == b"\x00\x00\x01\x00":
        return "ico"
    if sisu[:6] in (b"GIF87a", b"GIF89a"):
        return "gif"
    if sisu[:4] == b"RIFF" and sisu[8:12] == b"WEBP":
        return "webp"
    return None  # SVG ja HTML (nt veateade) jäävad välja


def lae(url):
    p = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (seire-sait logod)"})
    with urllib.request.urlopen(p, timeout=AEG) as v:
        return v.read(SUURIM + 1)


def kaas(url, laadija=None):
    """Kaanepilt 64×64 PNG-na või None (Pillow puudub või pilt ei avane)."""
    try:
        import io
        from PIL import Image
        sisu = laadija(url) if laadija else _lae_suur(url)
        im = Image.open(io.BytesIO(sisu)).convert("RGB").resize((64, 64), Image.LANCZOS)
        v = io.BytesIO()
        im.save(v, "PNG", optimize=True)
        return v.getvalue()
    except Exception:  # noqa: BLE001 — siis jääb favicon
        return None


def _lae_suur(url):
    p = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (seire-sait logod)"})
    with urllib.request.urlopen(p, timeout=AEG * 2) as v:
        return v.read(KAANE_SUURIM)


def hangi(d, laadija=lae):
    for url in (f"https://icons.duckduckgo.com/ip3/{d}.ico", f"https://{d}/favicon.ico"):
        try:
            sisu = laadija(url)
        except Exception:  # noqa: BLE001 — iga võrgu- või HTTP-viga tähendab, et proovime järgmist
            continue
        t = tuup(sisu)
        if t and 100 < len(sisu) <= SUURIM:
            return sisu, t
    return None


def main(laadija=lae, kaust=KAUST, uudised=UUDISED, ettekanded=None, kaaned=None, kaane_laadija=None):
    """ettekanded ja kaaned annab ette ainult käivitus käsurealt (testid ei lae võrgust)."""
    nimekiri_f = kaust / "logod.json"
    logod = json.loads(nimekiri_f.read_text(encoding="utf-8")) if nimekiri_f.exists() else {}
    read = [json.loads(x) for x in uudised.read_text(encoding="utf-8").splitlines() if x.strip()]
    urlid = [r["url"] for r in read if r.get("url")]
    if ettekanded and ettekanded.exists():  # ettekannete ja podcastide sarjad (Kadri 12.11.2026)
        urlid += [a["url"] for a in json.loads(ettekanded.read_text(encoding="utf-8")).get("allikad", []) if a.get("url")]
    domeenid = sorted({domeen(u) for u in urlid} - VAHELE - {""})
    uued, puudu = 0, []
    for d, url in (kaaned or {}).items():
        if d in logod:
            continue
        sisu = kaas(url, kaane_laadija)
        if sisu:
            kaust.mkdir(parents=True, exist_ok=True)
            (kaust / f"{d}.png").write_bytes(sisu)
            logod[d] = f"{d}.png"
            uued += 1
    for d in domeenid:
        if logo_fail(logod, "https://" + d):
            continue
        for katse in dict.fromkeys((d, baas(d))):
            leitud = hangi(katse, laadija)
            if leitud:
                sisu, t = leitud
                kaust.mkdir(parents=True, exist_ok=True)
                nimi = f"{katse}.{t}"
                (kaust / nimi).write_bytes(sisu)
                logod[katse] = nimi
                uued += 1
                break
        else:
            puudu.append(d)
    if uued:
        nimekiri_f.write_text(json.dumps(dict(sorted(logod.items())), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"Logosid {len(logod)}, uusi {uued}; logota {len(puudu)}: {', '.join(puudu) or '-'}")
    return uued


if __name__ == "__main__":
    sys.exit(0 if main(ettekanded=ETTEKANDED, kaaned=KAANED) >= 0 else 1)
