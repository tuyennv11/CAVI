import { useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../AuthContext";

function titleFor(pathname) {
  if (pathname === "/") return "Làm việc";
  if (pathname === "/dashboard") return "Dashboard";
  if (pathname === "/notices") return "Thông báo nội bộ";
  if (pathname === "/partners") return "Đối tác";
  if (pathname.startsWith("/partners/")) return "Chi tiết đối tác";
  if (pathname === "/pipeline") return "Pipeline bán hàng";
  if (pathname === "/tier-requests") return "Yêu cầu nâng hạng";
  if (pathname === "/approvals") return "Ký duyệt";
  if (pathname === "/shipments") return "Kiện hàng";
  if (pathname === "/shipment-batches") return "Quản lý vận hành";
  if (pathname === "/attendance") return "Chấm công";
  if (pathname === "/profile") return "Cá nhân";
  return "";
}

export default function Topbar({ onMenuClick }) {
  const { logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();

  function handleLogout() {
    logout();
    navigate("/login");
  }

  return (
    <header className="topbar">
      <button className="menu-toggle" onClick={onMenuClick} aria-label="Mở menu">
        <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.8">
          <path d="M3 5.5h14M3 10h14M3 14.5h14" strokeLinecap="round" />
        </svg>
      </button>
      <span className="page-title">{titleFor(location.pathname)}</span>
      <span className="spacer" />
      <button className="secondary" onClick={handleLogout}>
        Đăng xuất
      </button>
    </header>
  );
}
