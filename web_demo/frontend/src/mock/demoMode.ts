const STORAGE_KEY = "lab-safe-demo-mode";

const env = (import.meta as ImportMeta & { env?: Record<string, string> }).env;
let demoModeEnabled = env?.VITE_DEMO_MODE === "1";

export function initDemoMode(): void {
  if (typeof window === "undefined") return;

  const params = new URLSearchParams(window.location.search);
  const demoParam = params.get("demo");

  if (demoParam === "1") {
    localStorage.setItem(STORAGE_KEY, "1");
    demoModeEnabled = true;
    return;
  }

  if (demoParam === "0") {
    localStorage.removeItem(STORAGE_KEY);
    demoModeEnabled = false;
    return;
  }

  demoModeEnabled =
    demoModeEnabled || localStorage.getItem(STORAGE_KEY) === "1";
}

export function isDemoModeEnabled(): boolean {
  return demoModeEnabled;
}

export function setDemoMode(enabled: boolean): void {
  demoModeEnabled = enabled;
  if (typeof window === "undefined") return;

  if (enabled) {
    localStorage.setItem(STORAGE_KEY, "1");
  } else {
    localStorage.removeItem(STORAGE_KEY);
  }
}
