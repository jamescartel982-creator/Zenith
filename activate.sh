#!/usr/bin/env bash
# Source this file so activation remains in the current terminal.
if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  echo 'Activate in this terminal with: source ./activate.sh' >&2
  exit 1
fi
zenith_activation_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if [[ ! -f "$zenith_activation_root/.venv/bin/activate" ]]; then
  echo 'Zenith environment is missing. Run bash install.sh first.' >&2
  unset zenith_activation_root
  return 1
fi
source "$zenith_activation_root/.venv/bin/activate"
unset zenith_activation_root
printf '\nZenith environment active. Run zenith chat or zenith serve. Use deactivate to leave.\n'
