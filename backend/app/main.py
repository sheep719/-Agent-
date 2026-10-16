"""ResumePilot API 入口

D1 骨架验收：
- GET  /health         → 后端自检 200
- GET  /ping/frontend  → 反向探测前端 :3000（骨架互相 ping 通的另一半）
- POST /api/analyze    → 跑 LangGraph 三 Agent 流水线（stub 数据；SSE 流式 D4 接入）
"""
import asyncio
import json
import tempfile
from pathlib import Path

import httpx
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from app import observability
from app.agents.matcher_agent import match_jd
from app.agents.parser_agent import parse_resume
from app.config import settings
from app.graph.workflow import build_graph
from app.mcp_client import parse_resume_pdf_via_mcp
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

    # 定义书 v2：解析走 MCP（工具独立进程），失败自动降级进程内直调
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(raw)
        tmp_path = tmp.name
    try:
        result = await parse_resume_pdf_via_mcp(tmp_path)
    except Exception as exc:
        Path(tmp_path).unlink(missing_ok=True)
        raise HTTPException(502, _llm_error_detail(exc))
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    return {
        "filename": file.filename,
        "pages": result.get("pages"),
        "warnings": result.get("warnings", []),
        "resume": result["resume"],
        "stub_mode": not settings.api_key,
        "via_mcp": result.get("via_mcp", True),
    }


@app.post("/api/match")
async def match_endpoint(
    jd_text: str = Form(...),
    file: UploadFile | None = File(None),
    resume: str | None = Form(None),
):
    """Agent 2 独立入口：JD → 要求清单 → 逐条比对 → 四维评分

    两种用法：
    - 上传 PDF + JD 文本（内部先跑 Agent 1 再匹配）
    - 直接传已解析的 resume JSON + JD 文本（省一次解析调用，前端状态传递用）

    D3 验收：粘贴 JD 能输出评分
    """
    if file is None and not resume:
        raise HTTPException(400, "需要上传 PDF 文件或提供已解析的 resume JSON")

    if file is not None:
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
            resume_dict = await parse_resume(extracted.text)
        except ValueError as exc:
            raise HTTPException(502, f"LLM 解析失败：{exc}")
        except Exception as exc:
            raise HTTPException(502, _llm_error_detail(exc))
    else:
        import json as _json
        try:
            resume_dict = _json.loads(resume)
        except _json.JSONDecodeError:
            raise HTTPException(400, "resume 不是合法 JSON")

    try:
        match = await match_jd(resume_dict, jd_text)
    except ValueError as exc:
        raise HTTPException(502, f"LLM 匹配失败：{exc}")
    except Exception as exc:
        raise HTTPException(502, _llm_error_detail(exc))

    return {"resume": resume_dict, "match": match, "stub_mode": not settings.api_key}


def _llm_error_detail(exc: Exception) -> str:
    msg = str(exc)
    if "402" in msg or "Balance" in msg:
        return "LLM 账户余额不足（402），请充值后重试，或清空 DEEPSEEK_API_KEY 使用 stub 模式"
    if "401" in msg:
        return "LLM API key 无效（401），请检查 backend/.env 中的 DEEPSEEK_API_KEY"
    return f"LLM 调用失败：{msg[:200]}"


@app.post("/api/analyze", response_model=AnalyzeResponse)
async def analyze(req: AnalyzeRequest):
    result = await graph.ainvoke({"resume_text": req.resume_text, "jd_text": req.jd_text})
    return AnalyzeResponse(
        resume=result.get("resume"),
        match=result.get("match"),
        rewrites=result.get("rewrites", []),
        trace=result.get("trace", []),
    )


