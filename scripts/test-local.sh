#!/usr/bin/env bash
# Lance les tests du backend local (Colombie).
# Prérequis : Postgres dédié aux tests (futurekawa_local_test) accessible sur localhost:5432.
set -euo pipefail

racine="$(cd "$(dirname "$0")/.." && pwd)"
cd "$racine/local-country/backend"
mkdir -p "$racine/rapports"
../.venv/bin/python -m pytest -v --junitxml="$racine/rapports/junit-local.xml" "$@"