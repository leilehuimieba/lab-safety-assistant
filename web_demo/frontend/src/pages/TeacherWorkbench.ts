// ============================================
// TeacherWorkbench.ts — 老师工作台
// ============================================

import { MetricCard } from "../components/MetricCard";
import { DataTable } from "../components/DataTable";
import { RiskBadge } from "../components/RiskBadge";
import { Skeleton } from "../components/Skeleton";
import { EmptyState } from "../components/EmptyState";
import { toast } from "../components/Toast";
import { getAdminDashboard } from "../api/admin";
import type { AdminDashboardResponse, HighRiskScenario } from "../types";

interface ActionRecord {
  action: "approve" | "reject";
  time: string;
}

function loadAction(recordId: string): ActionRecord | null {
  try {
    const raw = localStorage.getItem(`teacher_actions_${recordId}`);
    return raw ? (JSON.parse(raw) as ActionRecord) : null;
  } catch {
    return null;
  }
}

function saveAction(recordId: string, action: "approve" | "reject"): void {
  try {
    const record: ActionRecord = { action, time: new Date().toISOString() };
    localStorage.setItem(`teacher_actions_${recordId}`, JSON.stringify(record));
  } catch {
    // silent fail
  }
}

function buildMetricsRow(data: AdminDashboardResponse): HTMLElement {
  const row = document.createElement("div");
  row.className = "grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6";

  data.metrics.forEach((m) => {
    row.appendChild(MetricCard({ label: m.label, value: m.value, detail: m.detail }));
  });

  return row;
}

function buildScenarioCard(scenario: HighRiskScenario, _index: number): HTMLElement {
  const card = document.createElement("div");
  card.className = "card flex flex-col gap-2";

  const header = document.createElement("div");
  header.className = "flex items-center justify-between";

  const title = document.createElement("span");
  title.className = "font-semibold text-sm text-gray-800";
  title.textContent = scenario.scenario || "未命名实验";

  const badge = RiskBadge(scenario.risk_level);
  header.appendChild(title);
  header.appendChild(badge);

  const meta = document.createElement("div");
  meta.className = "text-xs text-gray-500 flex flex-col gap-1";

  const timeLine = document.createElement("span");
  timeLine.textContent = `提交时间: ${new Date(scenario.submitted_at).toLocaleString("zh-CN")}`;

  const operatorLine = document.createElement("span");
  operatorLine.textContent = `操作人: ${scenario.operator || "—"}`;

  const statusLine = document.createElement("span");
  statusLine.textContent = `开工许可: ${scenario.allow_start ? "✅ 允许" : "❌ 阻断"}`;

  meta.appendChild(timeLine);
  meta.appendChild(operatorLine);
  meta.appendChild(statusLine);

  card.appendChild(header);
  card.appendChild(meta);
  return card;
}

export function TeacherWorkbench(): HTMLElement {
  const container = document.createElement("div");
  container.className = "space-y-6";

  const title = document.createElement("h2");
  title.className = "text-xl font-bold text-gray-900";
  title.textContent = "老师工作台（近7天）";
  container.appendChild(title);

  const metricsRow = document.createElement("div");
  metricsRow.className = "grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6";
  for (let i = 0; i < 4; i++) {
    metricsRow.appendChild(Skeleton({ height: "5rem" }));
  }
  container.appendChild(metricsRow);

  const pendingSection = document.createElement("div");
  pendingSection.className = "space-y-3";

  const pendingTitle = document.createElement("h3");
  pendingTitle.className = "text-lg font-semibold text-gray-800";
  pendingTitle.textContent = "待审核高风险清单";
  pendingSection.appendChild(pendingTitle);

  const pendingTableWrapper = document.createElement("div");
  pendingTableWrapper.appendChild(Skeleton({ height: "10rem" }));
  pendingSection.appendChild(pendingTableWrapper);
  container.appendChild(pendingSection);

  const recentSection = document.createElement("div");
  recentSection.className = "space-y-3";

  const recentTitle = document.createElement("h3");
  recentTitle.className = "text-lg font-semibold text-gray-800";
  recentTitle.textContent = "最近高风险场景";
  recentSection.appendChild(recentTitle);

  const recentGrid = document.createElement("div");
  recentGrid.className = "grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4";
  for (let i = 0; i < 3; i++) {
    recentGrid.appendChild(Skeleton({ height: "6rem" }));
  }
  recentSection.appendChild(recentGrid);
  container.appendChild(recentSection);

  async function loadData(): Promise<void> {
    try {
      const data = await getAdminDashboard(7);

      // Replace metrics
      const newMetrics = buildMetricsRow(data);
      metricsRow.replaceWith(newMetrics);

      // Pending review table
      const pendingRecords = data.recent_high_risk_scenarios.filter(
        (_, idx) => loadAction(`hr_${idx}`) === null
      );

      const pendingTable = DataTable<HighRiskScenario & { _idx: number }>({
        columns: [
          {
            key: "submitted_at",
            header: "提交时间",
            render: (row) => new Date(row.submitted_at).toLocaleString("zh-CN"),
          },
          { key: "operator", header: "学生" },
          { key: "scenario", header: "实验" },
          {
            key: "risk_level",
            header: "风险等级",
            render: (row) => RiskBadge(row.risk_level),
          },
          {
            key: "allow_start",
            header: "阻断原因",
            render: (row) => (row.allow_start ? "—" : "高风险自动阻断"),
          },
          {
            key: "_action",
            header: "操作",
            render: (row) => {
              const wrap = document.createElement("div");
              wrap.className = "flex gap-2";

              const approveBtn = document.createElement("button");
              approveBtn.className = "btn-primary text-xs px-2 py-1";
              approveBtn.textContent = "确认";
              approveBtn.addEventListener("click", () => {
                saveAction(`hr_${row._idx}`, "approve");
                toast.success("已确认");
                loadData();
              });

              const rejectBtn = document.createElement("button");
              rejectBtn.className = "btn-secondary text-xs px-2 py-1";
              rejectBtn.textContent = "驳回";
              rejectBtn.addEventListener("click", () => {
                saveAction(`hr_${row._idx}`, "reject");
                toast.info("已驳回");
                loadData();
              });

              wrap.appendChild(approveBtn);
              wrap.appendChild(rejectBtn);
              return wrap;
            },
          },
        ],
        data: pendingRecords.map((r, i) => ({ ...r, _idx: i })),
        keyField: "_idx" as keyof (HighRiskScenario & { _idx: number }),
        emptyMessage: "暂无待审核记录",
      });
      pendingTableWrapper.innerHTML = "";
      pendingTableWrapper.appendChild(pendingTable);

      // Recent scenarios cards
      const newRecentGrid = document.createElement("div");
      newRecentGrid.className = "grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4";
      if (data.recent_high_risk_scenarios.length === 0) {
        newRecentGrid.appendChild(EmptyState({ icon: "🧪", message: "暂无高风险场景" }));
      } else {
        data.recent_high_risk_scenarios.forEach((s, i) => {
          newRecentGrid.appendChild(buildScenarioCard(s, i));
        });
      }
      recentGrid.replaceWith(newRecentGrid);
    } catch {
      toast.error("加载数据失败");
    }
  }

  loadData();

  return container;
}
