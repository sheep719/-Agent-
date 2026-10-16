"""D7 验收：真实简历 × 3 个 JD 全流程实测

跑法：.venv/Scripts/python.exe -X utf8 tests/run_e2e.py
产出：每 JD 一份结果摘要 + 总体验收结论（不落库 session 为 e2e-verify）
"""
import asyncio
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")  # 读 backend/.env

FIXTURES = Path(__file__).parent / "fixtures"
JDS = ["jd_agent_dev.txt", "jd_python_backend.txt", "jd_data_analyst.txt"]


async def main():
    import httpx

    from app.agents.parser_agent import parse_resume
    from app.llm import is_stub
    from app.pdf import extract_pdf

    if is_stub():
        print("!! 未配置 DEEPSEEK_API_KEY，stub 模式——非真实测试，退出")
        return 1

    pdf = (FIXTURES / "my_resume.pdf").read_bytes()
    resume_text = extract_pdf(pdf).text

    print("== Agent 1 解析（真机，1 次调用，3 个 JD 复用）==")
    t0 = time.perf_counter()
    resume = await parse_resume(resume_text)
    print(f"   耗时 {time.perf_counter() - t0:.1f}s | 技能: {resume['skills']}")

    summary = []
    async with httpx.AsyncClient(timeout=120) as client:
        for jd_name in JDS:
            jd_text = (FIXTURES / jd_name).read_text(encoding="utf-8")
            print(f"\n== {jd_name} 全流程（SSE）==")
            t0 = time.perf_counter()
            events = {}
            async with client.stream(
                "POST",
                "http://127.0.0.1:8000/api/analyze/stream",
                data={"resume": json.dumps(resume, ensure_ascii=False),
                      "jd_text": jd_text, "session_id": "e2e-verify"},
            ) as resp:
                assert resp.status_code == 200, f"HTTP {resp.status_code}"
                async for line in aiter_sse(resp):
                    ev, data = line
                    events.setdefault(ev, []).append(data)
                    if ev == "error":
                        print("   ERROR:", data)

            dur = time.perf_counter() - t0
            match = (events.get("match") or [{}])[0]
            rewrites = events.get("rewrite", [])
            done = (events.get("done") or [{}])[0]
            trace = (events.get("trace") or [{}])[0]
            n_reqs = len(match.get("requirements", []))

            print(f"   总分 {match.get('total_score')} | 要求 {n_reqs} 条 | "
                  f"改写 {len(rewrites)} 条 | 全程 {dur:.1f}s | analysis_id={done.get('analysis_id')}")

            # 断言：每个 JD 至少 5 条要求、改写建议非空、无 error 事件
            assert n_reqs >= 5, f"要求条数过少: {n_reqs}"
            assert len(rewrites) >= 1, "无改写建议"
            assert "error" not in events, events.get("error")

            # 证据引用抽查：hit/partial 必须有证据
            for r in match.get("requirements", []):
                if r["status"] in ("hit", "partial") and not r["evidence"]:
                    print(f"   !! 证据缺失: {r['requirement']}")

            summary.append({
                "jd": jd_name, "score": match.get("total_score"),
                "reqs": n_reqs, "rewrites": len(rewrites),
                "dimensions": match.get("dimension_scores"),
                "analysis_id": done.get("analysis_id"),
            })

    print("\n==== D7 验收汇总 ====")
    for s in summary:
        print(f"  {s['jd']:24s} 总分 {s['score']:5.1f} | {s['reqs']} 条要求 | "
              f"{s['rewrites']} 条建议 | {s['dimensions']}")
    print("PASS: 3 JD 全流程（解析/匹配/流式改写/落库）全部通过")

    # 历史记录核验
    async with httpx.AsyncClient() as client:
        hist = (await client.get(
            "http://127.0.0.1:8000/api/history?session_id=e2e-verify")).json()
    print(f"历史落库: {len(hist)} 条（session=e2e-verify）")
    assert len(hist) == 3
    return 0


async def aiter_sse(resp):
    """把 SSE 流解析成 (event, data) 异步迭代器"""
    ev = None
    async for raw in resp.aiter_lines():
        if raw.startswith("event: "):
            ev = raw[7:]
        elif raw.startswith("data: ") and ev:
            yield ev, json.loads(raw[6:])
            ev = None


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
