import { useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../AuthContext";

function titleFor(pathname) {
  if (pathname === "/") return "Dashboard";
  if (pathname === "/customers") return "Khách hàng";
  if (pathname.startsWith("/customers/")) return "Chi tiết khách hàng";
  if (pathname === "/pipeline") return "Pipeline bán hàng";
  return "";
}

export default function Topbar() {
  const { logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();

  function handleLogout() {
    logout();
    navigate("/login");
  }

  return (
    <header className="topbar">
      <span className="page-title">{titleFor(location.pathname)}</span>
      <span className="spacer" />
      <button className="secondary" onClick={handleLogout}>
        Đăng xuất
      </button>
    </header>
  );
}
