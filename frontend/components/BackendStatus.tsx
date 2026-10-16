"use client";

import { useEffect, useState } from "react";

type HealthResp = {
  status: string;
  service: string;
  backend: { ok: boolean; status_code?: number; detail?: string };
};

export default function BackendStatus() {
  const [health, setHealth] = useState<HealthResp | null>(null);
  const [err, setErr] = useState<string | null>(null);

  async function refresh() {
    setErr(null);
    try {
      const resp = await fetch("/api/health", { cache: "no-store" });
      setHealth(await resp.json());
    } catch (e) {
      setErr(e instanceof Error ? e.message : "fetch failed");
    }
  }

  useEffect(() => {
    refresh();
    const t = setInterval(refresh, 10000);
    return () => clearInterval(t);
  }, []);

  const backendOk = health?.backend?.ok;

  return (
    <div className="mt-4 flex items-center gap-3 rounded-lg bg-gray-50 px-4 py-3 text-sm">
      <span
        className={`inline-block h-2.5 w-2.5 rounded-full ${
          backendOk ? "bg-emerald-500" : err || health ? "bg-red-500" : "bg-gray-300"
        }`}
      />
      {err ? (
        <span className="text-red-600">健康检查请求失败：{err}</span>
      ) : !health ? (
        <span className="text-gray-500">正在探测后端…</span>
      ) : backendOk ? (
        <span className="text-emerald-700">
          后端在线（{health.backend.status_code}）· 前后端已连通
        </span>
      ) : (
        <span className="text-red-600">
          后端离线：{health.backend.detail || `status ${health.backend.status_code}`}（请启动 uvicorn）
        </span>
      )}
      <button
        onClick={refresh}
        className="ml-auto rounded-md border border-gray-300 px-2.5 py-1 text-xs text-gray-600 hover:bg-white"
      >
        重新探测
      </button>
    </div>
  );
}
