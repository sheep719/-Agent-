"""Agent 1 · 解析器（Parser）：简历文本 → 结构化 JSON"""
from app.llm import chat_json, is_stub
from app.schemas import ResumeStructured

PARSER_PROMPT = """你是简历解析器。将用户提供的简历文本解析为如下 JSON 结构：
{{
  "education": ["学历条目，如：XX大学 · 计算机科学与技术 · 本科"],
  "experience": [{"company": "公司", "role": "职位", "bullets": ["职责/成果条目"]}],
  "skills": ["技能"],
  "projects": ["项目名称 · 一句话描述"]
}}
只输出 JSON，不要任何解释。"""


async def parse_resume(resume_text: str) -> dict:
    if is_stub():
        return _stub()

    data = await chat_json([
        {"role": "system", "content": PARSER_PROMPT},
        {"role": "user", "content": resume_text},
    ])
    # Pydantic 校验：字段缺失/类型错直接抛错，由上层重试机制兜底（D2 完整实现）
    return ResumeStructured(**data).model_dump()


def _stub() -> dict:
    return ResumeStructured(
        education=["XX大学 · 计算机科学与技术 · 本科"],
        experience=[{
            "company": "示例公司",
            "role": "后端开发实习生",
            "bullets": ["参与 XX 系统开发，接口 QPS 提升 30%"],
        }],
        skills=["Python", "FastAPI", "MySQL", "LangGraph"],
        projects=["ResumePilot · 简历优化多 Agent 工具"],
    ).model_dump()
