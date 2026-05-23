#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
ROOT="$(pwd)"
bash "$ROOT/installers/mac/setup-runtime.sh"
PY="$ROOT/installers/runtime/macos/python/bin/python3"
exec "$PY" "$ROOT/installers/common/bootstrap.py" launch
