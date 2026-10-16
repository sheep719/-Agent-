"""Agent 3 改写器单元测试（不依赖 API key）"""
import asyncio

from app.agents.rewriter_agent import _stub_stream, select_rewrite_targets


def _req(cat, status):
    return {"category": cat, "requirement": f"要求-{cat}-{status}",
            "status": status, "evidence": "证据" if status != "miss" else "", "score": 50}


def test_select_targets_priority():
    reqs = [
        _req("education", "miss"),      # 教育硬门槛，不可改写 → 跳过
        _req("bonus", "miss"),          # 加分项缺失 → 跳过
        _req("hard_skill", "miss"),     # 可给指导性建议 → 保留
        _req("project", "partial"),     # 有素材改写 → 保留（优先）
        _req("hard_skill", "partial"),  # → 保留（优先）
        _req("education", "partial"),   # partial 任意类 → 保留
    ]
    targets = select_rewrite_targets(reqs)
    cats = {(t["category"], t["status"]) for t in targets}
    assert ("project", "partial") in cats
    assert ("hard_skill", "partial") in cats
    assert ("education", "partial") in cats
    assert ("hard_skill", "miss") in cats
    assert all(not (t["category"] == "education" and t["status"] == "miss") for t in targets)
    assert all(not (t["category"] == "bonus" and t["status"] == "miss") for t in targets)


def test_select_targets_cap():
    reqs = [_req("hard_skill", "partial") for _ in range(10)]
    assert len(select_rewrite_targets(reqs)) == 6  # MAX_REWRITES 上限


def test_stub_stream_pushes_via_queue():
    async def run():
        queue = asyncio.Queue()
        targets = select_rewrite_targets([
            _req("hard_skill", "partial"), _req("project", "miss"),
        ])
        task = asyncio.create_task(_stub_stream(targets, queue))
        events = [await queue.get() for _ in range(len(targets))]  # 收齐即止（None 由外层发）
        results = await task
        return events, results

    events, results = asyncio.run(run())
    assert len(events) == 2 and all(e["type"] == "rewrite" for e in events)
    assert all(r["for_requirement"] for r in results)


def test_conditional_edge_routing():
    from app.graph.workflow import route_after_match
    assert route_after_match({"match": {"total_score": 86}}) == "end"      # >85 跳过改写
    assert route_after_match({"match": {"total_score": 85}}) == "rewriter" # 边界值不跳过
    assert route_after_match({"match": {"total_score": 30}}) == "rewriter"
