"""Agent 3 · 改写器（Rewriter）：只处理不达标条目，STAR 法则改写

D4 做实，核心设计（面试考点）：
1. 流式粒度取舍：JSON 结构化输出与 token 级流式天然冲突（JSON 没闭合无法解析），
   改用**条目级并发流式**——每条建议独立 LLM 调用，asyncio.gather 并发，
   完成一条经 queue 推一条（SSE）。比串行快 N 倍，比 token 流式可靠。
2. 伦理红线：不编造。miss 条目给"如何补充"的指导性建议（占位符标注），
   partial 条目基于简历已有素材 STAR 改写。量化数字只能来自简历原文或占位。
3. 筛选逻辑：partial（有素材，任意类）+ miss 的 hard_skill/project（指导性），
   跳过 education 硬门槛（改不了）和 bonus miss（编不出来），上限 MAX_REWRITES 条。
"""
import asyncio
import logging

from pydantic import ValidationError

from app.llm import chat_json, is_stub
from app.schemas import RewriteSuggestion

logger = logging.getLogger(__name__)

MAX_REWRITES = 6  # 控制成本与信噪比：单次最多改写条数

REWRITE_PROMPT = """你是简历改写专家。针对一条匹配不足的 JD 要求，给出改写建议。

背景：简历原文 + 目标 JD。你只处理这一条要求：
{requirement_block}

规则：
- STAR 法则（情境-任务-行动-结果），强调量化
- 如果简历中有相关素材：基于素材改写，量化数字只能来自简历原文
- 如果简历中完全没有相关素材：给出"建议补充"的指导性文案，用占位符（如 X%、N 次）标注需要用户填入真实数据，**严禁编造经历或数字**
- rewritten 要可直接粘贴进简历
- reason 一句话说明为什么这样写更匹配 JD

输出 JSON：
{{"original": "简历中被改写的原文（无素材时给该条要求的指向）", "rewritten": "改写后文案", "reason": "理由"}}
只输出 JSON。"""


def _get_queue(config: dict | None):
    """从 LangGraph config 拿 SSE 侧信道 queue（无则 None，非流式模式）"""
    if not config:
        return None
    return (config.get("configurable") or {}).get("stream_queue")


def select_rewrite_targets(requirements: list[dict]) -> list[dict]:
    """筛选可改写条目：partial 优先，其次 miss 的 hard_skill/project（指导性）"""
    partial = [r for r in requirements if r["status"] == "partial"]
    miss_actionable = [
        r for r in requirements
        if r["status"] == "miss" and r["category"] in ("hard_skill", "project")
    ]
    return (partial + miss_actionable)[:MAX_REWRITES]


async def _rewrite_one(resume: dict, req: dict, jd_hint: str) -> dict:
    """单条改写：一次小 LLM 调用，独立校验（单条失败不拖垮整批）"""
    requirement_block = (
        f"要求：{req['requirement']}\n类别：{req['category']}\n"
        f"当前判定：{req['status']}\n简历证据：{req['evidence'] or '（无）'}"
    )
    messages = [
        {"role": "system", "content": REWRITE_PROMPT.format(requirement_block=requirement_block)},
        {"role": "user", "content": f"【简历 JSON】\n{resume}\n\n【JD 摘要】\n{jd_hint[:300]}"},
    ]
    for attempt in range(2):
        data = await chat_json(messages)
        try:
            return RewriteSuggestion(**data).model_dump() | {
                "for_requirement": req["requirement"],
                "was_status": req["status"],
            }
        except ValidationError as exc:
            logger.warning("改写条目校验失败（第 %d 次）: %s", attempt + 1, exc.error_count())
            messages = messages + [
                {"role": "assistant", "content": str(data)},
                {"role": "user", "content": f"校验失败：{exc.errors(include_url=False)[:3]}，重新输出完整 JSON。"},
            ]
    raise ValueError(f"改写失败：{req['requirement']}")


async def rewrite(resume: dict, requirements: list[dict], config: dict | None = None) -> list[dict]:
    queue = _get_queue(config)
    targets = select_rewrite_targets(requirements)
    if not targets:
        return []

    if is_stub():
        return await _stub_stream(targets, queue)

    # 条目级并发：每条独立调用，完成一条推一条
    async def one_with_push(req: dict) -> dict:
        try:
            item = await _rewrite_one(resume, req, jd_hint="")
            ok = True
        except Exception as exc:  # 单条失败降级为占位说明，不拖垮整批
            logger.warning("单条改写失败: %s", exc)
            item = {
                "original": req["requirement"],
                "rewritten": "（该条改写生成失败，请重试）",
                "reason": str(exc)[:100],
                "for_requirement": req["requirement"],
                "was_status": req["status"],
            }
            ok = False
        if queue:
            await queue.put({"type": "rewrite", "data": item, "ok": ok})
        return item

    return list(await asyncio.gather(*[one_with_push(r) for r in targets]))


async def _stub_stream(targets: list[dict], queue) -> list[dict]:
    """stub 模式：模拟逐条推送节奏（演示流式效果，0 成本）"""
    results = []
    for i, req in enumerate(targets):
        await asyncio.sleep(0.4)  # 模拟 LLM 延迟
        item = {
            "original": f"简历中与「{req['requirement']}」相关的表述",
            "rewritten": f"运用 STAR 法则重构的「{req['requirement']}」条目（stub 演示文案，量化数据用占位 X% 标注）",
            "reason": "补齐行动与量化结果，直接命中 JD 关键词",
            "for_requirement": req["requirement"],
            "was_status": req["status"],
        }
        if queue:
            await queue.put({"type": "rewrite", "data": item, "ok": True})
        results.append(item)
    return results
