# DB Agents — Windows Quickstart

For running the framework on a Windows laptop with a real Microsoft SQL Server installed (no Docker).

---

## Prerequisites

1. **Python 3.10 or newer**
   Download from <https://www.python.org/downloads/windows/>.
   **Tick "Add Python to PATH"** in the installer.

2. **Microsoft Visual C++ Build Tools** *(only if `pip install` fails — you'll see an error mentioning `pymssql`)*
   <https://visualstudio.microsoft.com/visual-cpp-build-tools/>
   Install the workload "Desktop development with C++".

3. **SQL Server with TCP/IP enabled**
   - Open *SQL Server Configuration Manager* → SQL Server Network Configuration → Protocols for MSSQLSERVER → enable **TCP/IP**.
   - Restart the SQL Server service.
   - Confirm the SA login is enabled and you have its password.

4. **A backup folder the SQL Server service can write to**
   - Create one, e.g. `C:\SQLBackups`.
   - Right-click → Properties → Security → make sure the **NT SERVICE\MSSQLSERVER** account (or `MSSQL$<INSTANCE>`) has Modify permission.

---

## One-time setup

1. Unzip / clone the repo to e.g. `C:\db-agents\`.
2. Open Command Prompt in that folder (`Shift+Right-click` → "Open command window here").
3. Run:
   ```
   setup.bat
   ```
   This creates `.venv\`, installs dependencies, and copies `.env.example` to `.env`.

4. Open `.env` in Notepad. **Required values:**
   ```
   OLLAMA_API_KEY=<from https://ollama.com>
   OLLAMA_MODEL=kimi-k2.6

   MSSQL_SOURCE_SERVER=localhost
   MSSQL_SOURCE_PORT=1433
   MSSQL_SOURCE_USER=sa
   MSSQL_SOURCE_PASSWORD=<your SA password>

   MSSQL_DEST_SERVER=localhost
   MSSQL_DEST_PORT=1433
   MSSQL_DEST_USER=sa
   MSSQL_DEST_PASSWORD=<same as source if one server, two DBs>

   BACKUP_PATH_HOST=C:\SQLBackups
   BACKUP_PATH_CONTAINER=C:\SQLBackups
   ```
   `BACKUP_PATH_CONTAINER` should be the **same Windows path** as `BACKUP_PATH_HOST` — there's no Docker container on Windows-native installs.

   **Leave Jira and Teams blank** if you're not using them — the framework will skip those calls automatically:
   ```
   JIRA_URL=
   TEAMS_WEBHOOK_URL=
   ```

5. Open `policies\access_policy.yaml` in Notepad. Replace `*@yourorg.com` with your real email domain. The `requester` you pass on the command line must match one of the patterns here, or the auth gate will reject the refresh.

---

## Running a refresh

### Option 1 — `.bat` shortcut (easiest)

Open `run_refresh.bat` in Notepad. Edit the variables near the top:

```
set SOURCE_SERVER=localhost
set SOURCE_DB=ProductionDB
set DEST_SERVER=localhost
set DEST_DB=StagingDB
set REFRESH_TYPE=existing
set ENVIRONMENT=UAT
set REQUESTER=user@yourorg.com
```

Save, then **double-click `run_refresh.bat`** (or run it from the command prompt). A console opens, the agents run in sequence, you see live log output. The window stays open at the end so you can read the result.

### Option 2 — Direct command line

```
.venv\Scripts\activate
python run_refresh.py ^
    --source-server localhost --source-db ProductionDB ^
    --dest-server localhost --dest-db StagingDB ^
    --type existing --env UAT --requester user@yourorg.com
```

---

## What you should see

```
[start] MANUAL-1714560000: ProductionDB@localhost → StagingDB@localhost (existing, env=UAT)
[info] Jira not configured — running without ticket sync (audit log still active)
[info] Teams not configured — running without notifications
... agents run one by one ...
[done] MANUAL-1714560000 final_status=done
[audit] inspect with: sqlite3 db_agents.db "SELECT ..."
```

Final status values:
- `done` — refresh completed successfully
- `rework` — a step failed; Support Agent escalated
- `rejected` — auth gate rejected the requester

---

## Inspecting what happened

The audit log lives in `db_agents.db` (SQLite). Quickest way to read it on Windows:

1. Install **DB Browser for SQLite**: <https://sqlitebrowser.org/dl/>
2. Open `db_agents.db` → Browse Data → table `audit_log`.

Or from the command line if you have `sqlite3.exe` on PATH:
```
sqlite3 db_agents.db "SELECT created_at, agent, action, status FROM audit_log ORDER BY id DESC LIMIT 50;"
```

---

## Common Windows gotchas

| Symptom | Fix |
|---|---|
| `pip install pymssql` errors with `Microsoft Visual C++ 14.0 or greater is required` | Install Visual C++ Build Tools (link in Prerequisites), then re-run `setup.bat`. |
| `Login failed for user 'sa'` | SA login disabled, or password wrong, or SQL Server in Windows-auth-only mode. In SSMS: right-click server → Properties → Security → "SQL Server and Windows Authentication mode". Restart service. |
| `BACKUP DATABASE failed: Cannot open backup device ... Operating system error 5 (Access is denied)` | The SQL Server service account can't write to `BACKUP_PATH_HOST`. Grant Modify on that folder to `NT SERVICE\MSSQLSERVER`. |
| `auth_decision=rejected` for every refresh | Your `--requester` doesn't match any pattern in `policies\access_policy.yaml`. Edit the YAML to match your email. |
| Restore fails with "exclusive access could not be obtained" | Something is connected to the destination DB. The Refresh Agent runs `kill_connections` first, but SSMS sessions sometimes resist. Close SSMS query windows pointed at the dest DB. |
| Console window closes immediately after `run_refresh.bat` | An error happened before the agents ran. Open Command Prompt, `cd` to the folder, run `run_refresh.bat` from there to see the error. |

---

## What's running locally vs. in the cloud

| Component | Where it runs |
|---|---|
| The agent code (Python) | Your laptop |
| MCP server (`mssql-mcp`) | Your laptop (subprocess of the Python app) |
| SQL Server | Your laptop (your existing install) |
| Audit log | Your laptop (`db_agents.db`) |
| **`kimi-k2.6` LLM** | **Ollama Cloud** (https://ollama.com) — only the agent prompts and tool descriptions go over the network; **no SQL data is sent**. The agents send tool *calls* (e.g. "backup ProductionDB"), the LLM sends back tool *invocations* and final summaries. |

If you want everything on-prem with no internet calls, swap to a local Ollama install with a smaller model (edit `OLLAMA_HOST` and `OLLAMA_MODEL` in `.env`). Tool-calling reliability drops with smaller models — see `runbook.md` "Common gotchas".
