# DB Agents — Windows Quickstart

Personal-laptop testing setup. Run all 8 agents end-to-end against the Microsoft SQL Server you already have installed.

What you'll see when it works: a real `BACKUP DATABASE` produces a `.bak` file, a real `RESTORE DATABASE` overwrites the destination, agents log every step, and an audit row gets written for each. No Jira, no Teams, no Docker — just your SQL Server, Python, and Ollama Cloud for the LLM.

---

## The 5 steps (start to finish)

```
1. Install Python + verify SQL Server is reachable
2. setup.bat              ← creates venv, installs deps
3. seed.bat               ← creates ProductionDB + StagingDB with sample data
4. check.bat              ← verifies SQL + Ollama connectivity
5. run_refresh.bat        ← runs the 8 agents end to end
```

---

## 1. Prerequisites

### Python
Install Python 3.10+ from <https://www.python.org/downloads/windows/>.
**Tick "Add Python to PATH" during install.**

### Microsoft Visual C++ Build Tools — *only if step 2 fails*
<https://visualstudio.microsoft.com/visual-cpp-build-tools/> → install workload "Desktop development with C++". Needed because `pymssql` builds a native extension on first install.

### SQL Server — make sure it's reachable over TCP/IP

This is the most common stumbling block on personal laptops, especially with **SQL Server Express**.

#### If you have SQL Server Express (`localhost\SQLEXPRESS`)

By default Express **only listens on Shared Memory + Named Pipes**, not TCP/IP. The agents use TCP, so you have to enable it:

1. Open **SQL Server Configuration Manager** (search "SQL Server Configuration Manager" in Start).
2. Left pane → *SQL Server Network Configuration* → *Protocols for SQLEXPRESS*.
3. Right-click **TCP/IP** → **Enable**.
4. Right-click **TCP/IP** → **Properties** → tab *IP Addresses*.
5. Scroll to the bottom: **IPAll** section.
   - Clear `TCP Dynamic Ports` (leave it empty).
   - Set `TCP Port` to **`1433`**.
6. Apply → OK.
7. Left pane → *SQL Server Services* → right-click **SQL Server (SQLEXPRESS)** → **Restart**.

#### Enable SA login + SQL auth

By default SQL Server may be in Windows-Authentication-only mode. Enable mixed mode:

