"""MCP client：主程序以标准协议调用 tools/mcp_server.py 的解析工具

定义书 v2：主程序不再直接 import pdf.py + parser_agent 完成解析，
而是通过 MCP client 会话调用独立 server 进程暴露的 parse_resume_pdf 工具。
连接方式：stdio 子进程（本地部署最简，无端口占用）。

降级策略：MCP 连接失败时回退到进程内直调（老路径），保证骨架在任何环境可跑——
这层降级本身就是面试故事（协议化改造如何平滑落地）。
"""
import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

_TOOLS_DIR = Path(__file__).resolve().parents[1] / "tools"

_client = None  # FastMCP client（懒加载单例）
_session = None


async def _ensure_session():
    global _client, _session
    if _session is not None:
        return _session
    try:
        from fastmcp import Client

        _client = Client(_TOOLS_DIR / "mcp_server.py")
        _session = await _client.__aenter__()
        return _session
    except Exception as exc:
        logger.warning("MCP server 连接失败，降级为进程内直调: %s", exc)
        _session = False  # 标记失败，不再重试
        return False


async def parse_resume_pdf_via_mcp(pdf_path: str) -> dict:
    """通过 MCP 调用解析工具；失败时降级进程内直调"""
    session = await _ensure_session()
    if session is False:
        return await _fallback(pdf_path)

    try:
        result = await session.call_tool("parse_resume_pdf", {"pdf_path": pdf_path})
        # FastMCP 4.x：CallToolResult，内容在 .content[0].text（JSON 字符串）
        import json
        data = result.content[0].text if result.content else "{}"
        if isinstance(data, str):
            data = json.loads(data)
        if not data.get("ok"):
            raise RuntimeError(data.get("error", "MCP 工具返回失败"))
        return data
    except Exception as exc:
        logger.warning("MCP 调用失败，降级进程内直调: %s", exc)
        return await _fallback(pdf_path)


async def _fallback(pdf_path: str) -> dict:
    """进程内直调（老路径，MCP 不可用时的兜底）"""
    sys.path.insert(0, str(_TOOLS_DIR))
    from app.agents.parser_agent import parse_resume
    from app.pdf import NotTextPDFError, extract_pdf

    raw = Path(pdf_path).read_bytes()
    try:
        extracted = extract_pdf(raw)
    except NotTextPDFError as exc:
        raise RuntimeError(str(exc)) from exc
    resume = await parse_resume(extracted.text)
    return {"ok": True, "pages": extracted.pages, "warnings": extracted.warnings, "resume": resume}


async def close():
    global _client, _session
    if _client:
        try:
            await _client.__aexit__(None, None, None)
        except Exception:
            pass
        _client, _session = None, None
