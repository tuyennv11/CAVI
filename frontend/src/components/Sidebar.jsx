import { NavLink } from "react-router-dom";
import Avatar from "./Avatar";

const ICONS = {
  workspace: (
    <svg className="icon" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6">
      <path d="M6 3.5v2M14 3.5v2M3 7h14" strokeLinecap="round" />
      <rect x="3" y="4.5" width="14" height="12" rx="1.6" />
      <path d="M6.5 10.5l2 2 4.5-4.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  ),
  dashboard: (
    <svg className="icon" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6">
      <rect x="2.5" y="2.5" width="6.5" height="6.5" rx="1.2" />
      <rect x="11" y="2.5" width="6.5" height="4" rx="1.2" />
      <rect x="11" y="8.2" width="6.5" height="9.3" rx="1.2" />
      <rect x="2.5" y="10.7" width="6.5" height="6.8" rx="1.2" />
    </svg>
  ),
  customers: (
    <svg className="icon" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6">
      <circle cx="7" cy="6.5" r="2.8" />
      <path d="M2 17c0-2.8 2.2-4.6 5-4.6s5 1.8 5 4.6" strokeLinecap="round" />
      <circle cx="14.5" cy="6.8" r="2.1" />
      <path d="M13 12.6c2.2.2 4 1.8 4 4.4" strokeLinecap="round" />
    </svg>
  ),
  pipeline: (
    <svg className="icon" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6">
      <path d="M3 4h14l-5 6.5V16l-4 1.5v-7z" strokeLinejoin="round" />
    </svg>
  ),
  tierRequests: (
    <svg className="icon" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6">
      <path d="M10 3l2 4 4.4.6-3.2 3 .8 4.4L10 13l-4 2 .8-4.4-3.2-3L8 7z" strokeLinejoin="round" />
    </svg>
  ),
  notices: (
    <svg className="icon" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6">
      <path d="M3 9l13-5v11L3 11z" strokeLinejoin="round" />
      <path d="M6 11v3.5a1.5 1.5 0 0 0 3 0V12" strokeLinecap="round" />
    </svg>
  ),
  approvals: (
    <svg className="icon" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6">
      <path d="M4 3.5h9l3 3V17H4z" strokeLinejoin="round" />
      <path d="M7 9.5l2 2 4-4.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  ),
  shipments: (
    <svg className="icon" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6">
      <path d="M2.5 6.5L10 3l7.5 3.5L10 10z" strokeLinejoin="round" />
      <path d="M2.5 6.5V14L10 17.5V10M17.5 6.5V14L10 17.5" strokeLinejoin="round" />
    </svg>
  ),
  orderReceiving: (
    <svg className="icon" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6">
      <rect x="3" y="4" width="14" height="12.5" rx="1.4" />
      <path d="M6.5 8h7M6.5 11h7M6.5 14h4.5" strokeLinecap="round" />
      <path d="M13.5 12.5l1.5 1.5 2.5-2.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  ),
  batches: (
    <svg className="icon" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6">
      <rect x="2.5" y="5" width="6" height="6" rx="1" />
      <rect x="11.5" y="5" width="6" height="6" rx="1" />
      <rect x="7" y="11.5" width="6" height="4" rx="1" />
    </svg>
  ),
  attendance: (
    <svg className="icon" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6">
      <circle cx="10" cy="10.5" r="7" />
      <path d="M10 6.5v4l2.5 2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  ),
  profile: (
    <svg className="icon" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6">
      <circle cx="10" cy="6.8" r="3" />
      <path d="M3.5 17c0-3.3 2.9-5.5 6.5-5.5s6.5 2.2 6.5 5.5" strokeLinecap="round" />
    </svg>
  ),
  employees: (
    <svg className="icon" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6">
      <circle cx="7" cy="6" r="2.4" />
      <circle cx="14" cy="7" r="1.9" />
      <path d="M2.5 17c0-2.9 2-4.8 4.5-4.8s4.5 1.9 4.5 4.8" strokeLinecap="round" />
      <path d="M12.5 12.6c2.3.2 3.5 1.9 3.5 4.4" strokeLinecap="round" />
    </svg>
  ),
  biddingBoard: (
    <svg className="icon" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6">
      <path d="M4 16.5V9M10 16.5V4M16 16.5v-6" strokeLinecap="round" />
      <path d="M2.5 16.5h15" strokeLinecap="round" />
      <path d="M7 6.5l3-3 3 3" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  ),
};

function NavItem({ to, icon, children, end }) {
  return (
    <NavLink to={to} end={end} className={({ isActive }) => `sidebar-link${isActive ? " active" : ""}`}>
      {icon}
      {children}
    </NavLink>
  );
}

export default function Sidebar({ user }) {
  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <img src="/logo.jpg" alt="CAVI" className="mark-logo" />
        CAVI
      </div>
      <nav className="sidebar-nav">
        <NavItem to="/" end icon={ICONS.workspace}>
          Làm việc
        </NavItem>
        <NavItem to="/dashboard" icon={ICONS.dashboard}>
          Dashboard
        </NavItem>
        <NavItem to="/notices" icon={ICONS.notices}>
          Thông báo nội bộ
        </NavItem>
        <NavItem to="/approvals" icon={ICONS.approvals}>
          Ký duyệt
        </NavItem>

        <div className="sidebar-section">Kinh doanh</div>
        <NavItem to="/partners" icon={ICONS.customers}>
          Đối tác
        </NavItem>
        <NavItem to="/pipeline" icon={ICONS.pipeline}>
          Pipeline bán hàng
        </NavItem>
        <NavItem to="/tier-requests" icon={ICONS.tierRequests}>
          Yêu cầu nâng hạng
        </NavItem>

        <div className="sidebar-section">Vận hành</div>
        <NavItem to="/order-receiving" icon={ICONS.orderReceiving}>
          Chờ nhận hàng
        </NavItem>
        <NavItem to="/shipments" icon={ICONS.shipments}>
          Kiện hàng
        </NavItem>
        <NavItem to="/shipment-batches" icon={ICONS.batches}>
          Quản lý vận hành
        </NavItem>

        {(user?.is_manager || user?.is_supply) && (
          <>
            <div className="sidebar-section">Cung ứng</div>
            <NavItem to="/supply-board" icon={ICONS.biddingBoard}>
              Sàn báo giá
            </NavItem>
          </>
        )}

        {(user?.is_manager || user?.is_hr || user?.is_accountant) && (
          <>
            <div className="sidebar-section">Nhân sự</div>
            <NavItem to="/employees" icon={ICONS.employees}>
              Nhân viên
            </NavItem>
          </>
        )}

        <div className="sidebar-section">Cá nhân</div>
        <NavItem to="/attendance" icon={ICONS.attendance}>
          Chấm công
        </NavItem>
        <NavItem to="/profile" icon={ICONS.profile}>
          Hồ sơ cá nhân
        </NavItem>
      </nav>
      {user && (
        <div className="sidebar-foot">
          <div className="sidebar-user">
            <Avatar name={user.full_name} />
            <div>
              <div className="name">{user.full_name}</div>
              <div className="role">{user.role_label}</div>
            </div>
          </div>
        </div>
      )}
    </aside>
  );
}
