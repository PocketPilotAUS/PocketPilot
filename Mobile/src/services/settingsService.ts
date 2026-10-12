import { apiFetch } from "./apiClient";
import type { AuthUser } from "./authService";

export type ProfileUpdate = { name: string; email: string; phone: string | null; current_password?: string };

async function request(base: string, path: string, method = "GET", body?: object) {
  const response = await apiFetch(base, path, {
    method,
    ...(body ? { headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) } : {}),
  });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    const detail = typeof data.detail === "string" ? data.detail : Array.isArray(data.detail) ? data.detail.map((item: { msg?: string }) => item.msg).filter(Boolean).join("\n") : "";
    throw new Error(detail || "Unable to save your changes. Please try again.");
  }
  return response;
}

export async function getAccount(base: string): Promise<AuthUser> {
  return (await request(base, "/auth/me")).json();
}
export async function updateAccount(base: string, body: ProfileUpdate): Promise<AuthUser> {
  return (await request(base, "/auth/me", "PATCH", body)).json();
}
export async function changeAccountPassword(base: string, current_password: string, new_password: string) {
  await request(base, "/auth/password", "POST", { current_password, new_password });
}
