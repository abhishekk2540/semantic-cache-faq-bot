const BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

export const getToken = () => localStorage.getItem("token");
export const setSession = (token, username) => {
  localStorage.setItem("token", token);
  localStorage.setItem("username", username);
};
export const clearSession = () => {
  localStorage.removeItem("token");
  localStorage.removeItem("username");
};

export async function api(path, { method = "GET", body, signal } = {}) {
  const headers = { "Content-Type": "application/json" };
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;

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

  if (res.status === 401 && token) {
    clearSession();
    window.location.reload();
  }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = data.detail;
    throw new Error(typeof detail === "string" ? detail : "Request failed (" + res.status + ")");
  }
  return data;
}
