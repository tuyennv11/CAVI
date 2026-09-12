import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "../AuthContext";
import Sidebar from "./Sidebar";
import Topbar from "./Topbar";

export default function ProtectedLayout() {
  const { user, loading, activeCompany, switchCompany } = useAuth();

  if (loading) return <p className="center-msg">Đang tải...</p>;
  if (!user) return <Navigate to="/login" replace />;

  const companies = user.companies || [];
  if (companies.length === 0) {
    return <p className="center-msg">Tài khoản chưa được gán vào công ty nào — liên hệ Quản lý để được gán.</p>;
  }
  if (companies.length > 1 && !activeCompany) {
    return (
      <div className="center-msg">
        <p>Bạn thuộc nhiều công ty — hãy chọn công ty đang thao tác:</p>
        <select
          defaultValue=""
          onChange={(e) => e.target.value && switchCompany(e.target.value)}
          style={{ fontSize: 15, padding: "6px 10px" }}
        >
          <option value="" disabled>
            Chọn công ty…
          </option>
          {companies.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </select>
      </div>
    );
  }

  return (
    <div className="app-shell">
      <Sidebar user={user} />
      <div className="app-main">
        <Topbar />
        <main className="app-content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
