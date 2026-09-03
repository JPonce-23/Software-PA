#!/usr/bin/env bash
set -euo pipefail

export MIGRATIONS_DIR="${MIGRATIONS_DIR:-/opt/software-pa/migrations}"
export PSQL_BIN="${PSQL_BIN:-psql}"

/opt/software-pa/scripts/run_migrations.sh
