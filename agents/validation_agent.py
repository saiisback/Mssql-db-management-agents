"""Validation Agent — reused for pre-health and post-restore checks.

Uses Kimi K2.6 with bound MCP tools to inspect DB health and decide pass/fail.
"""
from __future__ import annotations

import json
from typing import Literal

from config import CFG
from state.db_state import DBRefreshState
from tools import audit
from agents.llm import run_react, extract_final_text


_TOOLS_PRE = ["db_health_check", "disk_space", "run_query"]
_TOOLS_POST = ["db_health_check", "run_query"]


_PRE_PROMPT = """You are the MSSQL Pre-Validation Agent.
Your job: verify the source and destination are ready for a database refresh.

Check, in order:
1. db_health_check on the SOURCE — must be online with valid owner.
2. db_health_check on the DEST — if existing-DB refresh, capture active connections.
3. disk_space on the dest server — must have at least 5 GB free.

After running checks, respond ONLY with a JSON object on the last line:
{"verdict": "pass"|"fail", "reason": "...", "facts": {...}}
"""

_POST_PROMPT = """You are the MSSQL Post-Restore Validation Agent.
Your job: verify the destination database is healthy after RESTORE.

Check:
1. db_health_check on the DEST — state must be ONLINE (not RESTORING/SUSPECT).
2. run_query: SELECT TOP 1 name FROM sys.tables — must succeed.

Respond ONLY with a JSON object on the last line:
{"verdict": "pass"|"fail", "reason": "...", "facts": {...}}
"""


def _extract_verdict(text: str) -> dict:
    text = (text or "").strip()
    for line in reversed(text.splitlines()):
        line = line.strip()
        if line.startswith("{") and line.endswith("}"):
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                continue
    return {"verdict": "fail", "reason": f"could not parse verdict from: {text[-200:]}"}


def _run(state: DBRefreshState, phase: Literal["pre", "post"]) -> dict:
    src = state["source"]
    dst = state["dest"]
    is_existing = state["refresh_type"] == "existing"

    user_msg = (
        f"Phase: {phase}. Refresh type: {state['refresh_type']}.\n"
        f"Source: server='source' db='{src['db']}'\n"
        f"Dest: server='dest' db='{dst['db']}'\n"
        f"{'Check pre-conditions for ' + ('existing-DB' if is_existing else 'new-DB') + ' refresh.' if phase == 'pre' else 'Check post-restore health.'}\n"
        f"Use the tools provided. End your reply with the JSON verdict line."
    )

    tools = _TOOLS_PRE if phase == "pre" else _TOOLS_POST
    prompt = _PRE_PROMPT if phase == "pre" else _POST_PROMPT
    result = run_react(tools, prompt, user_msg)
    text = extract_final_text(result)
    verdict = _extract_verdict(text)

    key = "pre_validation" if phase == "pre" else "post_validation"
    audit.write(CFG.sqlite_path, state["ticket_key"], "validation", phase,
                verdict.get("verdict", "fail"), verdict)

    update: dict = {key: verdict, "current_step": f"validation_{phase}_done"}
    if verdict.get("verdict") != "pass":
        update["errors"] = [{
            "step": f"validation_{phase}",
            "category": "validation_failed",
            "message": verdict.get("reason", "validation failed"),
            "sql": None,
        }]
    return update


def validation_pre_node(state: DBRefreshState) -> dict:
    return _run(state, "pre")


def validation_post_node(state: DBRefreshState) -> dict:
    return _run(state, "post")
