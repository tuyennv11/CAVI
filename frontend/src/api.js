const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

function getTokens() {
  return {
    access: localStorage.getItem("access"),
    refresh: localStorage.getItem("refresh"),
  };
}

function setTokens({ access, refresh }) {
  localStorage.setItem("access", access);
  if (refresh) localStorage.setItem("refresh", refresh);
}

export function clearTokens() {
  localStorage.removeItem("access");
  localStorage.removeItem("refresh");
}

export async function login(username, password) {
  const res = await fetch(`${API_URL}/api/auth/token/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  if (!res.ok) throw new Error("Sai tên đăng nhập hoặc mật khẩu");
  const data = await res.json();
  setTokens(data);
  return data;
}

async function refreshAccessToken() {
  const { refresh } = getTokens();
  if (!refresh) return null;
  const res = await fetch(`${API_URL}/api/auth/token/refresh/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh }),
  });
  if (!res.ok) return null;
  const data = await res.json();
  setTokens({ access: data.access });
  return data.access;
}

// DRF trả lỗi ở nhiều dạng khác nhau tuỳ nguồn (detail / non_field_errors / lỗi theo field) —
// gom về 1 thông điệp dễ hiểu thay vì luôn rơi về "Lỗi 400" chung chung.
function extractErrorMessage(body, status) {
  if (body.detail) return body.detail;
  if (Array.isArray(body.non_field_errors) && body.non_field_errors.length) return body.non_field_errors[0];
  const firstArray = Object.values(body).find((v) => Array.isArray(v) && v.length);
  if (firstArray) return firstArray[0];
  return `Lỗi ${status}`;
}

// Gọi API kèm sẵn token; nếu access token hết hạn thì tự làm mới rồi thử lại 1 lần.
export async function apiFetch(path, options = {}) {
  const { access } = getTokens();
  const doFetch = (token) =>
    fetch(`${API_URL}${path}`, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...options.headers,
      },
    });

  let res = await doFetch(access);
  if (res.status === 401) {
    const newAccess = await refreshAccessToken();
    if (newAccess) {
      res = await doFetch(newAccess);
    } else {
      clearTokens();
      window.location.href = "/login";
      throw new Error("Phiên đăng nhập đã hết hạn");
    }
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(extractErrorMessage(body, res.status));
  }
  if (res.status === 204) return null;
  return res.json();
}

// Gửi FormData (multipart, dùng cho upload file) kèm JWT; không set Content-Type để
// trình duyệt tự sinh boundary. Cùng cơ chế tự làm mới token khi hết hạn như apiFetch.
export async function apiUpload(path, formData, method = "POST") {
  const { access } = getTokens();
  const doFetch = (token) =>
    fetch(`${API_URL}${path}`, {
      method,
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: formData,
    });

  let res = await doFetch(access);
  if (res.status === 401) {
    const newAccess = await refreshAccessToken();
    if (newAccess) {
      res = await doFetch(newAccess);
    } else {
      clearTokens();
      window.location.href = "/login";
      throw new Error("Phiên đăng nhập đã hết hạn");
    }
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(extractErrorMessage(body, res.status));
  }
  if (res.status === 204) return null;
  return res.json();
}

export { API_URL };
