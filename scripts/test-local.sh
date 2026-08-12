#!/usr/bin/env bash
set -euo pipefail

racine="$(cd "$(dirname "$0")/.." && pwd)"
cd "$racine/local-country/backend"
mkdir -p "$racine/rapports"
../.venv/bin/python -m pytest -v --junitxml="$racine/rapports/junit-local.xml" "$@"