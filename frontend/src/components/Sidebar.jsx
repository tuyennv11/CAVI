import { NavLink } from "react-router-dom";
import Avatar from "./Avatar";

const ICONS = {
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
};

export default function Sidebar({ user }) {
  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <span className="mark">V</span>
        Vận Tải CRM
      </div>
      <nav className="sidebar-nav">
        <NavLink to="/" end className={({ isActive }) => `sidebar-link${isActive ? " active" : ""}`}>
          {ICONS.dashboard}
          Dashboard
        </NavLink>
        <NavLink to="/partners" className={({ isActive }) => `sidebar-link${isActive ? " active" : ""}`}>
          {ICONS.customers}
          Đối tác
        </NavLink>
        <NavLink to="/pipeline" className={({ isActive }) => `sidebar-link${isActive ? " active" : ""}`}>
          {ICONS.pipeline}
          Pipeline bán hàng
        </NavLink>
        <NavLink to="/tier-requests" className={({ isActive }) => `sidebar-link${isActive ? " active" : ""}`}>
          {ICONS.tierRequests}
          Yêu cầu nâng hạng
        </NavLink>
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
