#requires -Version 5.1
$ErrorActionPreference = 'Stop'
$ZenithRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$ZenithPython = Join-Path $ZenithRoot '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $ZenithPython)) {
    $ZenithPython = Join-Path $ZenithRoot '.venv/bin/python'
}
if (-not (Test-Path -LiteralPath $ZenithPython)) {
    Write-Error 'Zenith is not installed in .venv. Run install.ps1 first.'
    exit 1
}
& $ZenithPython -m agent @args
exit $LASTEXITCODE
