"""MCP server · 简历解析工具（独立进程）

定义书 v2（2026-10 修订）：
- 工具层遵循 MCP（Model Context Protocol）标准，FastMCP 封装
- 主程序（LangGraph 节点）作为 MCP client 调用本 server
- 好处：工具独立进程、与编排解耦，未来任何 MCP 客户端（Claude Desktop 等）可复用

启动：python tools/mcp_server.py（stdio 传输，子进程方式被 client 拉起）
"""
import sys
from pathlib import Path

# 让 tools/ 能 import 到 backend/app（复用 pdf.py 与 Pydantic 契约，不复制代码）
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastmcp import FastMCP

from app.agents.parser_agent import parse_resume
from app.pdf import NotTextPDFError, extract_pdf

mcp = FastMCP("resumepilot-tools")


@mcp.tool
def parse_resume_pdf(pdf_path: str) -> dict:
    """解析简历 PDF：提取文本 + LLM 结构化（教育/经历/技能/项目四段 JSON）

    Args:
        pdf_path: PDF 文件绝对路径
    """
    raw = Path(pdf_path).read_bytes()
    try:
        extracted = extract_pdf(raw)
    except NotTextPDFError as exc:
        return {"ok": False, "error": str(exc)}

    import asyncio
    resume = asyncio.run(parse_resume(extracted.text))
    return {"ok": True, "pages": extracted.pages, "warnings": extracted.warnings, "resume": resume}


if __name__ == "__main__":
    mcp.run()  # stdio 传输
