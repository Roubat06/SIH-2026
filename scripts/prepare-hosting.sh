#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
mkdir -p "$project_root/.openai"
cp "$project_root/web-host/hosting.json" "$project_root/.openai/hosting.json"
echo "Prepared .openai/hosting.json from web-host/hosting.json"
