import { clearToken, getSession, getToken, saveSession, sessionGeneration, TokenPair } from "./tokenStorage";

export class SessionExpiredError extends Error {
  constructor() {
    super("Your session has expired. Please sign in again.");
    this.name = "SessionExpiredError";
  }
}

let sessionExpiredHandler: (() => void) | null = null;
export function setSessionExpiredHandler(handler: (() => void) | null): void {
  sessionExpiredHandler = handler;
}
let refreshing: { generation: number; baseUrl: string; promise: Promise<string | null> } | null = null;

async function refreshAccess(apiBaseUrl: string, generation: number, failedToken: string | null): Promise<string | null> {
  if (refreshing?.generation === generation && refreshing.baseUrl === apiBaseUrl) return refreshing.promise;
  const promise = (async () => {
    const session = await getSession();
    if (generation !== sessionGeneration()) throw new SessionExpiredError();
    if (session?.access_token && session.access_token !== failedToken) return session.access_token;
    if (!session?.refresh_token) return null;
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 10000);
    try {
      const response = await fetch(`${apiBaseUrl}/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: session.refresh_token }),
        signal: controller.signal,
      });
      if (response.status === 401) return null;
      // Offline/5xx does not destroy the saved session or loop retries.
      if (!response.ok) throw new Error("Unable to refresh session. Please try again.");
      const pair: TokenPair = await response.json();
      if (!pair.access_token || !pair.refresh_token) throw new Error("Invalid refresh response");
      if (!await saveSession(pair, generation)) throw new SessionExpiredError();
      return pair.access_token;
    } finally {
      clearTimeout(timeout);
    }
  })();
  refreshing = { generation, baseUrl: apiBaseUrl, promise };
  try { return await promise; }
  finally { if (refreshing?.promise === promise) refreshing = null; }
}

export async function apiFetch(apiBaseUrl: string, path: string, options: RequestInit = {}): Promise<Response> {
  const generation = sessionGeneration();
  const token = await getToken();
  const request = (access: string | null) => {
    const headers = new Headers(options.headers);
    if (access) headers.set("Authorization", `Bearer ${access}`);
    return fetch(`${apiBaseUrl}${path}`, { ...options, headers });
  };
  let response = await request(token);
  if (generation !== sessionGeneration()) throw new SessionExpiredError();
  if (response.status !== 401) return response;

  // Another call may already have rotated while this request was in flight.
  const latest = await getToken();
  const renewed = latest && latest !== token ? latest : await refreshAccess(apiBaseUrl, generation, token);
  if (generation !== sessionGeneration()) throw new SessionExpiredError();
  if (renewed) response = await request(renewed);
  if (generation !== sessionGeneration()) throw new SessionExpiredError();
  if (response.status === 401) {
    // Invalidate synchronously, and notify only once across concurrent failures.
    const clearing = clearToken();
    sessionExpiredHandler?.();
    await clearing;
    throw new SessionExpiredError();
  }
  return response;
}
