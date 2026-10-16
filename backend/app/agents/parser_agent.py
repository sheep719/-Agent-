"""Agent 1 · 解析器（Parser）：简历文本 → 结构化 JSON

D2 做实：
- LLM 结构化输出（JSON mode）+ Pydantic 校验
- 校验失败自动重试（把校验错误喂回 LLM，最多 RETRY_TIMES 次）
- stub 模式保留（无 API key 骨架可跑）
"""
import logging

from pydantic import ValidationError

from app.llm import chat_json, is_stub
from app.schemas import ResumeStructured

logger = logging.getLogger(__name__)

RETRY_TIMES = 2  # 首次 + 重试 2 次

PARSER_PROMPT = """你是简历解析器。把用户提供的简历文本解析为如下 JSON 结构（一个对象，不要数组包裹）：
{{
  "education": ["学历条目，格式：学校 · 学历 · 起止时间"],
  "experience": [
    {{"company": "机构/公司名（家教类写'一对一辅导（科目）'）", "role": "角色/职位", "bullets": ["职责与量化成果，逐条"]}}
  ],
  "skills": ["技能条目（带掌握程度或应用场景更佳）"],
  "projects": ["项目名称 · 一句话描述（无则空数组）"]
}}
规则：
- 保留原文中的数字（分数、课时、年限等量化信息），不得编造
- 教育经历含学校/学历/时间；家教/实习/工作都归入 experience
- 简历中找不到的字段给空数组，不要输出 null
- 只输出 JSON，不要任何解释或 markdown 代码块"""


async def parse_resume(resume_text: str) -> dict:
    if is_stub():
        return _stub()

    messages = [
        {"role": "system", "content": PARSER_PROMPT},
        {"role": "user", "content": resume_text},
    ]

    last_err: Exception | None = None
    for attempt in range(1, RETRY_TIMES + 1):
        data = await chat_json(messages)
        try:
            return ResumeStructured(**data).model_dump()
        except ValidationError as exc:
            last_err = exc
            logger.warning("解析结果校验失败（第 %d 次）: %s", attempt, exc.error_count())
            # 把校验错误喂回 LLM 让它自纠（面试故事：校验重试机制）
            messages = messages + [
                {"role": "assistant", "content": str(data)},
                {"role": "user", "content": (
                    f"你的输出未通过 Pydantic 校验：\n{exc.errors(include_url=False)}\n"
                    "请修正字段名/类型（不要 null，缺失字段给空数组），重新输出完整 JSON。"
                )},
            ]

    raise ValueError(f"简历解析校验失败（已重试 {RETRY_TIMES} 次）: {last_err}")


def _stub() -> dict:
    return ResumeStructured(
        education=["黑龙江科技大学 · 本科 · 2024.09-2028.06"],
        experience=[
            {
                "company": "一对一辅导（初二数学）",
                "role": "数学家教",
                "bullets": ["20 课时一对一辅导，学生成绩从 92 分提升至 118 分"],
            },
            {
                "company": "一对一辅导（初二物理）",
                "role": "物理家教",
                "bullets": ["17 课时辅导，学生成绩从 52 分提升至 71 分"],
            },
        ],
        skills=["Python", "数形结合教学法", "思维导图知识框架"],
        projects=["ResumePilot · 简历优化多 Agent 工具"],
    ).model_dump()
