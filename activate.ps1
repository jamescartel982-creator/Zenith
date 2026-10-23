#requires -Version 5.1
# Dot-source so activation remains in the current PowerShell session.
if ($MyInvocation.InvocationName -ne '.') {
    Write-Error 'Activate in this terminal with: . .\activate.ps1'
    exit 1
}
$ZenithActivationPath = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) '.venv/Scripts/Activate.ps1'
if (-not (Test-Path -LiteralPath $ZenithActivationPath)) {
    Write-Error 'Zenith environment is missing. Run install.ps1 first.'
    return
}
. $ZenithActivationPath
Remove-Variable ZenithActivationPath
Write-Host 'Zenith environment active. Run zenith chat or zenith serve. Use deactivate to leave.'
