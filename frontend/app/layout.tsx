import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ResumePilot · 简历优化多 Agent 工具",
  description: "上传简历 + 目标 JD，三个 Agent 协作给出匹配度评分与逐段改写建议",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN">
      <body className="min-h-screen bg-gray-50 text-gray-900 antialiased">
        {children}
      </body>
    </html>
  );
}
