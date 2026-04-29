// ============================================
// AdminDashboard.ts — 管理看板
// ============================================

import { MetricCard } from "../components/MetricCard";
import { DataTable } from "../components/DataTable";
import { RiskBadge } from "../components/RiskBadge";
import { Skeleton } from "../components/Skeleton";
import { EmptyState } from "../components/EmptyState";
import { toast } from "../components/Toast";
import { getAdminDashboard, exportData, getWeeklyReport } from "../api/admin";
import type { AdminDashboardResponse, HighRiskScenario } from "../types";

function buildMetricsRow(data: AdminDashboardResponse): HTMLElement {
  const row = document.createElement("div");
  row.className = "grid grid-cols-2 lg:grid-cols-5 gap-4 mb-6";

  data.metrics.forEach((m) => {
    row.appendChild(MetricCard({ label: m.label, value: m.value, detail: m.detail }));
  });

  return row;
}

function buildLowConfidenceChart(
  items: { label: string; count: number }[]
): HTMLElement {
  const wrapper = document.createElement("div");
  wrapper.className = "card space-y-3";

  const title = document.createElement("h3");
  title.className = "text-sm font-semibold text-gray-700 mb-2";
  title.textContent = "低置信 Top 5";
  wrapper.appendChild(title);

  if (items.length === 0) {
    wrapper.appendChild(EmptyState({ message: "暂无数据" }));
    return wrapper;
  }

  const maxCount = Math.max(...items.map((i) => i.count));

  items.forEach((item) => {
    const row = document.createElement("div");
    row.className = "flex items-center gap-3 text-sm";

    const label = document.createElement("span");
    label.className = "text-gray-600 w-32 truncate flex-shrink-0";
    label.textContent = item.label;

    const barBg = document.createElement("div");
    barBg.className = "bg-gray-200 rounded-full h-4 flex-1 overflow-hidden";

    const barFill = document.createElement("div");
    barFill.className = "bg-orange-500 h-4 rounded-full transition-all";
    barFill.style.width = `${(item.count / maxCount) * 100}%`;

    barBg.appendChild(barFill);

    const count = document.createElement("span");
    count.className = "text-gray-500 w-8 text-right flex-shrink-0";
    count.textContent = String(item.count);

    row.appendChild(label);
    row.appendChild(barBg);
    row.appendChild(count);
    wrapper.appendChild(row);
  });

  return wrapper;
}

function buildIncidentSummary(summary: Record<string, number>): HTMLElement {
  const wrapper = document.createElement("div");
  wrapper.className = "card";

  const title = document.createElement("h3");
  title.className = "text-sm font-semibold text-gray-700 mb-3";
  title.textContent = "事故状态汇总";
  wrapper.appendChild(title);

  const entries = Object.entries(summary);
  if (entries.length === 0) {
    wrapper.appendChild(EmptyState({ message: "暂无事故数据" }));
    return wrapper;
  }

  const STATUS_LABELS: Record<string, string> = {
    open: "开放",
    in_review: "审核中",
    action_in_progress: "整改中",
    verified: "已验证",
    closed: "已关闭",
  };

  const STATUS_COLORS: Record<string, string> = {
    open: "bg-blue-500",
    in_review: "bg-yellow-500",
    action_in_progress: "bg-orange-500",
    verified: "bg-green-500",
    closed: "bg-gray-500",
  };

  const grid = document.createElement("div");
  grid.className = "grid grid-cols-2 sm:grid-cols-3 gap-3";

  entries.forEach(([status, count]) => {
    const cell = document.createElement("div");
    cell.className = "flex items-center gap-2";

    const dot = document.createElement("span");
    dot.className = `w-3 h-3 rounded-full ${STATUS_COLORS[status] ?? "bg-gray-400"}`;

    const label = document.createElement("span");
    label.className = "text-sm text-gray-600";
    label.textContent = `${STATUS_LABELS[status] ?? status}: ${count}`;

    cell.appendChild(dot);
    cell.appendChild(label);
    grid.appendChild(cell);
  });

  wrapper.appendChild(grid);
  return wrapper;
}

