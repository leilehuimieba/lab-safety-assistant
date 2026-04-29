// ============================================
// TrainingPage.ts — 安全培训页面
// ============================================

import { getTrainingQuestions, submitTrainingAnswers } from "../api/training";
import type { TrainingSessionResponse, TrainingSubmitResponse, TrainingAnswer } from "../types";

type Phase = "intro" | "quiz" | "result";

function optLabel(i: number): string { return String.fromCharCode(65 + i); }

export function TrainingPage(): HTMLElement {
  const container = document.createElement("div");
  container.className = "max-w-3xl mx-auto";

  let phase: Phase = "intro";
  let session: TrainingSessionResponse | null = null;
  let idx = 0;
  let answers: TrainingAnswer[] = [];
  let result: TrainingSubmitResponse | null = null;

  function render(): void {
    container.innerHTML = "";
    if (phase === "intro") rIntro();
    else if (phase === "quiz") rQuiz();
    else rResult();
  }

  function rIntro(): void {
    container.innerHTML = `
      <div class="card text-center py-10">
        <div class="text-5xl mb-4">🎓</div>
        <h2 class="text-xl font-bold mb-2">安全培训答题</h2>
        <p class="text-gray-600 text-sm mb-6 max-w-md mx-auto">
          通过答题检验你的实验室安全知识。每套题共 5 道，答对 80% 即可通过。答完后可查看错题回顾和薄弱类别分析。
        </p>
        <button id="tr-start" class="btn-primary px-8 py-2.5">开始答题</button>
      </div>`;
    document.getElementById("tr-start")!.addEventListener("click", start);
  }

  function rQuiz(): void {
    if (!session) return;
    const q = session.questions[idx];
    const prog = document.createElement("div"); prog.className = "mb-4";
    prog.innerHTML = `<div class="w-full h-2 bg-gray-200 rounded-full overflow-hidden">
      <div class="h-full bg-blue-600 transition-all duration-300" style="width:${((idx + 1) / session.total_questions) * 100}%"></div></div>`;
    container.appendChild(prog);
    container.insertAdjacentHTML("beforeend",
      `<p class="text-xs text-gray-500 mb-2">第 ${idx + 1} / ${session.total_questions} 题</p>
       <h3 class="text-lg font-bold text-gray-900 mb-4">${q.prompt}</h3>`);

    const opts = document.createElement("div"); opts.className = "space-y-2 mb-6";
    const cur = answers.find((a) => a.question_id === q.id);
    const sel = cur ? cur.selected_indices : [];

    q.options.forEach((opt, i) => {
      const row = document.createElement("label");
      row.className = "flex items-center gap-3 bg-white border border-gray-200 rounded-lg px-4 py-3 cursor-pointer hover:bg-gray-50 transition-colors";
      const t = q.multiple ? "checkbox" : "radio";
      const ch = sel.includes(i) ? "checked" : "";
      row.innerHTML = `<input type="${t}" name="q-${q.id}" value="${i}" ${ch} class="accent-blue-600"/><span class="text-sm text-gray-800">${optLabel(i)}. ${opt}</span>`;
      const inp = row.querySelector("input")!;
      inp.addEventListener("change", () => updateA(q.id, q.multiple, i, inp.checked));
      opts.appendChild(row);
    });
    container.appendChild(opts);

    const btnRow = document.createElement("div"); btnRow.className = "flex justify-end";
    const last = idx === session.total_questions - 1;
    const btn = document.createElement("button");
    btn.className = "btn-primary px-6 py-2"; btn.textContent = last ? "提交" : "下一题";
    btn.addEventListener("click", () => { if (last) doSub(); else { idx++; render(); } });
    btnRow.appendChild(btn);
    container.appendChild(btnRow);
  }

  function rResult(): void {
    if (!result) return;
    const scoreWrap = document.createElement("div"); scoreWrap.className = "card text-center py-8 mb-6";
    scoreWrap.innerHTML = `
      <div class="text-4xl font-bold mb-2 ${result.passed ? "text-green-600" : "text-red-600"}">${result.score} / ${result.total_questions}</div>
      <span class="inline-block ${result.passed ? "bg-green-100 text-green-800" : "bg-red-100 text-red-800"} text-sm font-bold px-3 py-1 rounded-full">${result.passed ? "通过" : "未通过"}</span>
      <p class="text-xs text-gray-500 mt-2">通过标准：答对 ${result.pass_threshold}% 以上</p>`;
    container.appendChild(scoreWrap);

    if (result.weak_categories.length > 0) {
      const w = document.createElement("div"); w.className = "mb-6";
      w.innerHTML = `<h4 class="text-sm font-bold text-gray-700 mb-2">薄弱类别</h4>` +
        result.weak_categories.map((c) => `<span class="inline-block bg-orange-100 text-orange-700 text-xs px-2 py-1 rounded-full mr-2 mb-2">${c}</span>`).join("");
      container.appendChild(w);
    }

    const wrong = result.review.filter((r) => !r.correct);
    if (wrong.length > 0) {
      const rw = document.createElement("div"); rw.className = "mb-6";
      rw.innerHTML = `<h4 class="text-sm font-bold text-gray-700 mb-3">错题回顾</h4>`;
      wrong.forEach((it) => {
        const card = document.createElement("div"); card.className = "bg-white border border-gray-200 rounded-lg p-3 mb-2";
        const ya = it.selected_indices.map(optLabel).join(", ") || "未作答";
        const ca = it.correct_indices.map(optLabel).join(", ");
        card.innerHTML = `<p class="text-sm font-medium text-gray-900 mb-1">${it.prompt}</p>
          <p class="text-xs text-red-600 mb-0.5">你的答案：${ya}</p>
          <p class="text-xs text-green-600 mb-0.5">正确答案：${ca}</p>
          ${it.explanation ? `<p class="text-xs text-gray-500 mt-1">${it.explanation}</p>` : ""}`;
        rw.appendChild(card);
      });
      container.appendChild(rw);
    }

    if (result.recommended_actions.length > 0) {
      const aw = document.createElement("div"); aw.className = "mb-6";
      aw.innerHTML = `<h4 class="text-sm font-bold text-gray-700 mb-2">建议操作</h4>
        <ol class="list-decimal pl-5 space-y-1">${result.recommended_actions.map((a) => `<li class="text-sm text-gray-700">${a}</li>`).join("")}</ol>`;
      container.appendChild(aw);
    }

    const rb = document.createElement("button");
    rb.className = "btn-secondary w-full py-2.5"; rb.textContent = "重新答题";
    rb.addEventListener("click", () => {
      phase = "intro"; session = null; idx = 0; answers = []; result = null; render();
    });
    container.appendChild(rb);
  }

  async function start(): Promise<void> {
    container.innerHTML = `<div class="space-y-3 mt-4"><div class="bg-gray-200 rounded animate-pulse h-24"></div></div>`;
    try {
      session = await getTrainingQuestions(5);
      idx = 0;
      answers = session.questions.map((q) => ({ question_id: q.id, selected_indices: [] }));
      phase = "quiz"; render();
    } catch { /* toast handled */ }
  }

  function updateA(qid: string, multi: boolean, i: number, checked: boolean): void {
    const e = answers.find((a) => a.question_id === qid);
    if (!e) return;
    if (multi) { const s = new Set(e.selected_indices); if (checked) s.add(i); else s.delete(i); e.selected_indices = Array.from(s).sort((a, b) => a - b); }
    else { e.selected_indices = checked ? [i] : []; }
  }

  async function doSub(): Promise<void> {
    if (!session) return;
    const name = prompt("请输入您的姓名：") || "匿名";
    try {
      result = await submitTrainingAnswers(session.session_id, name, answers);
      phase = "result"; render();
    } catch { /* toast handled */ }
  }

  render();
  return container;
}
