"""MCP server exposing 11 SQL Server tools over stdio.

Run as: python -m tools.mcp_server
The agents launch this as a subprocess; stdio is the MCP transport.
"""
from __future__ import annotations

import json
import os
import shutil
import time
from typing import Any

import pymssql
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("mssql-mcp")

SOURCE = {
    "server": os.getenv("MSSQL_SOURCE_SERVER", "localhost"),
    "port": int(os.getenv("MSSQL_SOURCE_PORT", "1433")),
    "user": os.getenv("MSSQL_SOURCE_USER", "sa"),
    "password": os.getenv("MSSQL_SOURCE_PASSWORD", ""),
}
DEST = {
    "server": os.getenv("MSSQL_DEST_SERVER", "localhost"),
    "port": int(os.getenv("MSSQL_DEST_PORT", "1434")),
    "user": os.getenv("MSSQL_DEST_USER", "sa"),
    "password": os.getenv("MSSQL_DEST_PASSWORD", ""),
}
BACKUP_PATH_CONTAINER = os.getenv("BACKUP_PATH_CONTAINER", "/var/opt/mssql/backups")
BACKUP_PATH_HOST = os.getenv("BACKUP_PATH_HOST", "./backups")
SCRIPTS_DIR = os.getenv("SCRIPTS_DIR", "./scripts")


def _conn(target: str, db: str = "master"):
    cfg = SOURCE if target == "source" else DEST
    return pymssql.connect(
        server=cfg["server"],
        port=cfg["port"],
        user=cfg["user"],
        password=cfg["password"],
        database=db,
        autocommit=True,
        timeout=60,
        login_timeout=10,
    )


def _rows(cursor) -> list[dict[str, Any]]:
    cols = [c[0] for c in cursor.description] if cursor.description else []
    return [dict(zip(cols, r)) for r in cursor.fetchall()]


_READONLY_PREFIXES = ("select", "with", "show", "exec sp_", "execute sp_")


def _is_readonly(sql: str) -> bool:
    s = sql.strip().lower()
    return any(s.startswith(p) for p in _READONLY_PREFIXES)


@mcp.tool()
def list_databases(server: str) -> str:
    """List all databases on a server (server='source'|'dest')."""
    with _conn(server) as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT name, state_desc, suser_sname(owner_sid) AS owner, "
            "(SELECT SUM(size)*8/1024 FROM sys.master_files WHERE database_id = d.database_id) AS size_mb "
            "FROM sys.databases d WHERE name NOT IN ('master','tempdb','model','msdb')"
        )
        return json.dumps(_rows(cur), default=str)


@mcp.tool()
def run_query(server: str, db: str, sql: str) -> str:
    """Execute a read-only SQL query. Rejects writes."""
    if not _is_readonly(sql):
        return json.dumps({"error": "run_query is read-only; use a dedicated tool for writes"})
    with _conn(server, db) as conn, conn.cursor() as cur:
        cur.execute(sql)
        return json.dumps({"columns": [c[0] for c in cur.description] if cur.description else [],
                           "rows": _rows(cur)}, default=str)


@mcp.tool()
def db_health_check(server: str, db: str) -> str:
    """Return online status, owner, and active connection count for a database."""
    with _conn(server) as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT name, state_desc, suser_sname(owner_sid) AS owner FROM sys.databases WHERE name = %s",
            (db,),
        )
        meta = _rows(cur)
        if not meta:
            return json.dumps({"online": False, "error": f"database {db} not found"})
        cur.execute(
            "SELECT COUNT(*) AS active_connections FROM sys.dm_exec_sessions s "
            "JOIN sys.databases d ON s.database_id = d.database_id WHERE d.name = %s",
            (db,),
        )
        ac = _rows(cur)[0]["active_connections"]
        m = meta[0]
        return json.dumps({
            "online": m["state_desc"] == "ONLINE",
            "status": m["state_desc"],
            "owner": m["owner"],
            "active_connections": ac,
        })


