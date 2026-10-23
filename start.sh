#!/usr/bin/env bash
set -euo pipefail
zenith_start_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd -- "$zenith_start_root"
exec bash "$zenith_start_root/run.sh" serve --open-browser "$@"
