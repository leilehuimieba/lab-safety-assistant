// ============================================
// Toast.ts — 全局 Toast 通知系统
// ============================================

interface ToastConfig {
  bg: string;
  text: string;
  border: string;
  icon: string;
}

const TOAST_STYLES: Record<string, ToastConfig> = {
  success: {
    bg: "bg-green-50",
    text: "text-green-800",
    border: "border-green-200",
    icon: "✓",
  },
  error: {
    bg: "bg-red-50",
    text: "text-red-800",
    border: "border-red-200",
    icon: "✕",
  },
  info: {
    bg: "bg-blue-50",
    text: "text-blue-800",
    border: "border-blue-200",
    icon: "ℹ",
  },
};

function getContainer(): HTMLElement {
  let container = document.getElementById("toast-container");
  if (!container) {
    container = document.createElement("div");
    container.id = "toast-container";
    container.className =
      "fixed top-4 left-1/2 -translate-x-1/2 z-[100] flex flex-col gap-2 pointer-events-none";
    document.body.appendChild(container);
  }
  return container;
}

function createToastElement(type: string, message: string): HTMLElement {
  const style = TOAST_STYLES[type] ?? TOAST_STYLES.info;
  const el = document.createElement("div");
  el.className = [
    "pointer-events-auto",
    "flex items-center gap-2",
    "px-4 py-3 rounded-lg shadow-lg",
    "border",
    "animate-fade-in",
    style.bg,
    style.text,
    style.border,
  ].join(" ");

  const icon = document.createElement("span");
  icon.className = "flex-shrink-0 w-5 h-5 flex items-center justify-center font-bold";
  icon.textContent = style.icon;

  const text = document.createElement("span");
  text.className = "text-sm font-medium";
  text.textContent = message;

  el.appendChild(icon);
  el.appendChild(text);
  return el;
}

function show(message: string, type: string): void {
  const container = getContainer();
  const toastEl = createToastElement(type, message);
  container.appendChild(toastEl);

  setTimeout(() => {
    toastEl.style.transition = "opacity 0.3s ease, transform 0.3s ease";
    toastEl.style.opacity = "0";
    toastEl.style.transform = "translateY(-8px)";
    setTimeout(() => {
      toastEl.remove();
      if (container.children.length === 0) {
        container.remove();
      }
    }, 300);
  }, 3000);
}

export const toast = {
  success(message: string): void {
    show(message, "success");
  },
  error(message: string): void {
    show(message, "error");
  },
  info(message: string): void {
    show(message, "info");
  },
};
