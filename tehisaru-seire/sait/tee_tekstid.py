"""Ettekannete tekstid Kadri arvutis (ADR-1, Kadri 14.11.2026).

YouTube ei anna subtiitreid GitHub Actionsile ega pilvele ja UTTV videotel subtiitreid pole. Seepärast teeb tekstid
see skript Kadri arvutis. Tekstid lähevad repost välja (vaikimisi ~/seire-tekstid) ja sealt zip-failina seire saidi
vestlusesse, kus Claude kirjutab kokkuvõtte mustandid. Repo ega saiti skript ei muuda.

  python3 tehisaru-seire/sait/tee_tekstid.py                      # kõik ootel kandidaadid (olek „uus“)
  python3 tehisaru-seire/sait/tee_tekstid.py --id uttv-43880 JMw4WSis80k   # ainult need
  python3 tehisaru-seire/sait/tee_tekstid.py --kaust ~/muu-kaust --kuni 5

Vajab: yt-dlp ja ffmpeg; kui subtiitreid pole, siis ka faster-whisper (pip install faster-whisper).
Iga video tekst on fail <id>.txt ridadega „[h:mm:ss] tekst“. Juba tehtud tekste uuesti ei tee.
Kokkuvõte on failis ulevaade.json (mis õnnestus, mis meetodiga, mis jäi tegemata ja miks).
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

SIIN = Path(__file__).resolve().parent
sys.path.insert(0, str(SIIN))
from lae_ettekanded import KANDIDAADID, UTTV_LEHT, tuntud_videod  # noqa: E402  (üks koht, mitte koopia)
REPO = SIIN.parents[1]
WHISPER_MUDEL = "small"  # sülearvutis mõistlik kiirus; eesti keel tuleb loetav, nimed võivad vigaseks jääda


def video_url(vid):
    """Kandidaadi id → video aadress (UTTV id-l on ees „uttv-“, YouTube'il 11 märki)."""
    if vid.startswith("uttv-"):
        return UTTV_LEHT.format(vid.split("-", 1)[1])
    return f"https://www.youtube.com/watch?v={vid}"


def vali(kandidaadid, tuntud, soovitud=None, kuni=None):
    """Millistest videotest teksti teha: soovitud id-d või kõik „uus“ kandidaadid, mida saidil veel pole."""
    if soovitud:
        olemas = {k["id"]: k for k in kandidaadid}
        valik = [olemas.get(v, {"id": v, "allikas": "", "pealkiri": "", "url": video_url(v)}) for v in soovitud]
    else:
        valik = [k for k in kandidaadid if k.get("olek") == "uus" and k["id"] not in tuntud]
    return valik[:kuni] if kuni else valik


def aeg(sek):
    sek = int(sek)
    return f"{sek // 3600}:{sek // 60 % 60:02d}:{sek % 60:02d}"


def vtt_read(vtt):
    """WebVTT → read „[h:mm:ss] tekst“. YouTube'i automaatsubtiitrid kordavad eelmist rida, kordused jäävad välja."""
    read, eelmine = [], ""
    for plokk in re.split(r"\n\s*\n", vtt.replace("\r", "")):
        m = re.search(r"(\d+):(\d{2}):(\d{2})[.,]\d{3}\s*-->", plokk) or re.search(r"(?m)^()(\d{2}):(\d{2})[.,]\d{3}\s*-->", plokk)
        if not m:
            continue
        sek = int(m.group(1) or 0) * 3600 + int(m.group(2)) * 60 + int(m.group(3))
        tekstiread = plokk[plokk.index("-->"):].split("\n")[1:]
        for t in tekstiread:
            t = re.sub(r"<[^>]+>", "", t).replace("&nbsp;", " ").replace("&amp;", "&").strip()
            if t and t != eelmine:
                read.append(f"[{aeg(sek)}] {t}")
                eelmine = t
    return read


def kaust_repost_valjas(kaust, repo=REPO):
    """Transkriptsioonid ei tohi minna repo (CLAUDE.md): kaust peab olema väljaspool repot."""
    k, r = Path(kaust).expanduser().resolve(), Path(repo).resolve()
    return k != r and r not in k.parents


def _jooks(kask, aeg_s=3600):
    return subprocess.run(kask, capture_output=True, text=True, timeout=aeg_s)


def subtiitritest(url, tmp):
    r = _jooks(["yt-dlp", "--skip-download", "--write-subs", "--write-auto-subs", "--sub-langs", "et.*,en.*",
                "--sub-format", "vtt", "-o", str(tmp / "v.%(ext)s"), url], 300)
    failid = sorted(tmp.glob("v*.vtt"), key=lambda p: (".et" not in p.name, ".en-orig" not in p.name))
    if r.returncode != 0 or not failid:
        return None
    read = vtt_read(failid[0].read_text(encoding="utf-8", errors="ignore"))
    return read or None


def meedia_lingid(html):
    """UTTV lehelt otsese mp4- või m3u8-lingi otsimine, kui yt-dlp lehte ise ei tunne."""
    return list(dict.fromkeys(re.findall(r"https?://[^\"'\s<>]+?\.(?:mp4|m3u8)[^\"'\s<>]*", html)))


def heli(url, tmp):
    for allikas in [url] + (meedia_lingid(_loe(url)) if "uttv.ee" in url else []):
        r = _jooks(["yt-dlp", "-x", "--audio-format", "m4a", "-o", str(tmp / "heli.%(ext)s"), allikas], 3600)
        failid = list(tmp.glob("heli.*"))
        if r.returncode == 0 and failid:
            return failid[0]
    return None


def _loe(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (seire tekstid)"})
        return urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "ignore")
    except Exception:
        return ""


def whisperiga(fail, keel=None):
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        raise RuntimeError("faster-whisper puudub: pip install faster-whisper")
    mudel = WhisperModel(WHISPER_MUDEL, device="auto", compute_type="int8")
    osad, _ = mudel.transcribe(str(fail), language=keel, vad_filter=True)
    return [f"[{aeg(o.start)}] {o.text.strip()}" for o in osad if o.text.strip()]


def tee_tekst(k, kaust):
    """Ühe video tekst. Tagastab ülevaate rea."""
    url = k.get("url") or video_url(k["id"])
    rida = {"id": k["id"], "pealkiri": k.get("pealkiri", ""), "url": url}
    valja = kaust / f"{k['id']}.txt"
    if valja.exists() and valja.stat().st_size > 0:
        return {**rida, "olek": "olemas"}
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        try:
            read, meetod = (subtiitritest(url, tmp) if "youtube.com" in url else None), "subtiitrid"
            if not read:
                fail = heli(url, tmp)
                if not fail:
                    return {**rida, "olek": "viga", "viga": "videot ega heli ei saanud kätte"}
                read, meetod = whisperiga(fail), f"whisper-{WHISPER_MUDEL}"
        except Exception as ex:  # üks video ei tohi teisi peatada
            return {**rida, "olek": "viga", "viga": str(ex)[:300]}
    if not read:
        return {**rida, "olek": "viga", "viga": "tekst jäi tühjaks"}
    valja.write_text("\n".join(read) + "\n", encoding="utf-8")
    return {**rida, "olek": "tehtud", "meetod": meetod, "ridu": len(read)}


def main(argv=None):
    a = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    a.add_argument("--kaust", default="~/seire-tekstid", help="kuhu tekstid lähevad (väljaspool repot)")
    a.add_argument("--id", nargs="*", default=None, help="ainult need id-d (nt uttv-43880 JMw4WSis80k)")
    a.add_argument("--kuni", type=int, default=None, help="kõige rohkem nii mitu videot")
    p = a.parse_args(argv)
    kaust = Path(p.kaust).expanduser().resolve()
    if not kaust_repost_valjas(kaust):
        print(f"VIGA: {kaust} on repo sees. Transkriptsioonid ei lähe repo; vali kaust väljaspool repot.")
        return 2
    if not shutil.which("yt-dlp"):
        print("VIGA: yt-dlp puudub. Paigalda: pip install yt-dlp (ja ffmpeg)")
        return 2
    kandidaadid = json.loads(KANDIDAADID.read_text(encoding="utf-8"))["kandidaadid"] if KANDIDAADID.exists() else []
    valik = vali(kandidaadid, tuntud_videod(), p.id, p.kuni)
    if not valik:
        print("Ootel kandidaate pole. Uuenda repo (git pull) või anna id-d: --id ...")
        return 0
    kaust.mkdir(parents=True, exist_ok=True)
    ulevaade = []
    for i, k in enumerate(valik, 1):
        print(f"[{i}/{len(valik)}] {k['id']} {k.get('pealkiri', '')[:70]}", flush=True)
        r = tee_tekst(k, kaust)
        print(f"    {r['olek']}" + (f": {r['viga']}" if r.get("viga") else f" ({r.get('meetod', '')})"), flush=True)
        ulevaade.append(r)
    (kaust / "ulevaade.json").write_text(json.dumps(ulevaade, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    zipitee = kaust.with_suffix(".zip")
    with zipfile.ZipFile(zipitee, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(kaust.glob("*.txt")) + [kaust / "ulevaade.json"]:
            z.write(f, f.name)
    ok = sum(r["olek"] in ("tehtud", "olemas") for r in ulevaade)
    print(f"\nValmis: {ok}/{len(ulevaade)} teksti. Laadi {zipitee} seire saidi vestlusesse.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
