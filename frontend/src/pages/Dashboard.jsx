import { useEffect, useState } from "react";
import { apiFetch } from "../api";

function formatMoney(v) {
  return Number(v).toLocaleString("vi-VN") + " đ";
}

function timeAgo(iso) {
  const diffMs = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diffMs / 60000);
  if (mins < 1) return "vừa xong";
  if (mins < 60) return `${mins} phút trước`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours} giờ trước`;
  const days = Math.floor(hours / 24);
  return `${days} ngày trước`;
}

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    apiFetch("/api/dashboard/stats/").then(setStats).catch((err) => setError(err.message));
  }, []);

  if (error) return <p className="error">{error}</p>;
  if (!stats) return <p className="muted">Đang tải...</p>;

  return (
    <div>
      <div className="page-head">
        <div>
          <h1>Tổng quan</h1>
          <div className="page-head-sub">Số liệu cập nhật theo thời gian thực</div>
        </div>
      </div>

      <div className="stat-grid">
        <div className="stat-card">
          <span className="label">Tổng khách hàng</span>
          <span className="value">{stats.total_customers}</span>
        </div>
        <div className="stat-card">
          <span className="label">Khách mới tuần này</span>
          <span className="value">{stats.new_customers_week}</span>
          {stats.new_customers_week > 0 && <span className="delta">+{stats.new_customers_week} tuần này</span>}
        </div>
        <div className="stat-card">
          <span className="label">Đơn hàng tháng này</span>
          <span className="value">{stats.orders_this_month}</span>
        </div>
        <div className="stat-card">
          <span className="label">Doanh thu tháng này</span>
          <span className="value">{formatMoney(stats.revenue_this_month)}</span>
        </div>
      </div>

      <div className="panel">
        <h2>Hoạt động gần đây</h2>
        {stats.recent_activity.length === 0 ? (
          <p className="muted">Chưa có hoạt động nào.</p>
        ) : (
          <ul className="activity-list">
            {stats.recent_activity.map((item, i) => (
              <li className="activity-item" key={i}>
                <span className={`activity-dot ${item.type}`} />
                <span className="activity-text">{item.text}</span>
                <span className="activity-time">{timeAgo(item.at)}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
