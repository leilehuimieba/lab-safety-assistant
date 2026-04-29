// ============================================
// 事件总线 — 基于 CustomEvent 的发布/订阅模式
// 全局状态管理与组件间通信
// ============================================

export type EventMap = {
  "toast:show": { type: "success" | "error" | "info"; message: string };
  "sidebar:toggle": { collapsed: boolean };
  "navigate": { route: string };
  "checklist:submit": { recordId: string };
  "training:submit": { attemptId: string };
  "incident:created": { incidentId: string };
  "incident:updated": { incidentId: string };
  "modal:open": { id: string; payload?: unknown };
  "modal:close": { id: string };
  "loading:start": { key: string };
  "loading:end": { key: string };
};

export type EventName = keyof EventMap;

class EventBus {
  private target: EventTarget;

  constructor() {
    this.target = new EventTarget();
  }

  emit<K extends EventName>(event: K, detail: EventMap[K]): void {
    const customEvent = new CustomEvent(event, { detail, bubbles: false });
    this.target.dispatchEvent(customEvent);
  }

  on<K extends EventName>(event: K, handler: (detail: EventMap[K]) => void): () => void {
    const wrapper = (e: Event) => {
      handler((e as CustomEvent<EventMap[K]>).detail);
    };
    this.target.addEventListener(event, wrapper);
    return () => this.target.removeEventListener(event, wrapper);
  }

  once<K extends EventName>(event: K, handler: (detail: EventMap[K]) => void): void {
    const wrapper = (e: Event) => {
      handler((e as CustomEvent<EventMap[K]>).detail);
      this.target.removeEventListener(event, wrapper);
    };
    this.target.addEventListener(event, wrapper);
  }

  off<K extends EventName>(event: K, handler: (e: Event) => void): void {
    this.target.removeEventListener(event, handler);
  }
}

export const eventBus = new EventBus();
