import os
from typing import Optional

import httpx
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:HIhe5dt4HDizNNc2@db.oyescxlnnmdqlwjxapax.supabase.co:5432/postgres",
)

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://oyescxlnnmdqlwjxapax.supabase.co")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

_engine: Optional[object] = None
SessionLocal = None
Base = declarative_base()


def _get_engine():
    global _engine, SessionLocal
    if _engine is None:
        _engine = create_engine(
            DATABASE_URL,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
            connect_args={
                "options": "-c statement_timeout=30000",
                "connect_timeout": 5,
            },
        )
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
    return _engine


def get_db():
    engine = _get_engine()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_connection() -> dict:
    """Try Supabase REST API first (fast/IPv4), then direct PostgreSQL."""
    result = {"postgres": False, "rest_api": False, "method": None}

    try:
        key = SUPABASE_SERVICE_KEY or SUPABASE_ANON_KEY
        if SUPABASE_URL and key:
            resp = httpx.get(
                f"{SUPABASE_URL}/rest/v1/",
                headers={
                    "apikey": key,
                    "Authorization": f"Bearer {key}",
                },
                timeout=10,
            )
            result["rest_api"] = resp.status_code in (200, 403)
            if result["rest_api"]:
                result["method"] = "rest_api"
                return result
    except Exception as e:
        print(f"Supabase REST API check failed: {e}")

    try:
        engine = _get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        result["postgres"] = True
        result["method"] = "postgres"
    except Exception as e:
        print(f"Direct PostgreSQL connection failed: {e}")

    return result


def supabase_headers() -> dict:
    key = SUPABASE_SERVICE_KEY or SUPABASE_ANON_KEY
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }


def supabase_rest_get(table: str, params: Optional[dict] = None) -> list:
    resp = httpx.get(
        f"{SUPABASE_URL}/rest/v1/{table}",
        headers=supabase_headers(),
        params=params or {},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


def supabase_rest_post(table: str, data: dict) -> dict:
    resp = httpx.post(
        f"{SUPABASE_URL}/rest/v1/{table}",
        headers=supabase_headers(),
        json=data,
        timeout=10,
    )
    resp.raise_for_status()
    result = resp.json()
    return result[0] if isinstance(result, list) and result else result
