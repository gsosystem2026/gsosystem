@echo off
setlocal

REM Double-click launcher for non-technical users.
REM Runs interactive setup_new_pc_backup.ps1 from this folder.

set "KIT_DIR=%~dp0"
set "PS_SCRIPT=%KIT_DIR%setup_new_pc_backup.ps1"

if not exist "%PS_SCRIPT%" (
    echo [ERROR] Missing file: "%PS_SCRIPT%"
    echo Ensure this .bat stays in the same folder as setup_new_pc_backup.ps1
    pause
    exit /b 1
)

echo.
echo ==========================================
echo  GSO Backup Kit - New PC Setup Launcher
echo ==========================================
echo.
echo A PowerShell window will open for setup prompts.
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%PS_SCRIPT%"
set "ERR=%ERRORLEVEL%"

echo.
if "%ERR%"=="0" (
    echo Setup completed successfully.
) else (
    echo Setup ended with exit code: %ERR%
)
echo.
pause
exit /b %ERR%
