// ============================================
// Sidebar.ts — 左侧导航组件（按角色分组）
// ============================================

import type { NavItem, PageRoute } from "@/types/index";

export interface SidebarOptions {
  currentRoute: string;
  onNavigate: (route: string) => void;
  collapsed?: boolean;
  onToggle?: () => void;
}

const NAV_ITEMS: NavItem[] = [
  { route: "/", label: "安全问答", icon: "💬", group: "student" },
  { route: "/checklist", label: "开工检查", icon: "✅", group: "student" },
  { route: "/emergency", label: "应急卡片", icon: "🚨", group: "student" },
  { route: "/training", label: "安全培训", icon: "📚", group: "student" },
  { route: "/teacher", label: "老师工作台", icon: "👨‍🏫", group: "teacher" },
  { route: "/admin", label: "管理看板", icon: "📊", group: "admin" },
  { route: "/incidents", label: "事故记录", icon: "📋", group: "admin" },
  { route: "/status", label: "系统状态", icon: "⚙️", group: "admin" },
];

const GROUP_LABELS: Record<string, string> = {
  student: "学生",
  teacher: "老师",
  admin: "管理员",
};

function groupBy<T>(items: T[], keyFn: (item: T) => string): Record<string, T[]> {
  const result: Record<string, T[]> = {};
  for (const item of items) {
    const key = keyFn(item);
    if (!result[key]) result[key] = [];
    result[key].push(item);
  }
  return result;
}

function createNavButton(
  item: NavItem,
  isActive: boolean,
  onClick: () => void
): HTMLElement {
  const btn = document.createElement("button");
  btn.className = [
    "w-full text-left flex items-center gap-3 px-4 py-2.5 rounded-lg transition-colors text-sm",
    "text-sidebar-text",
    isActive ? "bg-sidebar-active font-medium" : "hover:bg-sidebar-hover",
  ].join(" ");

  const iconSpan = document.createElement("span");
  iconSpan.className = "text-base leading-none";
  iconSpan.textContent = item.icon;

  const labelSpan = document.createElement("span");
  labelSpan.textContent = item.label;

  btn.appendChild(iconSpan);
  btn.appendChild(labelSpan);
  btn.addEventListener("click", onClick);

  return btn;
}

export function Sidebar(options: SidebarOptions): HTMLElement {
  const { currentRoute, onNavigate, collapsed = false, onToggle } = options;

  const sidebar = document.createElement("aside");
  sidebar.className = [
    "bg-sidebar-bg text-sidebar-text flex flex-col transition-transform duration-300 ease-in-out z-40",
    "fixed inset-y-0 left-0 w-[280px]",
    "lg:static lg:translate-x-0",
    collapsed ? "-translate-x-full" : "translate-x-0",
  ].join(" ");
  sidebar.id = "app-sidebar";

  // 顶部：Logo + 标题
  const header = document.createElement("div");
  header.className =
    "flex items-center gap-3 px-5 py-5 border-b border-gray-700/50";

  const logo = document.createElement("div");
  logo.className =
    "w-9 h-9 rounded-lg bg-blue-600 flex items-center justify-center text-white text-lg font-bold shrink-0";
  logo.textContent = "安";

  const titleWrap = document.createElement("div");
  const title = document.createElement("h1");
  title.className = "text-base font-semibold text-white leading-tight";
  title.textContent = "实验室安全小助手";
  const subtitle = document.createElement("p");
  subtitle.className = "text-xs text-gray-400 mt-0.5";
  subtitle.textContent = "Lab Safety Assistant";
  titleWrap.appendChild(title);
  titleWrap.appendChild(subtitle);

  header.appendChild(logo);
  header.appendChild(titleWrap);
  sidebar.appendChild(header);

  // 导航区
  const nav = document.createElement("nav");
  nav.className = "flex-1 overflow-y-auto px-3 py-4 space-y-5";

  const grouped = groupBy(NAV_ITEMS, (item) => item.group);
  const groupOrder = ["student", "teacher", "admin"];

  for (const groupKey of groupOrder) {
    const items = grouped[groupKey];
    if (!items || items.length === 0) continue;

    const section = document.createElement("div");

    const groupTitle = document.createElement("div");
    groupTitle.className =
      "px-4 mb-2 text-xs font-medium text-gray-400 uppercase tracking-wider";
    groupTitle.textContent = GROUP_LABELS[groupKey] ?? groupKey;
    section.appendChild(groupTitle);

    const list = document.createElement("div");
    list.className = "space-y-1";

    for (const item of items) {
      const isActive = item.route === (currentRoute as PageRoute);
      const btn = createNavButton(item, isActive, () => {
        onNavigate(item.route);
      });
      list.appendChild(btn);
    }

    section.appendChild(list);
    nav.appendChild(section);
  }

  sidebar.appendChild(nav);

  // 移动端汉堡按钮（当侧边栏折叠时，在侧边栏内部显示）
  const mobileToggle = document.createElement("button");
  mobileToggle.className = [
    "lg:hidden absolute top-4 right-4 w-10 h-10 rounded-lg bg-gray-700/80",
    "flex items-center justify-center text-white hover:bg-gray-600 transition-colors",
  ].join(" ");
  mobileToggle.innerHTML = `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="18" x2="21" y2="18"/></svg>`;
  mobileToggle.setAttribute("aria-label", "关闭菜单");
  mobileToggle.addEventListener("click", () => {
    onToggle?.();
  });
  sidebar.appendChild(mobileToggle);

  return sidebar;
}

export { NAV_ITEMS };
