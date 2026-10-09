import { clearToken, getToken } from "./tokenStorage";

// Thrown when the backend rejects the saved token (expired, invalid,
// or the account no longer exists). The app returns to the login screen.
export class SessionExpiredError extends Error {
  constructor() {
    super("Your session has expired. Please sign in again.");
    this.name = "SessionExpiredError";
  }
}

type SessionExpiredHandler = () => void;

let sessionExpiredHandler: SessionExpiredHandler | null = null;

// App.tsx registers this once so any screen's request can end the session
export function setSessionExpiredHandler(
  handler: SessionExpiredHandler | null
): void {
  sessionExpiredHandler = handler;
}

// fetch() for protected endpoints: adds the Bearer token and handles 401
export async function apiFetch(
  apiBaseUrl: string,
  path: string,
  options: RequestInit = {}
): Promise<Response> {
  const token = await getToken();
  const headers = new Headers(options.headers);

  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(`${apiBaseUrl}${path}`, {
    ...options,
    headers,
  });

  if (response.status === 401) {
    await clearToken();
    sessionExpiredHandler?.();
    throw new SessionExpiredError();
  }

  return response;
}
