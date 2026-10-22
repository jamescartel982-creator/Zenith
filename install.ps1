#requires -Version 5.1
$ErrorActionPreference = 'Stop'
$ZenithRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
if ($env:ZENITH_PYTHON) {
    & $env:ZENITH_PYTHON (Join-Path $ZenithRoot 'install.py') @args
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    & py -3 (Join-Path $ZenithRoot 'install.py') @args
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    & python (Join-Path $ZenithRoot 'install.py') @args
} else {
    Write-Error 'Python 3.10+ is required. Install Python 3.12 from python.org or winget, reopen your terminal, then rerun this script.'
    exit 1
}
exit $LASTEXITCODE
