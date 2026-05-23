#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
ROOT="$(pwd)"
PY="$ROOT/installers/runtime/linux/python/bin/python3"
if [[ -x "$PY" ]]; then exit 0; fi
echo "Setting up portable Python (first run)…"
bootstrap_py="$(command -v python3.11 || command -v python3.10 || command -v python3)"
export PYTHONPATH="$ROOT/installers/common${PYTHONPATH:+:$PYTHONPATH}"
"$bootstrap_py" "$ROOT/installers/common/bootstrap.py" setup
