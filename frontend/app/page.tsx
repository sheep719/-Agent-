"use client";

import { useRouter } from "next/navigation";
import { useRef, useState } from "react";
import { useAnalysis } from "@/lib/store";
import BackendStatus from "@/components/BackendStatus";

export default function UploadPage() {
  const { file, jdText, setInputs, start } = useAnalysis();
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);
  const [localErr, setLocalErr] = useState<string | null>(null);

  const ready = !!file && jdText.trim().length > 20;

  function pickFile(f: File | null | undefined) {
    if (!f) return;
    if (!f.name.toLowerCase().endsWith(".pdf")) {
      setLocalErr("只支持 PDF 文件（图片型扫描件无法解析）");
      return;
    }
    setLocalErr(null);
    setInputs(f, jdText);
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!ready) return;
    router.push("/result");
  }

  return (
    <main className="mx-auto max-w-2xl px-6 py-14">
      <p className="text-sm font-medium text-indigo-600">ResumePilot</p>
      <h1 className="mt-2 text-3xl font-bold tracking-tight">
        简历优化 · 三 Agent 协作分析
      </h1>
      <p className="mt-3 text-gray-600">
        上传简历 PDF + 粘贴目标岗位 JD，解析 → 匹配评分 → STAR 法则改写建议，全程流式推送。
      </p>

      <form onSubmit={onSubmit} className="mt-10 space-y-6">
        <div
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={(e) => { e.preventDefault(); setDragOver(false); pickFile(e.dataTransfer.files?.[0]); }}
          onClick={() => inputRef.current?.click()}
          className={`cursor-pointer rounded-xl border-2 border-dashed px-6 py-10 text-center transition ${
            dragOver ? "border-indigo-400 bg-indigo-50" : "border-gray-300 bg-white hover:border-indigo-300"
          }`}
        >
          <input
            ref={inputRef}
            type="file"
            accept=".pdf"
            className="hidden"
            onChange={(e) => pickFile(e.target.files?.[0])}
          />
          {file ? (
            <div>
              <p className="font-medium text-gray-900">{file.name}</p>
              <p className="mt-1 text-sm text-gray-500">
                {(file.size / 1024).toFixed(0)} KB · 点击更换
              </p>
            </div>
          ) : (
            <div>
              <p className="font-medium text-gray-700">拖拽 PDF 到这里，或点击选择文件</p>
              <p className="mt-1 text-sm text-gray-400">仅支持文本型 PDF，10MB 以内</p>
            </div>
          )}
        </div>
        {localErr && <p className="text-sm text-red-600">{localErr}</p>}

        <div>
          <label htmlFor="jd" className="text-sm font-semibold text-gray-900">
            目标岗位 JD
          </label>
          <textarea
            id="jd"
            value={jdText}
            onChange={(e) => setInputs(file, e.target.value)}
            rows={10}
            placeholder="粘贴完整的招聘 JD（职责 + 要求），越完整评分越准…"
            className="mt-2 w-full rounded-xl border border-gray-300 bg-white px-4 py-3 text-sm leading-relaxed outline-none focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100"
          />
          <p className="mt-1 text-right text-xs text-gray-400">{jdText.length} 字</p>
        </div>

        <button
          type="submit"
          disabled={!ready}
          className={`w-full rounded-xl px-6 py-3.5 font-medium transition ${
            ready
              ? "bg-indigo-600 text-white hover:bg-indigo-700"
              : "cursor-not-allowed bg-gray-200 text-gray-400"
          }`}
        >
          {ready ? "开始分析" : "请上传简历并粘贴 JD（至少 20 字）"}
        </button>
      </form>

      <div className="mt-10">
        <BackendStatus />
      </div>
    </main>
  );
}
