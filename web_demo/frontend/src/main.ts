// ============================================
// main.ts — 应用入口：挂载 AppShell、启动路由
// ============================================

import "./styles/base.css";
import { Sidebar } from "./components/Sidebar";
import { AppShell, type SidebarStateSyncTarget } from "./components/AppShell";
import { DemoModeBanner } from "./components/DemoModeBanner";
import { initRouter, navigateTo } from "./router";
import { eventBus } from "./store/events";
import { initDemoMode } from "./mock/demoMode";

let sidebarCollapsed = true; // 移动端默认折叠

function createContentContainer(): HTMLElement {
  const el = document.createElement("div");
  el.className = "w-full";
  el.id = "page-content";
  return el;
}

function bootstrap(): void {
  initDemoMode();

  const app = document.getElementById("app");
  if (!app) {
    console.error("App container not found: #app");
    return;
  }

  const contentContainer = createContentContainer();

  // Create sidebar
  const sidebar = Sidebar({
    currentRoute: window.location.pathname,
    collapsed: sidebarCollapsed,
    onNavigate: (route: string) => {
      navigateTo(route, true);
      // Auto-collapse on mobile after navigation
      if (window.innerWidth < 1024) {
        sidebarCollapsed = true;
        updateSidebarState();
      }
    },
    onToggle: () => {
      sidebarCollapsed = !sidebarCollapsed;
      updateSidebarState();
    },
  });

  // Create app shell
  const appShell = AppShell({
    sidebar,
    content: contentContainer,
    onMobileMenuToggle: () => {
      sidebarCollapsed = !sidebarCollapsed;
      updateSidebarState();
    },
  });

  app.appendChild(appShell);

  const demoBanner = DemoModeBanner();
  if (demoBanner) {
    app.appendChild(demoBanner);
  }

  // Sidebar state sync function
  function updateSidebarState(): void {
    if (sidebarCollapsed) {
      sidebar.classList.add("-translate-x-full");
      sidebar.classList.remove("translate-x-0");
    } else {
      sidebar.classList.remove("-translate-x-full");
      sidebar.classList.add("translate-x-0");
    }

    (sidebar as SidebarStateSyncTarget).__syncLayoutState?.(sidebarCollapsed);
  }

  // Sync sidebar highlight on navigation
  eventBus.on("navigate", ({ route }) => {
    // Update sidebar active state by re-rendering nav buttons
    const navButtons = sidebar.querySelectorAll("nav button");
    navButtons.forEach((btn) => {
      const isActive = btn.getAttribute("data-route") === route;
      if (isActive) {
        btn.classList.add("bg-sidebar-active", "font-medium");
        btn.classList.remove("hover:bg-sidebar-hover");
      } else {
        btn.classList.remove("bg-sidebar-active", "font-medium");
        btn.classList.add("hover:bg-sidebar-hover");
      }
    });
  });

  // Handle window resize
  const handleResize = (): void => {
    const isDesktop = window.innerWidth >= 1024;
    if (isDesktop) {
      sidebarCollapsed = false;
    } else {
      sidebarCollapsed = true;
    }
    updateSidebarState();
  };

  window.addEventListener("resize", handleResize);

  // Initialize router
  const cleanupRouter = initRouter(contentContainer);

  // Global cleanup on page unload
  window.addEventListener("beforeunload", () => {
    window.removeEventListener("resize", handleResize);
    cleanupRouter();
  });

  // Handle initial sidebar state
  handleResize();
}

// Start app when DOM is ready
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", bootstrap);
} else {
  bootstrap();
}
