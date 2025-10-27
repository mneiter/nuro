export const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000/api";

export type TimerStatus = "running" | "completed" | "canceled";

export interface AuthResponse {
  access_token: string;
  token_type: string;
}

export interface TimerResource {
  id: string;
  label: string;
  duration_seconds: number;
  status: TimerStatus;
  started_at: string;
  ends_at: string;
  completed_at: string | null;
  canceled_at: string | null;
  remaining_seconds: number;
  etag: string;
  last_modified: string;
}

export interface TimerTickResource {
  id: string;
  label: string;
  status: TimerStatus;
  ends_at: string;
  remaining_seconds: number;
  etag: string;
  last_modified: string;
}

class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function parseError(response: Response): Promise<Error> {
  try {
    const data = await response.json();
    if (data?.detail) {
      const detail = Array.isArray(data.detail) ? data.detail[0]?.msg ?? "Request failed" : data.detail;
      return new ApiError(response.status, detail);
    }
  } catch (error) {
    // ignore JSON parse failures
  }
  return new ApiError(response.status, response.statusText || "Request failed");
}

async function apiRequest<T>(
  path: string,
  init: RequestInit = {},
  token?: string
): Promise<T> {
  const headers = new Headers(init.headers ?? {});
  headers.set("Accept", "application/json");

  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  if (init.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers
  });

  if (response.status === 204) {
    return null as T;
  }

  if (!response.ok) {
    throw await parseError(response);
  }

  return (await response.json()) as T;
}

export async function register(email: string, password: string): Promise<AuthResponse> {
  return apiRequest<AuthResponse>("/auth/register", {
    method: "POST",
    body: JSON.stringify({ email, password })
  });
}

export async function login(email: string, password: string): Promise<AuthResponse> {
  return apiRequest<AuthResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password })
  });
}

export async function getProfile(token: string) {
  return apiRequest<{ id: string; email: string }>("/auth/me", {}, token);
}

export async function listTimers(token: string): Promise<TimerResource[]> {
  return apiRequest<TimerResource[]>("/timers", {}, token);
}

export async function startTimer(token: string, durationSeconds = 1500, label = "Pomodoro"): Promise<TimerResource> {
  return apiRequest<TimerResource>(
    "/timers",
    {
      method: "POST",
      body: JSON.stringify({ duration_seconds: durationSeconds, label })
    },
    token
  );
}

export async function cancelTimer(token: string, timerId: string): Promise<TimerResource> {
  return apiRequest<TimerResource>(
    `/timers/${timerId}/cancel`,
    {
      method: "POST"
    },
    token
  );
}

export async function longPollTimer(
  token: string,
  timerId: string,
  etag?: string,
  signal?: AbortSignal
): Promise<TimerTickResource | null> {
  const headers = new Headers({
    Accept: "application/json",
    Authorization: `Bearer ${token}`
  });

  if (etag) {
    headers.set("If-None-Match", etag);
  }

  const response = await fetch(`${API_BASE}/timers/${timerId}/tick?wait=true`, {
    method: "GET",
    headers,
    signal
  });

  if (response.status === 304) {
    return null;
  }

  if (!response.ok) {
    throw await parseError(response);
  }

  return (await response.json()) as TimerTickResource;
}

export { ApiError };
