// ============================================
// CitationList.ts — 引用来源列表（可折叠）
// ============================================

import type { Citation } from "../types/index";

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

export function CitationList(citations: Citation[]): HTMLElement {
  const el = document.createElement("div");
  el.className = "w-full";

  const header = document.createElement("button");
  header.className =
    "w-full flex items-center justify-between text-sm text-gray-600 hover:text-gray-900 py-2 border-b border-gray-100 transition-colors cursor-pointer";

  const left = document.createElement("div");
  left.className = "flex items-center gap-2";
  left.innerHTML = `<span class="text-gray-400">📚</span><span>引用来源 (${citations.length})</span>`;

  const arrow = document.createElement("span");
  arrow.className = "text-gray-400 transition-transform duration-200";
  arrow.textContent = "▶";

  header.appendChild(left);
  header.appendChild(arrow);
  el.appendChild(header);

  const list = document.createElement("div");
  list.className = "hidden mt-2 space-y-3";

  citations.forEach((cite) => {
    const item = document.createElement("div");
    item.className = "bg-gray-50 rounded-lg p-3 text-sm";

    const titleRow = document.createElement("div");
    titleRow.className = "flex items-center justify-between mb-1";

    const title = document.createElement("a");
    title.href = cite.source_url;
    title.target = "_blank";
    title.rel = "noopener noreferrer";
    title.className = "font-medium text-blue-700 hover:text-blue-900 hover:underline";
    title.textContent = cite.title;

    titleRow.appendChild(title);
    titleRow.appendChild(renderRiskBadge(cite.risk_level));
    item.appendChild(titleRow);

    const meta = document.createElement("p");
    meta.className = "text-xs text-gray-500 mb-1";
    meta.textContent = `${cite.source_org} · ${cite.source_title}`;
    item.appendChild(meta);

    const snippet = document.createElement("p");
    snippet.className = "text-xs text-gray-600 leading-relaxed";
    snippet.textContent = cite.snippet;
    item.appendChild(snippet);

    list.appendChild(item);
  });

  el.appendChild(list);

  let expanded = false;
  header.addEventListener("click", () => {
    expanded = !expanded;
    if (expanded) {
      list.classList.remove("hidden");
      arrow.style.transform = "rotate(90deg)";
    } else {
      list.classList.add("hidden");
      arrow.style.transform = "rotate(0deg)";
    }
  });

  return el;
}
