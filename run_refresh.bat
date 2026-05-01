@echo off
REM Convenience wrapper around run_refresh.py — edit the values below for your refresh.
setlocal

if not exist .venv (
    echo [error] .venv not found. Run setup.bat first.
    exit /b 1
)

REM ── EDIT THESE FOR YOUR REFRESH ─────────────────────────────────
set SOURCE_SERVER=localhost
set SOURCE_DB=ProductionDB
set DEST_SERVER=localhost
set DEST_DB=StagingDB
set REFRESH_TYPE=existing
set ENVIRONMENT=UAT
set REQUESTER=user@yourorg.com
REM ────────────────────────────────────────────────────────────────

.venv\Scripts\python run_refresh.py ^
    --source-server %SOURCE_SERVER% --source-db %SOURCE_DB% ^
    --dest-server %DEST_SERVER% --dest-db %DEST_DB% ^
    --type %REFRESH_TYPE% --env %ENVIRONMENT% --requester %REQUESTER%

endlocal
