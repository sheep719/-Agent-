"""Langfuse 全链路可观测层（定义书 v2 新增）

设计：
- 每 Agent 节点 = 1 个 langfuse generation，挂同一条 trace（session = 一次分析请求）
- 记录：模型、prompt 摘要、输入/输出摘要、token 用量、耗时、prompt 版本标签
- LANGFUSE_PUBLIC_KEY 未配置时 observability 关闭（零开销直通）——本地骨架无负担
"""
import logging
import os
import time
from contextlib import contextmanager

logger = logging.getLogger(__name__)

_client = None
_initialized = False


def _get_client():
    global _client, _initialized
    if _initialized:
        return _client
    _initialized = True
    if not (os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY")):
        return None
    try:
        from langfuse import Langfuse
        _client = Langfuse(
            host=os.getenv("LANGFUSE_HOST", "http://localhost:3001"),
        )
    except Exception as exc:
        logger.warning("Langfuse 初始化失败（可观测性关闭）: %s", exc)
    return _client


def enabled() -> bool:
    return _get_client() is not None


@contextmanager
def observe_generation(trace, name: str, prompt_version: str, model: str, metadata: dict | None = None):
    """一个 Agent 节点的 generation 埋点：with 块内的执行自动计时/记录"""
    client = _get_client()
    t0 = time.perf_counter()
    gen = None
    if client and trace:
        gen = trace.start_generation(
            name=name,
            model=model,
            metadata={"prompt_version": prompt_version, **(metadata or {})},
        )
    try:
        yield gen
    except Exception as exc:
        if gen:
            gen.end(output={"error": str(exc)[:300]}, completion_end_time=_now())
        raise
    finally:
        if gen:
            gen.end(
                completion_end_time=_now(),
                usage={"total_time_ms": round((time.perf_counter() - t0) * 1000, 1)},
            )


def start_trace(session_id: str, jd_digest: str):
    client = _get_client()
    if not client:
        return None
    return client.trace(
        name="resume-analysis",
        session_id=session_id,
        metadata={"jd_digest": jd_digest[:80]},
    )


def flush():
    if _client:
        try:
            _client.flush()
        except Exception:
            pass


def _now():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc)
