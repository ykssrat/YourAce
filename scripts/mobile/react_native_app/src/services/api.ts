import { AnalyzeResponse, SearchItem } from "../types";

const API_BASE_URL = "http://127.0.0.1:8000";
const REQUEST_TIMEOUT_MS = 10000;
const RETRY_COUNT = 1;

export async function searchAssets(query: string, limit: number = 20): Promise<SearchItem[]> {
  const url = `${API_BASE_URL}/search?query=${encodeURIComponent(query)}&limit=${limit}`;
  const response = await requestWithRetry(url, {
    method: "GET",
  });

  const payload = await response.json();
  return (payload.items ?? []) as SearchItem[];
}

export async function analyzeAsset(code: string): Promise<AnalyzeResponse> {
  const response = await requestWithRetry(`${API_BASE_URL}/analyze`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      code,
      long_fund_trend: 0,
    }),
  });

  return (await response.json()) as AnalyzeResponse;
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
      lastError = error instanceof Error ? error : new Error("未知错误");
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