1. Open **SQL Server Management Studio (SSMS)**, connect with your Windows account.
2. Right-click the server (top of Object Explorer) → **Properties** → page *Security*.
3. Select **SQL Server and Windows Authentication mode**. OK.
4. Object Explorer → Security → Logins → right-click **sa** → Properties.
5. Page *General*: set a password (you'll put this in `.env`).
6. Page *Status*: Login = **Enabled**.
7. Restart the SQL Server service (Configuration Manager → right-click service → Restart).

#### Verify TCP works

Open Command Prompt:
```
sqlcmd -S localhost,1433 -U sa -P "<your-sa-password>" -C -N -Q "SELECT @@VERSION"
```
If this prints a SQL Server version, you're good. If you get *"Cannot connect"*, TCP isn't on or the password is wrong.

> Don't have `sqlcmd`? Install **"SQL Server Command Line Utilities"**: <https://learn.microsoft.com/en-us/sql/tools/sqlcmd/sqlcmd-utility>. Or just skip this verify and let `check.bat` do it for you in step 4.

### A backup folder

Create one and let SQL Server write to it:

1. `mkdir C:\SQLBackups` (in Command Prompt).
2. Right-click the folder → Properties → Security → Edit → Add → type **`NT Service\MSSQLSERVER`** (or `NT Service\MSSQL$SQLEXPRESS` for Express) → check **Modify** → OK.

If the SQL Server service can't write here you'll see *"Operating system error 5 (Access is denied)"* during backup.

---

## 2. setup.bat

Open Command Prompt in the project folder (Shift+Right-click → "Open command window here") and run:

```
setup.bat
```

This creates `.venv\`, installs Python deps, and copies `.env.example` to `.env`.

**Now edit `.env`** in Notepad. Minimum required:

```ini
OLLAMA_API_KEY=<get from https://ollama.com>
OLLAMA_MODEL=kimi-k2.6

MSSQL_SOURCE_SERVER=localhost
MSSQL_SOURCE_PORT=1433
MSSQL_SOURCE_USER=sa
MSSQL_SOURCE_PASSWORD=<your sa password>

# If she has one SQL Server with two databases, point dest at the same instance
MSSQL_DEST_SERVER=localhost
MSSQL_DEST_PORT=1433
MSSQL_DEST_USER=sa
MSSQL_DEST_PASSWORD=<same sa password>

BACKUP_PATH_HOST=C:\SQLBackups
BACKUP_PATH_CONTAINER=C:\SQLBackups
```

Leave `JIRA_*` and `TEAMS_WEBHOOK_URL` blank — the framework auto-skips them.

**No need to edit `policies/access_policy.yaml`** — it now ships with a permissive test rule that approves any requester for `dev`/`uat`/`test`/`staging` environments. Tighten it later when going past the pilot.

---

## 3. seed.bat — create sample databases

```
seed.bat
```

This creates:
- **ProductionDB** with `dbo.Customers` (200 rows) and `dbo.Orders` (~600 rows) — the source.
- **StagingDB** (empty) — the destination.

If `seed.bat` says `sqlcmd not on PATH`, open `scripts\seed_sample_db.sql` in SSMS and press **F5** instead.

---

## 4. check.bat — verify everything

```
check.bat
```

Output should look like:

```
DB Agents — connection pre-flight
Checking SOURCE localhost:1433 as sa...
  OK  Microsoft SQL Server 2022 (RTM-CU...
  databases: master, model, msdb, ProductionDB, StagingDB, tempdb
Checking DEST   localhost:1433 as sa...
  OK  ...
Checking backup path C:\SQLBackups...
  OK  Python can write here
Checking Ollama https://ollama.com model=kimi-k2.6...
  OK  model said: 'ok'

Jira  enabled: False
Teams enabled: False

All required checks passed. You can run run_refresh.bat.
```

If anything fails, fix that before step 5.

---

## 5. run_refresh.bat — run the 8 agents

The defaults in `run_refresh.bat` already match what `seed.bat` created. Just double-click it (or run from the command line).

```
[start] MANUAL-1714560000: ProductionDB@localhost → StagingDB@localhost (existing, env=UAT)
[info] Jira not configured — running without ticket sync (audit log still active)
[info] Teams not configured — running without notifications

  reader        → reader_done
  dba_access    → approved (Pilot/test mode — auto-approved for non-prod)
  validation_pre → pass
  backup        → ProductionDB-full-20260501-103500.bak (12.3 MB, verified)
  copy_rights   → snapshot: 0 principals, 0 permissions (sample DB has no extra users)
  refresh       → kill_connections OK, restore OK in 4.1s
  validation_post → pass
  apply_rights  → 0 applied
  finalize      → done

[done] MANUAL-1714560000 final_status=done
```

You can verify by hand:
- The `.bak` file shows up in `C:\SQLBackups\`.
- StagingDB now has the same 200 customers and 600 orders as ProductionDB. Open SSMS → expand StagingDB → Tables → `dbo.Customers` → Select Top 1000 Rows.

---

## What you can do next (for "see all the recoveries and stuff")

### Run it again — it should be idempotent

Just double-click `run_refresh.bat` again. The Refresh Agent kills connections, takes a fresh backup, restores, and you get another audit trail row.

### Watch a failure path

Try inducing one of these to see the Support Agent kick in:

| What to do | What you'll see |
|---|---|
| Edit `run_refresh.bat`, change `--env UAT` to `--env prod` | DBA Access Agent rejects → Jira would be `Rework` (skipped here), exit code 1 |
| Stop the SQL Server service mid-refresh (Configuration Manager → right-click → Stop) | Refresh Agent fails → Support Agent classifies as `connectivity` → retries once → escalates |
| Open SSMS, run `USE StagingDB; WAITFOR DELAY '00:05:00';` in a query window, then run a refresh | `kill_connections` evicts SSMS, restore proceeds. (To see the failure path, comment out `kill_connections` in `agents/refresh_agent.py` first.) |
| Edit `scripts\patch_environment.sql` to add a deliberately broken statement like `SELECT * FROM nonexistent_table;` | Refresh Agent's `run_script` fails → Support classifies as `script_execution` |

### Inspect the audit log

Install **DB Browser for SQLite** from <https://sqlitebrowser.org/dl/>. Open `db_agents.db` → table `audit_log`. One row per agent action, ordered by time.

Or in Python:
```
.venv\Scripts\python -c "import sqlite3; [print(r) for r in sqlite3.connect('db_agents.db').execute('SELECT created_at, agent, action, status FROM audit_log ORDER BY id DESC LIMIT 20')]"
```

---

## Troubleshooting (specific to Windows / SQL Server)

| Symptom | Fix |
|---|---|
| `pip install pymssql` fails with `Microsoft Visual C++ 14.0 or greater is required` | Install Visual C++ Build Tools (link in Prerequisites), then re-run `setup.bat`. |
| `Login failed for user 'sa'` | SA disabled, password wrong, or mixed-mode auth not enabled. Re-do "Enable SA login" in Prerequisites. |
| `BACKUP DATABASE failed: Operating system error 5 (Access is denied)` | The SQL Server service account can't write to `BACKUP_PATH_HOST`. Grant Modify on that folder to `NT Service\MSSQL$SQLEXPRESS` (or `NT Service\MSSQLSERVER`). |
| `connection timed out` | TCP/IP not enabled on the instance. Re-do "Enable TCP" in Prerequisites. |
| `[Microsoft][ODBC Driver Manager] Data source name not found` | You may have `pyodbc` installed but the agents use `pymssql`. Confirm `pymssql` installed via `.venv\Scripts\pip list`. |
| Restore fails `exclusive access could not be obtained` | Something is connected to StagingDB. The Refresh Agent runs `kill_connections` first; SSMS query windows pointed at StagingDB are the usual culprit. Close them. |
| `auth_decision=rejected` for every refresh | Your `--env` doesn't match an approved environment. Defaults are `dev`/`uat`/`test`/`staging`. Either change `--env` or edit `policies\access_policy.yaml`. |
| The console window closes immediately | An error happened before agents started. Open Command Prompt, `cd` to the folder, run from there to see the error. |

---

## What's running locally vs. in the cloud

| Component | Where it runs |
|---|---|
| The agent code (Python) | Your laptop |
| MCP server (`tools/mcp_server.py`) | Your laptop (subprocess of the Python app) |
| SQL Server | Your laptop (your existing install) |
| Audit log + LangGraph state | Your laptop (`db_agents.db`) |
| **`kimi-k2.6` LLM** | **Ollama Cloud** (`https://ollama.com`) — only the agent prompts and tool descriptions cross the network. Tool *results* (JSON like `{"size_mb": 12.3, "verified": true}`) are sent to the LLM so it can decide the next step. **No table data, no row contents, no passwords are sent.** |

If you want **everything** on-prem (no internet at all): install Ollama locally (`https://ollama.com/download/windows`), pull a smaller model (`ollama pull qwen2.5:14b`), and edit `.env`:
```
OLLAMA_HOST=http://localhost:11434
OLLAMA_API_KEY=
OLLAMA_MODEL=qwen2.5:14b
```
Tool-calling reliability drops with smaller local models — expect more "support agent retried because the LLM didn't return clean JSON" events.
