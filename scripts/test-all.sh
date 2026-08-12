#!/usr/bin/env bash
# Suite complète : backend local + backend central + frontend.
# Utilisation : ./scripts/test-all.sh
set -euo pipefail

racine="$(cd "$(dirname "$0")/.." && pwd)"
date_debut=$(date +%s)

echo "  1/3  Backend local (Pays) - pytest"
"$racine/scripts/test-local.sh"

echo
echo "  2/3  Backend central (Siège) - pytest"
"$racine/scripts/test-central.sh"

echo
echo "  3/3  Frontend central - Vitest + build"
"$racine/scripts/test-frontend.sh"

date_fin=$(date +%s)
echo
echo "  Toutes les suites sont passées. ($((date_fin - date_debut))s)"