@mcp.tool()
def disk_space(server: str, path: str = "") -> str:
    """Return disk space stats for the SQL Server's backup path. `path` ignored locally."""
    target = BACKUP_PATH_HOST
    try:
        total, used, free = shutil.disk_usage(target)
        return json.dumps({
            "path": target,
            "total_gb": round(total / 1024**3, 2),
            "free_gb": round(free / 1024**3, 2),
            "used_gb": round(used / 1024**3, 2),
            "percent_used": round(used * 100 / total, 1),
        })
    except FileNotFoundError:
        return json.dumps({"error": f"path {target} not found"})


@mcp.tool()
def backup_db(server: str, db: str, backup_type: str = "full", compression: bool = True, checksum: bool = True) -> str:
    """Backup a database. backup_type='full'|'diff'|'log'. Returns the .bak path inside the container."""
    ts = time.strftime("%Y%m%d-%H%M%S")
    fname = f"{db}-{backup_type}-{ts}.bak"
    container_path = f"{BACKUP_PATH_CONTAINER}/{fname}"
    host_path = f"{BACKUP_PATH_HOST}/{fname}"

    opts = []
    if backup_type == "diff":
        opts.append("DIFFERENTIAL")
    if compression:
        opts.append("COMPRESSION")
    if checksum:
        opts.append("CHECKSUM")
    opts.append("FORMAT")
    opts.append("INIT")
    opts_sql = ", ".join(opts)

    if backup_type == "log":
        sql = f"BACKUP LOG [{db}] TO DISK = N'{container_path}' WITH {opts_sql}"
    else:
        sql = f"BACKUP DATABASE [{db}] TO DISK = N'{container_path}' WITH {opts_sql}"

    start = time.time()
    try:
        with _conn(server) as conn, conn.cursor() as cur:
            cur.execute(sql)
            while cur.nextset():
                pass
        duration = round(time.time() - start, 1)
        size_mb = round(os.path.getsize(host_path) / 1024**2, 2) if os.path.exists(host_path) else None
        return json.dumps({
            "success": True,
            "bak_path_container": container_path,
            "bak_path_host": host_path,
            "size_mb": size_mb,
            "duration_s": duration,
            "verified": False,
        })
    except Exception as e:
        return json.dumps({"success": False, "error": str(e), "sql": sql})


@mcp.tool()
def restore_verify(server: str, bak_path_container: str) -> str:
    """RESTORE VERIFYONLY against a backup file."""
    sql = f"RESTORE VERIFYONLY FROM DISK = N'{bak_path_container}' WITH CHECKSUM"
    try:
        with _conn(server) as conn, conn.cursor() as cur:
            cur.execute(sql)
            while cur.nextset():
                pass
        return json.dumps({"valid": True})
    except Exception as e:
        return json.dumps({"valid": False, "error": str(e)})


@mcp.tool()
def kill_connections(server: str, db: str) -> str:
    """Kill all active sessions on a database (sets SINGLE_USER then MULTI_USER)."""
    try:
        with _conn(server) as conn, conn.cursor() as cur:
            cur.execute(
                f"IF DB_ID('{db}') IS NOT NULL "
                f"ALTER DATABASE [{db}] SET SINGLE_USER WITH ROLLBACK IMMEDIATE"
            )
            cur.execute(
                f"IF DB_ID('{db}') IS NOT NULL "
                f"ALTER DATABASE [{db}] SET MULTI_USER"
            )
        return json.dumps({"success": True})
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


@mcp.tool()
def restore_db(server: str, bak_path_container: str, target_db: str) -> str:
    """RESTORE DATABASE ... WITH REPLACE, RECOVERY. Caller should kill_connections first."""
    sql = (
        f"RESTORE DATABASE [{target_db}] FROM DISK = N'{bak_path_container}' "
        f"WITH REPLACE, RECOVERY, STATS = 10"
    )
    start = time.time()
    try:
        with _conn(server) as conn, conn.cursor() as cur:
            cur.execute(sql)
            while cur.nextset():
                pass
        return json.dumps({"success": True, "duration_s": round(time.time() - start, 1)})
    except Exception as e:
        return json.dumps({"success": False, "error": str(e), "sql": sql})


