// ============================================
// DecisionCard.ts — 核心决策卡片组件
// ============================================

import type { DecisionCardData, Citation } from "../types/index";

const BAR_COLOR: Record<string, string> = {
  allow: "bg-decision-allow",
  review: "bg-decision-review",
  block: "bg-decision-block",
};

const TITLE_COLOR: Record<string, string> = {
  allow: "text-decision-allow",
  review: "text-decision-review",
  block: "text-decision-block",
};

const STATUS_TITLE: Record<string, string> = {
  allow: "可以开工",
  review: "需老师确认后开工",
  block: "暂不可开工",
};

const RISK_COLOR_MAP: Record<string, string> = {
  Low: "bg-risk-low text-white",
  "Medium-Low": "bg-risk-medium-low text-white",
  Medium: "bg-risk-medium text-black",
  High: "bg-risk-high text-white",
  Critical: "bg-risk-critical text-white",
};

function renderRiskBadge(level: string): HTMLElement {
  const el = document.createElement("span");
  const classes = RISK_COLOR_MAP[level] ?? "bg-gray-200 text-gray-700";
  el.className = `badge ${classes}`;
  el.textContent = level;
  return el;
}

function renderCitationList(citations: Citation[]): HTMLElement {
  const wrap = document.createElement("div");
  wrap.className = "w-full mt-3";

  const header = document.createElement("button");
  header.className =
    "w-full flex items-center justify-between text-xs text-gray-500 hover:text-gray-700 py-1.5 border-t border-gray-100 transition-colors cursor-pointer";
  header.innerHTML = `<span>引用来源 (${citations.length})</span><span class="arrow text-gray-400 transition-transform duration-200">▶</span>`;
  wrap.appendChild(header);

  const list = document.createElement("div");
  list.className = "hidden space-y-2 mt-2";

  citations.forEach((cite) => {
    const item = document.createElement("div");
    item.className = "bg-gray-50 rounded-lg p-2.5 text-xs";

    const top = document.createElement("div");
    top.className = "flex items-center justify-between mb-1";

    const a = document.createElement("a");
    a.href = cite.source_url;
    a.target = "_blank";
    a.rel = "noopener noreferrer";
    a.className = "font-medium text-blue-700 hover:underline";
    a.textContent = cite.title;

    top.appendChild(a);
    top.appendChild(renderRiskBadge(cite.risk_level));
    item.appendChild(top);

    const meta = document.createElement("p");
    meta.className = "text-[11px] text-gray-500 mb-1";
    meta.textContent = `${cite.source_org} · ${cite.source_title}`;
    item.appendChild(meta);

    const snippet = document.createElement("p");
    snippet.className = "text-[11px] text-gray-600 leading-relaxed";
    snippet.textContent = cite.snippet;
    item.appendChild(snippet);

    list.appendChild(item);
  });

  wrap.appendChild(list);

  let expanded = false;
  header.addEventListener("click", () => {
    expanded = !expanded;
    const arrow = header.querySelector(".arrow") as HTMLElement;
    if (expanded) {
      list.classList.remove("hidden");
      arrow.style.transform = "rotate(90deg)";
    } else {
      list.classList.add("hidden");
      arrow.style.transform = "rotate(0deg)";
    }
  });

  return wrap;
}

export function DecisionCard(data: DecisionCardData): HTMLElement {
  const el = document.createElement("div");
  el.className = "card relative overflow-hidden";

  const barColor = BAR_COLOR[data.type] ?? "bg-gray-400";
  const titleColor = TITLE_COLOR[data.type] ?? "text-gray-700";
  const statusTitle = (data.title || STATUS_TITLE[data.type]) ?? "未知状态";

  // Left accent bar
  const bar = document.createElement("div");
  bar.className = `absolute left-0 top-0 bottom-0 w-1 ${barColor}`;
  el.appendChild(bar);

  const content = document.createElement("div");
  content.className = "pl-4";

  // Title
  const titleRow = document.createElement("div");
  titleRow.className = "flex items-center gap-2 mb-1";

  const title = document.createElement("h4");
  title.className = `${titleColor} text-lg font-bold`;
  title.textContent = statusTitle;
  titleRow.appendChild(title);
  content.appendChild(titleRow);

  // Subtitle
  if (data.subtitle) {
    const sub = document.createElement("p");
    sub.className = "text-sm text-gray-500 mb-3";
    sub.textContent = data.subtitle;
    content.appendChild(sub);
  }

  // Details map
  if (data.details && Object.keys(data.details).length > 0) {
    const detailsGrid = document.createElement("div");
    detailsGrid.className = "grid grid-cols-2 gap-2 mb-3";
    Object.entries(data.details).forEach(([k, v]) => {
      const item = document.createElement("div");
      item.className = "bg-gray-50 rounded-lg px-3 py-2";
      item.innerHTML = `<p class="text-[10px] text-gray-400 uppercase">${k}</p><p class="text-sm font-medium text-gray-800">${v}</p>`;
      detailsGrid.appendChild(item);
    });
    content.appendChild(detailsGrid);
  }

  // Blocking reasons (red dot list)
  if (data.reasons && data.reasons.length > 0) {
    const reasonWrap = document.createElement("div");
    reasonWrap.className = "mb-3";

    const reasonTitle = document.createElement("p");
    reasonTitle.className = "text-xs font-semibold text-red-700 mb-1.5";
    reasonTitle.textContent = "阻止原因";
    reasonWrap.appendChild(reasonTitle);

    data.reasons.forEach((r) => {
      const row = document.createElement("div");
      row.className = "flex items-start gap-2 text-sm text-gray-700 mb-1";
      row.innerHTML = `<span class="mt-1.5 w-1.5 h-1.5 rounded-full bg-red-500 flex-shrink-0"></span><span>${r}</span>`;
      reasonWrap.appendChild(row);
    });

    content.appendChild(reasonWrap);
  }

  // Next actions (blue numbered steps)
  if (data.actions && data.actions.length > 0) {
    const actionWrap = document.createElement("div");
    actionWrap.className = "mb-3";

    const actionTitle = document.createElement("p");
    actionTitle.className = "text-xs font-semibold text-blue-700 mb-1.5";
    actionTitle.textContent = "下一步行动";
    actionWrap.appendChild(actionTitle);

    data.actions.forEach((a, idx) => {
      const row = document.createElement("div");
      row.className = "flex items-start gap-2 text-sm text-gray-700 mb-1";
      const num = idx + 1;
      row.innerHTML = `<span class="mt-0.5 w-5 h-5 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center text-xs font-bold flex-shrink-0">${num}</span><span>${a}</span>`;
      actionWrap.appendChild(row);
    });

    content.appendChild(actionWrap);
  }

  // Citations
  if (data.citations && data.citations.length > 0) {
    content.appendChild(renderCitationList(data.citations));
  }

  el.appendChild(content);
  return el;
}
