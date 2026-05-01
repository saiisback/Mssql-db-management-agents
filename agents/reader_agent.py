"""ReaderAgent — parses an already-fetched Jira ticket into DBRefreshState.

The polling loop lives in main.py; this node runs once per ticket as the
graph entrypoint.
"""
from __future__ import annotations

from config import CFG
from state.db_state import DBRefreshState
from tools import audit, teams_tools


def reader_node(state: DBRefreshState) -> dict:
    ticket_key = state["ticket_key"]
    audit.write(CFG.sqlite_path, ticket_key, "reader", "parse_ticket", "ok", {
        "source": state.get("source"),
        "dest": state.get("dest"),
        "type": state.get("refresh_type"),
    })
    src = state["source"]
    dst = state["dest"]
    teams_tools.send_started(
        ticket_key=ticket_key,
        source=f"{src['db']} ({src['server']})",
        dest=f"{dst['db']} ({dst['server']})",
        env=state["environment"],
        requester=state["requester"],
    )
    return {"current_step": "reader_done"}
