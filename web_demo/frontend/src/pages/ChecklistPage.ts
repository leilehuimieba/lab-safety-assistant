// ============================================
// ChecklistPage.ts — 开工检查（两步向导）
// ============================================

import { getChecklistTemplate, submitChecklist } from "../api/risk";
import { StepIndicator } from "../components/StepIndicator";
import { RiskBadge } from "../components/RiskBadge";
import { DecisionCard } from "../components/DecisionCard";
import { Skeleton } from "../components/Skeleton";
import type { ChecklistItem, ChecklistTemplateResponse, ChecklistSubmitResponse, DecisionCardData } from "../types";

function mkInput(label: string, placeholder: string): { wrap: HTMLElement; input: HTMLInputElement } {
  const wrap = document.createElement("div");
  wrap.innerHTML = `<label class="block text-sm font-medium text-gray-700 mb-1">${label}</label>`;
  const input = document.createElement("input");
  input.type = "text"; input.placeholder = placeholder;
  input.className = "w-full border border-gray-300 rounded-lg px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500";
  wrap.appendChild(input);
  return { wrap, input };
}

export function ChecklistPage(): HTMLElement {
  const container = document.createElement("div");
  container.className = "max-w-3xl mx-auto";
  let step = 1;
  let template: ChecklistTemplateResponse | null = null;
  let items: ChecklistItem[] = [];
  let result: ChecklistSubmitResponse | null = null;
  let s1: HTMLInputElement, s2: HTMLInputElement, s3: HTMLInputElement, s4: HTMLInputElement, opIn: HTMLInputElement;

  function render(): void {
    container.innerHTML = "";
    if (step === 1) r1();
    else if (step === 2) r2();
    else r3();
  }

  function r1(): void {
    container.innerHTML = `<h2 class="text-xl font-bold mb-4">开工检查 — 输入实验信息</h2>`;
    container.appendChild(StepIndicator({ steps: [{ label: "输入信息" }, { label: "逐项确认" }], current: 0 }));
    const f = document.createElement("div"); f.className = "mt-6 space-y-4";
    const a = mkInput("实验名称", "例如：有机合成实验");
    const b = mkInput("主要试剂", "例如：乙醇、浓硫酸");
    const c = mkInput("使用设备", "例如：旋转蒸发仪");
    const d = mkInput("操作简述", "简要描述实验步骤...");
    s1 = a.input; s2 = b.input; s3 = c.input; s4 = d.input;
    f.append(a.wrap, b.wrap, c.wrap, d.wrap);
    const btn = document.createElement("button");
    btn.className = "btn-primary w-full py-2.5 mt-2";
    btn.textContent = "生成检查清单";
    btn.addEventListener("click", gen);
    f.appendChild(btn);
    container.appendChild(f);
  }

  function r2(): void {
    if (!template) return;
    container.innerHTML = `<h2 class="text-xl font-bold mb-4">开工检查 — 逐项确认</h2>`;
    container.appendChild(StepIndicator({ steps: [{ label: "输入信息" }, { label: "逐项确认" }], current: 1 }));
    const riskRow = document.createElement("div");
    riskRow.className = "flex items-center gap-3 mt-4 mb-2 flex-wrap";
    riskRow.appendChild(RiskBadge(template.risk_level));
    template.key_hazards.forEach((h) => {
      const tag = document.createElement("span");
      tag.className = "text-xs bg-red-50 text-red-700 px-2 py-1 rounded-full border border-red-100";
      tag.textContent = h; riskRow.appendChild(tag);
    });
    container.appendChild(riskRow);

    const listWrap = document.createElement("div"); listWrap.className = "mt-4 space-y-3";
    items.forEach((item, idx) => {
      const row = document.createElement("div");
      row.className = `bg-white rounded-lg border ${item.critical ? "border-red-400" : "border-gray-200"} p-3`;
      const top = document.createElement("div"); top.className = "flex items-start gap-3";
      const cb = document.createElement("input"); cb.type = "checkbox"; cb.checked = item.checked; cb.className = "mt-1 accent-blue-600";
      cb.addEventListener("change", () => { items[idx] = { ...item, checked: cb.checked }; });
      const lbl = document.createElement("label"); lbl.className = `flex-1 text-sm ${item.critical ? "font-bold text-gray-900" : "text-gray-700"}`; lbl.textContent = item.label;
      top.append(cb, lbl); row.appendChild(top);
      const note = document.createElement("input"); note.type = "text"; note.placeholder = "备注（可选）";
      note.className = "mt-2 w-full border border-gray-200 rounded px-2 py-1 text-xs focus:outline-none focus:ring-1 focus:ring-blue-400";
      note.value = item.note;
      note.addEventListener("input", () => { items[idx] = { ...item, note: note.value }; });
      row.appendChild(note);
      listWrap.appendChild(row);
    });
    container.appendChild(listWrap);

    const opWrap = document.createElement("div"); opWrap.className = "mt-4";
    opWrap.innerHTML = `<label class="block text-sm font-medium text-gray-700 mb-1">操作人姓名</label>`;
    opIn = document.createElement("input"); opIn.type = "text"; opIn.placeholder = "请输入您的姓名";
    opIn.className = "w-full border border-gray-300 rounded-lg px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500";
    opWrap.appendChild(opIn);
    container.appendChild(opWrap);

    const btn = document.createElement("button");
    btn.className = "btn-primary w-full py-2.5 mt-4";
    btn.textContent = "提交检查";
    btn.addEventListener("click", sub);
    container.appendChild(btn);
  }

  function r3(): void {
    if (!result) return;
    container.innerHTML = `<h2 class="text-xl font-bold mb-4">检查结果</h2>`;
    const data: DecisionCardData = {
      type: result.allow_start ? "allow" : "block",
      title: result.allow_start ? "可以开工" : "暂不可开工",
      subtitle: `实验：${result.scenario} · 操作人：${result.operator}`,
      reasons: result.allow_start ? undefined : result.blocking_reasons,
      actions: result.allow_start ? undefined : result.next_actions,
    };
    container.appendChild(DecisionCard(data));
    const rb = document.createElement("button");
    rb.className = "btn-secondary w-full py-2.5 mt-4"; rb.textContent = "重新开始";
    rb.addEventListener("click", () => {
      step = 1; template = null; items = []; result = null;
      render();
    });
    container.appendChild(rb);
  }

  async function gen(): Promise<void> {
    if (!s1.value.trim() || !s2.value.trim() || !s3.value.trim() || !s4.value.trim()) { alert("请填写所有字段"); return; }
    container.innerHTML = ""; const sk = document.createElement("div"); sk.className = "space-y-3 mt-4";
    for (let i = 0; i < 6; i++) sk.appendChild(Skeleton({ height: "48px" }));
    container.appendChild(sk);
    try {
      template = await getChecklistTemplate({ scenario: s1.value.trim(), chemicals: s2.value.trim(), equipment: s3.value.trim(), procedure: s4.value.trim() });
      items = template.checklist.map((it) => ({ ...it })); step = 2;
    } catch { /* toast handled */ } finally { render(); }
  }

  async function sub(): Promise<void> {
    const op = opIn.value.trim();
    if (!op) { alert("请输入操作人姓名"); return; }
    if (!template) return;
    try {
      result = await submitChecklist({ scenario: template.scenario, operator: op, checklist: items });
      step = 3; render();
    } catch { /* toast handled */ }
  }

  render();
  return container;
}
