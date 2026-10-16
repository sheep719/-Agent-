"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { useAnalysis } from "@/lib/store";
import ScoreGauge from "@/components/ScoreGauge";
import RadarChart from "@/components/RadarChart";
import RequirementList from "@/components/RequirementList";
import RewriteCard from "@/components/RewriteCard";
import type { AgentName } from "@/lib/types";

const AGENT_LABEL: Record<AgentName, string> = {
  parser: "Agent 1 · 解析",
  matcher: "Agent 2 · 匹配",
  rewriter: "Agent 3 · 改写",
};

export default function ResultPage() {
  const {
    start, reset, started, progress, resume, warnings, match,
    rewrites, trace, skippedReason, error, finished, file, jdText,
  } = useAnalysis();
  const router = useRouter();

  useEffect(() => {
    if (!started) {
      if (!file || !jdText.trim()) {
        router.replace("/"); // 无输入（如直接刷新），回上传页
        return;
      }
      start();
    }
  }, [started, file, jdText, start, router]);

  const spinner = (
    <span className="inline-block h-3.5 w-3.5 animate-spin rounded-full border-2 border-gray-300 border-t-indigo-500" />
  );

  return (
    <main className="mx-auto max-w-4xl px-6 py-12">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-indigo-600">ResumePilot</p>
          <h1 className="mt-1 text-2xl font-bold tracking-tight">分析结果</h1>
          {file && <p className="mt-1 text-sm text-gray-500">{file.name}</p>}
        </div>
        <button
          onClick={() => { reset(); router.push("/"); }}
          className="rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
        >
          新的分析
        </button>
      </div>

      {warnings.length > 0 && (
        <div className="mt-6 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
          {warnings.map((w, i) => <p key={i}>⚠️ {w}</p>)}
        </div>
      )}

      {/* Agent 进度条 */}
      <div className="mt-8 grid grid-cols-3 gap-3">
        {(Object.keys(AGENT_LABEL) as AgentName[]).map((k) => {
          const st = progress[k];
          return (
            <div
              key={k}
              className={`flex items-center justify-center gap-2 rounded-xl border px-3 py-3 text-sm ${
                st === "done" ? "border-emerald-200 bg-emerald-50 text-emerald-700"
                : st === "running" ? "border-indigo-200 bg-indigo-50 text-indigo-700"
                : "border-gray-200 bg-white text-gray-400"
              }`}
            >
              {st === "running" && spinner}
              {st === "done" ? "✓" : "○"} {AGENT_LABEL[k]}
            </div>
          );
        })}
      </div>

      {error && (
        <div className="mt-8 rounded-xl border border-red-200 bg-red-50 px-5 py-4 text-sm text-red-700">
          <p className="font-semibold">分析失败</p>
          <p className="mt-1">{error}</p>
          <button
            onClick={() => { reset(); router.push("/"); }}
            className="mt-3 rounded-lg border border-red-300 bg-white px-3 py-1.5 text-xs text-red-600 hover:bg-red-50"
          >
            返回重试
          </button>
        </div>
      )}

      {/* 评分区：总分仪表盘 + 雷达 */}
      {match && (
        <section className="mt-10 grid grid-cols-1 items-center gap-6 rounded-2xl border border-gray-200 bg-white p-6 md:grid-cols-2">
          <ScoreGauge score={match.total_score} />
          <div className="flex flex-col items-center">
            <RadarChart scores={match.dimension_scores} />
            <p className="mt-2 text-xs text-gray-400">
              权重：硬技能 40% · 项目 30% · 学历 15% · 加分 15%
            </p>
          </div>
        </section>
      )}

      {/* 解析出的简历结构（Agent 1 产出） */}
      {resume && (
        <section className="mt-8">
          <h2 className="text-base font-semibold text-gray-900">简历结构（Agent 1 解析）</h2>
          <div className="mt-3 grid grid-cols-1 gap-3 text-sm md:grid-cols-2">
            <Card title={`教育 ×${resume.education.length}`} items={resume.education} />
            <Card
              title={`经历 ×${resume.experience.length}`}
              items={resume.experience.map((e) => `${e.role} @ ${e.company}：${e.bullets.join("；")}`)}
            />
            <Card title={`技能 ×${resume.skills.length}`} items={resume.skills} />
            <Card title={`项目 ×${resume.projects.length}`} items={resume.projects} />
          </div>
        </section>
      )}

      {/* 要求清单（Agent 2 产出） */}
      {match && (
        <section className="mt-10">
          <h2 className="text-base font-semibold text-gray-900">
            JD 要求逐条比对（{match.requirements.length} 条）
          </h2>
          <div className="mt-3">
            <RequirementList requirements={match.requirements} />
          </div>
        </section>
      )}

      {/* 改写建议（Agent 3 流式产出） */}
      {match && !skippedReason && (
        <section className="mt-10">
          <div className="flex items-center gap-2">
            <h2 className="text-base font-semibold text-gray-900">
              改写建议{rewrites.length > 0 && `（${rewrites.length}）`}
            </h2>
            {progress.rewriter === "running" && spinner}
          </div>
          <p className="mt-1 text-xs text-gray-400">
            ⚠️/❌ 条目按 STAR 法则改写；缺失项给出占位符模板（X%、N 次），请填入真实数据后再使用
          </p>
          <div className="mt-4 space-y-4">
            {rewrites.map((r, i) => (
              <RewriteCard key={i} item={r} index={i} />
            ))}
            {progress.rewriter === "running" && rewrites.length === 0 && (
              <p className="text-sm text-gray-400">正在生成改写建议…</p>
            )}
            {finished && rewrites.length === 0 && !error && (
              <p className="text-sm text-gray-400">没有需要改写的条目</p>
            )}
          </div>
        </section>
      )}

      {skippedReason && (
        <div className="mt-10 rounded-xl border border-blue-200 bg-blue-50 px-5 py-4 text-sm text-blue-800">
          🎉 {skippedReason}
        </div>
      )}

      {/* 链路耗时（可观测性） */}
      {finished && trace.length > 0 && (
        <section className="mt-10">
          <h2 className="text-base font-semibold text-gray-900">链路耗时</h2>
          <div className="mt-3 flex flex-wrap gap-2 text-xs text-gray-600">
            {trace.map((t, i) => (
              <span key={i} className="rounded-md border border-gray-200 bg-white px-2.5 py-1">
                {t.node} · {t.ms}ms{t.skipped_precomputed ? "（预计算）" : ""}
              </span>
            ))}
          </div>
        </section>
      )}
    </main>
  );
}

function Card({ title, items }: { title: string; items: string[] }) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-4">
      <p className="text-xs font-medium text-gray-400">{title}</p>
      {items.length === 0 ? (
        <p className="mt-2 text-sm text-gray-300">（空）</p>
      ) : (
        <ul className="mt-2 space-y-1.5 text-sm leading-relaxed text-gray-700">
          {items.map((it, i) => <li key={i} className="flex gap-1.5"><span className="text-gray-300">·</span>{it}</li>)}
        </ul>
      )}
    </div>
  );
}
