export const API_URL = (process.env.NEXT_PUBLIC_API_URL || "").replace(/\/$/, "");
const TOKEN_KEY = "mindpulse_access_token";

export type TrendPoint = {
  date: string;
  sentiment_score: number | null;
  mood_score: number | null;
  stress_score: number | null;
  moving_average: number | null;
  entry_count: number;
};

export type TrendSummary = {
  points: TrendPoint[];
  trend: "improving" | "steady" | "declining" | "insufficient_data";
  risk_level: "Green" | "Amber";
  summary: string;
};

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

export function getToken(): string | null {
  return typeof window === "undefined" ? null : window.localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  window.localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  window.localStorage.removeItem(TOKEN_KEY);
}

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers = new Headers(options.headers);
  if (options.body && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);

  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, { ...options, headers, cache: "no-store" });
  } catch {
    throw new ApiError("MindPulse could not reach the service. Check your connection and try again.", 0);
  }
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const detail = body?.detail;
    const message = Array.isArray(detail) ? detail.map((item) => item.msg).join(". ") : detail;
    throw new ApiError(typeof message === "string" ? message : "Something went wrong. Please try again.", response.status);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export async function signIn(path: string, payload?: unknown): Promise<void> {
  const result = await api<{ access_token: string }>(path, {
    method: "POST",
    ...(payload ? { body: JSON.stringify(payload) } : {}),
  });
  setToken(result.access_token);
}