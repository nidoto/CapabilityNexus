@echo off
setlocal

title CapabilityNexus - Driver Installation

echo ============================================================
echo  CapabilityNexus 驱动安装
echo  Driver Installation
echo ============================================================
echo.
echo This installs the bundled drivers:
echo   - ViGEmBus  (XInput-compatible controller backend)
echo   - HidHide   (game-exclusive physical-device hiding)
echo.
echo Requires administrator rights. A UAC prompt will appear.
echo.

net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Restarting as administrator...
    powershell -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b
)

set SCRIPT_DIR=%~dp0
set DRIVERS_DIR=%SCRIPT_DIR%drivers

echo [1/2] Installing ViGEmBus driver...
if exist "%DRIVERS_DIR%\ViGEmBus\x64\ViGEmBus.inf" (
    "%DRIVERS_DIR%\ViGEmBus\x64\nefconw.exe" --install-driver --inf-path "%DRIVERS_DIR%\ViGEmBus\x64\ViGEmBus.inf"
    if %errorlevel% equ 0 (
        echo       ViGEmBus installed OK.
    ) else (
        echo       ViGEmBus install returned error %errorlevel%.
    )
) else (
    echo       ViGEmBus driver files not found. Skipped.
)

echo.
echo [2/2] Installing HidHide driver...
if exist "%DRIVERS_DIR%\HidHide_1.5.230_x64.exe" (
    echo       Running HidHide setup (follow the prompts)...
    start /wait "%DRIVERS_DIR%\HidHide_1.5.230_x64.exe"
    echo       HidHide setup finished.
) else (
    echo       HidHide installer not found. Skipped.
)

echo.
echo ============================================================
echo  Done. A reboot may be required.
echo  After reboot, start CapabilityNexus.exe and enable the
echo  engine. Use System ^> Game-Exclusive Mode to hide a
echo  physical controller if a game auto-selects it.
echo ============================================================
echo.
pause
endlocal
