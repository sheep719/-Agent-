"""Agent 2 · 匹配器（Matcher）：JD 拆解 → 逐条比对 → 四维加权评分"""
from app.llm import chat_json, is_stub
from app.schemas import WEIGHTS, MatchResult

MATCHER_PROMPT = """你是 JD 匹配专家，分两步工作：
1. 把目标 JD 拆解为要求清单（类别：hard_skill 硬技能 / project 项目经历 / education 学历 / bonus 加分项）
2. 逐条与简历比对，标注 hit（命中）/ partial（部分）/ miss（缺失），并引用简历原文作为证据

输出 JSON：
{{
  "requirements": [
    {{"category": "hard_skill", "requirement": "Python", "status": "hit", "evidence": "简历原文引用", "score": 90}}
  ],
  "dimension_scores": {{"hard_skill": 0, "project": 0, "education": 0, "bonus": 0}}
}}
注意：区分"熟悉"与"精通"的掌握程度给分。只输出 JSON。"""


async def match_jd(resume: dict, jd_text: str) -> dict:
    if is_stub():
        return _stub()

    data = await chat_json([
        {"role": "system", "content": MATCHER_PROMPT},
        {"role": "user", "content": f"【简历 JSON】\n{resume}\n\n【目标 JD】\n{jd_text}"},
    ])
    result = MatchResult(**data)
    # 总分 = 四维加权（权重常量可配置）
    result.total_score = round(
        sum(result.dimension_scores.get(k, 0) * w for k, w in WEIGHTS.items()), 1
    )
    return result.model_dump()


def _stub() -> dict:
    return MatchResult(
        requirements=[
            {"category": "hard_skill", "requirement": "Python", "status": "hit",
             "evidence": "skills: Python", "score": 90},
            {"category": "hard_skill", "requirement": "LangGraph", "status": "partial",
             "evidence": "projects: ResumePilot（学习中）", "score": 60},
            {"category": "hard_skill", "requirement": "Kubernetes", "status": "miss",
             "evidence": "", "score": 0},
            {"category": "bonus", "requirement": "开源贡献", "status": "partial",
             "evidence": "GitHub: sheep719", "score": 50},
        ],
        dimension_scores={"hard_skill": 60, "project": 75, "education": 80, "bonus": 50},
        total_score=66.0,
    ).model_dump()
