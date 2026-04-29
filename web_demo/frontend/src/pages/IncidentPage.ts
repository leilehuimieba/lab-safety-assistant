// ============================================
// IncidentPage.ts — 事故记录
// ============================================

import { DataTable } from "../components/DataTable";
import { Modal } from "../components/Modal";
import { Skeleton } from "../components/Skeleton";
import { EmptyState } from "../components/EmptyState";
import { toast } from "../components/Toast";
import { getIncidents, createIncident, updateIncident } from "../api/incidents";
import type {
  IncidentRecord,
  IncidentStatus,
  IncidentSeverity,
  CreateIncidentRequest,
} from "../types";

const SEVERITY_LABELS: Record<string, string> = {
  low: "低",
  medium: "中",
  high: "高",
  critical: "严重",
};

const STATUS_LABELS: Record<string, string> = {
  open: "开放",
  in_review: "审核中",
  action_in_progress: "整改中",
  verified: "已验证",
  closed: "已关闭",
};

const STATUS_OPTIONS: { value: IncidentStatus; label: string }[] = [
  { value: "open", label: "开放" },
  { value: "in_review", label: "审核中" },
  { value: "action_in_progress", label: "整改中" },
  { value: "verified", label: "已验证" },
  { value: "closed", label: "已关闭" },
];

function renderSeverityBadge(severity: string): HTMLElement {
  const map: Record<string, string> = {
    low: "bg-risk-low text-white",
    medium: "bg-risk-medium text-black",
    high: "bg-risk-high text-white",
    critical: "bg-risk-critical text-white",
  };
  const el = document.createElement("span");
  el.className = `badge ${map[severity] ?? "bg-gray-200 text-gray-700"}`;
  el.textContent = SEVERITY_LABELS[severity] ?? severity;
  return el;
}

function renderStatusLabel(status: string): string {
  return STATUS_LABELS[status] ?? status;
}

function buildCreateForm(_onSubmit: (data: CreateIncidentRequest) => void): HTMLElement {
  const form = document.createElement("form");
  form.className = "space-y-3";
  form.id = "incident-create-form";

  const fields: {
    id: string;
    label: string;
    type: string;
    required: boolean;
    options?: string[];
  }[] = [
    { id: "title", label: "标题", type: "text", required: true },
    { id: "scenario", label: "实验场景", type: "text", required: true },
    {
      id: "severity",
      label: "严重程度",
      type: "select",
      required: true,
      options: ["low", "medium", "high", "critical"],
    },
    { id: "location", label: "位置", type: "text", required: true },
    { id: "reporter", label: "报告人", type: "text", required: true },
    { id: "owner", label: "负责人", type: "text", required: true },
    { id: "due_date", label: "截止日期", type: "date", required: true },
  ];

  fields.forEach((f) => {
    const group = document.createElement("div");
    group.className = "flex flex-col gap-1";

    const lbl = document.createElement("label");
    lbl.className = "text-xs font-medium text-gray-600";
    lbl.textContent = f.label;

    let input: HTMLElement;
    if (f.type === "select") {
      const sel = document.createElement("select");
      sel.id = f.id;
      sel.name = f.id;
      sel.className = "input";
      sel.required = f.required;
      sel.innerHTML = `<option value="">请选择</option>` +
        (f.options ?? []).map((o) => `<option value="${o}">${SEVERITY_LABELS[o] ?? o}</option>`).join("");
      input = sel;
    } else {
      const inp = document.createElement("input");
      inp.type = f.type;
      inp.id = f.id;
      inp.name = f.id;
      inp.className = "input";
      inp.required = f.required;
      input = inp;
    }

    group.appendChild(lbl);
    group.appendChild(input);
    form.appendChild(group);
  });

  const causeGroup = document.createElement("div");
  causeGroup.className = "flex flex-col gap-1";
  const causeLbl = document.createElement("label");
  causeLbl.className = "text-xs font-medium text-gray-600";
  causeLbl.textContent = "原因分类（每行一个）";
  const causeArea = document.createElement("textarea");
  causeArea.id = "cause_categories";
  causeArea.name = "cause_categories";
  causeArea.className = "input min-h-[4rem]";
  causeArea.placeholder = "输入原因分类，每行一个";
  causeGroup.appendChild(causeLbl);
  causeGroup.appendChild(causeArea);
  form.appendChild(causeGroup);

  const actionGroup = document.createElement("div");
  actionGroup.className = "flex flex-col gap-1";
  const actionLbl = document.createElement("label");
  actionLbl.className = "text-xs font-medium text-gray-600";
  actionLbl.textContent = "立即措施（每行一个）";
  const actionArea = document.createElement("textarea");
  actionArea.id = "immediate_actions";
  actionArea.name = "immediate_actions";
  actionArea.className = "input min-h-[4rem]";
  actionArea.placeholder = "输入立即措施，每行一个";
  actionGroup.appendChild(actionLbl);
  actionGroup.appendChild(actionArea);
  form.appendChild(actionGroup);

  return form;
}

