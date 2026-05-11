import { isDemoModeEnabled, setDemoMode } from "../mock/demoMode";

export function DemoModeBanner(): HTMLElement | null {
  if (!isDemoModeEnabled()) return null;

  const banner = document.createElement("div");
  banner.className = [
    "fixed right-4 bottom-4 z-[60] max-w-sm rounded-xl shadow-xl border border-amber-200",
    "bg-amber-50 text-amber-900 px-4 py-3",
  ].join(" ");

  const title = document.createElement("div");
  title.className = "text-sm font-bold mb-1";
  title.textContent = "当前为演示模式";

  const desc = document.createElement("p");
  desc.className = "text-xs leading-5";
  desc.textContent =
    "前端正在使用 mock 数据展示项目效果，适合答辩和截图，不依赖真实接口返回。";

  const actions = document.createElement("div");
  actions.className = "mt-3 flex items-center gap-2";

  const keepBtn = document.createElement("button");
  keepBtn.className = "btn-primary text-xs px-3 py-1.5";
  keepBtn.textContent = "继续演示";

  const exitBtn = document.createElement("button");
  exitBtn.className = "btn-secondary text-xs px-3 py-1.5";
  exitBtn.textContent = "退出演示模式";
  exitBtn.addEventListener("click", () => {
    setDemoMode(false);
    window.location.href = window.location.pathname;
  });

  actions.appendChild(keepBtn);
  actions.appendChild(exitBtn);

  banner.appendChild(title);
  banner.appendChild(desc);
  banner.appendChild(actions);

  return banner;
}
