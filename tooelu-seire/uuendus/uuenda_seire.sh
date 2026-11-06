#!/usr/bin/env bash
# Seire saidi (artefakt MKUSmw6WrrQFoidzARqsyd) igapäevane uuendus. Lisatud 5.11.2026 (Kadri: seire andmed peavad ise uuenema).
#
# Kasutus: bash uuenda_seire.sh TOOKAUST
#   TOOKAUST = ajutine kaust (nt sessiooni scratchpad/seire-too); kirjutatakse üle.
# Mida teeb:
#   1. võtab repo main-haru värske koodi (git archive, repo ennast ei muuda),
#   2. laeb numbrid otse allikatest (run.py: Eurostat, Statistikaamet; lae_valis.py: OECD, ILO, Põhjamaade ametid jt),
#   3. ehitab saidi (raportid/koosta.py), lisab avalehe fotod, lehe „Tehisaru ja töö“ (tooelu-leht-andmed) ja
#      osa „Mis toimub“ (lisalehed.py: Eurostati töötus, koondamised, AI-hanked hanked/leht.json, uudised),
#   4. kirjutab TOOKAUST/html (avaldamiseks), TOOKAUST/uued-numbrid ja $SEIRE_UUENDUS/seis.json.
# Kood on repos (tooelu-seire/uuendus/); andmed on väljas: SEIRE_UUENDUS (vaikimisi /mnt/project-files/seire-uuendus),
# UUDISED (tooelu-uudised), fotod ja „Tehisaru ja töö“ leht (tooelu-leht-andmed).
# Repo andmefaile see ei commit'i ega push'i: värsked numbrid elavad ainult avaldatud lehel.
# Kui mõni samm kukub, lõpetab veaga ja lehte ei tohi avaldada.
set -euo pipefail
TOO="${1:?anna töökaust}"
SIIN="$(cd "$(dirname "$0")" && pwd)"
REPO="${SEIRE_REPO:-$(cd "$SIIN/../.." && pwd)}"
ANDMED="${UUENDUS_ANDMED:-/mnt/project-files}"
DATA="${SEIRE_UUENDUS:-$ANDMED/seire-uuendus}"
FOTOD="${SEIRE_FOTOD:-$ANDMED/ai-work-observatory/tehisaru-seire/raportid/fotod}"
TOOELU="$ANDMED/tooelu-leht-andmed/tehisaru-ja-too-uhine.html"

if [ ! -d "$REPO/.git" ]; then
  git clone -q https://github.com/kadrik6/ai-work-observatory.git "$REPO"
fi
git -C "$REPO" fetch -q origin main
rm -rf "$TOO"; mkdir -p "$TOO"
KOOD=$(git -C "$REPO" rev-parse origin/main)
git clone -q --no-checkout "$REPO" "$TOO/repo"
git -C "$TOO/repo" checkout -q --detach "$KOOD"
KOOD=${KOOD:0:7}

cd "$TOO/repo/tehisaru-seire"
python3 run.py > "$TOO/run.log" 2>&1 || { tail -20 "$TOO/run.log"; echo "VIGA: run.py"; exit 1; }
python3 kataloog/lae_valis.py > "$TOO/valis.log" 2>&1 || { tail -20 "$TOO/valis.log"; echo "VIGA: lae_valis.py"; exit 1; }
# Uued või muutunud numbrid võrreldes repo main-haruga (sama kontroll nagu seire.yml; kuupäevamuutus ei loe)
python3 kataloog/uued_numbrid.py --valjund "$TOO/uued-numbrid" > /dev/null

mkdir -p raportid/fotod
cp "$FOTOD"/*.jpg raportid/fotod/ 2>/dev/null || echo "HOIATUS: fotosid ei leitud ($FOTOD)"
python3 raportid/koosta.py > "$TOO/koosta.log" 2>&1 || { tail -20 "$TOO/koosta.log"; echo "VIGA: koosta.py"; exit 1; }
mv raportid/html "$TOO/html"
# Avalehe pealkiri raamatukogus (artefaktide nimede reegel: "ID · Nimi")
sed -i 's|<title>Tehisaru seire</title>|<title>SEIRE · Tehisaru seire</title>|' "$TOO/html/index.html"
if [ -f "$TOOELU" ]; then cp "$TOOELU" "$TOO/html/tehisaru-ja-too.html"; else echo "HOIATUS: $TOOELU puudub, Tehisaru ja töö lehte ei uuendata"; fi
# AI-hangete tellija tuletus (KURSUS-i kood): haru hanked/tuvastus, pärast liitmist main
mkdir -p "$DATA/hanked"
( git -C "$REPO" fetch -q origin hanked/tuvastus 2>/dev/null && git -C "$REPO" show FETCH_HEAD:hanked/tellija.py > "$DATA/hanked/tellija.py" ) \
  || git -C "$REPO" show origin/main:hanked/tellija.py > "$DATA/hanked/tellija.py" 2>/dev/null || echo "HOIATUS: hanked/tellija.py puudub"
# Osa „Mis toimub“ (tööturg, koondamised, AI-hanked, uudised) ja selle link kõigi lehtede osade ribale (Kadri 5.11.2026)
python3 "$SIIN/lisalehed.py" "$TOO/html" || { echo "VIGA: lisalehed.py"; exit 1; }

python3 - "$TOO" "$KOOD" "$DATA/seis.json" <<'PY'
import json, sys, datetime
too, kood, valja = sys.argv[1:]
uued = json.load(open(f"{too}/uued-numbrid/uued-numbrid.json", encoding="utf-8"))
lehe = {"EE", "EU27_2020", "FI", "SE", "DK", "NO", "DE", "NL"}
def riik(l):
    return l["voti"][1] if l["fail"].startswith("kataloog/") else l["voti"][0]
seis = {"kuupaev": datetime.date.today().isoformat(), "kood": kood,
        "uusi_numbreid": len(uued), "uusi_eesti_ja_vordlusriigid": sum(riik(l) in lehe for l in uued),
        "uued": [f"{l['fail']} {' · '.join(l['voti'])}: {l['vana'] or '–'} → {l['uus']}" for l in uued][:40]}
json.dump(seis, open(valja, "w"), ensure_ascii=False, indent=1)
print("valmis:", json.dumps(seis, ensure_ascii=False))
PY
ls "$TOO/html"
