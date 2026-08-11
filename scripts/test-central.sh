#!/usr/bin/env bash
# Lance les tests du backend central (Siège).
# Prérequis : Postgres dédié aux tests (futurekawa_central_test) accessible sur localhost:5432.
set -euo pipefail

racine="$(cd "$(dirname "$0")/.." && pwd)"
cd "$racine/central-backend"
mkdir -p "$racine/rapports"
venv/bin/python -m pytest -v --junitxml="$racine/rapports/junit-central.xml" "$@"