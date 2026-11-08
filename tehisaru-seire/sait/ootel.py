"""Kinnitusjärjekord: automaatsed uuringu- ja väitemustandid lähevad saidile alles pärast Kadri „jah“-i
(Kadri otsus 8.11.2026 21:36, „Ootavad kinnitust“).

Mustandid kirjutab igapäevane töö projekti kausta:
  tooelu-leht-andmed/leiud-lisa.json  → „uuringud“ (uuringu leid ja kokkuvõte)
  tooelu-uudised/vaited.json          → väited (hinnang algallika vastu)
  seire-uks-sait/ettekanded.json      → usaldatud ürituste ettekanded (kokkuvõte oma sõnadega)
Kirje olek on väljal „seire_olek“: puudub = ootel, „kinnitatud“, „tagasi“ (ei lähe saidile) või „varasem“
(väide oli saidil enne kinnituskorda). sait/vota_kaasa.py võtab saidile ainult kinnitatud (ja varasemad) kirjed.

Kasutus:
  python3 sait/ootel.py KAUST                     # nimekiri; kirjutab ka KAUST/seire-uks-sait/ootel.md
  python3 sait/ootel.py KAUST kinnita ID [ID ...] # „koik“ kinnitab kõik ootel kirjed
  python3 sait/ootel.py KAUST tagasi ID [ID ...]
"""
import datetime as dt
import json
import sys
from pathlib import Path

FAILID = {"uuring": ("tooelu-leht-andmed/leiud-lisa.json", "uuringud"), "vaide": ("tooelu-uudised/vaited.json", None),
          "ettekanne": ("seire-uks-sait/ettekanded.json", "ettekanded")}  # ettekanded: Kadri 8.11.2026


def _loe(kaust, liik):
    rel, voti = FAILID[liik]
    p = Path(kaust) / rel
    if not p.exists():
        return p, None, []
    d = json.loads(p.read_text(encoding="utf-8"))
    return p, d, (d[voti] if voti else d)


def kirjed(kaust):
    """[(liik, kirje)] kõigist failidest."""
    return [(liik, r) for liik in FAILID for r in _loe(kaust, liik)[2]]


def ootel(kaust):
    return [(liik, r) for liik, r in kirjed(kaust) if not r.get("seire_olek")]


def muuda(kaust, olek, idd, tana=None):
    """Paneb kirjetele oleku. idd = ["koik"] muudab kõik ootel kirjed. Tagastab muudetud id-d."""
    tana = tana or dt.date.today().isoformat()
    koik = idd == ["koik"]
    leitud = []
    for liik in FAILID:
        p, d, read = _loe(kaust, liik)
        muutus = False
        for r in read:
            if (koik and not r.get("seire_olek")) or (not koik and r["id"] in idd):
                r["seire_olek"], r["seire_kinnitatud"] = olek, tana
                leitud.append(r["id"])
                muutus = True
        if muutus:
            p.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    puudu = [] if koik else [i for i in idd if i not in leitud]
    if puudu:
        raise SystemExit(f"Ei leidnud: {', '.join(puudu)}")
    return leitud


def kokkuvote(kaust):
    """Markdown: mis ootab kinnitust."""
    read = ootel(kaust)
    out = [f"# Ootab kinnitust ({len(read)})", "",
           "Vasta lõimes „jah ID“ (või „jah kõik“) või „tagasi ID“. Saidile lähevad ainult kinnitatud kirjed.", ""]
    for liik, r in read:
        if liik == "uuring":
            out += [f"## {r['id']} · uuring", f"{r.get('autorid', '')} {r.get('aasta', '')}: {r.get('pealkiri', '')}",
                    f"- Kus: {r.get('kus', '')}; meetod: {r.get('meetod', '')}; valim: {r.get('valim', '')}",
                    f"- Leid: {r.get('leid', '')}", f"- Link: {r.get('url', '')}", ""]
        elif liik == "ettekanne":
            out += [f"## {r['id']} · ettekanne", f"{r.get('esineja', '')}: {r.get('pealkiri', '')} ({r.get('uritus', '')}, {r.get('kuupaev', '')})",
                    f"- Kokkuvõte: {r.get('kokkuvote', '')}", f"- Video: {r.get('video', '')}", ""]
        else:
            out += [f"## {r['id']} · väide", f"„{r.get('vaide', '')}“ ({r.get('kes', '')})",
                    f"- Hinnang: {r.get('hinnang', '')}", f"- Kokkuvõte: {r.get('kokkuvote', '')}",
                    f"- Link: {r.get('kes_url', '')}", ""]
    return "\n".join(out)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    kaust = sys.argv[1]
    if len(sys.argv) > 2:
        kask, idd = sys.argv[2], sys.argv[3:]
        olek = {"kinnita": "kinnitatud", "tagasi": "tagasi"}.get(kask)
        if not olek or not idd:
            sys.exit(__doc__)
        print(f"{olek}: {', '.join(muuda(kaust, olek, idd)) or 'midagi polnud ootel'}")
    md = kokkuvote(kaust)
    siht = Path(kaust) / "seire-uks-sait" / "ootel.md"
    if siht.parent.exists():
        siht.write_text(md + "\n", encoding="utf-8")
    print(md)
