#!/usr/bin/env bash
# Lance les tests du backend local (Colombie).
# Prérequis : Postgres dédié aux tests (futurekawa_local_test) accessible sur localhost:5432.
set -euo pipefail

cd "$(dirname "$0")/../local-country/backend"
../.venv/bin/python -m pytest -v "$@"