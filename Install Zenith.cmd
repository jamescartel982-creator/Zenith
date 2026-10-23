@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1" --launch %*
set "ZenithExit=%ERRORLEVEL%"
if not "%ZenithExit%"=="0" (
    echo.
    echo Zenith setup stopped. Read the error above and run this installer again.
    if not defined ZENITH_NO_PAUSE pause
)
exit /b %ZenithExit%
