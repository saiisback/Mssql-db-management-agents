from __future__ import annotations

from typing import Annotated, Literal, TypedDict
from operator import add


class DBEndpoint(TypedDict):
    server: str
    port: int
    db: str


class ErrorEntry(TypedDict):
    step: str
    category: str
    message: str
    sql: str | None


class DBRefreshState(TypedDict, total=False):
    ticket_key: str
    requester: str
    environment: str
    refresh_type: Literal["new", "existing"]

    source: DBEndpoint
    dest: DBEndpoint

    auth_decision: Literal["approved", "rejected", "pending"]
    auth_reason: str

    pre_validation: dict
    backup_file: str | None
    rights_snapshot: dict
    refresh_result: dict
    post_validation: dict
    apply_rights_result: dict

    current_step: str
    errors: Annotated[list[ErrorEntry], add]
    retry_count: int
    final_status: Literal["done", "rework", "rejected"]
