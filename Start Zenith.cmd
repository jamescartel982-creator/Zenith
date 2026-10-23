@echo off
setlocal
cd /d "%~dp0"
if not exist "%~dp0.venv\Scripts\python.exe" (
    echo Run Install Zenith.cmd first. Keep all extracted Zenith files together.
    if not defined ZENITH_NO_PAUSE pause
    exit /b 1
)
"%~dp0.venv\Scripts\python.exe" -m agent serve --open-browser %*
set "ZenithExit=%ERRORLEVEL%"
if not "%ZenithExit%"=="0" (
    echo.
    echo Zenith could not start. Read the error above.
    if not defined ZENITH_NO_PAUSE pause
)
exit /b %ZenithExit%
