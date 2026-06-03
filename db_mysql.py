from __future__ import annotations

import os
from typing import Any, Dict, List, Sequence

import pymysql


def _env(name: str, default: str | None = None) -> str | None:
    v = os.getenv(name)
    if v is None or v == "":
        return default
    return v


def get_db_config() -> dict:
    return {
        "host": _env("DB_HOST", "127.0.0.1"),
        "port": int(_env("DB_PORT", "3306") or "3306"),
        "user": _env("DB_USER", "root"),
        "password": _env("DB_PASSWORD", ""),
        "database": _env("DB_NAME", None),
    }


def get_table_name() -> str:
    t = _env("DB_TABLE", None)
    if not t:
        raise RuntimeError("Missing DB_TABLE environment variable.")
    return t


def connect():
    cfg = get_db_config()
    if not cfg.get("database"):
        raise RuntimeError("Missing DB_NAME environment variable.")
    return pymysql.connect(
        host=cfg["host"],
        port=cfg["port"],
        user=cfg["user"],
        password=cfg["password"],
        database=cfg["database"],
        autocommit=True,
    )


def fetch_columns(conn, table: str) -> List[str]:
    cur = conn.cursor()
    cur.execute(f"DESCRIBE `{table}`")
    cols = [row[0] for row in cur.fetchall()]
    cur.close()
    return cols


def fetch_rows(conn, table: str, columns: Sequence[str], limit: int) -> List[Dict[str, Any]]:
    cols_sql = ", ".join(f"`{c}`" for c in columns)
    cur = conn.cursor()
    cur.execute(f"SELECT {cols_sql} FROM `{table}` LIMIT %s", (int(limit),))
    rows = cur.fetchall()
    cur.close()
    out: List[Dict[str, Any]] = []
    for tup in rows:
        out.append({columns[i]: tup[i] for i in range(len(columns))})
    return out
