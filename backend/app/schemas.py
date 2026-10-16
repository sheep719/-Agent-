"""Pydantic 数据模型：三个 Agent 的输入/输出契约 + 评分权重常量"""

from typing import Literal

from pydantic import BaseModel, Field

# ---- 评分模型常量（权重可配置）----
WEIGHTS = {
    "hard_skill": 0.40,   # 硬技能
    "project": 0.30,       # 项目经历
    "education": 0.15,     # 学历门槛
    "bonus": 0.15,         # 加分项
}

# 条件边阈值：总分 > 85 跳过改写器（D7 面试故事：拍的，后续基于用户反馈校准）
SKIP_REWRITE_THRESHOLD = 85


# ---- Agent 1 · 解析器输出 ----
class Experience(BaseModel):
    company: str
    role: str
    bullets: list[str] = []


class ResumeStructured(BaseModel):
    education: list[str] = []
    experience: list[Experience] = []
    skills: list[str] = []
    projects: list[str] = []


# ---- Agent 2 · 匹配器输出 ----
class JDRequirement(BaseModel):
    category: Literal["hard_skill", "project", "education", "bonus"]
    requirement: str
    status: Literal["hit", "partial", "miss"]  # 命中/部分/缺失
    evidence: str      # 简历原文引用（可解释评分的核心），miss 时为空
    score: float = Field(ge=0, le=100)


class MatchResult(BaseModel):
    requirements: list[JDRequirement] = []
    dimension_scores: dict[str, float] = {}  # 四维分
    total_score: float = 0                    # 加权总分 0-100


# ---- Agent 3 · 改写器输出 ----
class RewriteSuggestion(BaseModel):
    original: str    # 原文
    rewritten: str   # STAR 改写
    reason: str      # 为什么这样写更匹配 JD


# ---- API 请求/响应 ----
class AnalyzeRequest(BaseModel):
    resume_text: str = "(骨架模式：D2 接入 pdfplumber)"
    jd_text: str = "(骨架模式：D2 接入 JD 输入框)"


class AnalyzeResponse(BaseModel):
    resume: dict | None = None
    match: dict | None = None
    rewrites: list = []
    trace: list = []   # 每个节点的耗时与执行记录（可观测性）
