import { Navigate, Outlet } from "react-router-dom";
import { mediaUrl } from "../api";
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
      <div className="company-picker">
        <p>Bạn thuộc nhiều công ty — chọn công ty đang thao tác:</p>
        <div className="company-picker-grid">
          {companies.map((c) => (
            <button key={c.id} type="button" className="company-picker-card" onClick={() => switchCompany(c.id)}>
              {c.logo ? (
                <img src={mediaUrl(c.logo)} alt={c.name} />
              ) : (
                <span className="company-picker-fallback">{c.code.slice(0, 2)}</span>
              )}
              <span className="company-picker-name">{c.name}</span>
            </button>
          ))}
        </div>
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
