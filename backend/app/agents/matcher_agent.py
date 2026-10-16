"""Agent 2 · 匹配器（Matcher）：JD 拆解 → 逐条比对 → 四维加权评分

D3 做实：
- 单次调用完成"拆解 + 比对"两步（节约成本；两步分开更准但双倍 token，取舍记录在 prompt-iterations.md）
- Pydantic 校验（status 枚举、分数范围）+ 失败重试喂回
- 总分 = 四维加权，代码计算（不信 LLM 的算术）
"""
import logging

from pydantic import ValidationError

from app.llm import chat_json, is_stub
from app.schemas import WEIGHTS, MatchResult

logger = logging.getLogger(__name__)

RETRY_TIMES = 2

MATCHER_PROMPT = """你是 JD 匹配专家，内部完成两步后单次输出：
第一步，把 JD 拆解为要求清单，每条归类（category）：
- hard_skill：硬技能/语言/框架/工具
- project：项目与实战经验要求
- education：学历/专业/年限/实习时长门槛
- bonus：加分项（JD 中带"优先""加分"字样的条目）

第二步，逐条与简历比对：
- status 只能是 hit（简历有明确证据）/ partial（沾边但深度或年限不足）/ miss（简历未体现）
- evidence 必须引用简历原文；miss 时给空字符串
- score 单条 0-100：hit 给 70-100（按掌握深度），partial 给 30-69，miss 给 0-29
- 区分"熟悉"与"精通"：简历写"了解/学习过/课程学习"的技能不得按熟练给分

输出 JSON：
{{
  "requirements": [
    {{"category": "hard_skill", "requirement": "Python 熟练", "status": "hit", "evidence": "简历原文引用", "score": 85}}
  ],
  "dimension_scores": {{"hard_skill": 0, "project": 0, "education": 0, "bonus": 0}}
}}
dimension_scores 是四个类别的整体印象分（0-100），重要条目权重高于次要条目，不是简单平均。
只输出 JSON，不要任何解释或 markdown 代码块。"""


async def match_jd(resume: dict, jd_text: str) -> dict:
    if is_stub():
        return _stub()

    messages = [
        {"role": "system", "content": MATCHER_PROMPT},
        {"role": "user", "content": f"【简历 JSON】\n{resume}\n\n【目标 JD】\n{jd_text}"},
    ]

    last_err: Exception | None = None
    for attempt in range(1, RETRY_TIMES + 1):
        data = await chat_json(messages)
        try:
            result = MatchResult(**data)
            # 总分代码计算，不信 LLM 算术
            result.total_score = round(
                sum(result.dimension_scores.get(k, 0) * w for k, w in WEIGHTS.items()), 1
            )
            return result.model_dump()
        except ValidationError as exc:
            last_err = exc
            logger.warning("匹配结果校验失败（第 %d 次）: %s", attempt, exc.error_count())
            messages = messages + [
                {"role": "assistant", "content": str(data)},
                {"role": "user", "content": (
                    f"你的输出未通过校验：\n{exc.errors(include_url=False)}\n"
                    "注意 status 只能是 hit/partial/miss，score 是 0-100 数字，"
                    "dimension_scores 必须含 hard_skill/project/education/bonus 四键。重新输出完整 JSON。"
                )},
            ]

    raise ValueError(f"JD 匹配校验失败（已重试 {RETRY_TIMES} 次）: {last_err}")


def _stub() -> dict:
    result = MatchResult(
        requirements=[
            {"category": "hard_skill", "requirement": "Python 熟练", "status": "hit",
             "evidence": "编程：Python（程序设计课程实验报告全部满分）", "score": 85},
            {"category": "hard_skill", "requirement": "LangChain/LangGraph", "status": "partial",
             "evidence": "projects: ResumePilot（开发中）", "score": 45},
            {"category": "hard_skill", "requirement": "FastAPI 等 Web 框架", "status": "hit",
             "evidence": "ResumePilot 项目使用 FastAPI", "score": 75},
            {"category": "education", "requirement": "本科及以上 · 计算机 related", "status": "hit",
             "evidence": "黑龙江科技大学 · 本科", "score": 90},
            {"category": "education", "requirement": "每周实习 4 天+", "status": "miss",
             "evidence": "", "score": 20},
            {"category": "project", "requirement": "LLM 应用开发经验", "status": "partial",
             "evidence": "ResumePilot 多 Agent 工具（自研中）", "score": 55},
            {"category": "bonus", "requirement": "开源贡献/博客/竞赛", "status": "miss",
             "evidence": "", "score": 15},
        ],
        dimension_scores={"hard_skill": 68, "project": 55, "education": 55, "bonus": 15},
    )
    result.total_score = round(
        sum(result.dimension_scores.get(k, 0) * w for k, w in WEIGHTS.items()), 1
    )
    return result.model_dump()
