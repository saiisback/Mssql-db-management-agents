"""Copy Rights Agent — snapshot all permissions on the destination DB pre-restore."""
from __future__ import annotations

import json

from config import CFG
from state.db_state import DBRefreshState
from tools import audit
from agents.llm import run_react, extract_final_text


_TOOLS = ["get_db_permissions"]

_PROMPT = """You are the MSSQL Copy Rights Agent.
Your job: snapshot all principals, role memberships, and object permissions on a database
BEFORE it gets overwritten by a restore.

Call get_db_permissions exactly once with server='dest' and the destination db name.

End your reply with a JSON object on the last line:
{"success": bool, "principals": <count>, "permissions": <count>, "role_members": <count>}
"""


def _extract(text: str) -> dict:
    text = (text or "").strip()
    for line in reversed(text.splitlines()):
        line = line.strip()
        if line.startswith("{") and line.endswith("}"):
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                continue
    return {"success": False}


def copy_rights_node(state: DBRefreshState) -> dict:
    if state["refresh_type"] == "new":
        empty = {"principals": [], "role_members": [], "permissions": []}
        return {"rights_snapshot": empty, "current_step": "copy_rights_skipped"}

    dst = state["dest"]
    from tools.mcp_client import call_tool

    snapshot = call_tool("get_db_permissions", server="dest", db=dst["db"])
    success = "error" not in snapshot

    user_msg = (
        f"Snapshot the destination DB permissions: server='dest' db='{dst['db']}'.\n"
        f"Then summarize counts in the JSON result line."
    )
    summary_result = run_react(_TOOLS, _PROMPT, user_msg)
    summary = _extract(extract_final_text(summary_result))

    audit.write(CFG.sqlite_path, state["ticket_key"], "copy_rights",
                "snapshot", "ok" if success else "fail", summary)

    update: dict = {"current_step": "copy_rights_done"}
    if success:
        update["rights_snapshot"] = snapshot
    else:
        update["errors"] = [{
            "step": "copy_rights",
            "category": "permissions",
            "message": snapshot.get("error", "snapshot failed"),
            "sql": None,
        }]
    return update
