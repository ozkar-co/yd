#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
if [[ ! -d .venv ]]; then
  echo "falta .venv — make setup" >&2
  exit 1
fi
exec "$ROOT/.venv/bin/python" "$ROOT/main.py" "$@"
