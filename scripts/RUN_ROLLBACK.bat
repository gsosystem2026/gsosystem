@echo off
setlocal

REM Double-click launcher for guided rollback restore.

set "KIT_DIR=%~dp0"
set "PS_SCRIPT=%KIT_DIR%guided_rollback_restore.ps1"

if not exist "%PS_SCRIPT%" (
    echo [ERROR] Missing file: "%PS_SCRIPT%"
    pause
    exit /b 1
)

echo.
echo ==========================================
echo  GSO Guided Rollback Launcher
echo ==========================================
echo.
echo You will be asked for:
echo   1) Backup file path (.dump or .zip)
echo   2) Target DATABASE_URL
echo.
echo Type YES when prompted to confirm restore.
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%PS_SCRIPT%"
set "ERR=%ERRORLEVEL%"

echo.
if "%ERR%"=="0" (
    echo Rollback restore flow finished.
) else (
    echo Rollback ended with exit code: %ERR%
)
echo.
pause
exit /b %ERR%
