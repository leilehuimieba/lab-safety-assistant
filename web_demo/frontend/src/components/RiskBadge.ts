// ============================================
// RiskBadge.ts — 风险等级标签组件
// ============================================

const LEVEL_MAP: Record<string, string> = {
  Low: "bg-risk-low text-white",
  "Medium-Low": "bg-risk-medium-low text-white",
  Medium: "bg-risk-medium text-black",
  High: "bg-risk-high text-white",
  Critical: "bg-risk-critical text-white",
};

export function RiskBadge(level: string): HTMLElement {
  const el = document.createElement("span");
  const classes = LEVEL_MAP[level] ?? "bg-gray-200 text-gray-700";
  el.className = `badge ${classes}`;
  el.textContent = level;
  return el;
}
