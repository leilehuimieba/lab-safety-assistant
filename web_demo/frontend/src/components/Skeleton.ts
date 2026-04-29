// ============================================
// Skeleton.ts — 骨架屏占位组件
// ============================================

export interface SkeletonOptions {
  width?: string;
  height?: string;
  className?: string;
}

export function Skeleton(options?: SkeletonOptions): HTMLElement {
  const el = document.createElement("div");

  const width = options?.width ?? "100%";
  const height = options?.height ?? "1rem";
  const extra = options?.className ?? "";

  el.className = [`bg-gray-200 rounded animate-pulse`, extra].filter(Boolean).join(" ");
  el.style.width = width;
  el.style.height = height;

  return el;
}
