// ============================================
// router.ts — 轻量客户端路由（history.pushState）
// ============================================

import type { PageRoute } from "./types";
import { eventBus } from "./store/events";

// Page imports
import { ChatPage } from "./pages/ChatPage";
import { ChecklistPage } from "./pages/ChecklistPage";
import { EmergencyPage } from "./pages/EmergencyPage";
import { TrainingPage } from "./pages/TrainingPage";
import { TeacherWorkbench } from "./pages/TeacherWorkbench";
import { AdminDashboard } from "./pages/AdminDashboard";
import { IncidentPage } from "./pages/IncidentPage";
import { SystemStatus } from "./pages/SystemStatus";

export type PageFactory = () => HTMLElement;

const ROUTE_MAP: Record<PageRoute, PageFactory> = {
  "/": ChatPage,
  "/checklist": ChecklistPage,
  "/emergency": EmergencyPage,
  "/training": TrainingPage,
  "/teacher": TeacherWorkbench,
  "/admin": AdminDashboard,
  "/incidents": IncidentPage,
  "/status": SystemStatus,
};

const ROUTE_LIST = Object.keys(ROUTE_MAP) as PageRoute[];

let currentCleanup: (() => void) | null = null;
let contentContainer: HTMLElement | null = null;

export function getValidRoute(path: string): PageRoute {
  if ((ROUTE_LIST as string[]).includes(path)) {
    return path as PageRoute;
  }
  return "/";
}

export function navigateTo(route: string, pushState = true): void {
  const validRoute = getValidRoute(route);

  if (pushState && window.location.pathname !== validRoute) {
    window.history.pushState({ route: validRoute }, "", validRoute);
  }

  // Notify subscribers
  eventBus.emit("navigate", { route: validRoute });

  // Render page
  renderPage(validRoute);
}

function renderPage(route: PageRoute): void {
  if (!contentContainer) return;

  // Cleanup previous page
  if (currentCleanup) {
    try {
      currentCleanup();
    } catch {
      // ignore cleanup errors
    }
    currentCleanup = null;
  }

  // Clear content
  contentContainer.innerHTML = "";

  // Create new page
  const factory = ROUTE_MAP[route];
  if (!factory) return;

  const pageEl = factory();

  // Check if page has cleanup
  const cleanupFn = (pageEl as HTMLElement & { __cleanup?: () => void }).__cleanup;
  if (typeof cleanupFn === "function") {
    currentCleanup = cleanupFn;
  }

  contentContainer.appendChild(pageEl);
}

export function initRouter(container: HTMLElement): () => void {
  contentContainer = container;

  // Handle browser back/forward
  const handlePopState = (e: PopStateEvent): void => {
    const route = (e.state?.route as string) ?? window.location.pathname;
    navigateTo(route, false);
  };

  window.addEventListener("popstate", handlePopState);

  // Handle initial route
  const initialRoute = getValidRoute(window.location.pathname);
  if (initialRoute !== window.location.pathname) {
    window.history.replaceState({ route: initialRoute }, "", initialRoute);
  }
  renderPage(initialRoute);

  return () => {
    window.removeEventListener("popstate", handlePopState);
  };
}

export { ROUTE_LIST };
