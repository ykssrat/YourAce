import {
  AnalyzeRequest,
  AnalyzeResponse,
  AuthRequest,
  AuthResponse,
  DiagnoseRequest,
  DiagnoseResponse,
  Opinion,
  QuoteSnapshot,
  ScreenActionLogRequest,
  ScreenRequest,
  ScreenResponse,
  SearchItem,
  WatchlistAddRequest,
  WatchlistListResponse,
  WatchlistNotification,
  WatchlistQueueResponse,
  WatchlistQuotesResponse,
  WatchlistRecommendation,
  WatchlistRemoveRequest,
  WatchlistSignalsResponse,
  WatchlistSummaryResponse,
} from "../types";

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
      strategy: request?.strategy || "momentum_deviation",
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
      strategy: request?.strategy || "momentum_deviation",
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
      strategy: request.strategy || "momentum_deviation",
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

export async function registerUser(
  request: AuthRequest,
  preferredBaseUrl: string = "",
): Promise<AuthResponse> {
  return await requestJsonWithBaseFallback<AuthResponse>("/auth/register", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      username: request.username,
      password: request.password,
      persist_session: request.persist_session ?? false,
    }),
  }, buildBaseUrls(preferredBaseUrl));
}

export async function loginUser(
  request: AuthRequest,
  preferredBaseUrl: string = "",
): Promise<AuthResponse> {
  return await requestJsonWithBaseFallback<AuthResponse>("/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      username: request.username,
      password: request.password,
      persist_session: request.persist_session ?? false,
    }),
  }, buildBaseUrls(preferredBaseUrl));
}

export async function refreshAuthSession(
  userId: string,
  token: string,
  preferredBaseUrl: string = "",
): Promise<AuthResponse> {
  return await requestJsonWithBaseFallback<AuthResponse>("/auth/refresh", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id: userId, token }),
  }, buildBaseUrls(preferredBaseUrl));
}

export async function recommendWatchlistEtfs(
  code: string,
  preferredBaseUrl: string = "",
  stockName: string = "",
  limit: number = 5,
): Promise<WatchlistRecommendation[]> {
  const path = `/watchlist/recommendations?code=${encodeURIComponent(code)}&stock_name=${encodeURIComponent(stockName)}&limit=${limit}`;
  const payload = await requestJsonWithBaseFallback<{ items?: WatchlistRecommendation[] }>(path, { method: "GET" }, buildBaseUrls(preferredBaseUrl));
  return (payload.items ?? []) as WatchlistRecommendation[];
}

export async function addWatchlistItem(
  request: WatchlistAddRequest,
  preferredBaseUrl: string = "",
): Promise<{ user_id: string; item: unknown; recommendations: WatchlistRecommendation[] }> {
  return await requestJsonWithBaseFallback<{ user_id: string; item: unknown; recommendations: WatchlistRecommendation[] }>("/watchlist/add", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  }, buildBaseUrls(preferredBaseUrl));
}

export async function removeWatchlistItem(
  request: WatchlistRemoveRequest,
  preferredBaseUrl: string = "",
): Promise<{ user_id: string; code: string; removed: boolean }> {
  return await requestJsonWithBaseFallback<{ user_id: string; code: string; removed: boolean }>("/watchlist/remove", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  }, buildBaseUrls(preferredBaseUrl));
}

export async function listWatchlistItems(
  userId: string,
  token: string,
  preferredBaseUrl: string = "",
): Promise<WatchlistListResponse> {
  const path = `/watchlist?user_id=${encodeURIComponent(userId)}&token=${encodeURIComponent(token)}`;
  return await requestJsonWithBaseFallback<WatchlistListResponse>(path, { method: "GET" }, buildBaseUrls(preferredBaseUrl));
}

export async function getWatchlistQuotes(
  userId: string,
  token: string,
  preferredBaseUrl: string = "",
): Promise<WatchlistQuotesResponse> {
  const path = `/watchlist/quotes?user_id=${encodeURIComponent(userId)}&token=${encodeURIComponent(token)}`;
  return await requestJsonWithBaseFallback<WatchlistQuotesResponse>(path, { method: "GET" }, buildBaseUrls(preferredBaseUrl));
}

