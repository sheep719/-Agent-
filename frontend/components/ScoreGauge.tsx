"use client";

/** 总分仪表盘：纯 SVG 半圆环，零图表依赖 */
export default function ScoreGauge({ score }: { score: number }) {
  const pct = Math.max(0, Math.min(100, score));
  const R = 80;
  const C = Math.PI * R; // 半圆弧长
  const color = pct >= 70 ? "#059669" : pct >= 40 ? "#d97706" : "#dc2626";

  return (
    <div className="flex flex-col items-center">
      <svg viewBox="0 0 200 110" className="w-56">
        <path
          d={`M 20 100 A ${R} ${R} 0 0 1 180 100`}
          fill="none" stroke="#e5e7eb" strokeWidth="16" strokeLinecap="round"
        />
        <path
          d={`M 20 100 A ${R} ${R} 0 0 1 180 100`}
          fill="none" stroke={color} strokeWidth="16" strokeLinecap="round"
          strokeDasharray={`${(pct / 100) * C} ${C}`}
          style={{ transition: "stroke-dasharray 0.8s ease" }}
        />
        <text x="100" y="82" textAnchor="middle" dominantBaseline="central"
          fontSize="40" fontWeight="700" fill="#111827">
          {pct.toFixed(0)}
        </text>
        <text x="100" y="105" textAnchor="middle" fontSize="11" fill="#6b7280">
          / 100 匹配度
        </text>
      </svg>
    </div>
  );
}
