"use client";

import type { RewriteSuggestion } from "@/lib/types";

/** 改写建议卡片：原文 → STAR 改写 → 理由，流式逐条插入 */
export default function RewriteCard({ item, index }: { item: RewriteSuggestion; index: number }) {
  const isGuidance = item.was_status === "miss";
  return (
    <div
      className="rounded-xl border border-gray-200 bg-white p-5"
      style={{ animation: "fadeSlideIn 0.4s ease" }}
    >
      <div className="flex items-center justify-between gap-3">
        <p className="text-sm font-semibold text-gray-900">
          建议 {index + 1} · {item.for_requirement}
        </p>
        <span
          className={`shrink-0 rounded-md border px-2 py-0.5 text-xs ${
            isGuidance
              ? "border-blue-200 bg-blue-50 text-blue-700"
              : "border-amber-200 bg-amber-50 text-amber-700"
          }`}
        >
          {isGuidance ? "补充模板（占位符待填）" : "基于现有素材改写"}
        </span>
      </div>

      <div className="mt-4 space-y-3 text-sm">
        <div className="rounded-lg bg-gray-50 px-3.5 py-2.5">
          <p className="text-xs font-medium text-gray-400">原文</p>
          <p className="mt-1 text-gray-600">{item.original}</p>
        </div>
        <div className="rounded-lg border border-emerald-100 bg-emerald-50/60 px-3.5 py-2.5">
          <p className="text-xs font-medium text-emerald-600">STAR 改写</p>
          <p className="mt-1 leading-relaxed text-gray-900">{item.rewritten}</p>
        </div>
        <p className="text-xs leading-relaxed text-gray-500">💡 {item.reason}</p>
      </div>
    </div>
  );
}
