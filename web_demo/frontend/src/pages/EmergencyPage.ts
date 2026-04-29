// ============================================
// EmergencyPage.ts — 应急卡片页面
// ============================================

import { getEmergencyCards, matchEmergencyCard } from "../api/emergency";
import { Skeleton } from "../components/Skeleton";
import { EmptyState } from "../components/EmptyState";
import type { EmergencyCard, EmergencyMatchResponse } from "../types";

function renderCard(card: EmergencyCard, isMatch = false): HTMLElement {
  const el = document.createElement("div");
  el.className = isMatch
    ? "bg-white rounded-xl shadow-md border-2 border-orange-300 p-5 relative"
    : "bg-white rounded-xl shadow-sm border border-gray-200 p-4";

  if (isMatch) {
    const badge = document.createElement("span");
    badge.className = "absolute -top-2.5 left-4 bg-orange-500 text-white text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wide";
    badge.textContent = "最佳匹配";
    el.appendChild(badge);
  }

  // Title
  const title = document.createElement("h3");
  title.className = "font-bold text-lg text-gray-900 mb-1";
  title.textContent = card.title;
  el.appendChild(title);

  // Category badge
  const cat = document.createElement("span");
  cat.className = "inline-block bg-gray-100 text-gray-600 text-xs px-2 py-0.5 rounded-full mb-2";
  cat.textContent = card.category;
  el.appendChild(cat);

  // Summary
  const summary = document.createElement("p");
  summary.className = "text-gray-600 text-sm mb-3";
  summary.textContent = card.summary;
  el.appendChild(summary);

  // Immediate actions (red numbered list)
  if (card.immediate_actions.length > 0) {
    const actTitle = document.createElement("p");
    actTitle.className = "text-xs font-semibold text-red-700 mb-1";
    actTitle.textContent = "立即行动";
    el.appendChild(actTitle);

    const actList = document.createElement("ol");
    actList.className = "text-red-700 text-sm list-decimal pl-4 space-y-0.5 mb-3";
    card.immediate_actions.forEach((a) => {
      const li = document.createElement("li");
      li.textContent = a;
      actList.appendChild(li);
    });
    el.appendChild(actList);
  }

  // Forbidden (red warning icon + text)
  if (card.forbidden.length > 0) {
    const forbTitle = document.createElement("p");
    forbTitle.className = "text-xs font-semibold text-red-700 mb-1";
    forbTitle.textContent = "禁止事项";
    el.appendChild(forbTitle);

    card.forbidden.forEach((f) => {
      const row = document.createElement("div");
      row.className = "flex items-start gap-1.5 text-sm text-red-700 mb-0.5";
      row.innerHTML = `<span class="flex-shrink-0 mt-0.5">⚠</span><span>${f}</span>`;
      el.appendChild(row);
    });
  }

  // PPE
  if (card.ppe.length > 0) {
    const ppeRow = document.createElement("div");
    ppeRow.className = "mt-3 flex items-center gap-2 text-xs text-gray-600";
    ppeRow.innerHTML = `<span class="font-semibold">所需 PPE:</span><span>${card.ppe.join("、")}</span>`;
    el.appendChild(ppeRow);
  }

  // Escalation
  if (card.escalation.length > 0) {
    const escRow = document.createElement("div");
    escRow.className = "mt-2 flex items-center gap-2 text-xs text-gray-600";
    escRow.innerHTML = `<span class="font-semibold">升级流程:</span><span>${card.escalation.join(" → ")}</span>`;
    el.appendChild(escRow);
  }

  return el;
}

