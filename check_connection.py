"""Pre-flight check: verify .env values can actually connect to your SQL Server
and Ollama Cloud before running a real refresh.

Usage:  python check_connection.py
"""
from __future__ import annotations

import sys

import pymssql
import requests
from rich.console import Console

from config import CFG


console = Console()


def check_sql(label: str, cfg) -> bool:
    console.print(f"[cyan]Checking {label}[/cyan] {cfg.server}:{cfg.port} as {cfg.user}...")
    try:
        with pymssql.connect(server=cfg.server, port=cfg.port, user=cfg.user,
                             password=cfg.password, database="master",
                             login_timeout=5, timeout=10) as conn:
            cur = conn.cursor()
            cur.execute("SELECT @@VERSION")
            version = cur.fetchone()[0].split("\n")[0]
            console.print(f"  [green]OK[/green]  {version}")
            cur.execute("SELECT name FROM sys.databases ORDER BY name")
            dbs = [r[0] for r in cur.fetchall()]
            console.print(f"  databases: {', '.join(dbs)}")
            return True
    except Exception as e:
        console.print(f"  [red]FAIL[/red]  {e}")
        return False


def check_ollama() -> bool:
    console.print(f"[cyan]Checking Ollama[/cyan] {CFG.ollama_host} model={CFG.ollama_model}...")
    try:
        url = CFG.ollama_host.rstrip("/") + "/api/chat"
        headers = {"Authorization": f"Bearer {CFG.ollama_api_key}"} if CFG.ollama_api_key else {}
        r = requests.post(url, json={
            "model": CFG.ollama_model,
            "messages": [{"role": "user", "content": "respond with the single word: ok"}],
            "stream": False,
        }, headers=headers, timeout=30)
        r.raise_for_status()
        text = (r.json().get("message") or {}).get("content", "")
        console.print(f"  [green]OK[/green]  model said: {text!r}")
        return True
    except Exception as e:
        console.print(f"  [red]FAIL[/red]  {e}")
        return False


def check_backup_path() -> bool:
    import os
    console.print(f"[cyan]Checking backup path[/cyan] {CFG.backup_path_host}...")
    if not os.path.isdir(CFG.backup_path_host):
        console.print(f"  [yellow]MISSING[/yellow]  create the folder: mkdir \"{CFG.backup_path_host}\"")
        return False
    test = os.path.join(CFG.backup_path_host, ".write_test")
    try:
        with open(test, "w") as f:
            f.write("ok")
        os.remove(test)
        console.print(f"  [green]OK[/green]  Python can write here")
        console.print(f"  [yellow]NOTE[/yellow]  also ensure the SQL Server service account can write here")
        return True
    except Exception as e:
        console.print(f"  [red]FAIL[/red]  {e}")
        return False


def main() -> int:
    console.print("[bold]DB Agents — connection pre-flight[/bold]\n")
    ok_src = check_sql("SOURCE", CFG.source)
    ok_dst = check_sql("DEST  ", CFG.dest)
    ok_bk = check_backup_path()
    ok_ll = check_ollama()
    console.print()
    console.print(f"Jira  enabled: {CFG.jira_enabled}")
    console.print(f"Teams enabled: {CFG.teams_enabled}")
    all_ok = ok_src and ok_dst and ok_bk and ok_ll
    console.print()
    if all_ok:
        console.print("[bold green]All required checks passed.[/bold green] You can run run_refresh.bat.")
        return 0
    console.print("[bold red]Some checks failed.[/bold red] See errors above; fix them before running a refresh.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
