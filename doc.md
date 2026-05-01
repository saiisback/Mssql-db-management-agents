# DB Agentic AI Framework
### Enterprise Agentic Database Management — Build Blueprint
> **Stack:** Ollama (Local LLM) · LangGraph · SQL Server (Docker) · MCP Server · Jira Cloud / iServe · Microsoft Teams
> **Scope:** Multinational Database Management Company — Multi-Region, Multi-Instance, 24×7 Autonomous Operations

---

## Table of Contents
1. [What is Agentic AI](#1-what-is-agentic-ai)
2. [Why Agentic AI for DBA Operations](#2-why-agentic-ai-for-dba-operations)
3. [All Agents — Complete Catalogue](#3-all-agents--complete-catalogue)
4. [DB Refresh Flow — Full 1:1 Diagram](#4-db-refresh-flow--full-11-diagram)
5. [Step-by-Step Flow Breakdown](#5-step-by-step-flow-breakdown)
6. [Token Authentication Gate](#6-token-authentication-gate)
7. [Failure Handling & DB Support Agent](#7-failure-handling--db-support-agent)
8. [Multinational Considerations](#8-multinational-considerations)
9. [Tech Stack — Local Replacements](#9-tech-stack--local-replacements)
10. [Project Folder Structure](#10-project-folder-structure)
11. [Environment Variables](#11-environment-variables)
12. [Notification Templates](#12-notification-templates)
13. [Setup Checklist](#13-setup-checklist)

---

## 1. What is Agentic AI

> *"Agentic AI is AI that behaves like a self-directed worker capable of planning, acting, and completing tasks with minimal human guidance."*

At the core of this framework is a **Model Context Protocol (MCP) server** — a bridge that lets AI agents talk to Microsoft SQL Server directly. Through natural language, agents can:

- Run queries and execute stored procedures
- Take backups and restore databases
- Monitor server health in real time
- Manage permissions and access rights
- Perform performance tuning autonomously

The LLM (Ollama / llama3 locally) acts as the **reasoning engine** — it reads tickets, decides what action to take, calls the right agent, and interprets results. It never replaces DBAs; it executes their playbooks autonomously at scale.

---

## 2. Why Agentic AI for DBA Operations

From the presentation — these are the **5 DBA domains** that Agentic AI can autonomously own or assist:

| DBA Domain | What the Agent Does Autonomously |
|---|---|
| **Performance Tuning** | Detects slow queries, missing indexes, blocking chains — runs `OPTIMIZATION-AGENT` to resolve |
| **Backup & Recovery** | Schedules and executes Full / Differential / Log backups based on ticket or schedule — `BACKUP-AGENT` |
| **Monitoring** | Continuously checks DB server health, disk, CPU, blocking — `MONITORING-AGENT` runs 24×7 |
| **Security** | Validates access requests via token auth, audits permissions, captures and re-applies rights |
| **Troubleshooting Incidents** | Catches all agent failures, logs errors, updates Jira to Rework, notifies Teams — `DB-SUPPORT-AGENT` |

> **Multinational Advantage:** A single agentic framework running across all regional SQL Server clusters means one DBA team can manage thousands of database instances across time zones — tickets raised in APAC at 2am are resolved autonomously without waking anyone up.

---

## 3. All Agents — Complete Catalogue

### From the Presentation (Slide 5) — All 7 Core Agents

| # | Agent Name | Role | Trigger |
|---|---|---|---|
| 1 | `MSSQL-Validation-Agent` | Validates Pre-Health Checks of the database | Before backup, before restore, and after restore |
| 2 | `MSSQL-DBA-Access-Agent` | Validates and provides required level of access | Token authentication gate — Approved / Rejected / Override |
| 3 | `MSSQL-Backup-Agent` | Performs Full / Differential / Log backups based on requirement | Existing DB refresh requests; also on-schedule |
| 4 | `MSSQL-Copy-Rights-Agent` | Captures all user permissions on the requested database | Before restore — saves complete permission snapshot |
| 5 | `MSSQL-Refresh-Agent` | Performs full refresh activity from Source to Destination | After backup confirmed; restores `.bak` to destination |
| 6 | `MSSQL-Apply-Rights-Agent` | Grants all permissions as they were before the refresh | After post-restore validation passes |
| 7 | `MSSQL-Optimization-Agent` | Resolves all performance-related activities post-refresh | After Apply Rights Agent; also triggered by Monitoring Agent |

### Additional Agents in the Flow (Slide 6)

| Agent | Role |
|---|---|
| `Reader-Agent` | Polls Jira / iServe sequentially, parses ticket fields, kicks off the refresh pipeline |
| `Monitoring-Agent` | Runs independently — monitors DB Server Health 24×7, can trigger alerts or kick off support flows |
| `DB-Support-Agent` | Catches all failure notifications across every agent, logs errors, moves ticket to Rework, fires Teams alert |

---

## 4. DB Refresh Flow — Full 1:1 Diagram

> This diagram is a precise 1:1 reproduction of the flow on Slide 6 of the presentation.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           END USER                                          │
│           Raises request via natural language LLM Prompt                    │
└──────────────────────────────┬──────────────────────────────────────────────┘
                               │
                               ▼
                  ┌────────────────────────┐
                  │  Create User Story     │
                  │  Jira  ──OR──  iServe  │   ← Ticket created with:
                  │  (ticket system)       │     Source DB, Dest DB,
                  └────────────┬───────────┘     Servers, Refresh Type
                               │
                               ▼
                  ┌────────────────────────┐
                  │     READER AGENT       │   ← Polls Jira / iServe
                  │  Sequentially          │     Processes tickets one by one
                  │  processes tickets     │     Parses all ticket fields
                  └────────────┬───────────┘     into structured state
                               │
                  ┌────────────┴──────────────────────────────┐
                  │                                           │
                  ▼                                           ▼
  ┌───────────────────────────┐              ┌───────────────────────────────┐
  │   TOKEN AUTHENTICATION    │              │      MONITORING AGENT         │
  │   MSSQL-DBA-Access-Agent  │              │  Runs independently / 24×7    │
  │                           │              │  Checks: DB Server Health     │
  │  Validates access level   │              │  CPU, Memory, Disk, Blocking  │
  │  required for this ticket │              │  → Feeds alerts to            │
  └───────┬──────────┬────────┘              │    DB Support Agent           │
          │          │                       └───────────────────────────────┘
     Approved    Rejected /
          │       Override
          │          │
          │          ▼
          │   ┌──────────────────┐
          │   │ Update Jira →    │
          │   │ "Rework"         │
          │   │ Notify approver  │
          │   │ via Teams        │
          │   └──────────────────┘
          │
          ▼
┌─────────────────────────────┐
│     VALIDATION AGENT        │   ← Pre-Health Check
│  MSSQL-Validation-Agent     │     Checks: DB Online?
│                             │     Disk space sufficient?
│  ┌──────────────────────┐   │     Active connections?
│  │  DB Online?          │   │     SQL Server service up?
│  │  Server Reachable?   │   │     Blocking chains?
│  └──────────────────────┘   │
└─────────┬───────────────────┘
          │
          ├──────────────────────────────────────────────────┐
          │                                                  │
    Existing DB                                          New DB Request
          │                                             (Ignore backup)
          ▼                                                  │
┌─────────────────────────────┐                             │
│      BACKUP AGENT           │                             │
│  MSSQL-Backup-Agent         │                             │
│                             │                             │
│  Full / Diff / Log          │                             │
│  Backup based on need       │                             │
│  Saved to: BACKUP_PATH      │                             │
│                             │                             │
│  Full/Diff/Log Validation   │                             │
│  (confirms .bak integrity)  │                             │
└─────────┬───────────────────┘                             │
          │                                                  │
          └──────────────────────┬───────────────────────────┘
                                 │
                                 ▼
                  ┌──────────────────────────────┐
                  │     COPY RIGHTS AGENT        │
                  │  MSSQL-Copy-Rights-Agent     │
                  │                              │
                  │  Queries:                    │
                  │  sys.database_permissions    │
                  │  sys.server_principals       │
                  │  sys.database_role_members   │
                  │  Captures: All logins,       │
                  │  roles, object permissions   │
                  │  Snapshot saved to state     │
                  └──────────────┬───────────────┘
                                 │
                                 ▼
                  ┌──────────────────────────────┐
                  │      REFRESH AGENT           │
                  │   MSSQL-Refresh-Agent        │
                  │                              │
                  │  Restores Source .bak        │
                  │  to Destination DB           │
                  │  WITH REPLACE, RECOVERY      │
                  │                              │
                  │  Script Execution            │◄── Post-restore scripts
                  │  (custom SQL scripts         │    e.g. update connection
                  │   run after restore)         │    strings, anonymize PII,
                  │                              │    environment patches
                  │  Error Log captured          │
                  │  on any failure              │
                  └──────────────┬───────────────┘
                                 │
                    ┌────────────┴────────────┐
                    │                         │
                 Success                   Failure
                    │                         │
                    ▼                         ▼
  ┌───────────────────────────┐    ┌─────────────────────────┐
  │    VALIDATION AGENT       │    │   ERROR LOG             │
  │    (Post-Restore)         │    │   All failures saved    │
  │  MSSQL-Validation-Agent   │    │   → Routed to           │
  │                           │    │   DB SUPPORT AGENT      │
  │  Checks:                  │    └─────────────────────────┘
  │  ✓ DB Status / Online     │
  │  ✓ DB Owner correct       │
  │  ✓ Full/Diff/Log          │
  │    Validation pass        │
  │  ✓ Basic query executes   │
  └──────────────┬────────────┘
                 │
     ┌───────────┴──────────┐
     │                      │
  Passed                 Failed
     │                      │
     ▼                      ▼
┌──────────────────┐   ┌─────────────────────────┐
│  APPLY RIGHTS    │   │   DB SUPPORT AGENT      │
│  AGENT           │   │   All Failure            │
│  MSSQL-Apply-    │   │   Notifications          │
│  Rights-Agent    │   │   saved here             │
│                  │   │   → Jira → Rework        │
│  Re-grants all   │   │   → Teams Alert          │
│  permissions     │   └─────────────────────────┘
│  captured in     │
│  Copy Rights     │
│  User Permissions│
│  restored        │
└──────────┬───────┘
           │
           ▼
┌──────────────────────────────────┐
│     OPTIMIZATION AGENT           │
│  MSSQL-Optimization-Agent        │
│                                  │
│  Post-refresh performance tasks: │
│  ✓ Rebuild/Reorganize indexes    │
│  ✓ Update statistics             │
│  ✓ Check query plan cache        │
│  ✓ Identify blocking chains      │
│  ✓ Resolve performance alerts    │
└──────────┬───────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────────┐
│                    JIRA TASK UPDATE                          │
│  Attach all results / logs to Jira ticket                    │
│  Transition ticket status → Done                             │
│  Notify Approver in Teams                                    │
│                                                              │
│  APPLICATION TEAM HANDOFF:                                   │
│  "Database is ready — Application team can now connect."     │
└──────────────────────────────────────────────────────────────┘
```

---

## 5. Step-by-Step Flow Breakdown

### Step 1 — End User Creates Ticket
The end user raises a DB refresh request using a natural language LLM prompt. The system automatically creates a structured **User Story** in either **Jira Cloud** or **iServe** (the two supported ticket systems). The ticket contains:
- Source DB name and server
- Destination DB name and server
- Refresh type (new DB or existing DB)
- Priority and requester info
- Approver details

### Step 2 — Reader Agent Picks Up Ticket
- Polls Jira / iServe every configurable interval (default: 30 seconds)
- Processes tickets **sequentially** — one at a time to avoid conflicts
- Parses all ticket fields into a structured `DBRefreshState` object
- Transitions the Jira ticket status from `To Do` → `In Progress`
- Sends initial Teams notification: *"Ticket DBSUP-42 picked up — Refresh starting"*

### Step 3 — Token Authentication (DBA Access Agent)
- Validates that the requester has the correct access level for this operation
- Checks: Is this user authorised to request a refresh on this environment (Prod / UAT / Dev)?
- **Approved** → Flow continues
- **Rejected** → Jira updated to `Rework`, approver notified via Teams
- **Override** → Senior DBA can manually approve, flow resumes

### Step 4 — Monitoring Agent (Parallel)
- Runs **independently** of the main flow at all times
- Continuously monitors DB Server Health: CPU, memory, disk I/O, blocking chains, error logs
- If a critical health issue is detected during a refresh, it immediately fires to the DB Support Agent
- For multinational setups, one Monitoring Agent instance per region/cluster

### Step 5 — Validation Agent (Pre-Health)
Checks before any backup or restore begins:
- Is the source DB online and reachable?
- Is the destination server reachable?
- Is there enough disk space for the backup?
- Are there active connections to the destination DB that need terminating?
- Is the SQL Server service running on both ends?
- **If new DB request**: skip the backup step entirely, go straight to Copy Rights

### Step 6 — Backup Agent (Existing DB only)
- Determines backup type: Full / Differential / Log based on ticket and schedule
- Executes `BACKUP DATABASE` to `BACKUP_PATH`
- Verifies backup integrity (`RESTORE VERIFYONLY`)
- Validates: Full/Diff/Log backup checksums
- Saves `.bak` file path into state for Refresh Agent to use

### Step 7 — Copy Rights Agent
Before anything is overwritten on destination:
- Queries `sys.database_permissions`
- Queries `sys.server_principals` and `sys.database_principals`
- Queries `sys.database_role_members`
- Captures all logins, roles, schema permissions, object-level permissions
- Full permission snapshot stored in state

### Step 8 — Refresh Agent + Script Execution
- Restores source `.bak` to destination using `RESTORE DATABASE ... WITH REPLACE, RECOVERY`
- Runs **Script Execution** phase — post-restore SQL scripts:
  - Update environment-specific connection strings
  - Anonymise / mask PII data (critical for multinational GDPR compliance)
  - Apply environment patches (Dev/UAT-specific config)
  - Remove production-only objects (linked servers, production jobs)
- Any failure at this step is captured in the **Error Log** and routed to DB Support Agent

### Step 9 — Validation Agent (Post-Restore)
- Confirms DB is online after restore
- Checks DB Owner is correct
- Validates DB Status (`ONLINE`, not `RESTORING`, `SUSPECT`)
- Runs a basic test query to confirm DB is functional
- Performs Full/Diff/Log validation to ensure restore integrity

### Step 10 — Apply Rights Agent
- Takes the permission snapshot from Step 7
- Re-grants all logins, roles, and permissions onto the freshly restored DB
- Confirms each permission was applied successfully
- Logs any permissions that could not be applied (e.g. login no longer exists on destination)

### Step 11 — Optimization Agent
- Rebuilds or reorganises fragmented indexes
- Updates all statistics
- Checks query plan cache health
- Identifies and resolves any blocking chains introduced by the restore
- Logs all optimisation actions taken

### Step 12 — Final JIRA Update + Teams Notification + Application Handoff
- Attaches full operation log to the Jira ticket
- Transitions Jira ticket → `Done`
- Notifies the **approver** in Teams with a full summary
- Sends handoff message to **Application Team**: *"Database is ready — you may now connect."*

---

## 6. Token Authentication Gate

The `MSSQL-DBA-Access-Agent` is the security gateway of the entire flow. For a multinational company this is critical.

```
Ticket Received
      │
      ▼
  Check requester's role
  against environment policy
      │
  ┌───┴──────────────────────────────────────┐
  │  Policy Matrix (example)                 │
  │                                          │
  │  Dev  DB refresh  → L1 DBA can approve  │
  │  UAT  DB refresh  → L2 DBA required     │
  │  Prod DB refresh  → L3 Senior + CISO    │
  │  Cross-region     → Regional DBA Head   │
  └───────────────────────────────────────────┘
      │
  ┌───┴────────┬──────────────┐
  │            │              │
Approved   Rejected       Override
  │            │         (manual senior
  ▼            ▼          DBA approval)
Continue   Jira → Rework       │
           Teams Alert         ▼
                           Resume Flow
```

For multinational operations, access policies differ by:
- **Region** (APAC / EMEA / NA)
- **Environment** (Dev / UAT / Staging / Production)
- **Data Classification** (PII / Financial / Regulated)
- **Compliance requirement** (GDPR / SOX / HIPAA)

---

## 7. Failure Handling & DB Support Agent

The `DB-Support-Agent` is the **centralised error handler** for all agents. Every agent in the flow routes its failures here.

```
Any Agent Failure
       │
       ▼
┌─────────────────────────────────────────┐
│          DB SUPPORT AGENT               │
│                                         │
│  1. Capture full error log              │
│  2. Identify failing step               │
│  3. Attempt auto-remediation (1 retry)  │
│  4. If retry fails:                     │
│     → Update Jira ticket → "Rework"     │
│     → Attach error log to ticket        │
│     → Fire Teams alert to DBA on-call   │
│     → Escalate if P1 / production       │
└─────────────────────────────────────────┘
```

**Error categories handled:**
- Connectivity failure (SQL Server unreachable)
- Disk space exhausted during backup
- Restore conflict (active connections blocking)
- Permission denial during rights application
- Backup integrity failure (checksum mismatch)
- Post-restore DB in SUSPECT state
- Script execution failure
- Token auth rejection

---

## 8. Multinational Considerations

These are additional requirements beyond the core PPT flow, essential for a multinational database management company:

### Multi-Region Architecture
```
                    ┌─────────────────────────┐
                    │   Central Orchestrator   │
                    │   (LangGraph main graph) │
                    └──────┬──────┬────────────┘
                           │      │
            ┌──────────────┘      └──────────────┐
            ▼                                    ▼
  ┌──────────────────┐                ┌──────────────────┐
  │   APAC Region    │                │   EMEA Region    │
  │   SQL Cluster    │                │   SQL Cluster    │
  │   + MCP Server   │                │   + MCP Server   │
  │   + Monitoring   │                │   + Monitoring   │
  │     Agent        │                │     Agent        │
  └──────────────────┘                └──────────────────┘
            │                                    │
            └──────────────┬─────────────────────┘
                           ▼
                  ┌──────────────────┐
                  │   NA Region      │
                  │   SQL Cluster    │
                  └──────────────────┘
```

### Compliance & Data Governance
| Requirement | Agent Handling |
|---|---|
| **GDPR (EU)** | Refresh Agent runs PII masking scripts post-restore for EMEA DBs |
| **SOX (Finance)** | Token Auth requires dual approval for financial databases |
| **HIPAA (Health)** | Backup Agent enforces encryption at rest; access logged for audit |
| **Audit Trail** | All agent actions written to a central audit log table in SQL |
| **Data Residency** | Reader Agent checks source/dest region — blocks cross-border if policy restricts |

### Ticket Sources — Jira AND iServe
The Reader Agent supports both ticket systems as shown in the presentation:

```python
# Reader Agent logic
if ticket_source == "jira":
    tickets = jira_client.get_open_tickets(project=JIRA_PROJECT_KEY)
elif ticket_source == "iserve":
    tickets = iserve_client.get_pending_requests(category="DB_REFRESH")
```

### Time Zone Handling
- All timestamps stored in UTC
- Jira ticket comments and Teams notifications localised to requester's time zone
- Maintenance windows enforced per region (e.g. no Prod refresh during APAC business hours)

### Cross-Region Refresh Support
When source and destination are in different regions:
- Backup Agent compresses `.bak` file for transfer
- Secure transfer via encrypted channel (TLS)
- Validation Agent checks latency thresholds before proceeding

---

## 9. Tech Stack — Local Replacements

| Original (Azure AI Foundry) | Local Replacement | Notes |
|---|---|---|
| Azure AI Foundry | **Ollama + llama3** | Fully local, free, runs on-prem |
| Agent orchestration | **LangGraph** | Full control over multi-agent flow + conditional routing |
| Azure SQL / SQL Server | **SQL Server on Docker** | Free Developer Edition |
| MCP Server (Azure hosted) | **mssql-mcp** (open source) | `pip install mssql-mcp` |
| Azure AI Foundry auth | **Token-based via DBA-Access-Agent** | Custom auth policy engine |
| Jira / iServe | **Jira Cloud** (keep as-is) + **iServe API** | Both supported in Reader Agent |
| Teams notifications | **Teams Incoming Webhook** (keep as-is) | Free, no Azure required |

### Ollama Setup
```bash
# Install: https://ollama.com
ollama pull llama3       # or mistral, phi3, codellama
ollama serve             # runs on localhost:11434
```

### SQL Server on Docker
```bash
docker run \
  -e "ACCEPT_EULA=Y" \
  -e "SA_PASSWORD=YourPass123!" \
  -p 1433:1433 \
  --name sqlserver-source \
  -d mcr.microsoft.com/mssql/server:2022-latest

# Run a second instance for destination
docker run \
  -e "ACCEPT_EULA=Y" \
  -e "SA_PASSWORD=YourDestPass123!" \
  -p 1434:1433 \
  --name sqlserver-dest \
  -d mcr.microsoft.com/mssql/server:2022-latest
```

### MCP Server
```bash
pip install mssql-mcp
# GitHub: https://github.com/mark3labs/mssql-mcp
# Connects Ollama ↔ SQL Server over MCP protocol
```

### Python Dependencies
```
langgraph>=0.2.0
langchain>=0.3.0
langchain-ollama>=0.2.0
langchain-core>=0.3.0
pymssql>=2.3.0
atlassian-python-api>=3.41.0   # Jira Cloud
requests>=2.31.0                # Teams webhook + iServe API
python-dotenv>=1.0.0
pydantic>=2.0.0
rich>=13.0.0                    # terminal output
pytz>=2024.1                    # timezone handling
```

---

## 10. Project Folder Structure

```
db-agentic-framework/
│
├── .env                             ← your secrets (copy from .env.example)
├── .env.example
├── requirements.txt
├── config.py                        ← loads all env vars centrally
├── main.py                          ← entry point: starts Reader Agent polling loop
│
├── state/
│   └── db_state.py                  ← DBRefreshState TypedDict (shared across ALL agents)
│
├── graph/
│   └── db_refresh_graph.py          ← StateGraph: all nodes + conditional edges wired up
│
├── agents/
│   ├── reader_agent.py              ← polls Jira + iServe, parses ticket, kicks off graph
│   ├── dba_access_agent.py          ← token authentication gate (Approved/Rejected/Override)
│   ├── monitoring_agent.py          ← independent 24×7 DB health monitor
│   ├── validation_agent.py          ← reused for pre-health AND post-restore validation
│   ├── backup_agent.py              ← Full/Diff/Log backup + integrity check
│   ├── copy_rights_agent.py         ← captures all permissions pre-restore
│   ├── refresh_agent.py             ← restores DB + runs post-restore scripts
│   ├── apply_rights_agent.py        ← re-grants all permissions post-restore
│   ├── optimization_agent.py        ← indexes, stats, blocking resolution
│   └── support_agent.py            ← central error handler, Jira rework, Teams alert
│
├── tools/
│   ├── sql_tools.py                 ← pymssql helpers: connect, query, backup, restore
│   ├── jira_tools.py               ← get tickets, transition status, attach logs, comment
│   ├── iserve_tools.py             ← iServe API: get requests, update status
│   ├── teams_tools.py              ← send Adaptive Cards via Teams Incoming Webhook
│   ├── audit_tools.py              ← write all agent actions to central audit log
│   └── script_runner.py            ← executes post-restore SQL scripts safely
│
├── scripts/
│   ├── mask_pii.sql                 ← GDPR: anonymise sensitive columns post-restore
│   ├── patch_environment.sql        ← env-specific config updates
│   └── remove_prod_objects.sql      ← remove linked servers / production jobs on non-prod
│
└── policies/
    └── access_policy.yaml           ← Token auth rules per region / environment / data class
```

---

## 11. Environment Variables

```ini
# ── Ollama ──────────────────────────────────────────────
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3

# ── SQL Server — Source ─────────────────────────────────
MSSQL_SOURCE_SERVER=localhost
MSSQL_SOURCE_PORT=1433
MSSQL_SOURCE_USER=sa
MSSQL_SOURCE_PASSWORD=YourSourcePass123!

# ── SQL Server — Destination ────────────────────────────
MSSQL_DEST_SERVER=localhost
MSSQL_DEST_PORT=1434
MSSQL_DEST_USER=sa
MSSQL_DEST_PASSWORD=YourDestPass123!

# ── Backup ──────────────────────────────────────────────
BACKUP_PATH=/tmp/sqlbackups              # or UNC: \\server\share\backups
BACKUP_COMPRESSION=true
BACKUP_VERIFY=true

# ── Jira Cloud ──────────────────────────────────────────
JIRA_URL=https://yourorg.atlassian.net
JIRA_EMAIL=you@yourorg.com
JIRA_API_TOKEN=your_jira_api_token
JIRA_PROJECT_KEY=DBSUP
JIRA_POLL_INTERVAL_SEC=30

# ── iServe ──────────────────────────────────────────────
ISERVE_API_URL=https://iserve.yourorg.com/api
ISERVE_API_KEY=your_iserve_api_key
ISERVE_CATEGORY=DB_REFRESH

# ── Microsoft Teams ─────────────────────────────────────
TEAMS_WEBHOOK_URL=https://yourorg.webhook.office.com/webhookb2/xxxx

# ── Region & Compliance ─────────────────────────────────
REGION=APAC                              # APAC | EMEA | NA
ENABLE_PII_MASKING=true
ENABLE_AUDIT_LOG=true
AUDIT_LOG_DB=DBA_AuditDB
AUDIT_LOG_TABLE=AgentAuditLog

# ── Monitoring ──────────────────────────────────────────
MONITORING_INTERVAL_SEC=60
DISK_THRESHOLD_PERCENT=85               # alert if disk > 85% full
CPU_THRESHOLD_PERCENT=90
```

---

## 12. Notification Templates

### Teams — Refresh Started
```
🔵 DB Refresh Started
Ticket:    DBSUP-42
Requester: john.doe@company.com
Source:    ProductionDB  (srv-sql-apac-01)
Dest:      StagingDB     (srv-sql-apac-02)
Region:    APAC
Type:      Existing DB Refresh
Auth:      ✅ Approved by: jane.smith@company.com
[View Ticket →]
```

### Teams — Refresh Complete (Success)
```
✅ DB Refresh Complete
Ticket:       DBSUP-42  →  Done
Source:       ProductionDB (srv-sql-apac-01)
Dest:         StagingDB (srv-sql-apac-02)
Duration:     18 min 42 sec
Backup:       Full backup verified ✅
Rights:       27 permissions re-applied ✅
Optimisation: Indexes rebuilt, stats updated ✅
PII Masking:  Applied (GDPR) ✅

APPLICATION TEAM: Database is ready — you may now connect.
[View Ticket →]
```

### Teams — Failure Alert (DB Support Agent)
```
🔴 DB Refresh Failed — Action Required
Ticket:     DBSUP-42  →  Rework
Failed at:  Refresh Agent (Step 8)
Error:      Insufficient disk space on destination
            Needed: 84 GB  |  Available: 12 GB
Region:     APAC
DBA On-Call: @apac-dba-oncall
[View Ticket →]  [View Error Log →]
```

### Teams — Auth Rejected
```
⛔ DB Refresh Rejected — Authorisation Failed
Ticket:     DBSUP-43  →  Rework
Requester:  dev.user@company.com
Reason:     Production refresh requires L3 Senior DBA approval
Action:     Ticket returned for re-approval
[View Ticket →]
```

### Teams — Monitoring Alert (from Monitoring Agent)
```
⚠️ DB Server Health Alert
Server:   srv-sql-emea-03
Region:   EMEA
Issue:    Disk at 91% — threshold exceeded (85%)
Action:   DB Support Agent notified
Time:     2025-11-14 03:42 UTC
[View Server Dashboard →]
```

---

## 13. Setup Checklist

### Infrastructure
- [ ] Install Ollama → `ollama pull llama3` → `ollama serve`
- [ ] Start SQL Server Source via Docker (`-p 1433:1433`)
- [ ] Start SQL Server Destination via Docker (`-p 1434:1433`)
- [ ] Create shared backup directory with read/write access from both containers
- [ ] Install `mssql-mcp` MCP server → `pip install mssql-mcp`

### Credentials & Integrations
- [ ] Create Jira API token (Jira → Profile → Security → API Tokens)
- [ ] Set `JIRA_PROJECT_KEY` — create the project in Jira if not exists
- [ ] Set up iServe API key (if using iServe alongside Jira)
- [ ] Create Teams Incoming Webhook (Channel → `⋯` → Connectors → Incoming Webhook)
- [ ] Fill all values in `.env` (copy from `.env.example`)

### Compliance (Multinational)
- [ ] Configure `access_policy.yaml` with your region/environment/role matrix
- [ ] Populate `scripts/mask_pii.sql` with your PII column masking rules
- [ ] Populate `scripts/patch_environment.sql` with env-specific changes
- [ ] Create `DBA_AuditDB` database and `AgentAuditLog` table on SQL Server
- [ ] Confirm data residency rules per region — restrict cross-border if required

### Python
- [ ] `pip install -r requirements.txt`
- [ ] `python main.py`  ← starts polling Jira + iServe, Monitoring Agent begins 24×7

---

> **Next step:** Say **"build it"** and all code files will be generated — agents, graph wiring, tools, SQL scripts, and Teams Adaptive Cards — ready to run locally.