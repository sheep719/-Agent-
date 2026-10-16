export const dynamic = "force-dynamic";

const BACKEND_URL = process.env.BACKEND_URL || "http://127.0.0.1:8000";

/**
 * 前端自身的健康检查：
 * 1. Next.js 存活即返回 ok
 * 2. 同时探测后端 /health，把两端状态一起带回去（骨架 ping 通的核心探针）
 */
export async function GET() {
  let backend: { ok: boolean; status_code?: number; detail?: string } = { ok: false };

  try {
    const resp = await fetch(`${BACKEND_URL}/health`, {
      cache: "no-store",
      signal: AbortSignal.timeout(3000),
    });
    backend = { ok: resp.ok, status_code: resp.status };
  } catch (err) {
    backend = { ok: false, detail: err instanceof Error ? err.message : "unreachable" };
  }

  return Response.json({
    status: "ok",
    service: "resumepilot-frontend",
    backend,
  });
}
