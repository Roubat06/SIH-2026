#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_dir"

command -v python3 >/dev/null || { echo "python3 is required" >&2; exit 1; }
command -v pnpm >/dev/null || { echo "pnpm is required" >&2; exit 1; }

test -s backend/requirements.lock.txt
test -s frontend/pnpm-lock.yaml
test -s compose.yaml
test -s Dockerfile

if [[ ! -x .venv/bin/python ]]; then
  echo "Create .venv and install backend/requirements-dev.txt before running preflight." >&2
  exit 1
fi

echo "Checking backend imports..."
PYTHONPATH=backend .venv/bin/python -m compileall -q backend/app

echo "Running backend tests..."
PYTHONPATH=backend .venv/bin/python -m pytest backend/tests -q

echo "Installing locked frontend dependencies..."
pnpm --dir frontend install --frozen-lockfile --ignore-scripts

echo "Building the production frontend..."
pnpm --dir frontend run build

if command -v docker >/dev/null && docker compose version >/dev/null 2>&1; then
  if [[ ! -f .env ]]; then
    echo "Copy .env.example to .env and replace its secret placeholders before validating Compose." >&2
    exit 1
  fi
  if grep -q 'replace_with_' .env; then
    echo "Replace every secret placeholder in .env before deployment." >&2
    exit 1
  fi
  echo "Validating Docker Compose configuration..."
  docker compose config --quiet
else
  echo "Docker Compose is unavailable; container configuration validation was skipped."
fi

echo "Preflight completed successfully."
