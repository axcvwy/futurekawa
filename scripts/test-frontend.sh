#!/usr/bin/env bash
# Tests UI (Vitest) + build de production du frontend central.
set -euo pipefail

racine="$(cd "$(dirname "$0")/.." && pwd)"
cd "$racine/central-frontend"
mkdir -p "$racine/rapports"
npm run test -- --run --reporter=junit --outputFile="$racine/rapports/junit-frontend.xml"
npm run build
echo "Frontend : tests UI + build OK."