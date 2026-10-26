#!/usr/bin/env bash
set -euo pipefail
zenith_mac_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd -- "$zenith_mac_root"
exec bash "$zenith_mac_root/start.sh" "$@"
