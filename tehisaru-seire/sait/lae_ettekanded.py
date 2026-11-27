"""Ettekannete igapäevane otsing usaldatud kanalitest (Kadri 8.11.2026).

Loeb kataloog/ettekannete-kanalid.json, võtab igalt kanalilt YouTube'i RSS-voo (või TÜ seminarilehe lingid, UTTV video
lehed või podcasti RSS-voo),
jätab alles tehisaru, andmete ja tööga seotud videod ning kirjutab uued kandidaadid faili
sait/sisu/ettekannete-kandidaadid.json. Kokkuvõtet see skript ei tee: mustandi kirjutab igapäevane töö
ja saidile läheb see alles pärast Kadri kinnitust (sait/ootel.py).

  python3 sait/lae_ettekanded.py [--subtiitrid KAUST]

--subtiitrid: proovib uutele kandidaatidele yt-dlp-ga automaatsubtiitreid (ainult tööks, mitte repo ega saidi jaoks).
Kui subtiitreid ei saanud (pilves tavaline) või video on UTTV-s, saab kandidaat märke „vajab_teksti“ ja töö annab
hoiatuse; tekst tehakse siis Kadri arvutis skriptiga sait/tee_tekstid.py (ADR-1, 14.11.2026).
Esimesel korral (kandidaatide faili pole) märgib kõik leitud videod „vana“, et vanad salvestised ei tuleks korraga.
"""
import datetime as dt
import html
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
# Teema (Kadri 27.11.2026: liiga palju teemaväliseid kandidaate): ainult tehisaru, andmed ja töö tulevik.
# Üldsõnad nagu „work“, „jobs“, „skills“ või „digital“ üksi ei piisa, sest ILO ja UTTV videotes on neid peaaegu alati.
# \b asemel ümbrusekontroll, et „A.I.“ ja „AI-põhine“ ka sobiksid.
TEEMA = re.compile(r"(?<!\w)(AI|A\.I\.|GenAI|LLMs?|AGI|agentic|AI agents?|artificial intelligence|machine learning|"
                   r"deep learning|neural networks?|chatbots?|ChatGPT|Copilot|generative|world models?|data science|"
                   r"data scientists?|big data|open data|data governance|algorithm\w*|automation|automated|robot\w*|"
                   r"future of work|future skills|digital skills|digital transformation|digitali[sz]ation|"
                   r"tehisaru\w*|tehisintellekt\w*|masinõpe\w*|keelemudel\w*|vestlusrobot\w*|andmeteadus\w*|"
                   r"andmeanalüüs\w*|andmekaitse\w*|avaandme\w*|andmepõhi\w*|automatiseeri\w*|automaatika\w*|"
                   r"digipööre\w*|digiriigi?\w*|tööturu\w*|töö tulevik\w*|oskuste tulevik\w*)(?!\w)", re.I)
# Ei ole ettekanne, mida kokku võtta: kursuse tunnid, tseremooniad, kokkuvõttevideod, doktoritööde kaitsmised.
VALJA = re.compile(r"Nädal \d+|kordamine|tasemetöö|kontrolltöö|teenetemärk\w*|aktus\w*|aftermovie|best bits|"
                   r"closing ceremony|opening ceremony|official trailer|behind the scenes|doctoral defen[cs]e|"
                   r"defen[cs]e of a doctoral|doktoritöö kaitsmi\w*|^AMA \||Ask Me Anything", re.I)
SOEL_ALATES = "2026-11-27"  # sellest päevast hindab uus sõel; varem leitud ootel kandidaadid hinnatakse üle (soelu_uuesti)
VANUS_PAEVI = 120  # vanemad videod ei ole uued kandidaadid
# Tartu Ülikooli videoportaal UTTV (Kadri 12.11.2026). RSS-i pole ja otsing laeb tulemused skriptiga, seepärast loeb
# otsing video lehti id järgi: alates viimasest nähtud id-st kuni UTTV_SAMM lehte või UTTV_TUHI järjestikust tühja lehte.
UTTV_LEHT = "https://uttv.ee/pls/uttv/naita?id={}"
UTTV_SAMM = 80
UTTV_TUHI = 20


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