export function AdminDashboard(): HTMLElement {
  const container = document.createElement("div");
  container.className = "space-y-6";

  const headerRow = document.createElement("div");
  headerRow.className = "flex items-center justify-between";

  const title = document.createElement("h2");
  title.className = "text-xl font-bold text-gray-900";
  title.textContent = "管理看板（近30天）";
  headerRow.appendChild(title);

  const exportGroup = document.createElement("div");
  exportGroup.className = "flex gap-2";

  const csvBtn = document.createElement("button");
  csvBtn.className = "btn-secondary text-sm";
  csvBtn.textContent = "导出 CSV";
  csvBtn.addEventListener("click", async () => {
    try {
      const blob = await exportData("full", 30);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `export_${new Date().toISOString().slice(0, 10)}.csv`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success("导出成功");
    } catch {
      toast.error("导出失败");
    }
  });

  const weeklyBtn = document.createElement("button");
  weeklyBtn.className = "btn-primary text-sm";
  weeklyBtn.textContent = "导出周报";
  weeklyBtn.addEventListener("click", async () => {
    try {
      const resp = await getWeeklyReport();
      const blob = new Blob([resp.report], { type: "text/markdown" });
      const url = URL.createObjectURL(blob);
      window.open(url, "_blank");
    } catch {
      toast.error("获取周报失败");
    }
  });

  exportGroup.appendChild(csvBtn);
  exportGroup.appendChild(weeklyBtn);
  headerRow.appendChild(exportGroup);
  container.appendChild(headerRow);

  const metricsRow = document.createElement("div");
  metricsRow.className = "grid grid-cols-2 lg:grid-cols-5 gap-4 mb-6";
  for (let i = 0; i < 5; i++) {
    metricsRow.appendChild(Skeleton({ height: "5rem" }));
  }
  container.appendChild(metricsRow);

  const chartsRow = document.createElement("div");
  chartsRow.className = "grid grid-cols-1 lg:grid-cols-2 gap-6";

  const lowConfChartWrapper = document.createElement("div");
  lowConfChartWrapper.appendChild(Skeleton({ height: "12rem" }));
  chartsRow.appendChild(lowConfChartWrapper);

  const incidentSummaryWrapper = document.createElement("div");
  incidentSummaryWrapper.appendChild(Skeleton({ height: "12rem" }));
  chartsRow.appendChild(incidentSummaryWrapper);

  container.appendChild(chartsRow);

  const tableSection = document.createElement("div");
  tableSection.className = "space-y-3";

  const tableTitle = document.createElement("h3");
  tableTitle.className = "text-lg font-semibold text-gray-800";
  tableTitle.textContent = "高风险场景记录";
  tableSection.appendChild(tableTitle);

  const tableWrapper = document.createElement("div");
  tableWrapper.appendChild(Skeleton({ height: "10rem" }));
  tableSection.appendChild(tableWrapper);
  container.appendChild(tableSection);

  async function loadData(): Promise<void> {
    try {
      const data = await getAdminDashboard(30);

      const newMetrics = buildMetricsRow(data);
      metricsRow.replaceWith(newMetrics);

      const newLowConf = buildLowConfidenceChart(data.low_confidence_top);
      lowConfChartWrapper.innerHTML = "";
      lowConfChartWrapper.appendChild(newLowConf);

      const newIncidentSummary = buildIncidentSummary(data.incident_summary);
      incidentSummaryWrapper.innerHTML = "";
      incidentSummaryWrapper.appendChild(newIncidentSummary);

      const table = DataTable<HighRiskScenario>({
        columns: [
          {
            key: "submitted_at",
            header: "时间",
            render: (row) => new Date(row.submitted_at).toLocaleString("zh-CN"),
          },
          { key: "scenario", header: "实验场景" },
          {
            key: "risk_level",
            header: "风险等级",
            render: (row) => RiskBadge(row.risk_level),
          },
          {
            key: "allow_start",
            header: "允许开工",
            render: (row) => (row.allow_start ? "是" : "否"),
          },
          { key: "operator", header: "操作人" },
        ],
        data: data.recent_high_risk_scenarios,
        keyField: "submitted_at" as keyof HighRiskScenario,
        emptyMessage: "暂无高风险场景",
      });
      tableWrapper.innerHTML = "";
      tableWrapper.appendChild(table);
    } catch {
      toast.error("加载看板数据失败");
    }
  }

  loadData();

  return container;
}
