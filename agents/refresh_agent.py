"""Refresh Agent — kill connections, restore .bak, run post-restore scripts."""
from __future__ import annotations

import json
import os

from config import CFG
from state.db_state import DBRefreshState
from tools import audit
from agents.llm import run_react, extract_final_text


_TOOLS = ["kill_connections", "restore_db", "run_script"]

_PROMPT = """You are the MSSQL Refresh Agent.
Your job: restore a backup file onto the destination database.

Steps in order:
1. Call kill_connections with server='dest' and the dest db name (so RESTORE isn't blocked).
2. Call restore_db with server='dest', the bak_path_container provided, target_db=<dest_db>.
3. If post_scripts is non-empty, call run_script for each script with server='dest', db=<dest_db>.

End your reply with a JSON object on the last line:
{"success": bool, "restore_duration_s": ..., "scripts_run": [...], "error": "..."}
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
    return {"success": False, "error": f"could not parse: {text[-200:]}"}


def _scripts_for(environment: str) -> list[str]:
    if environment.lower() == "prod":
        return []
    candidates = []
    for name in ("patch_environment.sql", "mask_pii.sql"):
        if os.path.exists(os.path.join("scripts", name)):
            candidates.append(name)
    return candidates


def refresh_node(state: DBRefreshState) -> dict:
    dst = state["dest"]
    bak = state.get("backup_file")

    if state["refresh_type"] == "existing" and not bak:
        return {"current_step": "refresh_done", "errors": [{
            "step": "refresh", "category": "backup_integrity",
            "message": "no backup file in state", "sql": None,
        }]}

    post_scripts = _scripts_for(state["environment"])
    user_msg = (
        f"Dest: server='dest' db='{dst['db']}'.\n"
        f"Backup file (container path): {bak}\n"
        f"Post-restore scripts to run: {post_scripts}\n"
        f"Execute the steps. End with the JSON result line."
    )

    result = run_react(_TOOLS, _PROMPT, user_msg)
    parsed = _extract(extract_final_text(result))

    audit.write(CFG.sqlite_path, state["ticket_key"], "refresh",
                "restore", "ok" if parsed.get("success") else "fail", parsed)

    update: dict = {"current_step": "refresh_done", "refresh_result": parsed}
    if not parsed.get("success"):
        update["errors"] = [{
            "step": "refresh",
            "category": "script_execution" if "script" in parsed.get("error", "").lower() else "connectivity",
            "message": parsed.get("error", "restore failed"),
            "sql": None,
        }]
    return update
