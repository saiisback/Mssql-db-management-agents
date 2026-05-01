@echo off
REM One-shot Windows setup. Run from a fresh checkout: setup.bat
setlocal

echo === DB Agents — Windows setup ===

where python >nul 2>nul
if errorlevel 1 (
    echo [error] Python is not installed or not on PATH.
    echo         Install Python 3.10 or newer from https://www.python.org/downloads/windows/
    echo         IMPORTANT: tick "Add Python to PATH" during install.
    exit /b 1
)

if not exist .venv (
    echo [step] Creating virtual environment in .venv\
    python -m venv .venv
    if errorlevel 1 (
        echo [error] Failed to create venv.
        exit /b 1
    )
)

echo [step] Installing dependencies (this can take a few minutes the first time)...
.venv\Scripts\python -m pip install --upgrade pip
.venv\Scripts\python -m pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo [error] pip install failed.
    echo         Most common cause on Windows: pymssql needs Microsoft Visual C++ Build Tools.
    echo         Download from: https://visualstudio.microsoft.com/visual-cpp-build-tools/
    echo         Install "Desktop development with C++" workload, then re-run setup.bat.
    exit /b 1
)

if not exist .env (
    echo [step] Creating .env from .env.example
    copy .env.example .env >nul
    echo.
    echo *** EDIT .env NOW ***
    echo Required:
    echo     OLLAMA_API_KEY            ^(get from https://ollama.com^)
    echo     MSSQL_SOURCE_PASSWORD     ^(your SA password^)
    echo     MSSQL_DEST_PASSWORD       ^(same as source if one server, two DBs^)
    echo     BACKUP_PATH_HOST          ^(a folder SQL Server can write to, e.g. C:\SQLBackups^)
    echo     BACKUP_PATH_CONTAINER     ^(same as BACKUP_PATH_HOST on Windows native SQL^)
    echo Optional ^(leave blank to skip^):
    echo     JIRA_URL, JIRA_EMAIL, JIRA_API_TOKEN
    echo     TEAMS_WEBHOOK_URL
    echo.
)

echo [done] Setup complete.
echo.
echo Next steps:
echo     1. Edit .env in a text editor.
echo     2. Edit policies\access_policy.yaml — replace *@yourorg.com with your real domain.
echo     3. Make sure your SQL Server allows TCP/IP and the SA login is enabled.
echo     4. Create the backup folder ^(e.g. mkdir C:\SQLBackups^) and grant the SQL Server service account write access.
echo     5. Run a refresh:
echo         run_refresh.bat
echo.

endlocal
