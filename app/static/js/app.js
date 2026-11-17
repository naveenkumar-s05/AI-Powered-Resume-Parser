const TOKEN_KEY = "access_token";

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  }[char]));
}

function formatDate(value) {
  if (!value) return "Not provided";
  const date = new Date(`${value}T00:00:00`);
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

function setToken(token) {
  localStorage.setItem(TOKEN_KEY, token);
  document.cookie = `access_token=${token}; path=/; max-age=3600; SameSite=Lax`;
}

function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
  document.cookie = "access_token=; path=/; max-age=0; SameSite=Lax";
}

function showAlert(message, type = "error", sticky = false) {
  const el = document.getElementById("alert");
  if (!el) return;
  window.clearTimeout(el._timer);
  el.textContent = message;
  el.className = `alert ${type}`;
  if (!sticky && (type === "success" || type === "info")) {
    el._timer = window.setTimeout(() => {
      el.className = "alert hidden";
    }, 4500);
  }
}

function formatValidationErrors(payload) {
  const details = payload && payload.error && payload.error.details;
  if (!Array.isArray(details) || details.length === 0) return null;
  const messages = details.map((item) => {
    const loc = Array.isArray(item.loc) ? item.loc : [];
    const field = loc.filter((part) => part !== "body").join(".");
    const msg = String(item.msg || "").replace(/^Value error,\s*/i, "");
    return field ? `${field}: ${msg}` : msg;
  });
  return [...new Set(messages)].join(" • ");
}

async function apiFetch(path, options = {}) {
  const headers = Object.assign({}, options.headers || {});
  if (!(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const response = await fetch(path, Object.assign({}, options, { headers }));

  let payload = null;
  try {
    payload = await response.json();
  } catch (_) {
    payload = null;
  }

  if (response.status === 401) {
    clearToken();
    if (!location.pathname.startsWith("/login")) {
      location.href = "/login";
    }
    throw new Error("Session expired. Please log in again.");
  }

  if (!response.ok) {
    const detailMessage = formatValidationErrors(payload);
    const message =
      detailMessage || (payload && payload.message) || `Request failed (${response.status})`;
    const error = new Error(message);
    error.payload = payload;
    throw error;
  }

  return payload;
}

function logout() {
  clearToken();
  location.href = "/login";
}
