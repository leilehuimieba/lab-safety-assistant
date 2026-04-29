// ============================================
// StepIndicator.ts — 步骤指示器组件
// ============================================

export interface Step {
  label: string;
  description?: string;
}

export function StepIndicator(options: { steps: Step[]; current: number }): HTMLElement {
  const { steps, current } = options;
  const el = document.createElement("div");
  el.className = "w-full";

  const container = document.createElement("div");
  container.className = "flex items-center justify-between";

  steps.forEach((step, index) => {
    const isCompleted = index < current;
    const isActive = index === current;

    const stepWrapper = document.createElement("div");
    stepWrapper.className = "flex-1 flex flex-col items-center relative";

    // Circle
    const circle = document.createElement("div");
    if (isCompleted) {
      circle.className =
        "w-8 h-8 rounded-full bg-green-500 text-white flex items-center justify-center text-sm font-bold z-10";
      circle.textContent = "✓";
    } else if (isActive) {
      circle.className =
        "w-8 h-8 rounded-full bg-blue-600 text-white flex items-center justify-center text-sm font-bold z-10 ring-4 ring-blue-100";
      circle.textContent = String(index + 1);
    } else {
      circle.className =
        "w-8 h-8 rounded-full bg-gray-200 text-gray-500 flex items-center justify-center text-sm font-bold z-10";
      circle.textContent = String(index + 1);
    }

    // Label
    const label = document.createElement("span");
    label.className = `mt-2 text-xs font-medium ${isActive ? "text-blue-600" : isCompleted ? "text-green-600" : "text-gray-400"}`;
    label.textContent = step.label;

    stepWrapper.appendChild(circle);
    stepWrapper.appendChild(label);

    if (step.description) {
      const desc = document.createElement("span");
      desc.className = "mt-0.5 text-[10px] text-gray-400";
      desc.textContent = step.description;
      stepWrapper.appendChild(desc);
    }

    container.appendChild(stepWrapper);

    // Connector line (except after last step)
    if (index < steps.length - 1) {
      const line = document.createElement("div");
      line.className = "flex-1 h-0.5 mx-2 -mt-6";
      if (index < current) {
        line.classList.add("bg-green-500");
      } else {
        line.classList.add("bg-gray-200");
      }
      container.appendChild(line);
    }
  });

  el.appendChild(container);
  return el;
}
