#!/usr/bin/env bash
set -euo pipefail
zenith_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
zenith_python="$zenith_root/.venv/bin/python"
if [[ ! -x "$zenith_python" ]]; then
  echo 'Zenith is not installed in .venv. Run bash install.sh first.' >&2
  exit 1
fi
exec "$zenith_python" -m agent "$@"
