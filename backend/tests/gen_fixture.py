"""生成测试用简历 PDF：内容来自用户真实简历（家教简历.docx），排版模拟主流简历样式

用途：
1. D2 验收样本——用自己的简历验证 Agent 1 解析
2. pytest fixture 之外的手工测试入口
"""
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

OUT = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "my_resume.pdf"

FONT = None
for name, candidates in {
    "msyh": [r"C:\Windows\Fonts\msyh.ttc"],
    "simhei": [r"C:\Windows\Fonts\simhei.ttf"],
    "simsun": [r"C:\Windows\Fonts\simsun.ttc"],
}.items():
    for c in candidates:
        if Path(c).exists():
            pdfmetrics.registerFont(TTFont(name, c))
            FONT = name
            break
    if FONT:
        break

if not FONT:
    raise SystemExit("未找到中文字体（msyh/simhei/simsun），无法生成测试 PDF")


def draw(cv: canvas.Canvas, lines: list[tuple[int, str]]):
    """lines: (字号, 文本) 列表，从页顶往下排"""
    cv.setFont(FONT, 10)
    width, height = A4
    y = height - 60
    for size, text in lines:
        cv.setFont(FONT, size)
        cv.drawString(60, y, text)
        y -= size + 8
    cv.save()


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    cv = canvas.Canvas(str(OUT), pagesize=A4)
    cv.setTitle("杨扬-简历")
    draw(cv, [
        (18, "杨 扬"),
        (10, "男 · 20 岁 · 本科 · 黑龙江科技大学"),
        (10, "电话：138****0000 · 邮箱：yang@example.com"),
        (13, "教育经历"),
        (10, "黑龙江科技大学 · 本科 · 2024.09 - 2028.06"),
        (10, "主修课程：数学分析、高等代数、Python 程序设计"),
        (13, "辅导经历"),
        (10, "一对一数学家教 · 初二年级 · 2025暑假"),
        (10, "· 20 课时一对一辅导，学生数学成绩从 92 分提升至 118 分"),
        (10, "一对一家教 · 初二物理 · 2025寒假"),
        (10, "· 17 课时辅导，学生物理成绩从 52 分提升至 71 分"),
        (13, "技能"),
        (10, "教学工具：人教版/北师大版/湘教版教材体系，自备小学初中全套课本"),
        (10, "教学方法：数形结合、思维导图知识框架搭建"),
        (10, "编程：Python（程序设计课程实验报告全部满分）"),
        (13, "自我评价"),
        (10, "高考数学 112 分（2024 新高考 2 卷）、物理 84 分；家教经验 2 年，全天可授课"),
    ])
    print(f"生成: {OUT}")


if __name__ == "__main__":
    main()
