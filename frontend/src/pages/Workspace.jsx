import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { apiFetch } from "../api";
import { useAuth } from "../AuthContext";
import Avatar from "../components/Avatar";
import StatusBadge from "../components/StatusBadge";
import {
  ACTIVITY_TYPE_LABEL,
  formatMoney,
  TASK_PRIORITY_LABEL,
} from "../constants";

function fmtDateTime(iso) {
  if (!iso) return "";
  return new Date(iso).toLocaleString("vi-VN", { dateStyle: "short", timeStyle: "short" });
}

function fmtPct(pct) {
  return pct === null || pct === undefined ? "—" : `${pct}%`;
}

function isFollowUpOverdue(followUpDate, followUpTime) {
  if (!followUpDate) return false;
  const target = new Date(`${followUpDate}T${followUpTime || "23:59:59"}`);
  return target < new Date();
}

function fmtFollowUp(followUpDate, followUpTime) {
  const d = new Date(followUpDate).toLocaleDateString("vi-VN");
  return followUpTime ? `lúc ${followUpTime.slice(0, 5)} ${d}` : d;
}

function ProgressBar({ pct }) {
  const width = pct === null || pct === undefined ? 0 : Math.min(100, Math.max(0, pct));
  const over = pct !== null && pct !== undefined && pct >= 100;
  return (
    <div className="progress-track">
      <div className={`progress-fill${over ? " over" : ""}`} style={{ width: `${width}%` }} />
    </div>
  );
}

const TASK_TABS = [
  { key: "today", label: "Hôm nay" },
  { key: "overdue", label: "Quá hạn" },
  { key: "upcoming", label: "Sắp tới" },
  { key: "done", label: "Đã hoàn thành" },
];

