"""Jira Cloud integration: poll, parse template, transition, comment."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from atlassian import Jira

from config import CFG


_TEMPLATE_FIELDS = {
    "source_db": r"Source\s*DB\s*:\s*(.+)",
    "source_server": r"Source\s*Server\s*:\s*(.+)",
    "dest_db": r"Dest\s*DB\s*:\s*(.+)",
    "dest_server": r"Dest\s*Server\s*:\s*(.+)",
    "environment": r"Environment\s*:\s*(.+)",
    "refresh_type": r"Refresh\s*Type\s*:\s*(.+)",
}


@dataclass
class ParsedTicket:
    key: str
    requester: str
    source_db: str
    source_server: str
    dest_db: str
    dest_server: str
    environment: str
    refresh_type: str
    raw_description: str


class TemplateParseError(ValueError):
    pass


def _client() -> Jira | None:
    if not CFG.jira_enabled:
        return None
    return Jira(
        url=CFG.jira_url,
        username=CFG.jira_email,
        password=CFG.jira_api_token,
        cloud=True,
    )


def parse_description(description: str) -> dict[str, str]:
    out: dict[str, str] = {}
    missing: list[str] = []
    for field, pattern in _TEMPLATE_FIELDS.items():
        m = re.search(pattern, description, re.IGNORECASE)
        if not m:
            missing.append(field)
        else:
            out[field] = m.group(1).strip()
    if missing:
        raise TemplateParseError(f"Missing template fields: {', '.join(missing)}")
    rt = out["refresh_type"].lower()
    if rt not in ("new", "existing"):
        raise TemplateParseError(f"refresh_type must be 'new' or 'existing', got: {out['refresh_type']}")
    out["refresh_type"] = rt
    return out


def get_open_refresh_tickets() -> list[ParsedTicket]:
    """Return tickets in project=PROJECT_KEY with status='To Do'."""
    jira = _client()
    if jira is None:
        return []
    jql = f'project = "{CFG.jira_project_key}" AND status = "To Do" ORDER BY created ASC'
    issues = jira.jql(jql, limit=20).get("issues", [])
    parsed: list[ParsedTicket] = []
    for issue in issues:
        fields = issue["fields"]
        description = fields.get("description") or ""
        if isinstance(description, dict):
            description = _flatten_adf(description)
        try:
            d = parse_description(description)
        except TemplateParseError:
            continue
        parsed.append(ParsedTicket(
            key=issue["key"],
            requester=(fields.get("reporter") or {}).get("emailAddress") or "",
            source_db=d["source_db"],
            source_server=d["source_server"],
            dest_db=d["dest_db"],
            dest_server=d["dest_server"],
            environment=d["environment"],
            refresh_type=d["refresh_type"],
            raw_description=description,
        ))
    return parsed


def _flatten_adf(node: dict[str, Any]) -> str:
    """Flatten Jira's Atlassian Document Format to plain text."""
    if not isinstance(node, dict):
        return ""
    if node.get("type") == "text":
        return node.get("text", "")
    parts = [_flatten_adf(c) for c in node.get("content", [])]
    sep = "\n" if node.get("type") in ("paragraph", "heading", "listItem") else ""
    return sep.join(p for p in parts if p) + sep


def transition(ticket_key: str, status_name: str) -> bool:
    jira = _client()
    if jira is None:
        return False
    transitions = jira.get_issue_transitions(ticket_key)
    for t in transitions:
        if t["name"].lower() == status_name.lower():
            jira.set_issue_status_by_transition_id(ticket_key, t["id"])
            return True
    return False


def comment(ticket_key: str, body: str) -> None:
    jira = _client()
    if jira is None:
        return
    jira.issue_add_comment(ticket_key, body)
