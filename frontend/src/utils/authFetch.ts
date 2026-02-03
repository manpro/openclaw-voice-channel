/**
 * Authenticated fetch wrapper.
 *
 * Reads AUTH_TOKEN from localStorage (key: "authToken").
 * If set, adds Authorization: Bearer <token> to all requests.
 */

export function getAuthToken(): string {
  return localStorage.getItem("authToken") ?? "";
}

export function setAuthToken(token: string): void {
  localStorage.setItem("authToken", token);
}

export function authHeaders(): Record<string, string> {
  const token = getAuthToken();
  if (!token) return {};
  return { Authorization: `Bearer ${token}` };
}

export function authFetch(
  url: string,
  init?: RequestInit,
): Promise<Response> {
  const headers = new Headers(init?.headers);
  const token = getAuthToken();
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  return fetch(url, { ...init, headers });
}
