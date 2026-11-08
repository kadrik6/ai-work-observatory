#!/usr/bin/env bash
# Viib saidi igapäevaste kogumiste hetkeseisu (uudised, väited, koondajad, AI-kuulutused, hanked, publikatsioonid)
# main harusse, et Vercel ehitaks saidi uuesti. Kadri otsus 8.11.2026: igapäevane töö push'ib ise.
#
#   bash tehisaru-seire/sait/sisu_maini.sh [PROJEKTI_KAUST] [--ilma-pushita]
#
# Käivita PUHTAS koopias (nt git worktree origin/main peal), mitte töökaustas, kus on pooleli muudatusi.
# Commit'i tuleb ainult kaust tehisaru-seire/sait/sisu/. Enne commit'i: sait ehitub, testid ja turvakontroll läbivad.
# Kui midagi kukub, commit'i ega push'i ei tule ja skript lõpetab veakoodiga.
set -euo pipefail
PROJ="${1:-${PROJEKTI_KAUST:-/mnt/project-files}}"
PUSH=1
[ "${2:-}" = "--ilma-pushita" ] && PUSH=0
cd "$(git rev-parse --show-toplevel)"
if [ -n "$(git status --porcelain)" ]; then echo "VIGA: koopias on pooleli muudatusi" >&2; exit 1; fi
git fetch -q origin main
git checkout -q --detach origin/main
python3 tehisaru-seire/sait/vota_kaasa.py "$PROJ"
( cd tehisaru-seire && python3 sait/ehita.py > /dev/null && python3 -m pytest -q -p no:cacheprovider )
git add tehisaru-seire/sait/sisu
if git diff --cached --quiet; then echo "SISU muutusi pole"; exit 0; fi
python3 turvakontroll/kontrolli.py
muud="$(git status --porcelain | grep -v '^M  tehisaru-seire/sait/sisu/' | grep -v '^A  tehisaru-seire/sait/sisu/' || true)"
if [ -n "$muud" ]; then echo "VIGA: muutus ka midagi peale sait/sisu:" >&2; echo "$muud" >&2; exit 1; fi
git -c user.name="seire-igapaevane" -c user.email="seire-igapaevane@users.noreply.github.com" \
    commit -q -m "Andmed: uudised, hanked ja publikatsioonid $(date -u +%F)"
git diff --stat HEAD~1 HEAD | tail -1
if [ "$PUSH" = 1 ]; then git push -q origin HEAD:main && echo "SISU main harus: $(git rev-parse --short HEAD)"; else echo "SISU commit tehtud, push jäi vahele"; fi
