"""Support Agent — central error handler. Categorizes, retries once, escalates to Jira+Teams."""
from __future__ import annotations

import json

from config import CFG
from state.db_state import DBRefreshState
from tools import audit, jira_tools, teams_tools
from agents.llm import make_llm


_CATEGORY_ENUM = [
    "disk_space", "connectivity", "permissions", "suspect_db",
    "active_connections", "backup_integrity", "script_execution",
    "auth_rejected", "llm_tool_call", "unknown",
]

_PROMPT = """You are the DB Support Agent — the central error categorizer and triager.

Given an error from another agent, classify it into one category and decide whether a single retry is reasonable.

Categories: disk_space, connectivity, permissions, suspect_db, active_connections, backup_integrity, script_execution, auth_rejected, llm_tool_call, unknown.

Transient (retry-eligible): connectivity, active_connections, llm_tool_call.
Terminal (escalate): everything else.

Reply with a JSON object on a single line:
{"category": "...", "transient": bool, "reason": "...", "recovery_steps": "..."}
"""


def _classify(error: dict) -> dict:
    llm = make_llm()
    msg = json.dumps(error, default=str)
    response = llm.invoke([
        {"role": "system", "content": _PROMPT},
        {"role": "user", "content": f"Error to classify:\n{msg}"},
    ])
    text = response.content if hasattr(response, "content") else str(response)
    for line in reversed((text or "").splitlines()):
        line = line.strip()
        if line.startswith("{") and line.endswith("}"):
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                continue
    return {"category": "unknown", "transient": False,
            "reason": "could not classify", "recovery_steps": "Review error log manually."}


def support_node(state: DBRefreshState) -> dict:
    ticket_key = state["ticket_key"]
    errors = state.get("errors", [])
    if not errors:
        return {"current_step": "support_no_op"}

    last = errors[-1]
    classification = _classify(last)
    retry_count = state.get("retry_count", 0)

    audit.write(CFG.sqlite_path, ticket_key, "support", "classify",
                classification.get("category", "unknown"),
                {"error": last, "classification": classification, "retry_count": retry_count})

    if classification.get("transient") and retry_count < 1:
        return {"current_step": f"retry_{last['step']}", "retry_count": retry_count + 1}

    body_lines = [
        f"DB Refresh failed at step: {last['step']}",
        f"Category: {classification.get('category')}",
        f"Reason: {classification.get('reason')}",
        "",
        "Error:",
        f"```\n{last.get('message','')[:1500]}\n```",
        "",
        "Recovery steps:",
        classification.get("recovery_steps", "Review error and retry manually."),
    ]
    body = "\n".join(body_lines)
    jira_tools.transition(ticket_key, "Rework")
    jira_tools.comment(ticket_key, body)
    teams_tools.send_failure(
        ticket_key=ticket_key,
        failed_step=last["step"],
        error=last.get("message", "")[:500],
        category=classification.get("category", "unknown"),
    )
    audit.write(CFG.sqlite_path, ticket_key, "support", "escalate", "rework",
                {"step": last["step"], "category": classification.get("category")})
    return {"current_step": "support_escalated", "final_status": "rework"}
