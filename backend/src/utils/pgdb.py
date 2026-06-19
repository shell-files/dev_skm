"""
pgdb.py
레이어: Utils
역할: PostgreSQL 연결 유틸리티 (psycopg v3) — MariaDB db.py와 동일한 패턴으로 구성.
"""

import psycopg
from psycopg.rows import dict_row
from src.utils.settings import settings


def _conn_kwargs() -> dict:
    return {
        "host": settings.pg_db_host,
        "port": settings.pg_db_port,
        "dbname": settings.pg_db_database,
        "user": settings.pg_db_user,
        "password": settings.pg_db_password,
    }


def pgFindAll(sql: str, params=None) -> list[dict]:
    """PostgreSQL에서 여러 행 조회."""
    try:
        with psycopg.connect(**_conn_kwargs(), row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                return cur.fetchall()
    except Exception as e:
        print(f"[pgdb] PostgreSQL Error (findAll): {e}")
        return []


def pgFindOne(sql: str, params=None) -> dict | None:
    """PostgreSQL에서 단일 행 조회."""
    try:
        with psycopg.connect(**_conn_kwargs(), row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                return cur.fetchone()
    except Exception as e:
        print(f"[pgdb] PostgreSQL Error (findOne): {e}")
        return None
