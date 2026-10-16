import BackendStatus from "@/components/BackendStatus";

export default function Home() {
  return (
    <main className="mx-auto max-w-2xl px-6 py-16">
      <p className="text-sm font-medium text-indigo-600">ResumePilot · MVP</p>
      <h1 className="mt-2 text-3xl font-bold tracking-tight">
        简历优化多 Agent 工具
      </h1>
      <p className="mt-3 text-gray-600">
        上传简历 PDF + 粘贴目标岗位 JD → 三个 Agent 协作 → 匹配度评分 + 逐段改写建议。
      </p>

      <section className="mt-10 rounded-xl border border-gray-200 bg-white p-6">
        <h2 className="text-sm font-semibold text-gray-900">骨架状态（D1）</h2>
        <ul className="mt-3 space-y-2 text-sm text-gray-600">
          <li>· FastAPI 后端：/health、/ping/frontend、/api/analyze（stub 数据）</li>
          <li>· LangGraph：Parser → Matcher → Rewriter + 条件边（score &gt; 85 跳过改写）</li>
          <li>· 本页为上传页占位，D5 完整实现上传 + SSE 流式结果页</li>
        </ul>
        <BackendStatus />
      </section>
    </main>
  );
}
