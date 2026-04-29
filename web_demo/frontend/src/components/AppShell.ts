// ============================================
// AppShell.ts — 应用外壳（侧边栏 + 内容区布局）
// ============================================

export interface AppShellOptions {
  sidebar: HTMLElement;
  content: HTMLElement;
  onMobileMenuToggle?: () => void;
}

export function AppShell(options: AppShellOptions): HTMLElement {
  const { sidebar, content, onMobileMenuToggle } = options;

  const root = document.createElement("div");
  root.className = "min-h-screen flex";

  // 移动端遮罩层
  const overlay = document.createElement("div");
  overlay.className = [
    "fixed inset-0 bg-black/50 z-30 transition-opacity duration-300 lg:hidden",
    "opacity-0 pointer-events-none",
  ].join(" ");
  overlay.addEventListener("click", () => {
    onMobileMenuToggle?.();
  });

  // 内容区容器
  const contentWrapper = document.createElement("div");
  contentWrapper.className = [
    "flex-1 flex flex-col min-w-0 bg-gray-50 min-h-screen",
    "transition-all duration-300",
  ].join(" ");

  // 移动端顶部栏（含汉堡菜单）
  const topBar = document.createElement("header");
  topBar.className = [
    "lg:hidden flex items-center gap-3 px-4 py-3 bg-white border-b border-gray-200",
    "sticky top-0 z-20",
  ].join(" ");

  const hamburger = document.createElement("button");
  hamburger.className = [
    "w-10 h-10 rounded-lg flex items-center justify-center",
    "text-gray-600 hover:bg-gray-100 transition-colors",
  ].join(" ");
  hamburger.innerHTML = `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/></svg>`;
  hamburger.setAttribute("aria-label", "打开菜单");
  hamburger.addEventListener("click", () => {
    onMobileMenuToggle?.();
  });

  const topTitle = document.createElement("span");
  topTitle.className = "text-sm font-semibold text-gray-800";
  topTitle.textContent = "实验室安全小助手";

  topBar.appendChild(hamburger);
  topBar.appendChild(topTitle);
  contentWrapper.appendChild(topBar);

  // 内容区主体
  const contentInner = document.createElement("main");
  contentInner.className = "flex-1 overflow-auto p-6 lg:p-8";
  contentInner.appendChild(content);
  contentWrapper.appendChild(contentInner);

  root.appendChild(sidebar);
  root.appendChild(overlay);
  root.appendChild(contentWrapper);

  // 同步移动端侧边栏展开/关闭状态（通过 classList 操作）
  function syncState(collapsed: boolean): void {
    if (collapsed) {
      sidebar.classList.add("-translate-x-full");
      sidebar.classList.remove("translate-x-0");
      overlay.classList.add("opacity-0", "pointer-events-none");
      overlay.classList.remove("opacity-100", "pointer-events-auto");
    } else {
      sidebar.classList.remove("-translate-x-full");
      sidebar.classList.add("translate-x-0");
      overlay.classList.remove("opacity-0", "pointer-events-none");
      overlay.classList.add("opacity-100", "pointer-events-auto");
    }
  }

  // 挂载后根据 sidebar 当前状态同步遮罩
  const observer = new MutationObserver(() => {
    const isCollapsed = sidebar.classList.contains("-translate-x-full");
    syncState(isCollapsed);
  });
  observer.observe(sidebar, { attributes: true, attributeFilter: ["class"] });

  // 初始化同步一次
  syncState(sidebar.classList.contains("-translate-x-full"));

  return root;
}