export default function Workspace() {
  const { user } = useAuth();
  const [today, setToday] = useState(null);
  const [kpi, setKpi] = useState(null);
  const [ranking, setRanking] = useState(null);
  const [error, setError] = useState("");

  const [taskTab, setTaskTab] = useState("today");
  const [tasks, setTasks] = useState([]);

  const [showQuickTask, setShowQuickTask] = useState(false);
  const [taskForm, setTaskForm] = useState({ title: "", due_at: "", priority: "normal", content: "" });
  const [taskError, setTaskError] = useState("");

  async function loadOverview() {
    try {
      const [t, k, r] = await Promise.all([
        apiFetch("/api/workspace/today/"),
        apiFetch("/api/workspace/kpi/"),
        apiFetch("/api/workspace/ranking/"),
      ]);
      setToday(t);
      setKpi(k);
      setRanking(r);
    } catch (err) {
      setError(err.message);
    }
  }

  async function loadTasks(tab) {
    try {
      const params = tab === "done" ? "status=done" : `due=${tab}`;
      const res = await apiFetch(`/api/tasks/?${params}`);
      setTasks(res.results ?? res);
    } catch (err) {
      setError(err.message);
    }
  }

  useEffect(() => {
    loadOverview();
  }, []);

  useEffect(() => {
    loadTasks(taskTab);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [taskTab]);

  async function completeTask(id) {
    try {
      await apiFetch(`/api/tasks/${id}/`, { method: "PATCH", body: JSON.stringify({ status: "done" }) });
      loadTasks(taskTab);
      loadOverview();
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleCreateTask(e) {
    e.preventDefault();
    setTaskError("");
    try {
      await apiFetch("/api/tasks/", {
        method: "POST",
        body: JSON.stringify({
          title: taskForm.title,
          due_at: taskForm.due_at ? new Date(taskForm.due_at).toISOString() : null,
          priority: taskForm.priority,
          content: taskForm.content,
        }),
      });
      setTaskForm({ title: "", due_at: "", priority: "normal", content: "" });
      setShowQuickTask(false);
      loadTasks(taskTab);
      loadOverview();
    } catch (err) {
      setTaskError(err.message);
    }
  }

  if (error) return <p className="error">{error}</p>;
  if (!today || !kpi || !ranking) return <p className="muted">Đang tải...</p>;

  const actionItems = [
    ...today.tasks_overdue.map((t) => ({
      key: `task-${t.id}`,
      urgent: true,
      icon: "⏰",
      text: `Việc quá hạn: ${t.title}`,
      sub: t.partner_name ? `Khách hàng: ${t.partner_name}` : null,
      at: t.due_at,
    })),
    ...today.follow_ups_due.map((a) => ({
      key: `fu-${a.id}`,
      urgent: isFollowUpOverdue(a.follow_up_date, a.follow_up_time),
      icon: "🔔",
      text: `Nhắc hẹn: ${a.title}`,
      sub: a.customer_name,
      link: a.customer ? `/partners/${a.customer}` : null,
      at: a.follow_up_date,
      atText: fmtFollowUp(a.follow_up_date, a.follow_up_time),
    })),
    ...today.open_requests.map((a) => ({
      key: `req-${a.id}`,
      urgent: true,
      icon: "🆘",
      text: `${ACTIVITY_TYPE_LABEL[a.activity_type]}: ${a.title}`,
      sub: a.customer_name,
      link: a.customer ? `/partners/${a.customer}` : null,
      at: a.activity_at,
    })),
    ...today.tasks_today.map((t) => ({
      key: `task-today-${t.id}`,
      urgent: false,
      icon: "✅",
      text: `Việc hôm nay: ${t.title}`,
      sub: t.partner_name ? `Khách hàng: ${t.partner_name}` : null,
      at: t.due_at,
    })),
  ];

  const myRankRow = ranking.ranking.find((r) => r.user_id === user?.id);

  return (
    <div className="workspace">
      <div className="page-head">
        <div>
          <h1>Chào {user?.full_name}</h1>
          <div className="page-head-sub">
            {new Date().toLocaleDateString("vi-VN", { weekday: "long", day: "2-digit", month: "2-digit", year: "numeric" })}
          </div>
        </div>
        <button onClick={() => setShowQuickTask((v) => !v)}>{showQuickTask ? "Đóng" : "+ Tạo công việc"}</button>
      </div>

      {showQuickTask && (
        <form className="field-grid inline-add-activity" onSubmit={handleCreateTask}>
          <label>
            Tên công việc *
            <input
              required
              autoFocus
              placeholder="VD: Gọi lại khách ABC báo giá"
              value={taskForm.title}
              onChange={(e) => setTaskForm((f) => ({ ...f, title: e.target.value }))}
            />
          </label>
          <div className="order-item-row" style={{ gridTemplateColumns: "1fr 1fr" }}>
            <label>
              Hạn hoàn thành
              <input
                type="datetime-local"
                value={taskForm.due_at}
                onChange={(e) => setTaskForm((f) => ({ ...f, due_at: e.target.value }))}
              />
            </label>
            <label>
              Mức độ ưu tiên
              <select
                value={taskForm.priority}
                onChange={(e) => setTaskForm((f) => ({ ...f, priority: e.target.value }))}
              >
                {Object.entries(TASK_PRIORITY_LABEL).map(([v, l]) => (
                  <option key={v} value={v}>
                    {l}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <label>
            Nội dung
            <textarea
              rows={2}
              value={taskForm.content}
              onChange={(e) => setTaskForm((f) => ({ ...f, content: e.target.value }))}
            />
          </label>
          {taskError && <p className="error">{taskError}</p>}
          <div className="modal-actions">
            <button type="button" className="secondary" onClick={() => setShowQuickTask(false)}>
              Huỷ
            </button>
            <button type="submit">Lưu công việc</button>
          </div>
        </form>
      )}

      <div className="panel action-center">
        <h2>⚡ Việc cần chú ý</h2>
        {actionItems.length === 0 ? (
          <p className="muted">Không có việc gì cần chú ý ngay — làm tốt lắm!</p>
        ) : (
          <ul className="action-list">
            {actionItems.map((item) => (
              <li key={item.key} className={`action-item${item.urgent ? " urgent" : ""}`}>
                <span className="action-icon">{item.icon}</span>
                <span className="action-text">
                  {item.link ? <Link to={item.link}>{item.text}</Link> : item.text}
                  {item.sub && <span className="muted"> — {item.sub}</span>}
                </span>
                {item.at && <span className="action-time">{item.atText ?? fmtDateTime(item.at)}</span>}
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="workspace-grid">
        <div className="panel">
          <h2>Công việc</h2>
          <div className="tabs">
            {TASK_TABS.map((t) => (
              <button
                key={t.key}
                className={`tab-btn${taskTab === t.key ? " active" : ""}`}
                onClick={() => setTaskTab(t.key)}
              >
                {t.label}
              </button>
            ))}
          </div>
          {tasks.length === 0 ? (
            <p className="muted">Không có công việc nào.</p>
          ) : (
            <ul className="task-list">
              {tasks.map((t) => (
                <li key={t.id} className="task-row">
                  <div className="task-main">
                    <span className={`priority-dot priority-${t.priority}`} title={TASK_PRIORITY_LABEL[t.priority]} />
                    <div>
                      <div className="task-title">{t.title}</div>
                      <div className="task-meta">
                        {t.partner_name && <span>{t.partner_name} · </span>}
                        {t.due_at && <span>{fmtDateTime(t.due_at)}</span>}
                      </div>
                    </div>
                  </div>
                  <div className="task-actions">
                    <StatusBadge status={t.status} />
                    {t.status !== "done" && t.status !== "cancelled" && (
                      <button className="link-btn" onClick={() => completeTask(t.id)}>
                        Hoàn thành
                      </button>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="panel">
          <h2>Lịch hẹn & cuộc gọi hôm nay</h2>
          {today.appointments_today.length === 0 && today.calls_to_make.length === 0 ? (
            <p className="muted">Không có lịch hẹn hay cuộc gọi nào hôm nay.</p>
          ) : (
            <ul className="task-list">
              {today.appointments_today.map((a) => (
                <li key={`appt-${a.id}`} className="task-row">
                  <div className="task-main">
                    <span>🤝</span>
                    <div>
                      <div className="task-title">{a.title}</div>
                      <div className="task-meta">{fmtDateTime(a.activity_at)}</div>
                    </div>
                  </div>
                </li>
              ))}
              {today.calls_to_make.map((a) => (
                <li key={`call-${a.id}`} className="task-row">
                  <div className="task-main">
                    <span>📞</span>
                    <div>
                      <div className="task-title">{a.title}</div>
                      <div className="task-meta">{a.contact_person || "—"}</div>
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      <div className="panel">
        <h2>KPI tháng {new Date().getMonth() + 1}/{new Date().getFullYear()}</h2>
        {!kpi.kpi ? (
          <p className="muted">Chưa thiết lập chỉ tiêu KPI cho tháng này.</p>
        ) : (
          <div className="kpi-grid">
            <div className="kpi-row">
              <span className="kpi-label">Doanh thu</span>
              <ProgressBar pct={kpi.kpi.revenue.pct} />
              <span className="kpi-value">
                {formatMoney(kpi.kpi.revenue.actual)} / {formatMoney(kpi.kpi.revenue.target)} · {fmtPct(kpi.kpi.revenue.pct)}
              </span>
            </div>
            <div className="kpi-row">
              <span className="kpi-label">Khách hàng mới</span>
              <ProgressBar pct={kpi.kpi.new_customers.pct} />
              <span className="kpi-value">
                {kpi.kpi.new_customers.actual} / {kpi.kpi.new_customers.target} · {fmtPct(kpi.kpi.new_customers.pct)}
              </span>
            </div>
            <div className="kpi-row">
              <span className="kpi-label">Báo giá</span>
              <ProgressBar pct={kpi.kpi.quotes.pct} />
              <span className="kpi-value">
                {kpi.kpi.quotes.actual} / {kpi.kpi.quotes.target} · {fmtPct(kpi.kpi.quotes.pct)}
              </span>
            </div>
            <div className="kpi-row">
              <span className="kpi-label">Phiếu nhận hàng</span>
              <ProgressBar pct={kpi.kpi.orders.pct} />
              <span className="kpi-value">
                {kpi.kpi.orders.actual} / {kpi.kpi.orders.target} · {fmtPct(kpi.kpi.orders.pct)}
              </span>
            </div>
            <div className="kpi-row">
              <span className="kpi-label">Công việc</span>
              <ProgressBar pct={kpi.kpi.tasks.pct} />
              <span className="kpi-value">
                {kpi.kpi.tasks.actual} / {kpi.kpi.tasks.target} · {fmtPct(kpi.kpi.tasks.pct)}
              </span>
            </div>
          </div>
        )}
      </div>

      <div className="workspace-grid">
        <div className="panel">
          <h2>Doanh thu</h2>
          <div className="stat-grid" style={{ marginBottom: 0 }}>
            <div className="stat-card">
              <span className="label">Hôm nay</span>
              <span className="value" style={{ fontSize: 18 }}>{formatMoney(kpi.revenue.today)}</span>
            </div>
            <div className="stat-card">
              <span className="label">Tháng này</span>
              <span className="value" style={{ fontSize: 18 }}>{formatMoney(kpi.revenue.month)}</span>
              {kpi.revenue.vs_last_month_pct !== null && (
                <span className={`delta${kpi.revenue.vs_last_month_pct < 0 ? " down" : ""}`}>
                  {kpi.revenue.vs_last_month_pct >= 0 ? "+" : ""}
                  {kpi.revenue.vs_last_month_pct}% so với tháng trước
                </span>
              )}
            </div>
            <div className="stat-card">
              <span className="label">Quý này</span>
              <span className="value" style={{ fontSize: 18 }}>{formatMoney(kpi.revenue.quarter)}</span>
            </div>
            <div className="stat-card">
              <span className="label">Năm nay</span>
              <span className="value" style={{ fontSize: 18 }}>{formatMoney(kpi.revenue.year)}</span>
            </div>
          </div>
        </div>

        <div className="panel">
          <h2>Hiệu suất cá nhân</h2>
          <div className="performance-score">
            <span className="performance-pct">{fmtPct(kpi.performance.overall_pct)}</span>
            <span className="muted">hiệu suất tháng này</span>
          </div>
          <ul className="performance-breakdown">
            {kpi.performance.task_ontime_pct !== null && (
              <li>
                <span>Công việc đúng hạn</span> <b>{fmtPct(kpi.performance.task_ontime_pct)}</b>
              </li>
            )}
            {kpi.performance.followup_pct !== null && (
              <li>
                <span>Follow-up hoàn thành</span> <b>{fmtPct(kpi.performance.followup_pct)}</b>
              </li>
            )}
          </ul>
          {myRankRow && (
            <p className="muted" style={{ marginTop: 10 }}>
              Bạn đang đứng thứ <b>#{myRankRow.rank}</b> / {ranking.total} nhân viên kinh doanh.
            </p>
          )}
        </div>
      </div>

      {ranking.ranking.length > 0 && (
        <div className="panel">
          <h2>🏆 Bảng xếp hạng kinh doanh — tháng {new Date().getMonth() + 1}/{new Date().getFullYear()}</h2>
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Hạng</th>
                  <th>Nhân viên</th>
                  <th>KPI</th>
                  <th>Doanh thu</th>
                  <th>Công việc hoàn thành</th>
                  <th>Khách hàng mới</th>
                </tr>
              </thead>
              <tbody>
                {ranking.ranking.map((r) => (
                  <tr key={r.user_id} className={r.user_id === user?.id ? "clickable" : ""}>
                    <td>
                      {r.rank === 1 ? "🥇" : r.rank === 2 ? "🥈" : r.rank === 3 ? "🥉" : `#${r.rank}`}
                    </td>
                    <td>
                      <div className="row-name">
                        <Avatar name={r.name} />
                        {r.name}
                      </div>
                    </td>
                    <td>{fmtPct(r.kpi_pct)}</td>
                    <td>{formatMoney(r.revenue)}</td>
                    <td>{r.tasks_done}</td>
                    <td>{r.new_customers}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {today.notices.length > 0 && (
        <div className="panel">
          <h2>📣 Thông báo mới</h2>
          <ul className="task-list">
            {today.notices.map((n) => (
              <li key={n.id} className="task-row">
                <div className="task-main">
                  <div>
                    <div className="task-title">{n.title}</div>
                    <div className="task-meta">{fmtDateTime(n.created_at)}</div>
                  </div>
                </div>
              </li>
            ))}
          </ul>
          <p style={{ marginTop: 10 }}>
            <Link to="/notices">Xem tất cả thông báo &rarr;</Link>
          </p>
        </div>
      )}
    </div>
  );
}
