# DB Agents V1 — Internal Pilot Design

**Date:** 2026-05-01
**Scope:** 2-week internal pilot
**Source doc:** `doc.md` (full vision, multinational)

## Locked decisions

| # | Decision | Choice |
|---|---|---|
| 1 | Goal | Internal pilot on a non-prod DB pair |
| 2 | DB infra | Two local Docker SQL Server containers, shared backup volume |
| 3 | LLM-to-DB integration | MCP architecture (`mssql-mcp` over stdio) |
| 4 | LLM | `kimi-k2.6` via Ollama Cloud |
| 5 | Agent count | 8 separate LangGraph nodes (matches doc 1:1) |
| 6 | Auth gate | YAML policy file |
| 7 | Ticket input | Structured description template (regex-parsed) |
| 8 | State + audit | One SQLite file (`db_agents.db`), `SqliteSaver` checkpointer |

## Out of scope for V1

iServe, Monitoring Agent, Optimization Agent, multi-region orchestration, PII masking scripts (placeholders only), audit on a separate SQL Server DB, Postgres state, MCP-over-HTTP, auto-rollback on restore failure.

## Architecture

```
┌─ Host machine ─────────────────────────────────────────────┐
│  main.py ──► LangGraph app (8 nodes) ──► SqliteSaver       │
│      │                                                      │
│      └──► mssql-mcp (subprocess, stdio) ──► pymssql ──► SQL │
│                                                             │
│  Two SQL Server containers: 1433 (source), 1434 (dest)     │
│  Shared volume: ./backups → /var/opt/mssql/backups          │
└─────────────────────────────────────────────────────────────┘
       │                                   │
       ▼                                   ▼
   Jira Cloud                        Teams Webhook
```

LLM call pattern: `langchain-ollama` pointed at `https://ollama.com` with `model="kimi-k2.6"`, MCP tools bound per agent (1–3 tools each).

## State shape

```python
class DBRefreshState(TypedDict):
    ticket_key: str
    source: dict      # server, port, db, user
    dest: dict
    environment: str
    refresh_type: Literal["new", "existing"]
    requester: str
    auth_decision: Literal["approved", "rejected", "pending"]
    backup_file: str | None
    rights_snapshot: list[dict]
    errors: list[dict]
    current_step: str
```

Persisted by `SqliteSaver` keyed on `thread_id = ticket_key` so failed refreshes can resume.

## MCP tool surface (11 tools)

| Tool | Purpose |
|---|---|
| `list_databases` | Catalog DBs on a server |
| `run_query` | Read-only SQL |
| `db_health_check` | Online status, owner, active connections |
| `disk_space` | Free space on a path |
| `backup_db` | Full/Diff/Log backup with checksum |
| `restore_verify` | `RESTORE VERIFYONLY` integrity check |
| `kill_connections` | Drop active sessions on a DB |
| `restore_db` | `RESTORE DATABASE ... WITH REPLACE, RECOVERY` |
| `get_db_permissions` | Snapshot principals + permissions + roles |
| `apply_db_permissions` | Re-grant from snapshot |
| `run_script` | Execute a `.sql` file from `scripts/` |

## Agent → tool binding

| Agent | Bound MCP tools |
|---|---|
| Reader | none (Jira only) |
| DBAAccess | none (YAML only) |
| Validation (pre) | `db_health_check`, `disk_space`, `run_query` |
| Backup | `backup_db`, `restore_verify` |
| CopyRights | `get_db_permissions` |
| Refresh | `kill_connections`, `restore_db`, `run_script` |
| Validation (post) | `db_health_check`, `run_query` |
| ApplyRights | `apply_db_permissions` |
| Support | `run_query` (read-only diagnostics) |

## Error handling

- **Single retry** for transient errors (timeout, blocked connections)
- **No auto-rollback** on restore failure in V1; Support Agent posts recovery steps to Jira for human action
- **Failure categories** the LLM is taught to recognize: `disk_space`, `connectivity`, `permissions`, `suspect_db`, `active_connections`, `backup_integrity`, `script_execution`, `auth_rejected`, `llm_tool_call`, `unknown`
- **Jira comment** on failure includes last 50 lines of error log + failing SQL
- **Teams alert** uses adaptive card with ticket link, failed step, error excerpt, oncall mention

## Definition of pilot success

1. DBA opens Jira ticket using template → Teams notification within 60s
2. Existing-DB refresh of a 1GB+ DB completes end-to-end on the green path
3. Inducing 3 failures (disk full, active connections, bad backup) routes correctly to Support Agent → Jira Rework
4. SQLite audit log shows complete row-by-row trail
5. New DBA can run a refresh from `runbook.md` without help

## Build order (10 working days)

| Day | Deliverable |
|---|---|
| 1 | Docker compose up; mssql-mcp running; sample DB seeded |
| 2 | mcp_client.py + smoke tests for all 11 tools |
| 3 | state/, graph/ skeleton; SqliteSaver wired; audit.py |
| 4 | reader_agent.py + jira_tools.py + template parser |
| 5 | dba_access_agent.py + access_policy.yaml |
| 6 | validation_agent.py (both phases) + backup_agent.py |
| 7 | copy_rights_agent.py + refresh_agent.py |
| 8 | apply_rights_agent.py + happy path Jira/Teams |
| 9 | support_agent.py + induced failure tests |
| 10 | runbook.md + dry run + buffer |

## File layout

```
db-agents/
├── .env / .env.example / requirements.txt / docker-compose.yml
├── config.py / main.py
├── state/db_state.py
├── graph/db_refresh_graph.py
├── agents/{reader,dba_access,validation,backup,copy_rights,refresh,apply_rights,support}_agent.py
├── tools/{mcp_server,mcp_client,jira_tools,teams_tools,audit}.py
├── policies/access_policy.yaml
├── scripts/{mask_pii,patch_environment}.sql
├── runbook.md
└── docs/plans/2026-05-01-db-agents-v1-design.md
```
