#!/usr/bin/env bash
set -euo pipefail
zenith_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if [[ -n "${ZENITH_PYTHON:-}" ]]; then
  zenith_python="$ZENITH_PYTHON"
elif command -v python3 >/dev/null 2>&1; then
  zenith_python="$(command -v python3)"
elif command -v python >/dev/null 2>&1; then
  zenith_python="$(command -v python)"
else
  echo 'Python 3.10+ is required. Install Python 3.12 and python3-venv, then rerun this script.' >&2
  exit 1
fi
exec "$zenith_python" "$zenith_root/install.py" "$@"
