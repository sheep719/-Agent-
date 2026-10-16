"""Agent 3 · 改写器（Rewriter）：只处理 partial/miss 段落，STAR 法则改写

D4 将把本节点改为流式输出（SSE），逐字推送到前端。
"""
from app.llm import chat_json, is_stub
from app.schemas import RewriteSuggestion

REWRITER_PROMPT = """你是简历改写专家。只处理匹配度不足（partial/miss）的条目，用 STAR 法则
（情境-任务-行动-结果）改写，强调量化结果。
输出 JSON 数组，每条：
{{"original": "原文", "rewritten": "改写后", "reason": "为什么这样写更匹配 JD"}}"""


async def rewrite(resume: dict, requirements: list[dict]) -> list[dict]:
    weak = [r for r in requirements if r.get("status") in ("partial", "miss")]
    if not weak:
        return []

    if is_stub():
        return _stub()

    data = await chat_json([
        {"role": "system", "content": REWRITER_PROMPT},
        {"role": "user", "content": f"【简历 JSON】\n{resume}\n\n【待改进条目】\n{weak}"},
    ])
    if isinstance(data, dict):  # 兼容模型包一层的情况
        data = data.get("suggestions", [data])
    return [RewriteSuggestion(**item).model_dump() for item in data]


def _stub() -> list[dict]:
    return [
        RewriteSuggestion(
            original="参与 XX 系统开发",
            rewritten="主导 XX 系统核心模块开发（Action），接口平均响应从 800ms 降至 200ms（Result，量化）",
            reason="命中 JD 的『高性能服务』要求，STAR 法则补齐行动与量化结果",
        ).model_dump(),
        RewriteSuggestion(
            original="技能：Python",
            rewritten="技能：Python（3 年，FastAPI / LangGraph 项目实战）",
            reason="JD 要求 Python + Agent 框架经验，标注年限与框架命中度",
        ).model_dump(),
    ]
