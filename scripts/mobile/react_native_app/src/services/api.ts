import { AnalyzeRequest, AnalyzeResponse, DiagnoseRequest, DiagnoseResponse, Opinion, ScreenActionLogRequest, ScreenRequest, ScreenResponse, SearchItem } from "../types";

const DEFAULT_API_BASE_URLS = [
  "http://10.0.2.2:8000",
  "http://127.0.0.1:8000",
  "http://localhost:8000",
];
const REQUEST_TIMEOUT_MS = 10000;
const RETRY_COUNT = 1;

export async function searchAssets(
  query: string,
  limit: number = 20,
  preferredBaseUrl: string = "",
): Promise<SearchItem[]> {
  const path = `/search?query=${encodeURIComponent(query)}&limit=${limit}`;
  const response = await requestWithBaseFallback(path, { method: "GET" }, buildBaseUrls(preferredBaseUrl));

  const payload = await response.json();
  return (payload.items ?? []) as SearchItem[];
}

export async function analyzeAsset(
  code: string,
  preferredBaseUrl: string = "",
  request?: Partial<AnalyzeRequest>,
): Promise<AnalyzeResponse> {
  const response = await requestWithBaseFallback("/analyze", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      code,
      strategy: request?.strategy || "default",
      long_fund_trend: request?.long_fund_trend || 0,
      include_news: request?.include_news ?? true,
    }),
  }, buildBaseUrls(preferredBaseUrl));

  const payload = (await response.json()) as AnalyzeResponse;
  return normalizeAnalyzeResponse(payload);
}

export async function diagnoseAsset(
  code: string,
  preferredBaseUrl: string = "",
  request?: Partial<DiagnoseRequest>,
): Promise<DiagnoseResponse> {
  const response = await requestWithBaseFallback("/diagnose", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ 
      code, 
      strategy: request?.strategy || "default",
      include_news: request?.include_news ?? true 
    }),
  }, buildBaseUrls(preferredBaseUrl));

  const payload = (await response.json()) as DiagnoseResponse;
  return normalizeDiagnoseResponse(payload);
}

export async function screenAssets(
  request: ScreenRequest,
  preferredBaseUrl: string = "",
): Promise<ScreenResponse> {
  const response = await requestWithBaseFallback("/screen", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      ...request,
      strategy: request.strategy || "default",
    }),
  }, buildBaseUrls(preferredBaseUrl));

  const payload = (await response.json()) as ScreenResponse;
  return {
    ...payload,
    items: (payload.items ?? []).map((item) => ({
      ...item,
      label: normalizeOpinion(item.label),
      horizon_signals: normalizeHorizonSignals(item.horizon_signals),
    })),
  };
}

export async function logScreenAction(
  request: ScreenActionLogRequest,
  preferredBaseUrl: string = "",
): Promise<void> {
  await requestWithBaseFallback("/screen/log", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  }, buildBaseUrls(preferredBaseUrl));
}

function normalizeDiagnoseResponse(payload: DiagnoseResponse): DiagnoseResponse {
  return {
    ...normalizeAnalyzeResponse(payload),
    matrix: {
      short: normalizeOpinion(payload.matrix.short),
      mid: normalizeOpinion(payload.matrix.mid),
      long: normalizeOpinion(payload.matrix.long),
    },
  };
}

function normalizeAnalyzeResponse(payload: AnalyzeResponse): AnalyzeResponse {
  return {
    ...payload,
    label: normalizeOpinion(payload.label),
    horizon_signals: normalizeHorizonSignals(payload.horizon_signals),
  };
}

function normalizeHorizonSignals(signals: AnalyzeResponse["horizon_signals"]): AnalyzeResponse["horizon_signals"] {
  return {
    short: normalizeOpinion(signals.short),
    mid: normalizeOpinion(signals.mid),
    long: normalizeOpinion(signals.long),
  };
}

function normalizeOpinion(opinion: string): Opinion {
  if (opinion === "STRONG_BUY") {
    return "BUY";
  }
  if (opinion === "STRONG_SELL") {
    return "SELL";
  }
  if (opinion === "BUY" || opinion === "HOLD" || opinion === "SELL") {
    return opinion;
  }
  return "HOLD";
}

export async function checkServerHealth(
  preferredBaseUrl: string,
): Promise<{ ok: boolean; message: string }> {
  const baseUrl = normalizeBaseUrl(preferredBaseUrl);
  if (!baseUrl) {
    return { ok: false, message: "地址为空，请填写后端地址" };
  }

  const url = `${baseUrl}/health`;
  try {
    const response = await requestWithTimeout(url, { method: "GET" }, REQUEST_TIMEOUT_MS);
    if (!response.ok) {
      return { ok: false, message: `HTTP ${response.status}` };
    }
    const payload = await response.json();
    if (payload?.status === "ok") {
      return { ok: true, message: "连接成功" };
    }
    return { ok: false, message: "接口返回异常" };
  } catch (error) {
    const msg = error instanceof Error ? error.message : "未知错误";
    return { ok: false, message: msg };
  }
}

async function requestWithBaseFallback(path: string, init: RequestInit, baseUrls: string[]): Promise<Response> {
  const errors: string[] = [];
  for (const baseUrl of baseUrls) {
    const url = `${baseUrl}${path}`;
    try {
      return await requestWithRetry(url, init);
    } catch (error) {
      const msg = error instanceof Error ? error.message : "未知错误";
      errors.push(`${baseUrl}: ${msg}`);
    }
  }

  throw new Error(`network request failed: ${errors.join(" | ")}`);
}

function buildBaseUrls(preferredBaseUrl: string): string[] {
  const normalizedPreferred = normalizeBaseUrl(preferredBaseUrl);
  if (!normalizedPreferred) {
    return DEFAULT_API_BASE_URLS;
  }

  const result = [normalizedPreferred, ...DEFAULT_API_BASE_URLS];
  return Array.from(new Set(result));
}

function normalizeBaseUrl(input: string): string {
  const value = input.trim();
  if (!value) {
    return "";
  }
  if (value.startsWith("http://") || value.startsWith("https://")) {
    return value.replace(/\/$/, "");
  }
  return `http://${value.replace(/\/$/, "")}`;
}

async function requestWithRetry(url: string, init: RequestInit): Promise<Response> {
  let attempt = 0;
  let lastError: Error | null = null;

  while (attempt <= RETRY_COUNT) {
    try {
      const response = await requestWithTimeout(url, init, REQUEST_TIMEOUT_MS);
      if (!response.ok) {
        throw new Error(`请求失败: ${response.status}`);
      }
      return response;
    } catch (error) {
      if (error instanceof Error && error.message.includes("network request failed")) {
        lastError = error;
      } else {
        lastError = error instanceof Error ? error : new Error("未知错误");
      }
      attempt += 1;
      if (attempt > RETRY_COUNT) {
        throw lastError;
      }
    }
  }

  throw lastError ?? new Error("请求失败");
}

async function requestWithTimeout(url: string, init: RequestInit, timeoutMs: number): Promise<Response> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  try {
    return await fetch(url, {
      ...init,
      signal: controller.signal,
    });
  } catch (error) {
    if (error instanceof Error && error.name === "AbortError") {
      throw new Error("请求超时");
    }
    throw error;
  } finally {
    clearTimeout(timer);
  }
}
