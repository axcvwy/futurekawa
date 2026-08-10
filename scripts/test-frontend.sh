#!/usr/bin/env bash
# Tests UI (Vitest) + build de production du frontend central.
set -euo pipefail

cd "$(dirname "$0")/../central-frontend"
npm run test
npm run build
echo "Frontend : tests UI + build OK."