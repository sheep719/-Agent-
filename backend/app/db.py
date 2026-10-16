"""SQLite 历史记录（MVP 五件套第 5 项：按会话 ID 存，不做登录）

设计：
- 标准库 sqlite3（零依赖）+ asyncio.to_thread 包装，避免阻塞事件循环
- 库文件 backend/data/resumepilot.db（gitignore）
- 一个 session（浏览器 localStorage 生成 UUID）对应多条分析记录
"""
import asyncio
import json
import sqlite3
import time
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "resumepilot.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS analyses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    filename TEXT,
    jd_digest TEXT,
    total_score REAL,
    rewrites_count INTEGER DEFAULT 0,
    resume_json TEXT,
    match_json TEXT,
    rewrites_json TEXT,
    created_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_analyses_session ON analyses(session_id, created_at DESC);
"""


def _conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _init() -> None:
    with _conn() as conn:
        conn.executescript(_SCHEMA)


_init()  # import 时建表（幂等）


def _save(
    session_id: str, filename: str | None, jd_digest: str,
    total_score: float, rewrites_count: int,
    resume: dict | None, match: dict | None, rewrites: list,
) -> int:
    with _conn() as conn:
        cur = conn.execute(
            """INSERT INTO analyses
               (session_id, filename, jd_digest, total_score, rewrites_count,
                resume_json, match_json, rewrites_json, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                session_id, filename, jd_digest[:120], total_score, rewrites_count,
                json.dumps(resume, ensure_ascii=False) if resume else None,
                json.dumps(match, ensure_ascii=False) if match else None,
                json.dumps(rewrites, ensure_ascii=False),
                time.time(),
            ),
        )
        return cur.lastrowid


def _list_history(session_id: str, limit: int = 20) -> list[dict]:
    with _conn() as conn:
        rows = conn.execute(
            """SELECT id, filename, jd_digest, total_score, rewrites_count, created_at
               FROM analyses WHERE session_id = ?
               ORDER BY created_at DESC LIMIT ?""",
            (session_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]


def _get_analysis(analysis_id: int) -> dict | None:
    with _conn() as conn:
        row = conn.execute(
            "SELECT * FROM analyses WHERE id = ?", (analysis_id,)
        ).fetchone()
        if not row:
            return None
        d = dict(row)
        for k in ("resume_json", "match_json", "rewrites_json"):
            if d.get(k):
                d[k] = json.loads(d[k])
        return d


# ---- 异步包装（FastAPI 事件循环友好） ----
async def save_analysis(**kwargs) -> int:
    return await asyncio.to_thread(_save, **kwargs)


async def list_history(session_id: str, limit: int = 20) -> list[dict]:
    return await asyncio.to_thread(_list_history, session_id, limit)


async def get_analysis(analysis_id: int) -> dict | None:
    return await asyncio.to_thread(_get_analysis, analysis_id)
