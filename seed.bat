@echo off
REM Run the sample-DB seed script via sqlcmd (requires sqlcmd on PATH).
REM Alternative: open scripts\seed_sample_db.sql in SSMS and press F5.
setlocal

if not exist .env (
    echo [error] .env not found. Run setup.bat first.
    exit /b 1
)

REM Load SQL credentials from .env (very basic parser — only needs SOURCE values)
for /f "usebackq tokens=1,2 delims==" %%a in (".env") do (
    if /i "%%a"=="MSSQL_SOURCE_SERVER" set SQL_SERVER=%%b
    if /i "%%a"=="MSSQL_SOURCE_PORT"   set SQL_PORT=%%b
    if /i "%%a"=="MSSQL_SOURCE_USER"   set SQL_USER=%%b
    if /i "%%a"=="MSSQL_SOURCE_PASSWORD" set SQL_PASS=%%b
)

if "%SQL_SERVER%"=="" set SQL_SERVER=localhost
if "%SQL_PORT%"=="" set SQL_PORT=1433
if "%SQL_USER%"=="" set SQL_USER=sa

where sqlcmd >nul 2>nul
if errorlevel 1 (
    echo [error] sqlcmd is not on PATH.
    echo         Either install "Microsoft Command Line Utilities for SQL Server"
    echo         OR open scripts\seed_sample_db.sql in SSMS and press F5.
    exit /b 1
)

echo [step] Seeding ProductionDB and StagingDB on %SQL_SERVER%,%SQL_PORT% as %SQL_USER%...
sqlcmd -S "%SQL_SERVER%,%SQL_PORT%" -U "%SQL_USER%" -P "%SQL_PASS%" -C -N -i scripts\seed_sample_db.sql

if errorlevel 1 (
    echo.
    echo [error] seed failed. Check that:
    echo   - SQL Server is running and TCP/IP is enabled on port %SQL_PORT%
    echo   - SA login is enabled and the password in .env is correct
    echo   - You can connect with: sqlcmd -S "%SQL_SERVER%,%SQL_PORT%" -U sa -P "<password>" -C -N
    exit /b 1
)

echo.
echo [done] Seed complete. Now run:  run_refresh.bat
endlocal
