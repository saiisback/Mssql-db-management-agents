# DB Agents V1 — Pilot Runbook

## What this is

8-agent LangGraph framework that picks up DB refresh tickets from Jira, runs them end-to-end against two SQL Server containers, and reports back via Jira + Teams. LLM is Kimi K2.6 via Ollama Cloud. SQL access goes through a local MCP server (`tools/mcp_server.py`) over stdio.

## One-time setup

### 1. Infrastructure

```bash
# Python deps
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# SQL Server containers (source on 1433, dest on 1434, shared ./backups volume)
cp .env.example .env
# fill in passwords + tokens in .env
docker compose up -d
docker compose ps   # both containers healthy
```

### 2. Seed a sample source database

```bash
docker exec -it db-agents-source /opt/mssql-tools18/bin/sqlcmd -S localhost \
  -U sa -P "$MSSQL_SOURCE_PASSWORD" -C -N -Q "
CREATE DATABASE ProductionDB;
GO
USE ProductionDB;
CREATE TABLE dbo.Customers (Id INT PRIMARY KEY, Email NVARCHAR(200), PhoneNumber NVARCHAR(50));
INSERT INTO dbo.Customers VALUES (1, 'a@example.com', '+1-555-0001'), (2, 'b@example.com', '+1-555-0002');
GO
"
```

### 3. Configure Jira

- Set up a project with key `DBSUP` (or whatever you set in `.env`).
- Make sure these workflow transitions exist by name: `In Progress`, `Done`, `Rework`.
- Generate an API token at https://id.atlassian.com/manage-profile/security/api-tokens.
- Put `JIRA_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN`, `JIRA_PROJECT_KEY` in `.env`.

### 4. Configure Teams

- In your channel: `⋯` → Connectors → Incoming Webhook → copy URL → put in `.env`.

### 5. Configure Ollama Cloud

- Get an API key from https://ollama.com → put in `.env` as `OLLAMA_API_KEY`.
- Verify access:
  ```bash
  curl https://ollama.com/api/chat -H "Authorization: Bearer $OLLAMA_API_KEY" \
    -d '{"model":"kimi-k2.6","messages":[{"role":"user","content":"ping"}]}'
  ```

### 6. Edit the access policy

Open `policies/access_policy.yaml` and replace `*@yourorg.com` with your real domain. The senior DBA emails should match the `reporter.emailAddress` field on Jira tickets.

## Running the pilot

```bash
python main.py
```

Reader Agent now polls Jira every 30s.

## How to file a ticket the framework will accept

Create a Jira issue in project `DBSUP` with status `To Do` and a description that contains exactly this template (extra text around it is fine):

```
Source DB: ProductionDB
Source Server: db-agents-source
Dest DB: StagingDB
Dest Server: db-agents-dest
Environment: UAT
Refresh Type: existing
```

`Refresh Type` must be `existing` or `new`. `Environment` matches the policy YAML (case-insensitive). Use `db-agents-source` / `db-agents-dest` as the server names — those are the container hostnames.

## Reading the audit log

```bash
sqlite3 db_agents.db "SELECT created_at, agent, action, status FROM audit_log WHERE ticket_key='DBSUP-1' ORDER BY id;"
```

To inspect graph state for a ticket (LangGraph checkpoint table):

```bash
sqlite3 db_agents.db ".tables"   # see what's there
sqlite3 db_agents.db "SELECT thread_id, checkpoint_ns FROM checkpoints WHERE thread_id='DBSUP-1';"
```

## Resuming a stalled refresh

If `main.py` crashes mid-refresh, restart it. LangGraph's `SqliteSaver` will reload state for any ticket that hasn't reached `final_status`. The framework picks up fresh tickets only — to manually resume, use the LangGraph CLI or invoke the graph with the same `thread_id`.

## Inducing test failures (validation drills)

| Failure | How to induce |
|---|---|
| `disk_space` | `dd if=/dev/zero of=./backups/filler bs=1m count=20000` to fill the volume |
| `active_connections` | open `sqlcmd` against the dest DB and leave it idle, then file a ticket |
| `backup_integrity` | edit the `.bak` after the backup step (`echo bad >> backups/<file>.bak`) |
| `connectivity` | `docker stop db-agents-dest` mid-refresh |

In each case the Support Agent should classify, post to Jira → Rework, and fire the Teams card.

## Tearing down

```bash
docker compose down -v   # destroys both DBs
rm -f db_agents.db backups/*.bak
```

## Common gotchas

- **Backup file not found by dest container:** both containers must mount the *same* `./backups` directory. `docker compose down -v` then `up -d` if the volume got recreated.
- **`Login failed`:** SQL Server containers take ~30s to be ready after `up -d`; wait for `docker compose ps` to show `healthy`.
- **Jira parse failure:** description must match the template line-by-line. Hidden ADF formatting from rich-text editors sometimes inserts artifacts — paste in plain text mode.
- **Kimi K2.6 returns text instead of JSON verdict:** validation/backup/refresh agents look for the JSON line at the end. If the model went chatty, the fallback parser flags it as a failure → routes to Support → retries once. If it keeps happening, lower the temperature in `agents/llm.py` (already 0.0) or tighten the system prompt.
- **Auth always rejects:** check that the `requester` field in the parsed ticket actually matches one of the `requester` globs in `access_policy.yaml`. Jira sometimes hides the email behind `accountId` for privacy-mode users.

## Out of scope (V2 work)

iServe, Monitoring Agent, Optimization Agent, multi-region, real PII masking content, audit on a separate SQL Server DB, Postgres state, MCP-over-HTTP, auto-rollback on restore failure, prod approval via `/approve` Jira comment.
