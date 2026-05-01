"""MCP client: spawn the mssql-mcp subprocess and expose tool callables.

Used by every agent that needs to talk to SQL Server. Two ways to use:

1. Synchronous calls (`call_tool`) for deterministic agent code.
2. LangChain tool wrappers (`get_langchain_tools`) for LLM-driven tool selection.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def _server_params() -> StdioServerParameters:
    env = {
        "MSSQL_SOURCE_SERVER": os.getenv("MSSQL_SOURCE_SERVER", "localhost"),
        "MSSQL_SOURCE_PORT": os.getenv("MSSQL_SOURCE_PORT", "1433"),
        "MSSQL_SOURCE_USER": os.getenv("MSSQL_SOURCE_USER", "sa"),
        "MSSQL_SOURCE_PASSWORD": os.getenv("MSSQL_SOURCE_PASSWORD", ""),
        "MSSQL_DEST_SERVER": os.getenv("MSSQL_DEST_SERVER", "localhost"),
        "MSSQL_DEST_PORT": os.getenv("MSSQL_DEST_PORT", "1434"),
        "MSSQL_DEST_USER": os.getenv("MSSQL_DEST_USER", "sa"),
        "MSSQL_DEST_PASSWORD": os.getenv("MSSQL_DEST_PASSWORD", ""),
        "BACKUP_PATH_HOST": os.getenv("BACKUP_PATH_HOST", "./backups"),
        "BACKUP_PATH_CONTAINER": os.getenv("BACKUP_PATH_CONTAINER", "/var/opt/mssql/backups"),
        "SCRIPTS_DIR": os.getenv("SCRIPTS_DIR", "./scripts"),
        "PATH": os.environ.get("PATH", ""),
    }
    return StdioServerParameters(
        command=sys.executable,
        args=["-m", "tools.mcp_server"],
        env=env,
        cwd=str(Path(__file__).resolve().parent.parent),
    )


@asynccontextmanager
async def mcp_session():
    async with stdio_client(_server_params()) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            yield session


async def _async_call(name: str, args: dict[str, Any]) -> Any:
    async with mcp_session() as session:
        result = await session.call_tool(name, args)
        out = []
        for item in result.content:
            if hasattr(item, "text"):
                out.append(item.text)
        joined = "\n".join(out) if out else "{}"
        try:
            return json.loads(joined)
        except json.JSONDecodeError:
            return {"raw": joined}


def call_tool(name: str, **kwargs: Any) -> dict[str, Any]:
    """Synchronous tool call. Returns parsed JSON dict."""
    return asyncio.run(_async_call(name, kwargs))


async def get_langchain_tools(allowed: list[str] | None = None):
    """Return LangChain-compatible tools from the MCP server.

    Pass `allowed` to expose only a subset (per agent tool-binding matrix).
    """
    from langchain_mcp_adapters.tools import load_mcp_tools

    async with mcp_session() as session:
        tools = await load_mcp_tools(session)
        if allowed is not None:
            tools = [t for t in tools if t.name in allowed]
        return tools


def get_langchain_tools_sync(allowed: list[str] | None = None):
    return asyncio.run(get_langchain_tools(allowed))
