import { useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { apiFetch, apiUpload, API_URL } from "../api";
import { useAuth } from "../AuthContext";
import Avatar from "../components/Avatar";
import Modal from "../components/Modal";
import StatusBadge from "../components/StatusBadge";
import {
  ACTIVITY_RESULT_OPTIONS,
  ACTIVITY_STATUS_LABEL,
  ACTIVITY_TYPE_CATEGORY,
  ACTIVITY_TYPE_GROUPS,
  ACTIVITY_TYPE_LABEL,
  formatMoney,
  PARTNER_TYPE_LABEL,
  QUICK_ACTIVITY_TYPES,
  TIER_LABEL,
} from "../constants";

function timeAgo(iso) {
  const diffMs = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diffMs / 60000);
  if (mins < 1) return "vừa xong";
  if (mins < 60) return `${mins} phút trước`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours} giờ trước`;
  return new Date(iso).toLocaleDateString("vi-VN");
}

function formatDateTime(iso) {
  if (!iso) return "";
  return new Date(iso).toLocaleString("vi-VN", { dateStyle: "short", timeStyle: "short" });
}

function toLocalInputValue(date) {
  const pad = (n) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(
    date.getMinutes()
  )}`;
}

function addDaysStr(n) {
  const d = new Date();
  d.setDate(d.getDate() + n);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

const FOLLOW_UP_PRESETS = [
  { label: "Ngày mai", days: 1 },
  { label: "3 ngày tới", days: 3 },
  { label: "Tuần sau", days: 7 },
  { label: "2 tuần tới", days: 14 },
];

// Hẹn có giờ cụ thể (vd "15h gọi lại") thì quá hạn tính đúng theo giờ đó; hẹn chỉ có ngày
// (vd "thứ 4 tuần sau") thì coi như còn hạn tới hết ngày hôm đó.
function isFollowUpOverdue(followUpDate, followUpTime) {
  if (!followUpDate) return false;
  const target = new Date(`${followUpDate}T${followUpTime || "23:59:59"}`);
  return target < new Date();
}

function formatFollowUp(followUpDate, followUpTime) {
  const d = new Date(followUpDate).toLocaleDateString("vi-VN");
  return followUpTime ? `${d} lúc ${followUpTime.slice(0, 5)}` : d;
}

const EMPTY_ITEM = { description: "", quantity: 1, unit_price: 0, unit_cost: 0 };
const TIER_ORDER = ["standard", "vip", "super_vip"];

const EMPTY_FILTERS = {
  activity_type: "",
  assigned_to: "",
  performed_by: "",
  status: "",
  has_follow_up: "",
  date_from: "",
  date_to: "",
  search: "",
};

function emptyActivityForm(currentUserId, activityType = "call") {
  return {
    activity_type: activityType,
    activity_at: toLocalInputValue(new Date()),
    performed_by: currentUserId ?? "",
    content: "",
    result: "",
    follow_up_date: "",
    follow_up_time: "",
    attachment: null,
  };
}

export default function PartnerDetail() {
  const { id } = useParams();
  const { user: currentUser } = useAuth();
  const [partner, setPartner] = useState(null);
  const [orders, setOrders] = useState([]);
  const [tierRequests, setTierRequests] = useState([]);
  const [users, setUsers] = useState([]);
  const [error, setError] = useState("");
  const [tab, setTab] = useState("activity");
  const [showNewOrder, setShowNewOrder] = useState(false);
  const [items, setItems] = useState([{ ...EMPTY_ITEM }]);
  const [paid, setPaid] = useState(false);
  const [onPlatform, setOnPlatform] = useState(false);
  const [showTierRequest, setShowTierRequest] = useState(false);
  const [requestedTier, setRequestedTier] = useState("vip");
  const [requestReason, setRequestReason] = useState("");

  const [activities, setActivities] = useState([]);
  const [summary, setSummary] = useState(null);
  const [filters, setFilters] = useState(EMPTY_FILTERS);
  const [showAddActivity, setShowAddActivity] = useState(false);
  const [activityForm, setActivityForm] = useState(emptyActivityForm());
  const [activityError, setActivityError] = useState("");
  const activityContentRef = useRef(null);

  async function loadAll() {
    try {
      const [p, orderList, requestList, userList] = await Promise.all([
        apiFetch(`/api/partners/${id}/`),
        apiFetch(`/api/orders/?customer=${id}`),
        apiFetch(`/api/tier-requests/?partner=${id}`),
        apiFetch(`/api/users/`),
      ]);
      setPartner(p);
      setOrders(orderList.results ?? orderList);
      setTierRequests(requestList.results ?? requestList);
      setUsers(userList);
    } catch (err) {
      setError(err.message);
    }
  }

  async function loadActivities() {
    try {
      const params = new URLSearchParams();
      Object.entries(filters).forEach(([k, v]) => {
        if (v) params.set(k, v);
      });
      const qs = params.toString();
      const [list, sum] = await Promise.all([
        apiFetch(`/api/partners/${id}/activities/${qs ? `?${qs}` : ""}`),
        apiFetch(`/api/partners/${id}/activities/summary/`),
      ]);
      setActivities(list);
      setSummary(sum);
    } catch (err) {
      setError(err.message);
    }
  }

  async function markFollowUpDone(activityId) {
    try {
      await apiFetch(`/api/activities/${activityId}/`, {
        method: "PATCH",
        body: JSON.stringify({ follow_up_done: true }),
      });
      loadActivities();
    } catch (err) {
      setError(err.message);
    }
  }

  useEffect(() => {
    loadAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  useEffect(() => {
    loadActivities();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id, filters]);

  function updateFilter(field, value) {
    setFilters((prev) => ({ ...prev, [field]: value }));
  }

  function openAddActivity(activityType = "call") {
    if (showAddActivity && activityForm.activity_type === activityType) {
      setShowAddActivity(false);
      return;
    }
    setActivityForm(emptyActivityForm(currentUser?.id, activityType));
    setActivityError("");
    setShowAddActivity(true);
    setTimeout(() => activityContentRef.current?.focus(), 50);
  }

  function updateActivityField(field, value) {
    setActivityForm((prev) => ({ ...prev, [field]: value }));
  }

  async function handleAddActivity(e) {
    e.preventDefault();
    setActivityError("");
    try {
      const fd = new FormData();
      fd.set("activity_type", activityForm.activity_type);
      if (activityForm.activity_at) fd.set("activity_at", new Date(activityForm.activity_at).toISOString());
      if (activityForm.performed_by) fd.set("performed_by", activityForm.performed_by);
      if (activityForm.content) fd.set("content", activityForm.content);
      if (activityForm.result) fd.set("result", activityForm.result);
      if (activityForm.follow_up_date) fd.set("follow_up_date", activityForm.follow_up_date);
      if (activityForm.follow_up_date && activityForm.follow_up_time) {
        fd.set("follow_up_time", activityForm.follow_up_time);
      }
      if (activityForm.attachment) fd.set("attachment", activityForm.attachment);

      await apiUpload(`/api/partners/${id}/activities/`, fd);
      setShowAddActivity(false);
      loadActivities();
    } catch (err) {
      setActivityError(err.message);
    }
  }

  function updateItem(index, field, value) {
    setItems((prev) => prev.map((it, i) => (i === index ? { ...it, [field]: value } : it)));
  }

  async function handleCreateOrder(e) {
    e.preventDefault();
    try {
      await apiFetch("/api/orders/", {
        method: "POST",
        body: JSON.stringify({ customer: Number(id), status: "new", items, paid, on_platform: onPlatform }),
      });
      setItems([{ ...EMPTY_ITEM }]);
      setPaid(false);
      setOnPlatform(false);
      setShowNewOrder(false);
      setTab("orders");
      loadAll();
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleRequestTier(e) {
    e.preventDefault();
    try {
      await apiFetch("/api/tier-requests/", {
        method: "POST",
        body: JSON.stringify({ partner: Number(id), requested_tier: requestedTier, reason: requestReason }),
      });
      setShowTierRequest(false);
      setRequestReason("");
      loadAll();
    } catch (err) {
      setError(err.message);
    }
  }

  if (error) return <p className="error">{error}</p>;
  if (!partner) return <p className="muted">Đang tải...</p>;

  const overLimit = Number(partner.debt) > Number(partner.credit_limit);
  const debtRatio = partner.credit_limit > 0 ? Math.min(100, (partner.debt / partner.credit_limit) * 100) : 0;
  const pendingRequest = tierRequests.find((r) => r.status === "pending");
  const higherTiers = TIER_ORDER.slice(TIER_ORDER.indexOf(partner.tier) + 1);

  return (
    <div>
      <p style={{ marginBottom: 16 }}>
        <Link to="/partners">&larr; Danh sách đối tác</Link>
      </p>

      <div className="profile-header">
        <Avatar name={partner.name} size="lg" />
        <div style={{ flex: 1 }}>
          <h1>{partner.name}</h1>
          {partner.note && <div className="company">{partner.note}</div>}
          <div className="profile-pills">
            <span className="badge badge-neutral">{PARTNER_TYPE_LABEL[partner.partner_type]}</span>
            <span className={`badge badge-tier-${partner.tier}`}>
              {TIER_LABEL[partner.tier]}
              {partner.tier_source === "approved" ? " · đã duyệt" : " · tự động"}
            </span>
            {partner.contact_person && <span className="profile-pill">👤 {partner.contact_person}</span>}
            {partner.phone && <span className="profile-pill">📞 {partner.phone}</span>}
            {partner.assigned_to_detail && (
              <span className="profile-pill">Phụ trách: {partner.assigned_to_detail.username}</span>
            )}
          </div>
          <div className="profile-pills" style={{ marginTop: 6 }}>
            <span className="muted" style={{ fontSize: 12 }}>
              Gắn bó {partner.tenure_months} tháng · Doanh thu tích luỹ {formatMoney(partner.total_revenue)}
            </span>
          </div>

          {higherTiers.length > 0 && (
            <div style={{ marginTop: 10 }}>
              {pendingRequest ? (
                <span className="muted" style={{ fontSize: 12.5 }}>
                  Đang chờ duyệt lên <b>{TIER_LABEL[pendingRequest.requested_tier]}</b>
                </span>
              ) : (
                <button
                  className="secondary"
                  onClick={() => {
                    setRequestedTier(higherTiers[0]);
                    setShowTierRequest(true);
                  }}
                >
                  Xin nâng hạng
                </button>
              )}
            </div>
          )}

          {partner.partner_type !== "supplier" && (
            <div style={{ marginTop: 16 }}>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12.5 }}>
                <span className={overLimit ? "error" : "muted"}>
                  Công nợ: <b>{formatMoney(partner.debt)}</b>
                </span>
                <span className="muted">Hạn mức: {formatMoney(partner.credit_limit)}</span>
              </div>
              <div style={{ background: "var(--surface-muted)", borderRadius: 999, height: 6, marginTop: 6 }}>
                <div
                  style={{
                    width: `${debtRatio}%`,
                    background: overLimit ? "var(--danger)" : "var(--primary)",
                    height: "100%",
                    borderRadius: 999,
                  }}
                />
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="tabs">
        <button className={`tab-btn${tab === "activity" ? " active" : ""}`} onClick={() => setTab("activity")}>
          Hoạt động
        </button>
        <button className={`tab-btn${tab === "orders" ? " active" : ""}`} onClick={() => setTab("orders")}>
          Đơn hàng ({orders.length})
        </button>
      </div>

      {tab === "activity" && (
        <div>
          {summary && (
            <div className="stat-grid" style={{ marginBottom: 20 }}>
              <div className="stat-card">
                <span className="label">Tổng số hoạt động</span>
                <span className="value">{summary.total_activities}</span>
              </div>
              <div className="stat-card">
                <span className="label">Hoạt động gần nhất</span>
                <span className="value" style={{ fontSize: 16 }}>
                  {summary.last_activity_at ? timeAgo(summary.last_activity_at) : "—"}
                </span>
              </div>
              <div className="stat-card">
                <span className="label">Follow-up sắp tới</span>
                <span className="value">{summary.upcoming_follow_ups}</span>
              </div>
              <div className="stat-card">
                <span className="label">Công việc chưa hoàn thành</span>
                <span className="value">{summary.unfinished_tasks}</span>
              </div>
            </div>
          )}

          <div className="panel">
            <div className="page-head" style={{ marginBottom: 14 }}>
              <h2 style={{ margin: 0 }}>Timeline</h2>
            </div>

            <div className="quick-actions">
              {QUICK_ACTIVITY_TYPES.map((t) => (
                <button
                  key={t.value}
                  type="button"
                  className={`quick-action-btn${showAddActivity && activityForm.activity_type === t.value ? " active" : ""}`}
                  onClick={() => openAddActivity(t.value)}
                >
                  <span>{t.icon}</span> {t.label}
                </button>
              ))}
              <button
                type="button"
                className={`quick-action-btn${
                  showAddActivity && !QUICK_ACTIVITY_TYPES.some((t) => t.value === activityForm.activity_type)
                    ? " active"
                    : ""
                }`}
                onClick={() => openAddActivity("opportunity")}
              >
                <span>➕</span> Khác...
              </button>
            </div>

            {showAddActivity && (
              <form className="field-grid inline-add-activity" onSubmit={handleAddActivity}>
                {!QUICK_ACTIVITY_TYPES.some((t) => t.value === activityForm.activity_type) && (
                  <label>
                    Loại hoạt động *
                    <select
                      value={activityForm.activity_type}
                      onChange={(e) => updateActivityField("activity_type", e.target.value)}
                    >
                      {ACTIVITY_TYPE_GROUPS.map((g) => (
                        <optgroup label={g.label} key={g.label}>
                          {g.options.map((o) => (
                            <option key={o.value} value={o.value}>
                              {o.label}
                            </option>
                          ))}
                        </optgroup>
                      ))}
                    </select>
                  </label>
                )}
                <div className="order-item-row" style={{ gridTemplateColumns: "1fr 1fr" }}>
                  <label>
                    Ngày giờ *
                    <input
                      type="datetime-local"
                      required
                      value={activityForm.activity_at}
                      onChange={(e) => updateActivityField("activity_at", e.target.value)}
                    />
                  </label>
                  <label>
                    Người thực hiện
                    <select
                      value={activityForm.performed_by}
                      onChange={(e) => updateActivityField("performed_by", e.target.value)}
                    >
                      <option value="">— Tôi —</option>
                      {users.map((u) => (
                        <option key={u.id} value={u.id}>
                          {u.full_name}
                        </option>
                      ))}
                    </select>
                  </label>
                </div>
                <label>
                  Nội dung *
                  <textarea
                    ref={activityContentRef}
                    required
                    rows={3}
                    placeholder="VD: Đã gọi điện cho anh Nam, trao đổi về..."
                    value={activityForm.content}
                    onChange={(e) => updateActivityField("content", e.target.value)}
                  />
                </label>
                <label>
                  Kết quả
                  <select value={activityForm.result} onChange={(e) => updateActivityField("result", e.target.value)}>
                    <option value="">— Chưa đánh giá —</option>
                    {ACTIVITY_RESULT_OPTIONS.map((r) => (
                      <option key={r} value={r}>
                        {r}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  🔔 Hẹn nhắc lại
                  <div className="followup-picker">
                    {FOLLOW_UP_PRESETS.map((p) => (
                      <button
                        key={p.label}
                        type="button"
                        className={`followup-preset-btn${
                          activityForm.follow_up_date === addDaysStr(p.days) ? " active" : ""
                        }`}
                        onClick={() => updateActivityField("follow_up_date", addDaysStr(p.days))}
                      >
                        {p.label}
                      </button>
                    ))}
                    <input
                      type="date"
                      value={activityForm.follow_up_date}
                      onChange={(e) => updateActivityField("follow_up_date", e.target.value)}
                    />
                    {activityForm.follow_up_date && (
                      <>
                        <input
                          type="time"
                          title="Giờ cụ thể (vd khách hẹn 15h gọi lại) — để trống nếu chỉ hẹn ngày"
                          value={activityForm.follow_up_time}
                          onChange={(e) => updateActivityField("follow_up_time", e.target.value)}
                        />
                        <button
                          type="button"
                          className="link-btn"
                          onClick={() => {
                            updateActivityField("follow_up_date", "");
                            updateActivityField("follow_up_time", "");
                          }}
                        >
                          Bỏ hẹn
                        </button>
                      </>
                    )}
                  </div>
                </label>
                <label>
                  File đính kèm
                  <input
                    type="file"
                    onChange={(e) => updateActivityField("attachment", e.target.files[0] ?? null)}
                  />
                </label>
                {activityError && <p className="error">{activityError}</p>}
                <div className="modal-actions">
                  <button type="button" className="secondary" onClick={() => setShowAddActivity(false)}>
                    Huỷ
                  </button>
                  <button type="submit">Lưu hoạt động</button>
                </div>
              </form>
            )}

            <div className="filter-bar">
              <input
                className="search-input"
                placeholder="Tìm theo tiêu đề/nội dung..."
                value={filters.search}
                onChange={(e) => updateFilter("search", e.target.value)}
              />
              <select value={filters.activity_type} onChange={(e) => updateFilter("activity_type", e.target.value)}>
                <option value="">Mọi loại hoạt động</option>
                {ACTIVITY_TYPE_GROUPS.map((g) => (
                  <optgroup label={g.label} key={g.label}>
                    {g.options.map((o) => (
                      <option key={o.value} value={o.value}>
                        {o.label}
                      </option>
                    ))}
                  </optgroup>
                ))}
              </select>
              <select value={filters.status} onChange={(e) => updateFilter("status", e.target.value)}>
                <option value="">Mọi trạng thái</option>
                {Object.entries(ACTIVITY_STATUS_LABEL).map(([v, l]) => (
                  <option key={v} value={v}>
                    {l}
                  </option>
                ))}
              </select>
              <select value={filters.assigned_to} onChange={(e) => updateFilter("assigned_to", e.target.value)}>
                <option value="">Mọi người phụ trách</option>
                {users.map((u) => (
                  <option key={u.id} value={u.id}>
                    {u.full_name}
                  </option>
                ))}
              </select>
              <select value={filters.performed_by} onChange={(e) => updateFilter("performed_by", e.target.value)}>
                <option value="">Mọi người thực hiện</option>
                {users.map((u) => (
                  <option key={u.id} value={u.id}>
                    {u.full_name}
                  </option>
                ))}
              </select>
              <select
                value={filters.has_follow_up}
                onChange={(e) => updateFilter("has_follow_up", e.target.value)}
              >
                <option value="">Follow-up: tất cả</option>
                <option value="true">Có follow-up</option>
                <option value="false">Không follow-up</option>
              </select>
              <input
                type="date"
                title="Từ ngày"
                value={filters.date_from}
                onChange={(e) => updateFilter("date_from", e.target.value)}
              />
              <input
                type="date"
                title="Đến ngày"
                value={filters.date_to}
                onChange={(e) => updateFilter("date_to", e.target.value)}
              />
              {Object.values(filters).some(Boolean) && (
                <button type="button" className="link-btn" onClick={() => setFilters(EMPTY_FILTERS)}>
                  Xoá bộ lọc
                </button>
              )}
            </div>

            {activities.length === 0 ? (
              <p className="muted">Chưa có hoạt động nào.</p>
            ) : (
              <ul className="timeline">
                {activities.map((a) => {
                  const category = ACTIVITY_TYPE_CATEGORY[a.activity_type] ?? "interaction";
                  const overdue = !a.follow_up_done && isFollowUpOverdue(a.follow_up_date, a.follow_up_time);
                  return (
                    <li className="timeline-item" key={a.id}>
                      <div className="timeline-marker">
                        <span className={`timeline-dot cat-${category}`} />
                      </div>
                      <div className="timeline-body">
                        <div className="timeline-head">
                          <span className="timeline-type">{ACTIVITY_TYPE_LABEL[a.activity_type]}</span>
                          <span className="timeline-title">{a.title}</span>
                          <span className="timeline-time">{formatDateTime(a.activity_at)}</span>
                        </div>
                        <div className="timeline-meta">
                          {a.performed_by_name && <span>Thực hiện: {a.performed_by_name}</span>}
                          {a.assigned_to_name && a.assigned_to_name !== a.performed_by_name && (
                            <span>Phụ trách: {a.assigned_to_name}</span>
                          )}
                          {a.contact_person && <span>Liên hệ: {a.contact_person}</span>}
                        </div>
                        {a.content && <div className="timeline-content">{a.content}</div>}
                        {a.result && (
                          <div className="timeline-result">
                            Kết quả: <b>{a.result}</b>
                          </div>
                        )}
                        <div className="timeline-tags">
                          <StatusBadge status={a.status} />
                          {a.follow_up_date && (
                            <span
                              className={`timeline-followup${overdue ? " overdue" : ""}${
                                a.follow_up_done ? " done" : ""
                              }`}
                            >
                              🔔 Follow-up {formatFollowUp(a.follow_up_date, a.follow_up_time)}
                              {overdue ? " (quá hạn)" : ""}
                              {a.follow_up_done ? " ✓ đã nhắc" : ""}
                            </span>
                          )}
                          {a.follow_up_date && !a.follow_up_done && (
                            <button
                              type="button"
                              className="link-btn timeline-link"
                              onClick={() => markFollowUpDone(a.id)}
                            >
                              Đánh dấu đã nhắc
                            </button>
                          )}
                          {a.related_order_label && (
                            <button type="button" className="link-btn timeline-link" onClick={() => setTab("orders")}>
                              {a.related_order_label}
                            </button>
                          )}
                          {a.related_reference && <span className="badge badge-neutral">{a.related_reference}</span>}
                          {a.attachment && (
                            <a
                              className="timeline-link"
                              href={`${API_URL}${a.attachment}`}
                              target="_blank"
                              rel="noreferrer"
                            >
                              📎 Tệp đính kèm
                            </a>
                          )}
                        </div>
                        {a.note && <div className="timeline-note">Ghi chú: {a.note}</div>}
                      </div>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
        </div>
      )}

      {tab === "orders" && (
        <div className="panel">
          <div className="page-head" style={{ marginBottom: 14 }}>
            <h2 style={{ margin: 0 }}>Danh sách đơn hàng</h2>
            <button onClick={() => setShowNewOrder((v) => !v)}>{showNewOrder ? "Đóng" : "+ Tạo đơn hàng"}</button>
          </div>

          {showNewOrder && (
            <form className="field-grid" onSubmit={handleCreateOrder} style={{ marginBottom: 18 }}>
              {items.map((it, i) => (
                <div className="order-item-row" style={{ gridTemplateColumns: "1fr 70px 110px 110px" }} key={i}>
                  <input
                    placeholder="Mô tả hàng/dịch vụ"
                    value={it.description}
                    onChange={(e) => updateItem(i, "description", e.target.value)}
                    required
                  />
                  <input
                    type="number"
                    min="0"
                    step="0.01"
                    placeholder="SL"
                    value={it.quantity}
                    onChange={(e) => updateItem(i, "quantity", e.target.value)}
                  />
                  <input
                    type="number"
                    min="0"
                    step="0.01"
                    placeholder="Giá bán"
                    value={it.unit_price}
                    onChange={(e) => updateItem(i, "unit_price", e.target.value)}
                  />
                  <input
                    type="number"
                    min="0"
                    step="0.01"
                    placeholder="Giá vốn"
                    value={it.unit_cost}
                    onChange={(e) => updateItem(i, "unit_cost", e.target.value)}
                  />
                </div>
              ))}
              <button type="button" className="link-btn" onClick={() => setItems([...items, { ...EMPTY_ITEM }])}>
                + Thêm dòng
              </button>
              <div style={{ display: "flex", gap: 20 }}>
                <label style={{ flexDirection: "row", alignItems: "center", gap: 6 }}>
                  <input type="checkbox" checked={paid} onChange={(e) => setPaid(e.target.checked)} /> Đã thanh toán
                </label>
                <label style={{ flexDirection: "row", alignItems: "center", gap: 6 }}>
                  <input
                    type="checkbox"
                    checked={onPlatform}
                    onChange={(e) => setOnPlatform(e.target.checked)}
                  />{" "}
                  Qua sàn
                </label>
              </div>
              <div className="modal-actions">
                <button type="submit">Lưu đơn hàng</button>
              </div>
            </form>
          )}

          {orders.length === 0 ? (
            <p className="muted">Chưa có đơn hàng.</p>
          ) : (
            <div className="table-wrap">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Đơn hàng</th>
                    <th>Trạng thái</th>
                    <th>Thanh toán</th>
                    <th>Doanh thu</th>
                    <th>Lợi nhuận gộp</th>
                  </tr>
                </thead>
                <tbody>
                  {orders.map((o) => (
                    <tr key={o.id}>
                      <td>#{o.id}</td>
                      <td>
                        <StatusBadge status={o.status} />
                      </td>
                      <td>
                        <span className={`badge ${o.paid ? "badge-done" : "badge-processing"}`}>
                          {o.paid ? "Đã trả" : "Chưa trả"}
                        </span>
                      </td>
                      <td>{formatMoney(o.total)}</td>
                      <td>{formatMoney(o.gross_profit)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {showTierRequest && (
        <Modal title="Xin nâng hạng" onClose={() => setShowTierRequest(false)}>
          <form className="field-grid" onSubmit={handleRequestTier}>
            <label>
              Xin lên hạng
              <select value={requestedTier} onChange={(e) => setRequestedTier(e.target.value)}>
                {higherTiers.map((t) => (
                  <option key={t} value={t}>
                    {TIER_LABEL[t]}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Lý do *
              <textarea
                rows={3}
                required
                placeholder="Vì sao đối tác này nên được nâng hạng sớm..."
                value={requestReason}
                onChange={(e) => setRequestReason(e.target.value)}
              />
            </label>
            {error && <p className="error">{error}</p>}
            <div className="modal-actions">
              <button type="button" className="secondary" onClick={() => setShowTierRequest(false)}>
                Huỷ
              </button>
              <button type="submit">Gửi yêu cầu</button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  );
}