export function EmergencyPage(): HTMLElement {
  const container = document.createElement("div");
  container.className = "max-w-6xl mx-auto";

  let cards: EmergencyCard[] = [];
  let matchResult: EmergencyMatchResponse | null = null;
  let isLoading = true;

  // Search area
  const searchWrap = document.createElement("div");
  searchWrap.className = "flex gap-2 mb-6";

  const searchInput = document.createElement("input");
  searchInput.type = "text";
  searchInput.placeholder = "输入关键词搜索应急卡片（如：火灾、化学品泄漏）...";
  searchInput.className = "flex-1 border border-gray-300 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500";

  const searchBtn = document.createElement("button");
  searchBtn.className = "btn-primary px-5 py-2.5 text-sm";
  searchBtn.textContent = "搜索";

  searchWrap.appendChild(searchInput);
  searchWrap.appendChild(searchBtn);
  container.appendChild(searchWrap);

  // Content area
  const contentArea = document.createElement("div");
  container.appendChild(contentArea);

  async function loadCards(): Promise<void> {
    isLoading = true;
    renderContent();
    try {
      cards = await getEmergencyCards();
    } catch {
      // Error handled by API client toast
    } finally {
      isLoading = false;
      renderContent();
    }
  }

  async function doSearch(): Promise<void> {
    const query = searchInput.value.trim();
    if (!query) return;
    isLoading = true;
    renderContent();
    try {
      matchResult = await matchEmergencyCard(query);
      if (matchResult.card) {
        cards = [matchResult.card, ...cards.filter((c) => c.id !== matchResult!.card!.id)];
      }
    } catch {
      // Error handled by API client toast
    } finally {
      isLoading = false;
      renderContent();
    }
  }

  searchBtn.addEventListener("click", doSearch);
  const onEnter = (e: KeyboardEvent): void => {
    if (e.key === "Enter") doSearch();
  };
  searchInput.addEventListener("keydown", onEnter);

  function renderContent(): void {
    contentArea.innerHTML = "";

    if (isLoading) {
      const grid = document.createElement("div");
      grid.className = "grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4";
      for (let i = 0; i < 6; i++) {
        const cell = document.createElement("div");
        cell.className = "bg-white rounded-xl border border-gray-200 p-4 space-y-2";
        cell.appendChild(Skeleton({ width: "60%", height: "16px" }));
        cell.appendChild(Skeleton({ width: "40%", height: "12px" }));
        cell.appendChild(Skeleton({ width: "100%", height: "12px" }));
        cell.appendChild(Skeleton({ width: "80%", height: "12px" }));
        grid.appendChild(cell);
      }
      contentArea.appendChild(grid);
      return;
    }

    if (matchResult && matchResult.card) {
      const matchSection = document.createElement("div");
      matchSection.className = "mb-6";
      const matchLabel = document.createElement("h3");
      matchLabel.className = "text-sm font-semibold text-gray-500 mb-2";
      matchLabel.textContent = `搜索结果（匹配度: ${(matchResult.confidence * 100).toFixed(0)}%）`;
      matchSection.appendChild(matchLabel);
      matchSection.appendChild(renderCard(matchResult.card, true));
      contentArea.appendChild(matchSection);
    }

    if (cards.length === 0) {
      contentArea.appendChild(EmptyState({ icon: "📭", message: "暂无应急卡片" }));
      return;
    }

    const grid = document.createElement("div");
    grid.className = "grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4";

    const displayCards = matchResult && matchResult.card
      ? cards.filter((c) => c.id !== matchResult!.card!.id)
      : cards;

    if (displayCards.length === 0 && matchResult && matchResult.card) {
      const allLabel = document.createElement("h3");
      allLabel.className = "text-sm font-semibold text-gray-500 mb-2 col-span-full";
      allLabel.textContent = "全部卡片";
      // No other cards to show
    }

    if (matchResult && matchResult.card && displayCards.length > 0) {
      const allLabel = document.createElement("h3");
      allLabel.className = "text-sm font-semibold text-gray-500 mb-2 col-span-full";
      allLabel.textContent = "全部卡片";
      grid.appendChild(allLabel);
    }

    displayCards.forEach((card) => {
      grid.appendChild(renderCard(card));
    });

    contentArea.appendChild(grid);
  }

  loadCards();

  (container as HTMLElement & { __cleanup?: () => void }).__cleanup = () => {
    searchInput.removeEventListener("keydown", onEnter);
  };

  return container;
}
