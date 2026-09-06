import { useEffect, useState } from "react";
import { apiFetch } from "../api";

const CURRENT_YEAR = new Date().getFullYear();

export default function Attendance() {
  const [balance, setBalance] = useState(null);
  const [records, setRecords] = useState([]);
  const [error, setError] = useState("");
  const [checkingIn, setCheckingIn] = useState(false);
  const [loading, setLoading] = useState(true);

  async function load() {
    setLoading(true);
    try {
      const [balances, attendance] = await Promise.all([
        apiFetch(`/api/hr/leave-balances/?year=${CURRENT_YEAR}`),
        apiFetch("/api/hr/attendance/"),
      ]);
      const list = balances.results ?? balances;
      setBalance(list.find((b) => b.year === CURRENT_YEAR) ?? null);
      setRecords(attendance.results ?? attendance);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  const now = new Date();
  const today = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
  const checkedInToday = records.some((r) => r.date === today);

  async function handleCheckIn() {
    setCheckingIn(true);
    try {
      await apiFetch("/api/hr/attendance/", { method: "POST", body: JSON.stringify({}) });
      load();
    } catch (err) {
      setError(err.message);
    } finally {
      setCheckingIn(false);
    }
  }

  const tiles = balance
    ? [
        { label: "Phép năm nay", value: balance.annual_current, color: "#2563eb" },
        { label: "Phép năm cũ", value: balance.annual_carried, color: "#0d9488" },
        { label: "Phép tăng thêm năm nay", value: balance.bonus_current, color: "#16a34a" },
        { label: "Phép tăng thêm năm cũ", value: balance.bonus_carried, color: "#7c3aed" },
        { label: "Phép tăng thêm chờ phân bổ", value: balance.bonus_pending, color: "#ea580c" },
      ]
    : [];

  return (
    <div>
      <div className="page-head">
        <div>
          <h1>Chấm công</h1>
          <div className="page-head-sub">Số ngày chấm công trong tháng: {records.length}</div>
        </div>
        <button onClick={handleCheckIn} disabled={checkingIn || checkedInToday}>
          {checkedInToday ? "Đã chấm công hôm nay" : checkingIn ? "Đang lưu..." : "Chấm công hôm nay"}
        </button>
      </div>

      {error && <p className="error">{error}</p>}

      <div className="panel">
        <h2>Số dư ngày phép — {CURRENT_YEAR}</h2>
        {loading ? (
          <p className="muted">Đang tải...</p>
        ) : !balance ? (
          <p className="muted">Chưa có dữ liệu ngày phép cho năm nay.</p>
        ) : (
          <div className="stat-grid">
            <div className="stat-card">
              <span className="label">Tổng có thể nghỉ</span>
              <span className="value" style={{ color: "var(--success)" }}>
                {balance.total_available}
              </span>
            </div>
            {tiles.map((t) => (
              <div className="stat-card" key={t.label} style={{ borderLeft: `3px solid ${t.color}` }}>
                <span className="label">{t.label}</span>
                <span className="value">{t.value}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="panel">
        <h2>Lịch sử chấm công</h2>
        {records.length === 0 ? (
          <p className="muted">Chưa có bản ghi chấm công nào.</p>
        ) : (
          <ul className="activity-list">
            {records.map((r) => (
              <li className="activity-item" key={r.id}>
                <span className="activity-dot contact" />
                <span className="activity-text">Chấm công ngày {r.date}</span>
                <span className="activity-time">{new Date(r.checked_in_at).toLocaleTimeString("vi-VN")}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
