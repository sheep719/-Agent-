"use client";

import { useEffect, useState } from "react";
import { BACKEND_URL } from "@/lib/sse";
import { useAnalysis } from "@/lib/store";

interface HistoryItem {
  id: number;
  filename: string | null;
  jd_digest: string;
  total_score: number;
  rewrites_count: number;
  created_at: number;
}

/** 历史记录面板：本次浏览器会话（localStorage session ID）的分析列表 */
export default function HistoryPanel() {
  const { sessionId } = useAnalysis();
  const [items, setItems] = useState<HistoryItem[] | null>(null);

  useEffect(() => {
    if (sessionId === "ssr") return;
    fetch(`${BACKEND_URL}/api/history?session_id=${sessionId}`)
      .then((r) => (r.ok ? r.json() : []))
      .then(setItems)
      .catch(() => setItems([]));
  }, [sessionId]);

  if (!items || items.length === 0) return null;

  return (
    <section className="mt-8">
      <h2 className="text-sm font-semibold text-gray-900">历史分析（本浏览器）</h2>
      <div className="mt-3 space-y-2">
        {items.map((it) => (
          <div
            key={it.id}
            className="flex items-center gap-3 rounded-lg border border-gray-200 bg-white px-4 py-2.5 text-sm"
          >
            <span
              className={`w-10 text-right font-semibold tabular-nums ${
                it.total_score >= 70 ? "text-emerald-600"
                : it.total_score >= 40 ? "text-amber-600" : "text-red-600"
              }`}
            >
              {it.total_score.toFixed(0)}
            </span>
            <span className="text-gray-400">·</span>
            <span className="truncate text-gray-700">{it.filename || "未命名简历"}</span>
            <span className="ml-auto shrink-0 text-xs text-gray-400">
              {it.rewrites_count} 条建议 ·{" "}
              {new Date(it.created_at * 1000).toLocaleString("zh-CN", {
                month: "numeric", day: "numeric", hour: "2-digit", minute: "2-digit",
              })}
            </span>
          </div>
        ))}
      </div>
    </section>
  );
}
