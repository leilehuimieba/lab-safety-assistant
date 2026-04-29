// ============================================
// HTTP 客户端封装 — 基于原生 fetch
// 职责：超时控制、拦截器、错误回调、便捷方法
// ============================================

const BASE_URL = "/api";
const TIMEOUT_MS = 30000;

type HttpMethod = "GET" | "POST" | "PATCH" | "DELETE";

export interface RequestOptions {
  headers?: Record<string, string>;
  responseType?: "json" | "blob";
}

export type RequestInterceptor = (config: {
  method: HttpMethod;
  path: string;
  body?: unknown;
  options?: RequestOptions;
}) => void | Promise<void>;

export type ResponseInterceptor = (response: Response, data: unknown) => void | Promise<void>;

const requestInterceptors: RequestInterceptor[] = [];
const responseInterceptors: ResponseInterceptor[] = [];
let onErrorHandler: ((message: string) => void) | null = null;

export function setOnError(handler: (message: string) => void): void {
  onErrorHandler = handler;
}

export function registerRequestInterceptor(interceptor: RequestInterceptor): () => void {
  requestInterceptors.push(interceptor);
  return () => {
    const idx = requestInterceptors.indexOf(interceptor);
    if (idx !== -1) requestInterceptors.splice(idx, 1);
  };
}

export function registerResponseInterceptor(interceptor: ResponseInterceptor): () => void {
  responseInterceptors.push(interceptor);
  return () => {
    const idx = responseInterceptors.indexOf(interceptor);
    if (idx !== -1) responseInterceptors.splice(idx, 1);
  };
}

function emitError(message: string): void {
  if (onErrorHandler) {
    onErrorHandler(message);
  }
}

export async function request<T>(
  method: HttpMethod,
  path: string,
  body?: unknown,
  options: RequestOptions = {}
): Promise<T> {
  const url = `${BASE_URL}${path}`;
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), TIMEOUT_MS);

  const isFormData = body instanceof FormData;

  const headers: Record<string, string> = {
    Accept: "application/json",
    ...(isFormData ? {} : { "Content-Type": "application/json" }),
    ...options.headers,
  };

  const config = { method, path, body, options };
  for (const interceptor of requestInterceptors) {
    await interceptor(config);
  }

  let httpErrorHandled = false;

  try {
    const response = await fetch(url, {
      method,
      headers,
      body: body !== undefined ? (isFormData ? body : JSON.stringify(body)) : undefined,
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    let data: unknown;
    if (options.responseType === "blob") {
      data = await response.blob();
    } else {
      const text = await response.text();
      data = text ? (JSON.parse(text) as unknown) : undefined;
    }

    for (const interceptor of responseInterceptors) {
      await interceptor(response, data);
    }

    if (!response.ok) {
      httpErrorHandled = true;
      const detail =
        (data as { detail?: string } | undefined)?.detail || `请求失败 (${response.status})`;
      emitError(detail);
      throw new Error(detail);
    }

    return data as T;
  } catch (err) {
    clearTimeout(timeoutId);
    if (httpErrorHandled) {
      throw err;
    }

    if (err instanceof Error && err.name === "AbortError") {
      const msg = "请求超时";
      emitError(msg);
      throw new Error(msg);
    }

    emitError("网络请求失败");
    throw err;
  }
}

export async function get<T>(path: string, options?: RequestOptions): Promise<T> {
  return request<T>("GET", path, undefined, options);
}

export async function post<T>(path: string, body?: unknown, options?: RequestOptions): Promise<T> {
  return request<T>("POST", path, body, options);
}

export async function patch<T>(path: string, body?: unknown, options?: RequestOptions): Promise<T> {
  return request<T>("PATCH", path, body, options);
}

export async function del<T>(path: string, options?: RequestOptions): Promise<T> {
  return request<T>("DELETE", path, undefined, options);
}
