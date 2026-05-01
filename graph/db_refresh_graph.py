"""LangGraph wiring: 8 nodes, conditional edges, SqliteSaver checkpointer."""
from __future__ import annotations

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver

from config import CFG
from state.db_state import DBRefreshState
from agents.reader_agent import reader_node
from agents.dba_access_agent import dba_access_node
from agents.validation_agent import validation_pre_node, validation_post_node
from agents.backup_agent import backup_node
from agents.copy_rights_agent import copy_rights_node
from agents.refresh_agent import refresh_node
from agents.apply_rights_agent import apply_rights_node
from agents.support_agent import support_node
from tools import jira_tools, teams_tools, audit


def _has_new_error(state: DBRefreshState, step_prefix: str) -> bool:
    errors = state.get("errors") or []
    return any(e["step"].startswith(step_prefix) for e in errors)


def route_after_auth(state: DBRefreshState) -> str:
    return "support" if state.get("auth_decision") == "rejected" else "validation_pre"


def route_after_validation_pre(state: DBRefreshState) -> str:
    if _has_new_error(state, "validation_pre"):
        return "support"
    return "copy_rights" if state["refresh_type"] == "new" else "backup"


def route_after_backup(state: DBRefreshState) -> str:
    return "support" if _has_new_error(state, "backup") else "copy_rights"


def route_after_copy_rights(state: DBRefreshState) -> str:
    return "support" if _has_new_error(state, "copy_rights") else "refresh"


def route_after_refresh(state: DBRefreshState) -> str:
    return "support" if _has_new_error(state, "refresh") else "validation_post"


def route_after_validation_post(state: DBRefreshState) -> str:
    return "support" if _has_new_error(state, "validation_post") else "apply_rights"


def route_after_apply_rights(state: DBRefreshState) -> str:
    return "support" if _has_new_error(state, "apply_rights") else "finalize"


def route_after_support(state: DBRefreshState) -> str:
    step = state.get("current_step", "")
    if step.startswith("retry_"):
        return step.replace("retry_", "")
    return END


def finalize_node(state: DBRefreshState) -> dict:
    ticket_key = state["ticket_key"]
    summary = {
        "Source": f"{state['source']['db']} ({state['source']['server']})",
        "Dest": f"{state['dest']['db']} ({state['dest']['server']})",
        "Type": state["refresh_type"],
        "Backup": state.get("backup_file") or "skipped (new DB)",
        "Rights applied": (state.get("apply_rights_result") or {}).get("applied", 0),
    }
    jira_tools.transition(ticket_key, "Done")
    jira_tools.comment(ticket_key, "✅ Refresh completed successfully.\n\n" +
                       "\n".join(f"- {k}: {v}" for k, v in summary.items()))
    teams_tools.send_complete(ticket_key, summary)
    audit.write(CFG.sqlite_path, ticket_key, "finalize", "complete", "ok", summary)
    return {"current_step": "finalize_done", "final_status": "done"}


def build_graph():
    g = StateGraph(DBRefreshState)

    g.add_node("reader", reader_node)
    g.add_node("dba_access", dba_access_node)
    g.add_node("validation_pre", validation_pre_node)
    g.add_node("backup", backup_node)
    g.add_node("copy_rights", copy_rights_node)
    g.add_node("refresh", refresh_node)
    g.add_node("validation_post", validation_post_node)
    g.add_node("apply_rights", apply_rights_node)
    g.add_node("support", support_node)
    g.add_node("finalize", finalize_node)

    g.set_entry_point("reader")
    g.add_edge("reader", "dba_access")
    g.add_conditional_edges("dba_access", route_after_auth,
                            {"validation_pre": "validation_pre", "support": "support"})
    g.add_conditional_edges("validation_pre", route_after_validation_pre,
                            {"backup": "backup", "copy_rights": "copy_rights", "support": "support"})
    g.add_conditional_edges("backup", route_after_backup,
                            {"copy_rights": "copy_rights", "support": "support"})
    g.add_conditional_edges("copy_rights", route_after_copy_rights,
                            {"refresh": "refresh", "support": "support"})
    g.add_conditional_edges("refresh", route_after_refresh,
                            {"validation_post": "validation_post", "support": "support"})
    g.add_conditional_edges("validation_post", route_after_validation_post,
                            {"apply_rights": "apply_rights", "support": "support"})
    g.add_conditional_edges("apply_rights", route_after_apply_rights,
                            {"finalize": "finalize", "support": "support"})

    g.add_conditional_edges("support", route_after_support, {
        "validation_pre": "validation_pre",
        "backup": "backup",
        "copy_rights": "copy_rights",
        "refresh": "refresh",
        "validation_post": "validation_post",
        "apply_rights": "apply_rights",
        END: END,
    })
    g.add_edge("finalize", END)

    return g


_compiled = None


def get_app():
    global _compiled
    if _compiled is not None:
        return _compiled
    saver = SqliteSaver.from_conn_string(CFG.sqlite_path).__enter__()
    _compiled = build_graph().compile(checkpointer=saver)
    return _compiled
