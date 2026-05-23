#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
ROOT="$(pwd)"
bash "$ROOT/installers/linux/setup-runtime.sh"
PY="$ROOT/installers/runtime/linux/python/bin/python3"
exec "$PY" "$ROOT/installers/common/bootstrap.py" launch
