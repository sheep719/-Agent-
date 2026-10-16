"""ResumePilot API 入口

D1 骨架验收：
- GET  /health         → 后端自检 200
- GET  /ping/frontend  → 反向探测前端 :3000（骨架互相 ping 通的另一半）
- POST /api/analyze    → 跑 LangGraph 三 Agent 流水线（stub 数据；SSE 流式 D4 接入）
"""
import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.graph.workflow import build_graph
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


@app.post("/api/analyze", response_model=AnalyzeResponse)
async def analyze(req: AnalyzeRequest):
    result = await graph.ainvoke({"resume_text": req.resume_text, "jd_text": req.jd_text})
    return AnalyzeResponse(
        resume=result.get("resume"),
        match=result.get("match"),
        rewrites=result.get("rewrites", []),
        trace=result.get("trace", []),
    )
