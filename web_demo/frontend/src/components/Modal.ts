// ============================================
// Modal.ts — 通用弹窗组件
// ============================================

export interface ModalOptions {
  title: string;
  content: HTMLElement | string;
  onClose?: () => void;
  actions?: {
    label: string;
    primary?: boolean;
    onClick: () => void;
  }[];
}

export interface ModalAPI {
  open: () => void;
  close: () => void;
  element: HTMLElement;
}

export function Modal(options: ModalOptions): ModalAPI {
  const overlay = document.createElement("div");
  overlay.className =
    "fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center hidden";
  overlay.setAttribute("role", "dialog");
  overlay.setAttribute("aria-modal", "true");

  const card = document.createElement("div");
  card.className = "bg-white rounded-xl shadow-xl max-w-lg w-full mx-4 p-6 flex flex-col gap-4";

  const header = document.createElement("div");
  header.className = "flex items-center justify-between";

  const title = document.createElement("h3");
  title.className = "text-lg font-semibold text-gray-900";
  title.textContent = options.title;

  const closeBtn = document.createElement("button");
  closeBtn.className =
    "text-gray-400 hover:text-gray-600 transition-colors text-xl leading-none";
  closeBtn.setAttribute("aria-label", "关闭");
  closeBtn.innerHTML = "&times;";

  header.appendChild(title);
  header.appendChild(closeBtn);

  const body = document.createElement("div");
  body.className = "text-gray-700 text-sm leading-relaxed";
  if (typeof options.content === "string") {
    body.innerHTML = options.content;
  } else {
    body.appendChild(options.content);
  }

  card.appendChild(header);
  card.appendChild(body);

  if (options.actions && options.actions.length > 0) {
    const footer = document.createElement("div");
    footer.className = "flex items-center justify-end gap-3 pt-2";

    options.actions.forEach((action) => {
      const btn = document.createElement("button");
      btn.textContent = action.label;
      if (action.primary) {
        btn.className = "btn-primary";
      } else {
        btn.className = "btn-secondary";
      }
      btn.addEventListener("click", () => {
        action.onClick();
      });
      footer.appendChild(btn);
    });

    card.appendChild(footer);
  }

  overlay.appendChild(card);

  function close(): void {
    overlay.classList.add("hidden");
    if (options.onClose) {
      options.onClose();
    }
  }

  function open(): void {
    overlay.classList.remove("hidden");
  }

  closeBtn.addEventListener("click", close);
  overlay.addEventListener("click", (e) => {
    if (e.target === overlay) {
      close();
    }
  });

  const onKey = (e: KeyboardEvent) => {
    if (e.key === "Escape" && !overlay.classList.contains("hidden")) {
      close();
    }
  };
  document.addEventListener("keydown", onKey);

  // Store cleanup reference on element
  (overlay as HTMLElement & { __modalCleanup?: () => void }).__modalCleanup = () => {
    document.removeEventListener("keydown", onKey);
  };

  return { open, close, element: overlay };
}
