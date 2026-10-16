"""ResumePilot API 入口

D1 骨架验收：
- GET  /health         → 后端自检 200
- GET  /ping/frontend  → 反向探测前端 :3000（骨架互相 ping 通的另一半）
- POST /api/analyze    → 跑 LangGraph 三 Agent 流水线（stub 数据；SSE 流式 D4 接入）
"""
import httpx
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from app.agents.parser_agent import parse_resume
from app.config import settings
from app.graph.workflow import build_graph
from app.pdf import NotTextPDFError, extract_pdf
from app.schemas import AnalyzeRequest, AnalyzeResponse

app = FastAPI(title="ResumePilot API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 编译一次，全局复用（图结构不可变，运行时只是传状态）
graph = build_graph()


@app.get("/health")
async def health():
    return {"status": "ok", "service": "resumepilot-backend", "version": "0.1.0"}


@app.get("/ping/frontend")
async def ping_frontend():
    """后端 → 前端 反向健康检查"""
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            resp = await client.get(f"{settings.frontend_url}/api/health")
            return {
                "frontend_url": settings.frontend_url,
                "status_code": resp.status_code,
                "frontend_says": resp.json(),
                "ok": resp.status_code == 200,
            }
    except Exception as exc:
        return {"frontend_url": settings.frontend_url, "ok": False, "error": str(exc)}


@app.post("/api/parse", response_model=None)
async def parse_endpoint(file: UploadFile = File(...)):
    """Agent 1 独立入口：上传简历 PDF → 提取文本 → LLM 结构化解析

    D2 验收：用自己的简历实测，四段（教育/经历/技能/项目）解析正确
    """
    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(400, "只支持 PDF 文件")

    raw = await file.read()
    if len(raw) > 10 * 1024 * 1024:
        raise HTTPException(413, "PDF 超过 10MB 上限")

    try:
        extracted = extract_pdf(raw)
    except NotTextPDFError as exc:
        raise HTTPException(422, str(exc))

    try:
        resume = await parse_resume(extracted.text)
    except ValueError as exc:
        raise HTTPException(502, f"LLM 解析失败：{exc}")
    except Exception as exc:  # LLM API 错误（余额不足 402 / 鉴权失败 401 / 限流 429 等）
        msg = str(exc)
        if "402" in msg or "Balance" in msg:
            detail = "LLM 账户余额不足（402），请充值后重试，或清空 DEEPSEEK_API_KEY 使用 stub 模式"
        elif "401" in msg:
            detail = "LLM API key 无效（401），请检查 backend/.env 中的 DEEPSEEK_API_KEY"
        else:
            detail = f"LLM 调用失败：{msg[:200]}"
        raise HTTPException(502, detail)

    return {
        "filename": file.filename,
        "pages": extracted.pages,
        "warnings": extracted.warnings,
        "resume": resume,
        "stub_mode": not settings.api_key,
    }


@app.post("/api/analyze", response_model=AnalyzeResponse)
async def analyze(req: AnalyzeRequest):
    result = await graph.ainvoke({"resume_text": req.resume_text, "jd_text": req.jd_text})
    return AnalyzeResponse(
        resume=result.get("resume"),
        match=result.get("match"),
        rewrites=result.get("rewrites", []),
        trace=result.get("trace", []),
    )
