// ============================================
// SystemStatus.ts — 系统状态
// ============================================

import { MetricCard } from "../components/MetricCard";
import { Skeleton } from "../components/Skeleton";
import { EmptyState } from "../components/EmptyState";
import { toast } from "../components/Toast";
import { get } from "../api/client";
import type { WorkspaceStatusResponse, DemoMetaResponse } from "../types";
import { isDemoModeEnabled } from "../mock/demoMode";
import { getMockMeta, getMockWorkspaceStatus } from "../mock/mockApi";

function buildHorizontalBarChart(
  items: { label: string; count: number }[],
  title: string
): HTMLElement {
  const wrapper = document.createElement("div");
  wrapper.className = "card space-y-3";

  const heading = document.createElement("h3");
  heading.className = "text-sm font-semibold text-gray-700 mb-2";
  heading.textContent = title;
  wrapper.appendChild(heading);

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
    barFill.className = "bg-blue-500 h-4 rounded-full transition-all";
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

export function SystemStatus(): HTMLElement {
  const container = document.createElement("div");
  container.className = "space-y-6";

  const title = document.createElement("h2");
  title.className = "text-xl font-bold text-gray-900";
  title.textContent = "系统状态";
  container.appendChild(title);

  const systemCardWrapper = document.createElement("div");
  systemCardWrapper.appendChild(Skeleton({ height: "5rem" }));
  container.appendChild(systemCardWrapper);

  const kbRow = document.createElement("div");
  kbRow.className = "grid grid-cols-2 lg:grid-cols-4 gap-4";
  for (let i = 0; i < 4; i++) {
    kbRow.appendChild(Skeleton({ height: "5rem" }));
  }
  container.appendChild(kbRow);

  const difyRow = document.createElement("div");
  difyRow.className = "flex items-center gap-4";
  difyRow.appendChild(Skeleton({ height: "3rem", width: "12rem" }));
  container.appendChild(difyRow);

  const chartsRow = document.createElement("div");
  chartsRow.className = "grid grid-cols-1 lg:grid-cols-2 gap-6";
  const catChartWrapper = document.createElement("div");
  catChartWrapper.appendChild(Skeleton({ height: "12rem" }));
  chartsRow.appendChild(catChartWrapper);
  const hazardChartWrapper = document.createElement("div");
  hazardChartWrapper.appendChild(Skeleton({ height: "12rem" }));
  chartsRow.appendChild(hazardChartWrapper);
  container.appendChild(chartsRow);

  async function loadData(): Promise<void> {
    try {
      const [workspace, meta] = isDemoModeEnabled()
        ? await Promise.all([getMockWorkspaceStatus(), getMockMeta()])
        : await Promise.all([
            get<WorkspaceStatusResponse>("/workspace/status"),
            get<DemoMetaResponse>("/meta"),
          ]);

      // System info card
      const sysCard = document.createElement("div");
      sysCard.className = "card";
      const sysTitle = document.createElement("h3");
      sysTitle.className = "text-sm font-semibold text-gray-700 mb-2";
      sysTitle.textContent = "系统信息";
      sysCard.appendChild(sysTitle);

      const sysGrid = document.createElement("div");
      sysGrid.className = "grid grid-cols-2 gap-2 text-sm";

      const versionRow = document.createElement("div");
      versionRow.innerHTML = `<span class="text-gray-500">版本号:</span> <span class="text-gray-800">${meta.app_version}</span>`;
      sysGrid.appendChild(versionRow);

      const laneRow = document.createElement("div");
      laneRow.innerHTML = `<span class="text-gray-500">当前主链路:</span> <span class="text-gray-800">${meta.chat_lane_lab}</span>`;
      sysGrid.appendChild(laneRow);

      const evalRow = document.createElement("div");
      evalRow.innerHTML = `<span class="text-gray-500">正式回归:</span> <span class="text-gray-800">${meta.formal_eval_score} / ${meta.stability_status}</span>`;
      sysGrid.appendChild(evalRow);

      const modelRow = document.createElement("div");
      modelRow.innerHTML = `<span class="text-gray-500">运行模型:</span> <span class="text-gray-800">${meta.runtime_model}</span>`;
      sysGrid.appendChild(modelRow);

      sysCard.appendChild(sysGrid);
      systemCardWrapper.innerHTML = "";
      systemCardWrapper.appendChild(sysCard);

      // KB stats
      const newKbRow = document.createElement("div");
      newKbRow.className = "grid grid-cols-2 lg:grid-cols-4 gap-4";
      newKbRow.appendChild(
        MetricCard({
          label: "知识库总量",
          value: String(workspace.kb_rows),
          detail: "总条目数",
        })
      );
      newKbRow.appendChild(
        MetricCard({
          label: "已导入量",
          value: String(workspace.kb_imported),
          detail: "成功导入",
        })
      );
      newKbRow.appendChild(
        MetricCard({
          label: "低置信队列",
          value: String(workspace.low_confidence_queue_count),
          detail: "待处理",
        })
      );
      newKbRow.appendChild(
        MetricCard({
          label: "知识库覆盖率",
          value:
            workspace.kb_rows > 0
              ? `${Math.round((workspace.kb_imported / workspace.kb_rows) * 100)}%`
              : "0%",
          detail: "导入/总量",
        })
      );
      kbRow.replaceWith(newKbRow);

      // Dify status
      const difyCard = document.createElement("div");
      difyCard.className = "card flex items-center gap-3";

      const dot = document.createElement("span");
      const difyStatusTone = workspace.dify_connection_status === "reachable"
        ? "bg-green-500"
        : workspace.dify_connection_status === "unconfigured"
          ? "bg-yellow-500"
          : "bg-red-500";
      dot.className = `w-3 h-3 rounded-full ${difyStatusTone}`;

      const difyText = document.createElement("span");
      difyText.className = "text-sm text-gray-700";
      const difyStatusLabel =
        workspace.dify_connection_status === "reachable"
          ? "连接正常"
          : workspace.dify_connection_status === "unconfigured"
            ? "未配置"
            : "连接异常";
      difyText.textContent = `Dify ${workspace.dify_enabled ? "已启用" : "未启用"} — ${difyStatusLabel}`;

      difyCard.appendChild(dot);
      difyCard.appendChild(difyText);
      difyRow.innerHTML = "";
      difyRow.appendChild(difyCard);

      // Charts
      const catChart = buildHorizontalBarChart(workspace.top_categories, "类别分布");
      catChartWrapper.innerHTML = "";
      catChartWrapper.appendChild(catChart);

      const hazardChart = buildHorizontalBarChart(workspace.top_hazards, "危险类型分布");
      hazardChartWrapper.innerHTML = "";
      hazardChartWrapper.appendChild(hazardChart);
    } catch {
      toast.error("加载系统状态失败");
    }
  }

  loadData();

  return container;
}
