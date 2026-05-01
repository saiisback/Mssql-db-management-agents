"""Backup Agent — Full backup of source DB + verify integrity."""
from __future__ import annotations

import json

from config import CFG
from state.db_state import DBRefreshState
from tools import audit
from agents.llm import run_react, extract_final_text


_TOOLS = ["backup_db", "restore_verify"]

_PROMPT = """You are the MSSQL Backup Agent.
Your job: take a full backup of a database and verify its integrity.

Steps:
1. Call backup_db with server='source', db=<source_db>, backup_type='full', compression=true, checksum=true.
2. Take the bak_path_container from the response.
3. Call restore_verify with server='source' and that bak_path_container.

End your reply with a JSON object on the last line:
{"success": bool, "bak_path_container": "...", "size_mb": ..., "verified": bool, "error": "..."}
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
    return {"success": False, "error": f"could not parse result from: {text[-200:]}"}


def backup_node(state: DBRefreshState) -> dict:
    if state["refresh_type"] == "new":
        return {"current_step": "backup_skipped", "backup_file": None}

    src = state["source"]
    user_msg = (
        f"Source DB: server='source' db='{src['db']}'.\n"
        f"Take a full backup with compression and checksum, then verify it.\n"
        f"End with the JSON result line."
    )
    result = run_react(_TOOLS, _PROMPT, user_msg)
    parsed = _extract(extract_final_text(result))

    audit.write(CFG.sqlite_path, state["ticket_key"], "backup",
                "full_backup", "ok" if parsed.get("success") and parsed.get("verified") else "fail", parsed)

    update: dict = {"current_step": "backup_done"}
    if parsed.get("success") and parsed.get("verified"):
        update["backup_file"] = parsed.get("bak_path_container")
    else:
        update["errors"] = [{
            "step": "backup",
            "category": "backup_integrity" if not parsed.get("verified") else "backup_failed",
            "message": parsed.get("error", "backup or verify failed"),
            "sql": None,
        }]
    return update