export async function getWatchlistSignals(
  userId: string,
  token: string,
  preferredBaseUrl: string = "",
): Promise<WatchlistSignalsResponse> {
  const path = `/watchlist/signals?user_id=${encodeURIComponent(userId)}&token=${encodeURIComponent(token)}`;
  return await requestJsonWithBaseFallback<WatchlistSignalsResponse>(path, { method: "GET" }, buildBaseUrls(preferredBaseUrl));
}

export async function getWatchlistSummary(
  userId: string,
  token: string,
  preferredBaseUrl: string = "",
): Promise<WatchlistSummaryResponse> {
  const path = `/watchlist/summary?user_id=${encodeURIComponent(userId)}&token=${encodeURIComponent(token)}`;
  return await requestJsonWithBaseFallback<WatchlistSummaryResponse>(path, { method: "GET" }, buildBaseUrls(preferredBaseUrl));
}

export async function drainWatchlistNotifications(
  userId: string,
  token: string,
  preferredBaseUrl: string = "",
): Promise<WatchlistQueueResponse> {
  const path = `/watchlist/notifications?user_id=${encodeURIComponent(userId)}&token=${encodeURIComponent(token)}`;
  return await requestJsonWithBaseFallback<WatchlistQueueResponse>(path, { method: "GET" }, buildBaseUrls(preferredBaseUrl));
}

export function buildWatchlistStreamUrl(
  userId: string,
  token: string,
  preferredBaseUrl: string = "",
  intervalSeconds: number = 20,
  durationSeconds: number = 300,
): string {
  const baseUrl = normalizeBaseUrl(preferredBaseUrl) || DEFAULT_API_BASE_URLS[0];
  const query = new URLSearchParams({
    user_id: userId,
    token,
    interval_seconds: String(intervalSeconds),
    duration_seconds: String(durationSeconds),
  });
  return `${baseUrl}/watchlist/stream?${query.toString()}`;
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

async function requestWithBaseFallbackAllowHttpError(path: string, init: RequestInit, baseUrls: string[]): Promise<Response> {
  const errors: string[] = [];
  for (const baseUrl of baseUrls) {
    const url = `${baseUrl}${path}`;
    try {
      return await requestWithTimeout(url, init, REQUEST_TIMEOUT_MS);
    } catch (error) {
      const msg = error instanceof Error ? error.message : "未知错误";
      errors.push(`${baseUrl}: ${msg}`);
    }
  }

  throw new Error(`network request failed: ${errors.join(" | ")}`);
}

async function requestJsonWithBaseFallback<T>(path: string, init: RequestInit, baseUrls: string[]): Promise<T> {
  const response = await requestWithBaseFallbackAllowHttpError(path, init, baseUrls);
  const payload = await readResponsePayload(response);
  if (!response.ok) {
    throw new Error(extractApiErrorMessage(payload, response.status, response.statusText));
  }
  return payload as T;
}

async function readResponsePayload(response: Response): Promise<unknown> {
  const text = await response.text();
  if (!text) {
    return {};
  }

  try {
    return JSON.parse(text) as unknown;
  } catch {
    return text;
  }
}

function extractApiErrorMessage(payload: unknown, status: number, statusText: string): string {
  if (typeof payload === "string" && payload.trim()) {
    return payload;
  }

  if (payload && typeof payload === "object") {
    const detail = (payload as { detail?: unknown }).detail;
    if (typeof detail === "string" && detail.trim()) {
      return detail;
    }
    if (Array.isArray(detail) && detail.length > 0) {
      const firstDetail = detail[0];
      if (typeof firstDetail === "string" && firstDetail.trim()) {
        return firstDetail;
      }
    }
  }

  return statusText ? `${status}: ${statusText}` : `请求失败: ${status}`;
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
