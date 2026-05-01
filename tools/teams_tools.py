"""Teams Incoming Webhook: send adaptive cards / message cards."""
from __future__ import annotations

import requests

from config import CFG


def _post(card: dict) -> None:
    if not CFG.teams_enabled:
        return
    r = requests.post(CFG.teams_webhook_url, json=card, timeout=10)
    r.raise_for_status()


def send_started(ticket_key: str, source: str, dest: str, env: str, requester: str) -> None:
    _post({
        "@type": "MessageCard",
        "@context": "https://schema.org/extensions",
        "themeColor": "0078D7",
        "summary": f"DB Refresh Started — {ticket_key}",
        "title": f"🔵 DB Refresh Started — {ticket_key}",
        "sections": [{
            "facts": [
                {"name": "Ticket", "value": ticket_key},
                {"name": "Requester", "value": requester},
                {"name": "Source", "value": source},
                {"name": "Destination", "value": dest},
                {"name": "Environment", "value": env},
                {"name": "Region", "value": CFG.region},
            ],
        }],
        "potentialAction": [{
            "@type": "OpenUri",
            "name": "View Ticket",
            "targets": [{"os": "default", "uri": f"{CFG.jira_url}/browse/{ticket_key}"}],
        }],
    })


def send_complete(ticket_key: str, summary: dict) -> None:
    facts = [{"name": "Ticket", "value": f"{ticket_key} → Done"}]
    for k, v in summary.items():
        facts.append({"name": k, "value": str(v)})
    _post({
        "@type": "MessageCard",
        "@context": "https://schema.org/extensions",
        "themeColor": "2EB886",
        "summary": f"DB Refresh Complete — {ticket_key}",
        "title": f"✅ DB Refresh Complete — {ticket_key}",
        "sections": [{
            "facts": facts,
            "text": "**APPLICATION TEAM:** Database is ready — you may now connect.",
        }],
        "potentialAction": [{
            "@type": "OpenUri",
            "name": "View Ticket",
            "targets": [{"os": "default", "uri": f"{CFG.jira_url}/browse/{ticket_key}"}],
        }],
    })


def send_failure(ticket_key: str, failed_step: str, error: str, category: str) -> None:
    _post({
        "@type": "MessageCard",
        "@context": "https://schema.org/extensions",
        "themeColor": "C0392B",
        "summary": f"DB Refresh Failed — {ticket_key}",
        "title": f"🔴 DB Refresh Failed — {ticket_key}",
        "sections": [{
            "facts": [
                {"name": "Ticket", "value": f"{ticket_key} → Rework"},
                {"name": "Failed at", "value": failed_step},
                {"name": "Category", "value": category},
                {"name": "Region", "value": CFG.region},
                {"name": "Error", "value": error[:500]},
            ],
        }],
        "potentialAction": [{
            "@type": "OpenUri",
            "name": "View Ticket",
            "targets": [{"os": "default", "uri": f"{CFG.jira_url}/browse/{ticket_key}"}],
        }],
    })


def send_auth_rejected(ticket_key: str, requester: str, reason: str) -> None:
    _post({
        "@type": "MessageCard",
        "@context": "https://schema.org/extensions",
        "themeColor": "B07219",
        "summary": f"DB Refresh Rejected — {ticket_key}",
        "title": f"⛔ DB Refresh Rejected — {ticket_key}",
        "sections": [{
            "facts": [
                {"name": "Ticket", "value": f"{ticket_key} → Rework"},
                {"name": "Requester", "value": requester},
                {"name": "Reason", "value": reason},
            ],
        }],
        "potentialAction": [{
            "@type": "OpenUri",
            "name": "View Ticket",
            "targets": [{"os": "default", "uri": f"{CFG.jira_url}/browse/{ticket_key}"}],
        }],
    })
