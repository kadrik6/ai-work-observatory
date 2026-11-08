"""Ettekannete igapäevane otsing usaldatud kanalitest (Kadri 8.11.2026).

Loeb kataloog/ettekannete-kanalid.json, võtab igalt kanalilt YouTube'i RSS-voo (või TÜ seminarilehe lingid),
jätab alles tehisaru, andmete ja tööga seotud videod ning kirjutab uued kandidaadid faili
sait/sisu/ettekannete-kandidaadid.json. Kokkuvõtet see skript ei tee: mustandi kirjutab igapäevane töö
ja saidile läheb see alles pärast Kadri kinnitust (sait/ootel.py).

  python3 sait/lae_ettekanded.py [--subtiitrid KAUST]

--subtiitrid: proovib uutele kandidaatidele yt-dlp-ga automaatsubtiitreid (ainult tööks, mitte repo ega saidi jaoks).
Esimesel korral (kandidaatide faili pole) märgib kõik leitud videod „vana“, et vanad salvestised ei tuleks korraga.
"""
import datetime as dt
import json
import re
import subprocess
import sys
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

SIIN = Path(__file__).resolve().parent
KANALID = SIIN.parent / "kataloog" / "ettekannete-kanalid.json"
KANDIDAADID = SIIN / "sisu" / "ettekannete-kandidaadid.json"
TUNTUD = SIIN / "sisu" / "ettekanded.json"
NS = {"a": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015", "m": "http://search.yahoo.com/mrss/"}
UA = {"User-Agent": "Mozilla/5.0 (seire ettekannete otsing)", "Accept-Language": "en"}
# Teema: tehisaru, andmed, töö ja oskused (eesti ja inglise keeles)
TEEMA = re.compile(r"\b(AI|A\.I\.|GenAI|LLMs?|AGI|agents?|agentic|artificial intelligence|machine learning|deep learning|"
                   r"data|algorithm\w*|automation|robot\w*|digital\w*|future of work|jobs?|labou?r|workers?|workforce|"
                   r"skills?|productivity|employment|tehisaru\w*|tehisintellekt\w*|masinõpe\w*|andme\w*|tööturu\w*|"
                   r"tööl\w*|töö|oskus\w*|automatiseeri\w*|digi\w*)\b", re.I)
VANUS_PAEVI = 120  # vanemad videod ei ole uued kandidaadid


def _get(url, timeout=30):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def kanali_id(kasutaja, get=_get):
    """@kasutajanimi → UC… kanali id kanali lehe canonical-lingist."""
    h = get(f"https://www.youtube.com/{kasutaja}")
    m = re.search(r'<link rel="canonical" href="https://www\.youtube\.com/channel/(UC[\w-]{22})"', h) or \
        re.search(r'"(?:externalId|channelId)":"(UC[\w-]{22})"', h)
    if not m:
        raise ValueError(f"kanali id puudub: {kasutaja}")
    return m.group(1)


def voog(xml_tekst, allikas):
    """YouTube'i Atom-voo kirjed: [{id, pealkiri, avaldatud, url, kirjeldus}]."""
    juur = ET.fromstring(xml_tekst)
    read = []
    for k in juur.findall("a:entry", NS):
        vid = k.findtext("yt:videoId", namespaces=NS)
        if not vid:
            continue
        g = k.find("m:group", NS)
        read.append({"id": vid, "allikas": allikas, "pealkiri": (k.findtext("a:title", namespaces=NS) or "").strip(),
                     "avaldatud": (k.findtext("a:published", namespaces=NS) or "")[:10],
                     "url": f"https://www.youtube.com/watch?v={vid}",
                     "kirjeldus": ((g.findtext("m:description", namespaces=NS) if g is not None else "") or "")[:600]})
    return read


def lehe_videod(html, allikas):
    """Seminarilehe YouTube'i lingid (TÜ andmeteaduse seminar): [{id, url}] lehe järjekorras."""
    ids = []
    for m in re.finditer(r'href="https?://(?:www\.)?(?:youtu\.be/|youtube\.com/watch\?v=)([\w-]{11})', html):
        if m.group(1) not in ids:
            ids.append(m.group(1))
    return [{"id": i, "allikas": allikas, "pealkiri": "", "avaldatud": "", "url": f"https://www.youtube.com/watch?v={i}", "kirjeldus": ""} for i in ids]


def teemas(r):
    return bool(TEEMA.search(r["pealkiri"] + " " + r["kirjeldus"]))


def tuntud_videod():
    """Videod, millest kokkuvõte juba on (saidi ettekanded)."""
    if not TUNTUD.exists():
        return set()
    d = json.loads(TUNTUD.read_text(encoding="utf-8"))
    return {m.group(1) for r in d.get("ettekanded", []) for m in [re.search(r"(?:youtu\.be/|v=)([\w-]{11})", r.get("video", ""))] if m}


def uuenda(kandidaadid, leitud, tuntud, tana, esimene):
    """Lisab uued videod kandidaatide hulka. Tagastab uute kandidaatide id-d (olek „uus“)."""
    olemas = {k["id"] for k in kandidaadid}
    uued = []
    piir = (tana - dt.timedelta(days=VANUS_PAEVI)).isoformat()
    for r in leitud:
        if r["id"] in olemas or r["id"] in tuntud:
            continue
        olemas.add(r["id"])
        vana = esimene or (r["avaldatud"] and r["avaldatud"] < piir)
        olek = "vana" if vana else ("uus" if r.get("filter") is False or teemas(r) else "teemaväline")
        k = {kk: r[kk] for kk in ("id", "allikas", "pealkiri", "avaldatud", "url")}
        k.update({"leitud": tana.isoformat(), "olek": olek})
        kandidaadid.append(k)
        if olek == "uus":
            uued.append(r["id"])
    return uued


def oembed_pealkiri(url):
    try:
        return json.loads(_get(f"https://www.youtube.com/oembed?url={url}&format=json")).get("title", "")
    except Exception:
        return ""


def subtiitrid(vid, kaust):
    kaust.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(["yt-dlp", "--skip-download", "--write-auto-subs", "--write-subs", "--sub-langs", "en.*,et.*",
                        "--sub-format", "vtt", "-o", str(kaust / "%(id)s.%(ext)s"), f"https://www.youtube.com/watch?v={vid}"],
                       capture_output=True, text=True, timeout=180)
    return r.returncode == 0 and any(kaust.glob(f"{vid}*.vtt"))


def main(argv):
    sub = Path(argv[argv.index("--subtiitrid") + 1]) if "--subtiitrid" in argv else None
    tana = dt.date.today()
    K = json.loads(KANALID.read_text(encoding="utf-8"))
    esimene = not KANDIDAADID.exists()
    olek = json.loads(KANDIDAADID.read_text(encoding="utf-8")) if not esimene else {"kandidaadid": [], "kanalid": {}}
    leitud, vead = [], []
    for k in K["kanalid"]:
        try:
            if k.get("leht"):
                rr = lehe_videod(_get(k["leht"]), k["id"])
            else:
                if k.get("esitusloend"):
                    u = f"https://www.youtube.com/feeds/videos.xml?playlist_id={k['esitusloend']}"
                else:
                    cid = k.get("kanal") or olek["kanalid"].get(k["id"]) or kanali_id(k["kasutaja"])
                    olek["kanalid"][k["id"]] = cid
                    u = f"https://www.youtube.com/feeds/videos.xml?channel_id={cid}"
                rr = voog(_get(u), k["id"])
            for r in rr:
                r["filter"] = k.get("filter", True)
            leitud += rr
            print(f"KANAL {k['id']}: {len(rr)} videot")
        except Exception as ex:  # üks kanal ei tohi kogu otsingut peatada
            vead.append(f"{k['id']}: {ex}")
            print(f"HOIATUS {k['id']}: {ex}")
    uued = uuenda(olek["kandidaadid"], leitud, tuntud_videod(), tana, esimene)
    for k in olek["kandidaadid"]:
        if k["id"] in uued and not k["pealkiri"]:
            k["pealkiri"] = oembed_pealkiri(k["url"])
        if k["id"] in uued and sub is not None:
            try:
                k["subtiitrid"] = subtiitrid(k["id"], sub)
            except Exception:
                k["subtiitrid"] = False
    olek["kandidaadid"] = sorted(olek["kandidaadid"], key=lambda k: (k["leitud"], k["avaldatud"]), reverse=True)[:500]
    olek.update({"uuendatud": tana.isoformat(), "vead": vead})
    KANDIDAADID.write_text(json.dumps(olek, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"UUSI KANDIDAATE {len(uued)}" + (" (esimene jooks: kõik märgiti vanaks)" if esimene else ""))
    for k in olek["kandidaadid"]:
        if k["id"] in uued:
            print(f"UUS {k['allikas']} {k['avaldatud']} {k['url']} {k['pealkiri'][:100]}")
    return 1 if len(vead) == len(K["kanalid"]) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
