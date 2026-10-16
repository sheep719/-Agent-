"""PDF 文本提取（pdfplumber 封装）

职责边界（产品红线）：
- 只处理文本型 PDF；图片型/扫描件直接报错提示"请上传文本型 PDF"，不搞 OCR
- 检测双栏布局（常见解析坑，见 docs/prompt-iterations.md），提取结果带警告
"""
from dataclasses import dataclass, field

import pdfplumber


@dataclass
class PDFExtractResult:
    text: str
    pages: int
    warnings: list[str] = field(default_factory=list)


class NotTextPDFError(Exception):
    """图片型/扫描件 PDF（无可提取文本）"""


def extract_pdf(file_bytes: bytes) -> PDFExtractResult:
    """提取 PDF 全文文本，附布局警告"""
    import io

    warnings: list[str] = []

    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        pages = len(pdf.pages)
        page_texts: list[str] = []
        two_column_pages = 0

        for page in pdf.pages:
            text = page.extract_text() or ""
            page_texts.append(text)

            # 双栏检测：单页字符 x 坐标中位数明显分成左右两簇
            # （简化启发式：右半页字符占比 35%-65% 视为疑似双栏）
            if page.chars:
                mid = (page.bbox[0] + page.bbox[2]) / 2
                right = sum(1 for c in page.chars if c["x0"] > mid)
                ratio = right / len(page.chars)
                if 0.35 < ratio < 0.65:
                    two_column_pages += 1

        text = "\n".join(page_texts).strip()

    if not text:
        raise NotTextPDFError(
            "未能从 PDF 提取到文本，可能为扫描件/图片型 PDF，请上传文本型 PDF"
        )

    if two_column_pages:
        warnings.append(
            f"检测到 {two_column_pages} 页疑似双栏布局，段落顺序可能与视觉顺序不一致，解析结果请人工复核"
        )

    return PDFExtractResult(text=text, pages=pages, warnings=warnings)
