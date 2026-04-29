// ============================================
// ChatPage.ts — 安全问答页面
// ============================================

import { chat } from "../api/chat";
import { CitationList } from "../components/CitationList";
import { Skeleton } from "../components/Skeleton";
import type { ChatResponse, ChatDecision, Citation } from "../types";

interface ChatMessage {
  role: "user" | "ai";
  content: string;
  decision?: ChatDecision;
  lowConfidence?: boolean;
  lowConfidenceReason?: string;
  citations?: Citation[];
}

function createDecisionBanner(decision: ChatDecision, content: string): HTMLElement {
  const el = document.createElement("div");
  if (decision === "rule_blocked") {
    el.className = "bg-red-50 border border-red-200 rounded-lg p-3 my-2";
    el.innerHTML = `<p class="text-red-700 font-bold text-sm mb-1">⚠ 系统已拦截此问题</p><p class="text-red-600 text-sm">${content}</p>`;
  } else if (decision === "emergency_redirect") {
    el.className = "bg-orange-50 border border-orange-200 rounded-lg p-3 my-2";
    el.innerHTML = `<p class="text-orange-700 font-bold text-sm mb-1">🚨 应急指引</p><p class="text-orange-600 text-sm">${content}</p>`;
  } else if (decision === "need_more_info") {
    el.className = "bg-yellow-50 border border-yellow-200 rounded-lg p-3 my-2";
    el.innerHTML = `<p class="text-yellow-700 font-bold text-sm mb-1">📝 需要更多信息</p><p class="text-yellow-600 text-sm">${content}</p>`;
  } else {
    el.className = "bg-white border border-gray-100 rounded-lg p-3 my-2";
    el.innerHTML = `<p class="text-gray-700 text-sm">${content}</p>`;
  }
  return el;
}

export function ChatPage(): HTMLElement {
  const container = document.createElement("div");
  container.className = "flex flex-col h-full max-w-4xl mx-auto";

  let messages: ChatMessage[] = [];
  let mode: "lab" | "agent" = "lab";
  let isLoading = false;

  const scrollArea = document.createElement("div");
  scrollArea.className = "flex-1 overflow-y-auto p-4 space-y-4 min-h-0";

  const inputArea = document.createElement("div");
  inputArea.className = "border-t bg-white p-4 shrink-0";

  // Mode selector
  const modeRow = document.createElement("div");
  modeRow.className = "flex items-center gap-4 mb-3";

  const labRadio = document.createElement("label");
  labRadio.className = "flex items-center gap-1.5 text-sm cursor-pointer";
  labRadio.innerHTML = `<input type="radio" name="chat-mode" value="lab" checked class="accent-blue-600"/><span>lab</span>`;

  const agentRadio = document.createElement("label");
  agentRadio.className = "flex items-center gap-1.5 text-sm cursor-pointer";
  agentRadio.innerHTML = `<input type="radio" name="chat-mode" value="agent" class="accent-blue-600"/><span>agent</span>`;

  modeRow.appendChild(labRadio);
  modeRow.appendChild(agentRadio);

  labRadio.querySelector("input")!.addEventListener("change", () => {
    if ((labRadio.querySelector("input") as HTMLInputElement).checked) mode = "lab";
  });
  agentRadio.querySelector("input")!.addEventListener("change", () => {
    if ((agentRadio.querySelector("input") as HTMLInputElement).checked) mode = "agent";
  });

  // Input row
  const inputRow = document.createElement("div");
  inputRow.className = "flex gap-2";

  const input = document.createElement("input");
  input.type = "text";
  input.placeholder = "请输入安全相关问题...";
  input.className = "flex-1 border border-gray-300 rounded-lg px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500";

  const sendBtn = document.createElement("button");
  sendBtn.className = "btn-primary px-4 py-2 text-sm";
  sendBtn.textContent = "发送";

  inputRow.appendChild(input);
  inputRow.appendChild(sendBtn);

  inputArea.appendChild(modeRow);
  inputArea.appendChild(inputRow);

  function renderMessages(): void {
    scrollArea.innerHTML = "";
    messages.forEach((msg) => {
      if (msg.role === "user") {
        const wrapper = document.createElement("div");
        wrapper.className = "flex justify-end";
        const bubble = document.createElement("div");
        bubble.className = "bg-blue-600 text-white rounded-xl rounded-tr-sm px-4 py-2.5 max-w-[80%] text-sm shadow-sm";
        bubble.textContent = msg.content;
        wrapper.appendChild(bubble);
        scrollArea.appendChild(wrapper);
      } else {
        const wrapper = document.createElement("div");
        wrapper.className = "flex justify-start";
        const card = document.createElement("div");
        card.className = "bg-white rounded-xl shadow-sm px-4 py-3 max-w-[85%] text-sm border border-gray-100";

        const banner = createDecisionBanner(msg.decision ?? "llm_answer", msg.content);
        card.appendChild(banner);

        if (msg.lowConfidence) {
          const tip = document.createElement("div");
          tip.className = "bg-yellow-50 border border-yellow-200 rounded-lg p-2 mt-2 text-xs text-yellow-700";
          tip.innerHTML = `⚠ 此回答置信度较低，已加入待补强队列${msg.lowConfidenceReason ? "<br/>" + msg.lowConfidenceReason : ""}`;
          card.appendChild(tip);
        }

        if (msg.citations && msg.citations.length > 0) {
          card.appendChild(CitationList(msg.citations));
        }

        wrapper.appendChild(card);
        scrollArea.appendChild(wrapper);
      }
    });

    if (isLoading) {
      const wrapper = document.createElement("div");
      wrapper.className = "flex justify-start";
      const card = document.createElement("div");
      card.className = "bg-white rounded-xl shadow-sm p-4 max-w-[80%] border border-gray-100 space-y-2";
      card.appendChild(Skeleton({ width: "200px", height: "12px" }));
      card.appendChild(Skeleton({ width: "160px", height: "12px" }));
      card.appendChild(Skeleton({ width: "240px", height: "12px" }));
      wrapper.appendChild(card);
      scrollArea.appendChild(wrapper);
    }

    scrollArea.scrollTop = scrollArea.scrollHeight;
  }

  async function sendMessage(): Promise<void> {
    const text = input.value.trim();
    if (!text || isLoading) return;

    messages.push({ role: "user", content: text });
    input.value = "";
    isLoading = true;
    renderMessages();

    try {
      const resp: ChatResponse = await chat({ mode, question: text });
      messages.push({
        role: "ai",
        content: resp.answer,
        decision: resp.decision,
        lowConfidence: resp.low_confidence,
        lowConfidenceReason: resp.low_confidence_reason,
        citations: resp.citations,
      });
    } catch {
      // Error already emitted by client via toast
    } finally {
      isLoading = false;
      renderMessages();
    }
  }

  sendBtn.addEventListener("click", sendMessage);
  const onKeydown = (e: KeyboardEvent): void => {
    if (e.key === "Enter") sendMessage();
  };
  input.addEventListener("keydown", onKeydown);

  container.appendChild(scrollArea);
  container.appendChild(inputArea);

  // Initial render
  renderMessages();

  // Cleanup stored on element
  (container as HTMLElement & { __cleanup?: () => void }).__cleanup = () => {
    input.removeEventListener("keydown", onKeydown);
  };

  return container;
}
