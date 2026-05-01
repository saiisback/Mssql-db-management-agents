"""LLM factory: kimi-k2.6 via Ollama Cloud, with optional MCP tool binding."""
from __future__ import annotations

import asyncio
from typing import Any

from langchain_ollama import ChatOllama
from langgraph.prebuilt import create_react_agent

from config import CFG
from tools.mcp_client import get_langchain_tools


def make_llm(temperature: float = 0.0) -> ChatOllama:
    kwargs: dict = {
        "model": CFG.ollama_model,
        "base_url": CFG.ollama_host,
        "temperature": temperature,
    }
    if CFG.ollama_api_key:
        kwargs["client_kwargs"] = {
            "headers": {"Authorization": f"Bearer {CFG.ollama_api_key}"}
        }
    return ChatOllama(**kwargs)


async def make_react_agent_async(allowed_tools: list[str], system_prompt: str):
    llm = make_llm()
    tools = await get_langchain_tools(allowed=allowed_tools)
    return create_react_agent(llm, tools, prompt=system_prompt)


def run_react(allowed_tools: list[str], system_prompt: str, user_message: str) -> dict[str, Any]:
    """One-shot: build a ReAct agent, invoke with user_message, return the final state."""
    async def _run():
        agent = await make_react_agent_async(allowed_tools, system_prompt)
        result = await agent.ainvoke({"messages": [{"role": "user", "content": user_message}]})
        return result
    return asyncio.run(_run())


def extract_final_text(react_result: dict[str, Any]) -> str:
    msgs = react_result.get("messages", [])
    if not msgs:
        return ""
    last = msgs[-1]
    return getattr(last, "content", "") or last.get("content", "") if isinstance(last, dict) else ""