def _puhas(tekst):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", tekst or ""))).strip()


# Podcasti kirjelduse lõpus on sponsorid ja kontaktid („Fin: AI agent for customer service“), mis ei ütle osa teema kohta midagi.
REKLAAM = re.compile(r"Thank you for listening|Check out our sponsors|SPONSORS:|#ad\b|Support Mindscape|Blog post with", re.I)


def podcasti_voog(xml_tekst, allikas, tee=None):
    """Podcasti RSS-voo osad (Kadri 27.11.2026: podcastid automaatselt). [{id, pealkiri, avaldatud, url, kirjeldus,
    tekst_url}]. tee: ainult osad, mille link sisaldab seda teed (nt Mindscape'i voos on ka blogipostitused).
    tekst_url on osa transkriptsioon (Lex Fridman: link kirjelduses; Mindscape: osa leht ise), nii et kokkuvõte
    ei vaja Kadri arvutit."""
    from email.utils import parsedate_to_datetime

    def silt(osa, nimi):  # regex, mitte XML-parser: voogudes on puuduvaid nimeruumide kirjeldusi ja muud lohakust
        m = re.search(rf"<{nimi}\b[^>]*>(.*?)</{nimi}>", osa, re.S | re.I)
        return re.sub(r"^\s*<!\[CDATA\[(.*)\]\]>\s*$", r"\1", m.group(1), flags=re.S).strip() if m else ""

    read = []
    for it in re.findall(r"<item\b.*?</item>", xml_tekst, re.S | re.I):
        url = html.unescape(silt(it, "link")).split("?")[0]
        if not url or (tee and tee not in url):
            continue
        sisu = silt(it, "description") + " " + silt(it, "content:encoded")
        try:
            kp = parsedate_to_datetime(silt(it, "pubDate")).date().isoformat()
        except (TypeError, ValueError):
            kp = ""
        m = re.search(r'href="(https?://[^"]+-transcript)/?"', sisu)
        slug = url.rstrip("/").rsplit("/", 1)[-1][:60]
        read.append({"id": f"{allikas}-{slug}", "allikas": allikas, "pealkiri": _puhas(silt(it, "title")),
                     "avaldatud": kp, "url": url, "kirjeldus": REKLAAM.split(_puhas(sisu), 1)[0][:1500],
                     "tekst_url": m.group(1) if m else url})
    return read


def lehe_videod(html, allikas):
    """Seminarilehe YouTube'i lingid (TÜ andmeteaduse seminar): [{id, url}] lehe järjekorras."""
    ids = []
    for m in re.finditer(r'href="https?://(?:www\.)?(?:youtu\.be/|youtube\.com/watch\?v=)([\w-]{11})', html):
        if m.group(1) not in ids:
            ids.append(m.group(1))
    return [{"id": i, "allikas": allikas, "pealkiri": "", "avaldatud": "", "url": f"https://www.youtube.com/watch?v={i}", "kirjeldus": ""} for i in ids]


def uttv_video(html, vid, allikas="uttv"):
    """UTTV video leht → kandidaat või None (lehte pole või kuupäeva ei leitud)."""
    keha = re.sub(r"<(script|style)\b.*?</\1>", " ", html, flags=re.S | re.I)
    m_kp = re.search(r"\b(\d{2})\.(\d{2})\.(\d{4})\b", re.sub(r"<[^>]+>", " ", keha))
    if not m_kp:
        return None
    m_p = re.search(r"<h4[^>]*>(.*?)</h4>", keha, re.S | re.I)
    tekst = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", keha)).strip()
    pealkiri = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", m_p.group(1))).strip() if m_p else ""
    if not pealkiri or pealkiri.lower().startswith("otsingu"):
        pealkiri = tekst.split(" Embed ")[0].replace("Avaleht Videod Fotod Teenused", "").strip()[:160]
    return {"id": f"uttv-{vid}", "allikas": allikas, "pealkiri": pealkiri,
            "avaldatud": f"{m_kp.group(3)}-{m_kp.group(2)}-{m_kp.group(1)}", "url": UTTV_LEHT.format(vid), "kirjeldus": tekst[:1500]}


