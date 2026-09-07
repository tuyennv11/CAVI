import { useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { apiFetch, apiUpload, API_URL } from "../api";
import { useAuth } from "../AuthContext";
import Avatar from "../components/Avatar";
import Modal from "../components/Modal";
import StatusBadge from "../components/StatusBadge";
import {
  ACTIVITY_TYPE_CATEGORY,
  formatMoney,
  PARTNER_TYPE_LABEL,
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

// Hẹn có giờ cụ thể (vd "15h gọi lại") thì quá hạn tính đúng theo giờ đó; hẹn chỉ có ngày
// (vd "thứ 4 tuần sau") thì coi như còn hạn tới hết ngày hôm đó.
function isFollowUpOverdue(followUpDate, followUpTime) {
  if (!followUpDate) return false;
  const target = new Date(`${followUpDate}T${followUpTime || "23:59:59"}`);
  return target < new Date();
}

function formatFollowUp(followUpDate, followUpTime) {
  const d = new Date(followUpDate).toLocaleDateString("vi-VN");
  return followUpTime ? `lúc ${followUpTime.slice(0, 5)} ${d}` : d;
}

function nowDateStr() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

function nowTimeStr() {
  const d = new Date();
  return `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
}

const EMPTY_ITEM = { description: "", quantity: 1, unit_price: 0, unit_cost: 0 };
const TIER_ORDER = ["standard", "vip", "super_vip"];

const EMPTY_FILTERS = {
  search: "",
};

function emptyActivityForm(currentUserId) {
  return {
    activity_type: "note",
    performed_by: currentUserId ?? "",
    activity_date: nowDateStr(),
    activity_time: nowTimeStr(),
    content: "",
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
  const [activityForm, setActivityForm] = useState(() => emptyActivityForm(currentUser?.id));
  const [activityError, setActivityError] = useState("");
  const activityContentRef = useRef(null);

  async function loadAll() {
    try {
      const [p, orderList, requestList] = await Promise.all([
        apiFetch(`/api/partners/${id}/`),
        apiFetch(`/api/orders/?customer=${id}`),
        apiFetch(`/api/tier-requests/?partner=${id}`),
      ]);
      setPartner(p);
      setOrders(orderList.results ?? orderList);
      setTierRequests(requestList.results ?? requestList);
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

  function updateActivityField(field, value) {
    setActivityForm((prev) => ({ ...prev, [field]: value }));
  }

  async function handleAddActivity(e) {
    e.preventDefault();
    setActivityError("");
    if (activityForm.follow_up_date && !activityForm.follow_up_time) {
      setActivityError("Hẹn nhắc lại cần chọn giờ chính xác.");
      return;
    }
    try {
      const fd = new FormData();
      fd.set("activity_type", activityForm.activity_type);
      const activityAt =
        activityForm.activity_date && activityForm.activity_time
          ? new Date(`${activityForm.activity_date}T${activityForm.activity_time}`).toISOString()
          : new Date().toISOString();
      fd.set("activity_at", activityAt);
      if (activityForm.performed_by) fd.set("performed_by", activityForm.performed_by);
      if (activityForm.content) fd.set("content", activityForm.content);
      if (activityForm.follow_up_date) {
        fd.set("follow_up_date", activityForm.follow_up_date);
        fd.set("follow_up_time", activityForm.follow_up_time);
      }
      if (activityForm.attachment) fd.set("attachment", activityForm.attachment);

      await apiUpload(`/api/partners/${id}/activities/`, fd);
      setActivityForm(emptyActivityForm(currentUser?.id));
      activityContentRef.current?.focus();
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
      <p style={{ marginBottom: 10 }}>
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
            <div style={{ marginTop: 10 }}>
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
            <div className="stat-grid">
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
            </div>
          )}

          <div className="panel">
            <div className="page-head">
              <h2 style={{ margin: 0 }}>Lịch sử tương tác</h2>
            </div>

            <form className="quick-log-bar" onSubmit={handleAddActivity}>
              <div className="quick-log-group">
                <input
                  type="date"
                  className="quick-log-date"
                  title="Ngày"
                  required
                  value={activityForm.activity_date}
                  onChange={(e) => updateActivityField("activity_date", e.target.value)}
                />
                <input
                  type="time"
                  className="quick-log-time"
                  title="Giờ"
                  required
                  value={activityForm.activity_time}
                  onChange={(e) => updateActivityField("activity_time", e.target.value)}
                />
              </div>
              <input
                ref={activityContentRef}
                required
                className="quick-log-input"
                placeholder="Ghi nhanh hoạt động với khách... (VD: Đã gọi cho anh Nam báo giá lô hàng T9)"
                value={activityForm.content}
                onChange={(e) => updateActivityField("content", e.target.value)}
              />
              <div className="quick-log-group quick-log-followup">
                <span className="quick-log-group-icon" title="Hẹn nhắc lại">
                  🔔
                </span>
                <input
                  type="date"
                  className="quick-log-date"
                  title="Hẹn nhắc lại — ngày"
                  value={activityForm.follow_up_date}
                  onChange={(e) => updateActivityField("follow_up_date", e.target.value)}
                />
                <input
                  type="time"
                  className="quick-log-time"
                  title="Hẹn nhắc lại — giờ chính xác"
                  value={activityForm.follow_up_time}
                  onChange={(e) => updateActivityField("follow_up_time", e.target.value)}
                />
              </div>
              <label className="quick-log-file" title="Đính kèm file">
                📎
                <input
                  type="file"
                  hidden
                  onChange={(e) => updateActivityField("attachment", e.target.files[0] ?? null)}
                />
              </label>
              <button type="submit" className="quick-log-submit">
                Lưu
              </button>
            </form>
            {activityError && <p className="error">{activityError}</p>}

            <div className="filter-bar">
              <input
                className="search-input"
                placeholder="Tìm theo nội dung..."
                value={filters.search}
                onChange={(e) => updateFilter("search", e.target.value)}
              />
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
                        <div className="timeline-row">
                          <span className="timeline-time">{formatDateTime(a.activity_at)}</span>
                          <span className="timeline-content-text">{a.content || a.title}</span>
                          {a.follow_up_date && (
                            <span
                              className={`timeline-followup${overdue ? " overdue" : ""}${
                                a.follow_up_done ? " done" : ""
                              }`}
                            >
                              🔔 Nhắc hẹn {formatFollowUp(a.follow_up_date, a.follow_up_time)}
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
                        {a.contact_person && (
                          <div className="timeline-meta">
                            <span>Liên hệ: {a.contact_person}</span>
                          </div>
                        )}
                        {a.result && (
                          <div className="timeline-result">
                            Kết quả: <b>{a.result}</b>
                          </div>
                        )}
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
            <form className="field-grid" onSubmit={handleCreateOrder} style={{ marginBottom: 12 }}>
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
