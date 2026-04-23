@echo off
setlocal

REM Runs Django backup command from project root and logs output.
REM Usage:
REM   scripts\run_gso_backup.bat

set "PROJECT_DIR=C:\Users\CLIENT\Desktop\GSO Final System 2026"
set "PYTHON_EXE=python"
set "LOG_DIR=%PROJECT_DIR%\logs"
set "PG_BIN_DIR="

if not exist "%LOG_DIR%" (
    mkdir "%LOG_DIR%"
)

if exist "%PROJECT_DIR%\.env" (
    for /f "usebackq tokens=1,* delims==" %%A in ("%PROJECT_DIR%\.env") do (
        if /I "%%~A"=="PG_BIN_DIR" set "PG_BIN_DIR=%%~B"
    )
)
if defined PG_BIN_DIR (
    if exist "%PG_BIN_DIR%\pg_dump.exe" (
        set "PATH=%PG_BIN_DIR%;%PATH%"
    )
)

for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set "TS=%%i"
set "LOG_FILE=%LOG_DIR%\backup_run_%TS%.log"

pushd "%PROJECT_DIR%"
echo [%DATE% %TIME%] Starting gso_backup... > "%LOG_FILE%"
"%PYTHON_EXE%" manage.py gso_backup --keep 10 >> "%LOG_FILE%" 2>&1
set "ERR=%ERRORLEVEL%"
echo [%DATE% %TIME%] Exit code: %ERR% >> "%LOG_FILE%"
popd

if "%ERR%"=="0" (
    echo Backup command finished successfully. See log: %LOG_FILE%
) else (
    echo Backup command failed. See log: %LOG_FILE%
)

exit /b %ERR%
