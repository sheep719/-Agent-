"""SQLite 历史记录测试"""
import asyncio

from app import db


def test_save_and_list_history():
    async def run():
        sid = "test-session-xyz"
        aid = await db.save_analysis(
            session_id=sid, filename="t.pdf", jd_digest="AI 实习 JD",
            total_score=66.6, rewrites_count=3,
            resume={"skills": ["Python"]}, match={"total_score": 66.6},
            rewrites=[{"rewritten": "x"}],
        )
        assert aid > 0

        items = await db.list_history(sid)
        assert len(items) >= 1
        latest = items[0]
        assert latest["total_score"] == 66.6
        assert latest["rewrites_count"] == 3

        detail = await db.get_analysis(aid)
        assert detail is not None
        assert detail["resume_json"]["skills"] == ["Python"]  # 已反序列化
        return aid

    asyncio.run(run())


def test_get_missing_returns_none():
    assert asyncio.run(db.get_analysis(999999)) is None