@app.post("/api/analyze/stream")
async def analyze_stream(
    jd_text: str = Form(...),
    file: UploadFile | None = File(None),
    resume: str | None = Form(None),
):
    """三 Agent 串联 + SSE 流式：D4 核心交付

    事件序列（text/event-stream）：
      progress  - Agent 1/2 执行进度（含耗时）
      resume    - 结构化简历 JSON
      match     - 四维评分 + 要求清单
      rewrite   - 改写建议逐条推送（条目级并发，完成一条推一条）
      trace     - 全链路耗时与跳过信息（含条件边是否触发）
      error     - 错误（流中途失败）
      done      - 结束标记
    """
    if file is None and not resume:
        raise HTTPException(400, "需要上传 PDF 文件或提供已解析的 resume JSON")

    if file is not None:
        if not (file.filename or "").lower().endswith(".pdf"):
            raise HTTPException(400, "只支持 PDF 文件")
        raw = await file.read()
        if len(raw) > 10 * 1024 * 1024:
            raise HTTPException(413, "PDF 超过 10MB 上限")
        try:
            extracted = extract_pdf(raw)
        except NotTextPDFError as exc:
            raise HTTPException(422, str(exc))
        resume_text, warnings = extracted.text, extracted.warnings
    else:
        try:
            parsed = json.loads(resume)
            resume_text, warnings = json.dumps(parsed, ensure_ascii=False), []
        except json.JSONDecodeError:
            raise HTTPException(400, "resume 不是合法 JSON")

    async def event_gen():
        queue: asyncio.Queue = asyncio.Queue()
        import uuid
        trace = observability.start_trace(
            session_id=str(uuid.uuid4())[:8], jd_digest=jd_text
        )
        yield _sse("progress", {"node": "parser", "status": "running"})

        try:
            # Agent 1
            with observability.observe_generation(trace, "parser", "parser-v2", settings.model):
                resume_dict = await parse_resume(resume_text)
            yield _sse("progress", {"node": "parser", "status": "done"})
            yield _sse("resume", {"data": resume_dict, "warnings": warnings})

            # Agent 2
            yield _sse("progress", {"node": "matcher", "status": "running"})
            with observability.observe_generation(trace, "matcher", "matcher-v2", settings.model):
                match_dict = await match_jd(resume_dict, jd_text)
            yield _sse("progress", {"node": "matcher", "status": "done"})
            yield _sse("match", match_dict)

            # 条件边判定（与 LangGraph route_after_match 同一阈值逻辑）
            from app.schemas import SKIP_REWRITE_THRESHOLD
            if match_dict["total_score"] > SKIP_REWRITE_THRESHOLD:
                yield _sse("trace", {
                    "skipped": "rewriter",
                    "reason": f"总分 {match_dict['total_score']} > {SKIP_REWRITE_THRESHOLD}，跳过改写",
                })
                yield _sse("done", {"rewrites": 0})
                return

            # Agent 3（LangGraph 图执行，queue 侧信道逐条推送）
            yield _sse("progress", {"node": "rewriter", "status": "running"})

            async def run_graph():
                config = {"configurable": {"stream_queue": queue}}
                result = await graph.ainvoke(
                    {"resume": resume_dict, "jd_text": jd_text,
                     "match": match_dict, "rewrites": [], "trace": []},
                    config=config,
                )
                await queue.put(None)  # 结束信号
                return result

            graph_task = asyncio.create_task(run_graph())

            # 边跑边推：queue 消息即时下发；图异常立即冒出（不再被 create_task 吞掉）
            rewrites_count = 0
            while True:
                get_task = asyncio.create_task(queue.get())
                done, _ = await asyncio.wait(
                    {get_task, graph_task}, return_when=asyncio.FIRST_COMPLETED
                )
                if graph_task in done and get_task not in done:
                    get_task.cancel()
                    graph_task.result()  # 有异常直接抛给 except
                    break
                msg = await get_task
                if msg is None:
                    break
                yield _sse(msg["type"], msg["data"])
                rewrites_count += 1

            if not graph_task.done():
                await graph_task
            result = graph_task.result()
            observability.flush()
            yield _sse("progress", {"node": "rewriter", "status": "done", "count": rewrites_count})
            yield _sse("trace", {"trace": result.get("trace", []), "skipped": None})
            yield _sse("done", {"rewrites": rewrites_count})

        except Exception as exc:
            yield _sse("error", {"detail": _llm_error_detail(exc)})

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
