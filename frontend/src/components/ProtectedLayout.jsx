import { Navigate, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../AuthContext";

export default function ProtectedLayout() {
  const { user, loading, logout } = useAuth();
  const navigate = useNavigate();

  if (loading) return <p className="center-msg">Đang tải...</p>;
  if (!user) return <Navigate to="/login" replace />;

  function handleLogout() {
    logout();
    navigate("/login");
  }

  return (
    <div>
      <header className="topbar">
        <span className="brand">CRM</span>
        <span className="user-info">
          {user.full_name} · {user.role_label}
        </span>
        <button className="link-btn" onClick={handleLogout}>
          Đăng xuất
        </button>
      </header>
      <main>
        <Outlet />
      </main>
    </div>
  );
}
