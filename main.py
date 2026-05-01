"""Entry point: poll Jira, kick off the refresh graph for new tickets."""
from __future__ import annotations

import logging
import time
import traceback

from rich.logging import RichHandler

from config import CFG
from graph.db_refresh_graph import get_app
from state.db_state import DBRefreshState
from tools import audit, jira_tools, teams_tools


logging.basicConfig(
    level=CFG.log_level,
    format="%(message)s",
    handlers=[RichHandler(rich_tracebacks=True, show_path=False)],
)
log = logging.getLogger("db-agents")


_seen: set[str] = set()


def _ticket_to_state(t: jira_tools.ParsedTicket) -> DBRefreshState:
    return {
        "ticket_key": t.key,
        "requester": t.requester,
        "environment": t.environment,
        "refresh_type": t.refresh_type,
        "source": {"server": t.source_server, "port": CFG.source.port, "db": t.source_db},
        "dest": {"server": t.dest_server, "port": CFG.dest.port, "db": t.dest_db},
        "errors": [],
        "retry_count": 0,
        "current_step": "queued",
    }


def process_ticket(t: jira_tools.ParsedTicket) -> None:
    log.info(f"[reader] picked up {t.key} ({t.refresh_type}: {t.source_db} → {t.dest_db})")
    audit.write(CFG.sqlite_path, t.key, "main", "received", "ok", {
        "requester": t.requester, "env": t.environment,
    })
    try:
        jira_tools.transition(t.key, "In Progress")
    except Exception as e:
        log.warning(f"could not transition {t.key} → In Progress: {e}")

    app = get_app()
    state = _ticket_to_state(t)
    config = {"configurable": {"thread_id": t.key}}
    try:
        final = app.invoke(state, config=config)
        log.info(f"[done] {t.key} final_status={final.get('final_status')}")
    except Exception as e:
        log.error(f"[fatal] {t.key} crashed: {e}")
        log.error(traceback.format_exc())
        audit.write(CFG.sqlite_path, t.key, "main", "crash", "fail",
                    {"error": str(e), "traceback": traceback.format_exc()})
        try:
            jira_tools.transition(t.key, "Rework")
            jira_tools.comment(t.key, f"Refresh crashed: {e}")
            teams_tools.send_failure(t.key, "main", str(e), "unknown")
        except Exception:
            pass


def poll_loop() -> None:
    log.info(f"[main] polling Jira project={CFG.jira_project_key} every {CFG.jira_poll_interval_sec}s")
    audit.init(CFG.sqlite_path)
    while True:
        try:
            tickets = jira_tools.get_open_refresh_tickets()
            for t in tickets:
                if t.key in _seen:
                    continue
                _seen.add(t.key)
                process_ticket(t)
        except Exception as e:
            log.error(f"[poll] error: {e}")
        time.sleep(CFG.jira_poll_interval_sec)


if __name__ == "__main__":
    poll_loop()
