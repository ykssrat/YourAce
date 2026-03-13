import { AnalyzeResponse, SearchItem } from "../types";

const API_BASE_URL = "http://127.0.0.1:8000";

export async function searchAssets(query: string, limit: number = 20): Promise<SearchItem[]> {
  const url = `${API_BASE_URL}/search?query=${encodeURIComponent(query)}&limit=${limit}`;
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`检索失败: ${response.status}`);
  }

  const payload = await response.json();
  return (payload.items ?? []) as SearchItem[];
}

export async function analyzeAsset(code: string): Promise<AnalyzeResponse> {
  const response = await fetch(`${API_BASE_URL}/analyze`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      code,
      long_fund_trend: 0,
    }),
  });

  if (!response.ok) {
    throw new Error(`分析失败: ${response.status}`);
  }

  return (await response.json()) as AnalyzeResponse;
}
