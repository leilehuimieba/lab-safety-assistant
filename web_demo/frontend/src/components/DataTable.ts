// ============================================
// DataTable.ts — 通用数据表格组件
// ============================================

export interface Column<T> {
  key: string;
  header: string;
  width?: string;
  render?: (row: T) => HTMLElement | string;
  sortable?: boolean;
}

export interface DataTableOptions<T> {
  columns: Column<T>[];
  data: T[];
  keyField: keyof T;
  emptyMessage?: string;
  onRowClick?: (row: T) => void;
}

type SortState = {
  key: string;
  dir: "asc" | "desc";
} | null;

export function DataTable<T>(options: DataTableOptions<T>): HTMLElement {
  const wrapper = document.createElement("div");
  wrapper.className = "w-full overflow-x-auto";

  if (options.data.length === 0) {
    const empty = document.createElement("div");
    empty.className = "flex flex-col items-center justify-center py-12 text-gray-400";
    empty.innerHTML = `<span class="text-4xl mb-3">📭</span><p class="text-sm">${options.emptyMessage ?? "暂无数据"}</p>`;
    wrapper.appendChild(empty);
    return wrapper;
  }

  const table = document.createElement("table");
  table.className = "table-base";

  const thead = document.createElement("thead");
  const headerRow = document.createElement("tr");

  let sortState: SortState = null;

  const renderBody = (rows: T[]): void => {
    tbody.innerHTML = "";
    rows.forEach((row) => {
      const tr = document.createElement("tr");
      if (options.onRowClick) {
        tr.classList.add("cursor-pointer");
        tr.addEventListener("click", () => options.onRowClick!(row));
      }

      options.columns.forEach((col) => {
        const td = document.createElement("td");
        if (col.width) {
          td.style.width = col.width;
        }

        const value = (row as Record<string, unknown>)[col.key];
        if (col.render) {
          const rendered = col.render(row);
          if (typeof rendered === "string") {
            td.innerHTML = rendered;
          } else {
            td.appendChild(rendered);
          }
        } else {
          td.textContent = value !== undefined && value !== null ? String(value) : "";
        }

        tr.appendChild(td);
      });

      tbody.appendChild(tr);
    });
  };

  const getSortedData = (): T[] => {
    if (!sortState) return [...options.data];
    const { key, dir } = sortState;
    return [...options.data].sort((a, b) => {
      const av = (a as Record<string, string | number>)[key];
      const bv = (b as Record<string, string | number>)[key];
      if (av === bv) return 0;
      const cmp = av > bv ? 1 : -1;
      return dir === "asc" ? cmp : -cmp;
    });
  };

  const updateSortUI = (): void => {
    headerRow.querySelectorAll("th").forEach((th, idx) => {
      const col = options.columns[idx];
      if (!col.sortable) return;
      const arrow = th.querySelector(".sort-arrow");
      if (!arrow) return;
      if (sortState && sortState.key === col.key) {
        arrow.textContent = sortState.dir === "asc" ? " ↑" : " ↓";
      } else {
        arrow.textContent = " ↕";
      }
    });
  };

  options.columns.forEach((col) => {
    const th = document.createElement("th");
    if (col.width) {
      th.style.width = col.width;
    }

    const label = document.createElement("span");
    label.textContent = col.header;
    th.appendChild(label);

    if (col.sortable) {
      th.style.cursor = "pointer";
      const arrow = document.createElement("span");
      arrow.className = "sort-arrow text-gray-400 ml-1";
      arrow.textContent = " ↕";
      th.appendChild(arrow);

      th.addEventListener("click", () => {
        if (sortState && sortState.key === col.key) {
          sortState = { key: col.key, dir: sortState.dir === "asc" ? "desc" : "asc" };
        } else {
          sortState = { key: col.key, dir: "asc" };
        }
        renderBody(getSortedData());
        updateSortUI();
      });
    }

    headerRow.appendChild(th);
  });

  thead.appendChild(headerRow);
  table.appendChild(thead);

  const tbody = document.createElement("tbody");
  renderBody(options.data);
  table.appendChild(tbody);

  wrapper.appendChild(table);
  return wrapper;
}