def uttv_uued(alates, get=_get, samm=UTTV_SAMM, tuhi=UTTV_TUHI, allikas="uttv"):
    """Uued UTTV videod alates id-st `alates` (välja arvatud). Tagastab (videod, suurim leitud id)."""
    read, suurim, tyhju = [], alates, 0
    for vid in range(alates + 1, alates + 1 + samm):
        try:
            r = uttv_video(get(UTTV_LEHT.format(vid)), vid, allikas)
        except Exception:  # noqa: BLE001 — puuduv leht või võrguviga loeb tühjaks
            r = None
        if r is None:
            tyhju += 1
            if tyhju >= tuhi:
                break
            continue
        tyhju, suurim = 0, vid
        read.append(r)
    return read, suurim


def teemas(r):
    return bool(TEEMA.search(r["pealkiri"] + " " + r.get("kirjeldus", "")))


def valjas(r):
    """Kursuse tund, tseremoonia või kokkuvõttevideo: ei tule kandidaadiks ka teemakanalilt."""
    return bool(VALJA.search(r["pealkiri"]))


def hinda(r):
    """Uue video olek: „uus“ (teemas või teemakanalilt) või „teemaväline“."""
    if valjas(r):
        return "teemaväline"
    return "uus" if r.get("filter") is False or teemas(r) else "teemaväline"


def soelu_uuesti(kandidaadid, kanalid, tana):
    """Hindab enne SOEL_ALATES leitud ootel („uus“) kandidaadid uue sõelaga ümber. Ainult pealkirja järgi, sest kirjeldust
    failis pole; seepärast ei puuduta hilisemaid kandidaate, mida hinnati juba kirjeldusega. Kordamisel ei muuda midagi.
    Tagastab teemaväliseks märgitud id-d. Vanad ja teemavälised kandidaadid ei muutu."""
    filtrita = {k["id"] for k in kanalid if k.get("filter") is False}
    valja = []
    for k in kandidaadid:
        if k.get("olek") != "uus" or k.get("leitud", "") >= SOEL_ALATES:
            continue
        r = {"pealkiri": html.unescape(k.get("pealkiri", "")), "filter": False if k["allikas"] in filtrita else True}
        if hinda(r) == "teemaväline":
            k.update({"olek": "teemaväline", "soelutud": tana.isoformat()})
            valja.append(k["id"])
    return valja


def tuntud_videod(tuntud_fail=None):
    """Saidil juba olevate ettekannete id-d ja YouTube'i video id-d (neile kandidaati ega teksti ei tehta)."""
    tuntud_fail = tuntud_fail or TUNTUD
    if not tuntud_fail.exists():
        return set()
    d = json.loads(tuntud_fail.read_text(encoding="utf-8"))
    ids = set()
    for r in d.get("ettekanded", []):
        ids.add(r.get("id", ""))
        m = re.search(r"(?:youtu\.be/|v=)([\w-]{11})", r.get("video", ""))
        if m:
            ids.add(m.group(1))
        if r.get("uritus_url"):  # podcasti osa leht (Lex Fridman, Mindscape)
            ids.add(r["uritus_url"].split("?")[0].split("#")[0])
    return ids - {""}


