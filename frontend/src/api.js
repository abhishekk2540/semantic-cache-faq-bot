import { useAuth } from "@clerk/react";

const BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

/**
 * Standalone api() that accepts a token parameter.
 * Components call useClerkApi() to get a wrapper that auto-injects the token.
 */
export async function api(path, { method = "GET", body, signal, token } = {}) {
  const headers = { "Content-Type": "application/json" };
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  let res;
  try {
    res = await fetch(BASE + path, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
      signal,
    });
  } catch {
    throw new Error("Cannot reach the backend. Is uvicorn running on port 8000?");
  }

  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = data.detail;
    throw new Error(typeof detail === "string" ? detail : "Request failed (" + res.status + ")");
  }
  return data;
}

/**
 * React hook: returns an `api` function that automatically attaches
 * the current Clerk session token to every request.
 */
export function useClerkApi() {
  const { getToken } = useAuth();

  return async (path, options = {}) => {
    const token = await getToken();
    return api(path, { ...options, token });
  };
}