export function IncidentPage(): HTMLElement {
  const container = document.createElement("div");
  container.className = "space-y-6";

  const title = document.createElement("h2");
  title.className = "text-xl font-bold text-gray-900";
  title.textContent = "事故记录";
  container.appendChild(title);

  const toolbar = document.createElement("div");
  toolbar.className = "flex flex-wrap items-center gap-3";

  const statusFilter = document.createElement("select");
  statusFilter.className = "input text-sm w-40";
  statusFilter.innerHTML =
    `<option value="">全部状态</option>` +
    STATUS_OPTIONS.map((s) => `<option value="${s.value}">${s.label}</option>`).join("");

  const overdueCheck = document.createElement("label");
  overdueCheck.className = "flex items-center gap-2 text-sm text-gray-600 cursor-pointer";
  const overdueBox = document.createElement("input");
  overdueBox.type = "checkbox";
  overdueBox.className = "rounded";
  overdueCheck.appendChild(overdueBox);
  overdueCheck.appendChild(document.createTextNode("仅看逾期"));

  const addBtn = document.createElement("button");
  addBtn.className = "btn-primary text-sm ml-auto";
  addBtn.textContent = "新增事故";

  toolbar.appendChild(statusFilter);
  toolbar.appendChild(overdueCheck);
  toolbar.appendChild(addBtn);
  container.appendChild(toolbar);

  const tableWrapper = document.createElement("div");
  tableWrapper.appendChild(Skeleton({ height: "12rem" }));
  container.appendChild(tableWrapper);

  let allIncidents: IncidentRecord[] = [];
  let modalInstance = buildCreateModal();

  function buildCreateModal(): ReturnType<typeof Modal> {
    const formContent = buildCreateForm((data) => {
      handleCreate(data);
    });

    const modal = Modal({
      title: "新增事故",
      content: formContent,
      actions: [
        {
          label: "取消",
          onClick: () => {
            modal.close();
          },
        },
        {
          label: "创建",
          primary: true,
          onClick: () => {
            const form = document.getElementById("incident-create-form") as HTMLFormElement | null;
            if (!form) return;
            if (!form.reportValidity()) return;

            const fd = new FormData(form);
            const severity = (form.querySelector("#severity") as HTMLSelectElement).value as IncidentSeverity;
            const causes = (form.querySelector("#cause_categories") as HTMLTextAreaElement).value
              .split("\n")
              .map((s) => s.trim())
              .filter(Boolean);
            const actions = (form.querySelector("#immediate_actions") as HTMLTextAreaElement).value
              .split("\n")
              .map((s) => s.trim())
              .filter(Boolean);

            const payload: CreateIncidentRequest = {
              title: String(fd.get("title") ?? ""),
              scenario: String(fd.get("scenario") ?? ""),
              severity,
              location: String(fd.get("location") ?? ""),
              reporter: String(fd.get("reporter") ?? ""),
              cause_categories: causes,
              immediate_actions: actions,
              owner: String(fd.get("owner") ?? ""),
              due_date: String(fd.get("due_date") ?? ""),
            };

            handleCreate(payload);
            modal.close();
          },
        },
      ],
    });

    document.body.appendChild(modal.element);
    return modal;
  }

  async function handleCreate(data: CreateIncidentRequest): Promise<void> {
    try {
      await createIncident(data);
      toast.success("事故创建成功");
      refresh();
    } catch {
      toast.error("创建失败");
    }
  }

  async function handleStatusUpdate(id: string, newStatus: IncidentStatus): Promise<void> {
    try {
      await updateIncident(id, { status: newStatus });
      toast.success("状态更新成功");
      refresh();
    } catch {
      toast.error("更新失败");
    }
  }

  function getFilteredData(): IncidentRecord[] {
    let result = [...allIncidents];
    const statusVal = statusFilter.value;
    if (statusVal) {
      result = result.filter((r) => r.status === statusVal);
    }
    if (overdueBox.checked) {
      result = result.filter((r) => r.overdue);
    }
    return result;
  }

  function renderTable(): void {
    const data = getFilteredData();
    const table = DataTable<IncidentRecord>({
      columns: [
        { key: "incident_id", header: "事故ID", width: "8rem" },
        { key: "title", header: "标题" },
        {
          key: "severity",
          header: "严重程度",
          render: (row) => renderSeverityBadge(row.severity),
        },
        {
          key: "status",
          header: "状态",
          render: (row) => renderStatusLabel(row.status),
        },
        { key: "location", header: "位置" },
        { key: "reporter", header: "报告人" },
        { key: "owner", header: "负责人" },
        {
          key: "due_date",
          header: "截止日期",
          render: (row) => row.due_date ? new Date(row.due_date).toLocaleDateString("zh-CN") : "—",
        },
        {
          key: "overdue_days",
          header: "逾期天数",
          render: (row) => {
            const span = document.createElement("span");
            if (row.overdue && row.overdue_days > 0) {
              span.className = "text-red-600 font-semibold";
              span.textContent = `${row.overdue_days}天`;
            } else {
              span.textContent = "—";
            }
            return span;
          },
        },
        {
          key: "_actions",
          header: "操作",
          render: (row) => {
            const wrap = document.createElement("div");
            wrap.className = "flex items-center gap-2";

            const select = document.createElement("select");
            select.className = "input text-xs py-1 px-1 w-24";
            select.innerHTML =
              `<option value="">变更状态</option>` +
              STATUS_OPTIONS.map((s) => `<option value="${s.value}">${s.label}</option>`).join("");
            select.addEventListener("change", () => {
              if (select.value) {
                handleStatusUpdate(row.incident_id, select.value as IncidentStatus);
              }
            });

            wrap.appendChild(select);
            return wrap;
          },
        },
      ],
      data,
      keyField: "incident_id",
      emptyMessage: "暂无事故记录",
    });

    table.querySelectorAll("tbody tr").forEach((tr) => {
      const rowData = data[Array.from(tr.parentElement!.children).indexOf(tr)];
      if (rowData?.overdue) {
        tr.classList.add("bg-red-50");
      }
    });

    tableWrapper.innerHTML = "";
    tableWrapper.appendChild(table);
  }

  async function refresh(): Promise<void> {
    try {
      const resp = await getIncidents();
      allIncidents = resp.incidents;
      renderTable();
    } catch {
      toast.error("加载事故数据失败");
      tableWrapper.innerHTML = "";
      tableWrapper.appendChild(EmptyState({ icon: "⚠️", message: "加载失败" }));
    }
  }

  statusFilter.addEventListener("change", () => renderTable());
  overdueBox.addEventListener("change", () => renderTable());
  addBtn.addEventListener("click", () => {
    modalInstance.close();
    modalInstance = buildCreateModal();
    modalInstance.open();
  });

  refresh();

  return container;
}
