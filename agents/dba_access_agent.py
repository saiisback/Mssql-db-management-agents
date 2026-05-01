"""DBA Access Agent — token authentication gate driven by access_policy.yaml."""
from __future__ import annotations

import fnmatch
from pathlib import Path

import yaml

from config import CFG
from state.db_state import DBRefreshState
from tools import audit, jira_tools, teams_tools

_POLICY_PATH = Path(__file__).resolve().parent.parent / "policies" / "access_policy.yaml"


def _load_policy() -> dict:
    with open(_POLICY_PATH) as f:
        return yaml.safe_load(f)


def _match(rule: dict, requester: str, environment: str, action: str) -> bool:
    if rule.get("action") != action:
        return False
    envs = rule.get("environment", [])
    envs = envs if isinstance(envs, list) else [envs]
    if environment.lower() not in [e.lower() for e in envs]:
        return False
    return fnmatch.fnmatch(requester or "", rule.get("requester", ""))


def dba_access_node(state: DBRefreshState) -> dict:
    ticket_key = state["ticket_key"]
    requester = state["requester"]
    environment = state["environment"]

    policy = _load_policy()
    decision = "rejected"
    reason = "no policy matched"

    for rule in policy.get("policies", []):
        if _match(rule, requester, environment, "refresh"):
            decision = rule.get("decision", "rejected")
            reason = rule.get("reason", f"matched rule for env={environment}")
            break

    audit.write(CFG.sqlite_path, ticket_key, "dba_access", "decision", decision, {
        "requester": requester, "environment": environment, "reason": reason,
    })

    if decision == "rejected":
        jira_tools.transition(ticket_key, "Rework")
        jira_tools.comment(ticket_key, f"Auth rejected: {reason}")
        teams_tools.send_auth_rejected(ticket_key, requester, reason)
        return {"auth_decision": "rejected", "auth_reason": reason,
                "current_step": "dba_access_done", "final_status": "rejected"}

    return {"auth_decision": "approved", "auth_reason": reason,
            "current_step": "dba_access_done"}
