import { createContext, useContext, useEffect, useState } from "react";
import { apiFetch, clearTokens, getActiveCompanyId, login as loginApi, setActiveCompanyId } from "./api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeCompanyId, setActiveCompanyIdState] = useState(getActiveCompanyId());

  function applyUser(me) {
    setUser(me);
    // Nếu công ty đang lưu không còn hợp lệ (bị đổi quyền, hoặc chưa từng chọn) — tự chọn công ty
    // duy nhất nếu chỉ thuộc 1 công ty, không thì để trống, bắt buộc chọn (Sidebar sẽ hiện bộ chọn).
    const companies = me.companies || [];
    const current = getActiveCompanyId();
    const stillValid = current && companies.some((c) => String(c.id) === String(current));
    if (!stillValid) {
      const next = companies.length === 1 ? String(companies[0].id) : null;
      setActiveCompanyId(next);
      setActiveCompanyIdState(next);
    } else {
      setActiveCompanyIdState(current);
    }
  }

  useEffect(() => {
    const access = localStorage.getItem("access");
    if (!access) {
      setLoading(false);
      return;
    }
    apiFetch("/api/auth/me/")
      .then(applyUser)
      .catch(() => setUser(null))
      .finally(() => setLoading(false));
  }, []);

  async function login(username, password) {
    await loginApi(username, password);
    const me = await apiFetch("/api/auth/me/");
    applyUser(me);
    return me;
  }

  function logout() {
    clearTokens();
    setActiveCompanyId(null);
    setUser(null);
    setActiveCompanyIdState(null);
  }

  // Đổi công ty đang thao tác ảnh hưởng gần như mọi màn hình đang mở (Đơn hàng, Hỏi giá, Tồn kho...)
  // — tải lại trang là cách đơn giản và chắc chắn nhất để mọi nơi lấy đúng dữ liệu công ty mới,
  // thay vì phải tự invalidate từng nơi đang cache dữ liệu theo công ty cũ.
  function switchCompany(companyId) {
    setActiveCompanyId(companyId);
    window.location.reload();
  }

  const activeCompany = (user?.companies || []).find((c) => String(c.id) === String(activeCompanyId)) || null;

  return (
    <AuthContext.Provider
      value={{ user, loading, login, logout, activeCompany, activeCompanyId, switchCompany }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
