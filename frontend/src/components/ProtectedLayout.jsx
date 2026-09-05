import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "../AuthContext";
import Sidebar from "./Sidebar";
import Topbar from "./Topbar";

export default function ProtectedLayout() {
  const { user, loading } = useAuth();

  if (loading) return <p className="center-msg">Đang tải...</p>;
  if (!user) return <Navigate to="/login" replace />;

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