@mcp.tool()
def get_db_permissions(server: str, db: str) -> str:
    """Snapshot principals, role memberships, and object permissions for a DB."""
    try:
        with _conn(server, db) as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT name, type_desc, default_schema_name "
                "FROM sys.database_principals "
                "WHERE type IN ('S','U','G') AND name NOT IN ('dbo','guest','INFORMATION_SCHEMA','sys')"
            )
            principals = _rows(cur)

            cur.execute(
                "SELECT r.name AS role_name, m.name AS member_name "
                "FROM sys.database_role_members rm "
                "JOIN sys.database_principals r ON rm.role_principal_id = r.principal_id "
                "JOIN sys.database_principals m ON rm.member_principal_id = m.principal_id"
            )
            role_members = _rows(cur)

            cur.execute(
                "SELECT pr.name AS principal, p.permission_name, p.state_desc, "
                "       OBJECT_SCHEMA_NAME(p.major_id) AS schema_name, "
                "       OBJECT_NAME(p.major_id) AS object_name, p.class_desc "
                "FROM sys.database_permissions p "
                "JOIN sys.database_principals pr ON p.grantee_principal_id = pr.principal_id "
                "WHERE pr.name NOT IN ('public','dbo','guest')"
            )
            perms = _rows(cur)

            return json.dumps({
                "principals": principals,
                "role_members": role_members,
                "permissions": perms,
            }, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def apply_db_permissions(server: str, db: str, snapshot_json: str) -> str:
    """Re-grant permissions from a snapshot produced by get_db_permissions."""
    snapshot = json.loads(snapshot_json) if isinstance(snapshot_json, str) else snapshot_json
    applied = 0
    failed: list[dict[str, Any]] = []
    statements: list[str] = []

    for p in snapshot.get("principals", []):
        name = p["name"]
        statements.append(
            f"IF NOT EXISTS (SELECT 1 FROM sys.database_principals WHERE name = '{name}') "
            f"BEGIN CREATE USER [{name}] FOR LOGIN [{name}] END"
        )

    for rm in snapshot.get("role_members", []):
        statements.append(f"ALTER ROLE [{rm['role_name']}] ADD MEMBER [{rm['member_name']}]")

    for perm in snapshot.get("permissions", []):
        action = perm["state_desc"]
        permission = perm["permission_name"]
        principal = perm["principal"]
        cls = perm.get("class_desc", "")
        if cls == "DATABASE" or not perm.get("object_name"):
            statements.append(f"{action} {permission} TO [{principal}]")
        elif cls == "OBJECT_OR_COLUMN":
            obj = f"[{perm['schema_name']}].[{perm['object_name']}]"
            statements.append(f"{action} {permission} ON {obj} TO [{principal}]")

    with _conn(server, db) as conn, conn.cursor() as cur:
        for stmt in statements:
            try:
                cur.execute(stmt)
                while cur.nextset():
                    pass
                applied += 1
            except Exception as e:
                failed.append({"sql": stmt, "error": str(e)})

    return json.dumps({"applied": applied, "failed": failed})


@mcp.tool()
def run_script(server: str, db: str, script_name: str) -> str:
    """Execute a .sql file from the scripts/ directory against a DB."""
    safe = os.path.basename(script_name)
    path = os.path.join(SCRIPTS_DIR, safe)
    if not os.path.exists(path):
        return json.dumps({"success": False, "error": f"script {safe} not found"})
    with open(path) as f:
        sql = f.read()
    batches = [b.strip() for b in sql.split("\nGO\n") if b.strip()]
    try:
        with _conn(server, db) as conn, conn.cursor() as cur:
            for batch in batches:
                cur.execute(batch)
                while cur.nextset():
                    pass
        return json.dumps({"success": True, "batches": len(batches)})
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


if __name__ == "__main__":
    mcp.run()
