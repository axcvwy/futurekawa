#!/usr/bin/env bash
# Lance les tests du backend central (Siège).
# Prérequis : Postgres dédié aux tests (futurekawa_central_test) accessible sur localhost:5432.
set -euo pipefail

cd "$(dirname "$0")/../central-backend"
venv/bin/python -m pytest -v "$@"