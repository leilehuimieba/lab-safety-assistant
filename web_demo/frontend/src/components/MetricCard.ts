// ============================================
// MetricCard.ts — 指标卡片组件
// ============================================

export interface MetricCardOptions {
  label: string;
  value: string;
  detail?: string;
  trend?: "up" | "down" | "neutral";
}

const TREND_ICON: Record<string, string> = {
  up: "▲",
  down: "▼",
  neutral: "—",
};

const TREND_CLASS: Record<string, string> = {
  up: "text-green-600",
  down: "text-red-600",
  neutral: "text-gray-400",
};

export function MetricCard(options: MetricCardOptions): HTMLElement {
  const el = document.createElement("div");
  el.className = "card";

  const label = document.createElement("p");
  label.className = "text-sm text-gray-500 mb-1";
  label.textContent = options.label;

  const valueRow = document.createElement("div");
  valueRow.className = "flex items-baseline gap-2";

  const value = document.createElement("span");
  value.className = "text-2xl font-bold text-gray-900";
  value.textContent = options.value;
  valueRow.appendChild(value);

  if (options.trend) {
    const trend = document.createElement("span");
    trend.className = `text-xs font-medium ${TREND_CLASS[options.trend]}`;
    trend.textContent = TREND_ICON[options.trend];
    valueRow.appendChild(trend);
  }

  el.appendChild(label);
  el.appendChild(valueRow);

  if (options.detail) {
    const detail = document.createElement("p");
    detail.className = "text-xs text-gray-400 mt-2";
    detail.textContent = options.detail;
    el.appendChild(detail);
  }

  return el;
}
