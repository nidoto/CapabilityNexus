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
set NEED_REBOOT=0

echo Checking installed drivers...

rem ---- ViGEmBus ----
sc query ViGEmBus >nul 2>&1
if %errorlevel% equ 0 (
    echo   [OK] ViGEmBus already installed.
    set SKIP_VIGEMBUS=1
) else (
    echo   [--] ViGEmBus not installed.
    set SKIP_VIGEMBUS=0
)

rem ---- HidHide ----
sc query HidHide >nul 2>&1
if %errorlevel% equ 0 (
    echo   [OK] HidHide already installed.
    set SKIP_HIDHIDE=1
) else (
    reg query "HKLM\SOFTWARE\Nefarius Software Solutions e.U.\Nefarius Software Solutions e.U. HidHide" >nul 2>&1
    if %errorlevel% equ 0 (
        echo   [OK] HidHide already installed.
        set SKIP_HIDHIDE=1
    ) else (
        echo   [--] HidHide not installed.
        set SKIP_HIDHIDE=0
    )
)

echo.
echo ============================================================
echo  Installing / repairing drivers...
echo ============================================================
echo.

if "%SKIP_VIGEMBUS%"=="1" goto skip_vigembus

echo [1/2] Installing ViGEmBus driver...
if exist "%DRIVERS_DIR%\ViGEmBus\x64\ViGEmBus.inf" (
    "%DRIVERS_DIR%\ViGEmBus\x64\nefconw.exe" --install-driver --inf-path "%DRIVERS_DIR%\ViGEmBus\x64\ViGEmBus.inf"
    if %errorlevel% equ 0 (
        echo       ViGEmBus installed OK.
        set NEED_REBOOT=1
    ) else (
        echo       ViGEmBus install returned error %errorlevel%.
    )
) else (
    echo       ViGEmBus driver files not found. Skipped.
)
goto after_vigembus

:skip_vigembus
echo [1/2] ViGEmBus already present - skipped.

:after_vigembus

echo.
if "%SKIP_HIDHIDE%"=="1" goto skip_hidhide

echo [2/2] Installing HidHide driver...
if exist "%DRIVERS_DIR%\HidHide_1.5.230_x64.exe" (
    echo       Running HidHide setup (follow the prompts)...
    start /wait "%DRIVERS_DIR%\HidHide_1.5.230_x64.exe"
    echo       HidHide setup finished.
    set NEED_REBOOT=1
) else (
    echo       HidHide installer not found. Skipped.
)
goto after_hidhide

:skip_hidhide
echo [2/2] HidHide already present - skipped.

:after_hidhide

echo.
echo ============================================================
echo  Summary
echo ============================================================
sc query ViGEmBus >nul 2>&1 && echo   ViGEmBus: OK
reg query "HKLM\SOFTWARE\Nefarius Software Solutions e.U.\Nefarius Software Solutions e.U. HidHide" >nul 2>&1 && echo   HidHide: OK
echo.

if "%NEED_REBOOT%"=="1" (
    echo  A reboot is recommended so the drivers fully activate.
)

echo  After reboot, start CapabilityNexus.exe and enable the engine.
echo  Use System ^> Game-Exclusive Mode to hide a physical controller
echo  if a game auto-selects it.
echo ============================================================
echo.
pause
endlocal
