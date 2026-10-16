"use client";

import { useAnalysis } from "@/lib/store";
import type { ReqStatus } from "@/lib/types";

const STATUS_META: Record<ReqStatus, { icon: string; label: string; cls: string }> = {
  hit: { icon: "✅", label: "命中", cls: "bg-emerald-50 text-emerald-700 border-emerald-200" },
  partial: { icon: "⚠️", label: "部分", cls: "bg-amber-50 text-amber-700 border-amber-200" },
  miss: { icon: "❌", label: "缺失", cls: "bg-red-50 text-red-700 border-red-200" },
};

const CAT_LABEL: Record<string, string> = {
  hard_skill: "硬技能", project: "项目", education: "学历", bonus: "加分",
};

/** 逐条要求对照表：状态 + 分数 + 证据引用 */
export default function RequirementList({
  requirements,
}: {
  requirements: { category: string; requirement: string; status: ReqStatus; evidence: string; score: number }[];
}) {
  return (
    <div className="overflow-hidden rounded-xl border border-gray-200 bg-white">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-200 bg-gray-50 text-left text-xs text-gray-500">
            <th className="px-4 py-2.5 font-medium">状态</th>
            <th className="px-4 py-2.5 font-medium">JD 要求</th>
            <th className="px-4 py-2.5 font-medium">类别</th>
            <th className="px-4 py-2.5 font-medium">得分</th>
            <th className="px-4 py-2.5 font-medium">简历证据</th>
          </tr>
        </thead>
        <tbody>
          {requirements.map((r, i) => {
            const m = STATUS_META[r.status];
            return (
              <tr key={i} className="border-b border-gray-100 last:border-0 align-top hover:bg-gray-50/60">
                <td className="px-4 py-3">
                  <span className={`inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-xs ${m.cls}`}>
                    {m.icon} {m.label}
                  </span>
                </td>
                <td className="max-w-56 px-4 py-3 font-medium text-gray-800">{r.requirement}</td>
                <td className="px-4 py-3 text-xs text-gray-500">{CAT_LABEL[r.category] || r.category}</td>
                <td className="px-4 py-3 tabular-nums text-gray-700">{r.score.toFixed(0)}</td>
                <td className="max-w-64 px-4 py-3 text-xs italic text-gray-500">
                  {r.evidence ? `“${r.evidence}”` : "—"}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

/** 供结果页直接引用的导出包装（避免循环依赖） */
export { useAnalysis };
