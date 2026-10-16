"use client";

/** 四维雷达图：纯 SVG，零依赖 */
const DIMS = [
  { key: "hard_skill", label: "硬技能" },
  { key: "project", label: "项目经历" },
  { key: "education", label: "学历门槛" },
  { key: "bonus", label: "加分项" },
];

export default function RadarChart({ scores }: { scores: Record<string, number> }) {
  const size = 220;
  const cx = size / 2;
  const cy = size / 2;
  const R = 78;

  // 四维 → 正四边形（上/右/下/左）
  const angle = (i: number) => (Math.PI / 2) * i + Math.PI / 2; // 起点在上
  const pt = (i: number, r: number) => {
    const a = angle(i);
    return [cx + r * Math.cos(a), cy - r * Math.sin(a)] as const;
  };

  const poly = DIMS.map((d, i) => pt(i, (R * Math.max(0, Math.min(100, scores[d.key] ?? 0))) / 100).join(" ")).join(" ");
  const gridRing = (f: number) => DIMS.map((_, i) => pt(i, R * f).join(" ")).join(" ");

  return (
    <svg viewBox={`0 0 ${size} ${size}`} className="w-56">
      {[0.25, 0.5, 0.75, 1].map((f) => (
        <polygon key={f} points={gridRing(f)} fill="none" stroke="#e5e7eb" strokeWidth="1" />
      ))}
      {DIMS.map((_, i) => {
        const [x, y] = pt(i, R);
        return <line key={i} x1={cx} y1={cy} x2={x} y2={y} stroke="#e5e7eb" strokeWidth="1" />;
      })}
      <polygon points={poly} fill="rgba(79,70,229,0.25)" stroke="#4f46e5" strokeWidth="2" />
      {DIMS.map((d, i) => {
        const [x, y] = pt(i, R + 18);
        return (
          <text key={d.key} x={x} y={y} textAnchor="middle" dominantBaseline="central"
            fontSize="11" fill="#374151">
            {d.label}
            <tspan x={x} dy="13" fill="#6b7280" fontSize="10">
              {(scores[d.key] ?? 0).toFixed(0)}
            </tspan>
          </text>
        );
      })}
    </svg>
  );
}
