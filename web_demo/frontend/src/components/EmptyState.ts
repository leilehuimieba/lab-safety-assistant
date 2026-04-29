// ============================================
// EmptyState.ts — 空状态占位组件
// ============================================

export interface EmptyStateOptions {
  icon?: string;
  message?: string;
}

export function EmptyState(options?: EmptyStateOptions): HTMLElement {
  const el = document.createElement("div");
  el.className = "flex flex-col items-center justify-center py-12 text-gray-400";

  const icon = document.createElement("span");
  icon.className = "text-4xl mb-3";
  icon.textContent = options?.icon ?? "📭";

  const text = document.createElement("p");
  text.className = "text-sm";
  text.textContent = options?.message ?? "暂无数据";

  el.appendChild(icon);
  el.appendChild(text);
  return el;
}
