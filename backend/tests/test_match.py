"""Agent 2 匹配器单元测试（不依赖 API key）"""
import pytest
from pydantic import ValidationError

from app.agents.matcher_agent import _stub
from app.schemas import WEIGHTS, MatchResult


def test_stub_contract():
    data = _stub()
    m = MatchResult(**data)
    assert m.requirements, "要求清单不能为空"
    assert m.total_score == pytest.approx(
        sum(m.dimension_scores[k] * w for k, w in WEIGHTS.items()), abs=0.1
    )


def test_requirement_validation():
    # 非法 status / 超范围分数 / 非法 category 都要被 Pydantic 拦下（触发重试机制）
    with pytest.raises(ValidationError):
        MatchResult(**{
            "requirements": [{"category": "other", "requirement": "x",
                              "status": "maybe", "evidence": "", "score": 150}],
            "dimension_scores": {"hard_skill": 0, "project": 0, "education": 0, "bonus": 0},
        })


def test_weights_sum():
    assert sum(WEIGHTS.values()) == pytest.approx(1.0)
