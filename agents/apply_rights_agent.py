"""Apply Rights Agent — re-grants the snapshotted permissions onto the new DB."""
from __future__ import annotations

import json

from config import CFG
from state.db_state import DBRefreshState
from tools import audit
from tools.mcp_client import call_tool


def apply_rights_node(state: DBRefreshState) -> dict:
    if state["refresh_type"] == "new":
        return {"current_step": "apply_rights_skipped",
                "apply_rights_result": {"applied": 0, "failed": []}}

    snapshot = state.get("rights_snapshot") or {}
    dst = state["dest"]
    result = call_tool(
        "apply_db_permissions",
        server="dest",
        db=dst["db"],
        snapshot_json=json.dumps(snapshot),
    )

    audit.write(CFG.sqlite_path, state["ticket_key"], "apply_rights", "regrant",
                "ok" if "error" not in result else "fail", result)

    update: dict = {"current_step": "apply_rights_done", "apply_rights_result": result}
    if "error" in result:
        update["errors"] = [{
            "step": "apply_rights", "category": "permissions",
            "message": result["error"], "sql": None,
        }]
    return update
