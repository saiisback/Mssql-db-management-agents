"""Run a single DB refresh from the command line — no Jira required.

Example (Windows):
    python run_refresh.py ^
        --source-server localhost --source-db ProductionDB ^
        --dest-server localhost --dest-db StagingDB ^
        --type existing --env UAT --requester user@org.com

Example (Mac/Linux):
    python run_refresh.py \
        --source-server localhost --source-db ProductionDB \
        --dest-server localhost --dest-db StagingDB \
        --type existing --env UAT --requester user@org.com
"""
from __future__ import annotations

import argparse
import logging
import sys
import time
import traceback

from rich.logging import RichHandler

from config import CFG
from graph.db_refresh_graph import get_app
from state.db_state import DBRefreshState
from tools import audit


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run a DB refresh through the agent pipeline.")
    p.add_argument("--ticket-key", default=None,
                   help="Identifier for this run (default: auto-generated MANUAL-<timestamp>)")
    p.add_argument("--source-server", required=True, help="Source SQL Server hostname or IP")
    p.add_argument("--source-port", type=int, default=None,
                   help="Source SQL Server port (default: from MSSQL_SOURCE_PORT env var)")
    p.add_argument("--source-db", required=True, help="Source database name")
    p.add_argument("--dest-server", required=True, help="Destination SQL Server hostname or IP")
    p.add_argument("--dest-port", type=int, default=None,
                   help="Destination SQL Server port (default: from MSSQL_DEST_PORT env var)")
    p.add_argument("--dest-db", required=True, help="Destination database name")
    p.add_argument("--type", choices=["existing", "new"], default="existing",
                   help="Refresh type: 'existing' (backup+restore) or 'new' (skip backup)")
    p.add_argument("--env", required=True, help="Environment label (matched against access_policy.yaml)")
    p.add_argument("--requester", required=True,
                   help="Requester email — must match a rule in policies/access_policy.yaml")
    return p.parse_args()


def main() -> int:
    logging.basicConfig(
        level=CFG.log_level,
        format="%(message)s",
        handlers=[RichHandler(rich_tracebacks=True, show_path=False)],
    )
    log = logging.getLogger("db-agents")

    args = parse_args()
    ticket_key = args.ticket_key or f"MANUAL-{int(time.time())}"

    state: DBRefreshState = {
        "ticket_key": ticket_key,
        "requester": args.requester,
        "environment": args.env,
        "refresh_type": args.type,
        "source": {
            "server": args.source_server,
            "port": args.source_port or CFG.source.port,
            "db": args.source_db,
        },
        "dest": {
            "server": args.dest_server,
            "port": args.dest_port or CFG.dest.port,
            "db": args.dest_db,
        },
        "errors": [],
        "retry_count": 0,
        "current_step": "queued",
    }

    log.info(f"[start] {ticket_key}: {args.source_db}@{args.source_server} → "
             f"{args.dest_db}@{args.dest_server} ({args.type}, env={args.env})")
    audit.write(CFG.sqlite_path, ticket_key, "main", "manual_invoke", "ok",
                {"requester": args.requester, "type": args.type, "env": args.env})

    if not CFG.jira_enabled:
        log.info("[info] Jira not configured — running without ticket sync (audit log still active)")
    if not CFG.teams_enabled:
        log.info("[info] Teams not configured — running without notifications")

    app = get_app()
    config = {"configurable": {"thread_id": ticket_key}}
    try:
        final = app.invoke(state, config=config)
    except Exception as e:
        log.error(f"[fatal] graph crashed: {e}")
        log.error(traceback.format_exc())
        audit.write(CFG.sqlite_path, ticket_key, "main", "crash", "fail",
                    {"error": str(e), "traceback": traceback.format_exc()})
        return 2

    status = final.get("final_status", "unknown")
    log.info(f"[done] {ticket_key} final_status={status}")
    log.info(f"[audit] inspect with: sqlite3 {CFG.sqlite_path} "
             f"\"SELECT created_at, agent, action, status FROM audit_log "
             f"WHERE ticket_key='{ticket_key}' ORDER BY id;\"")
    return 0 if status == "done" else 1


if __name__ == "__main__":
    sys.exit(main())
