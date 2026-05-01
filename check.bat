@echo off
setlocal
if not exist .venv (
    echo [error] .venv not found. Run setup.bat first.
    exit /b 1
)
.venv\Scripts\python check_connection.py
endlocal
