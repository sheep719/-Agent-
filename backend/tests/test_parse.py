"""Agent 1 解析链路单元测试（不依赖 API key）

覆盖：
- PDF 提取：文本型 PDF 正常提取
- PDF 提取：非 PDF / 图片型边界
- stub 解析：Pydantic 契约
"""
from pathlib import Path

import pytest

from app.pdf import NotTextPDFError, extract_pdf
from app.agents.parser_agent import _stub
from app.schemas import ResumeStructured

FIXTURES = Path(__file__).parent / "fixtures"


def test_extract_text_pdf():
    raw = (FIXTURES / "my_resume.pdf").read_bytes()
    result = extract_pdf(raw)
    assert "杨 扬" in result.text
    assert "黑龙江科技大学" in result.text
    assert result.pages == 1


def test_extract_image_pdf_raises():
    # 用 reportlab 生成合法但无文本层的空白页 PDF（模拟扫描件）
    import io

    from reportlab.pdfgen import canvas

    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    c.showPage()
    c.save()
    with pytest.raises(NotTextPDFError):
        extract_pdf(buf.getvalue())


def test_stub_contract():
    data = _stub()
    parsed = ResumeStructured(**data)
    assert parsed.education and parsed.experience
    assert all(e.company and e.role for e in parsed.experience)
    assert all(isinstance(e.bullets, list) for e in parsed.experience)
