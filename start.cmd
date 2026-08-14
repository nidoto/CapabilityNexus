@echo off
setlocal

title CapabilityNexus
cd /d "%~dp0"

where py >nul 2>nul
if %errorlevel%==0 (
    py -3 tools\cnx_gui.py
) else (
    python tools\cnx_gui.py
)

if errorlevel 1 (
    echo.
    echo CapabilityNexus failed to start.
    pause
)

endlocal
