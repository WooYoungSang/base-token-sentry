import type {
  AnalyzeResponse,
  RecentTokensResponse,
  TokenDetail,
  TokenListResponse,
} from "./types";

const API_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API ${res.status}: ${body}`);
  }
  return res.json();
}

export async function analyzeToken(address: string): Promise<AnalyzeResponse> {
  return apiFetch<AnalyzeResponse>(`/analyze/${address}`, { method: "POST" });
}

export async function listTokens(params: {
  page?: number;
  page_size?: number;
  grade?: string;
  is_honeypot?: boolean;
}): Promise<TokenListResponse> {
  const q = new URLSearchParams();
  if (params.page) q.set("page", String(params.page));
  if (params.page_size) q.set("page_size", String(params.page_size));
  if (params.grade) q.set("grade", params.grade);
  if (params.is_honeypot !== undefined)
    q.set("is_honeypot", String(params.is_honeypot));
  return apiFetch<TokenListResponse>(`/tokens?${q}`);
}

export async function getToken(address: string): Promise<TokenDetail> {
  return apiFetch<TokenDetail>(`/tokens/${address}`);
}

export async function getRecentTokens(
  limit = 20
): Promise<RecentTokensResponse> {
  return apiFetch<RecentTokensResponse>(`/watch/recent?limit=${limit}`);
}