def uuenda(kandidaadid, leitud, tuntud, tana, esimene):
    """Lisab uued videod kandidaatide hulka. Tagastab uute kandidaatide id-d (olek „uus“)."""
    olemas = {k["id"] for k in kandidaadid}
    uued = []
    piir = (tana - dt.timedelta(days=VANUS_PAEVI)).isoformat()
    for r in leitud:
        if r["id"] in olemas or r["id"] in tuntud or r.get("url") in tuntud:
            continue
        olemas.add(r["id"])
        vana = esimene or (r["avaldatud"] and r["avaldatud"] < piir)
        olek = "vana" if vana else hinda(r)
        k = {kk: r[kk] for kk in ("id", "allikas", "pealkiri", "avaldatud", "url", "tekst_url") if kk in r}
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


def vajab_teksti_teade(kandidaadid):
    """Valju teade, kui ootel kandidaatidel pole teksti (ADR-1). GitHub näitab ::warning:: rida töö kokkuvõttes."""
    n = sum(1 for k in kandidaadid if k.get("olek") == "uus" and not k.get("tekst_url") and (
        k.get("vajab_teksti") or k.get("subtiitrid") is False or k["id"].startswith("uttv-")))
    if not n:
        return "Kõigil uutel kandidaatidel on tekst või neid pole"
    return (f"::warning::{n} ootel ettekandel pole teksti (pilv ei saa YouTube'i subtiitreid, UTTV-l neid pole). "
            "Tee tekstid oma arvutis: python3 tehisaru-seire/sait/tee_tekstid.py")


def main(argv):
    sub = Path(argv[argv.index("--subtiitrid") + 1]) if "--subtiitrid" in argv else None
    tana = dt.date.today()
    K = json.loads(KANALID.read_text(encoding="utf-8"))
    esimene = not KANDIDAADID.exists()
    olek = json.loads(KANDIDAADID.read_text(encoding="utf-8")) if not esimene else {"kandidaadid": [], "kanalid": {}}
    leitud, vead = [], []
    for k in K["kanalid"]:
        try:
            if k.get("uttv_alates"):
                rr, suurim = uttv_uued(int(olek["kanalid"].get(k["id"]) or k["uttv_alates"]), allikas=k["id"])
                olek["kanalid"][k["id"]] = suurim
            elif k.get("rss"):
                rr = podcasti_voog(_get(k["rss"]), k["id"], k.get("rss_tee"))
            elif k.get("leht"):
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
    soelutud = soelu_uuesti(olek["kandidaadid"], K["kanalid"], tana)
    if soelutud:
        print(f"SÕEL: {len(soelutud)} varem leitud ootel kandidaati märgiti teemaväliseks")
    uued = uuenda(olek["kandidaadid"], leitud, tuntud_videod(), tana, esimene)
    for k in olek["kandidaadid"]:
        if k["id"] in uued and not k["pealkiri"]:
            k["pealkiri"] = oembed_pealkiri(k["url"])
        if k["id"] in uued and sub is not None and not k.get("tekst_url"):
            try:
                k["subtiitrid"] = subtiitrid(k["id"], sub)
            except Exception:
                k["subtiitrid"] = False
        if k["id"] in uued and not k.get("tekst_url") and (k.get("subtiitrid") is False or k["id"].startswith("uttv-")):
            k["vajab_teksti"] = True  # ADR-1: tekst tehakse Kadri arvutis (sait/tee_tekstid.py)
    olek["kandidaadid"] = sorted(olek["kandidaadid"], key=lambda k: (k["leitud"], k["avaldatud"]), reverse=True)[:500]
    olek.update({"uuendatud": tana.isoformat(), "vead": vead})
    KANDIDAADID.write_text(json.dumps(olek, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"UUSI KANDIDAATE {len(uued)}" + (" (esimene jooks: kõik märgiti vanaks)" if esimene else ""))
    print(vajab_teksti_teade(olek["kandidaadid"]))
    for k in olek["kandidaadid"]:
        if k["id"] in uued:
            print(f"UUS {k['allikas']} {k['avaldatud']} {k['url']} {k['pealkiri'][:100]}")
    return 1 if len(vead) == len(K["kanalid"]) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
