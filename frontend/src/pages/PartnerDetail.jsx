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
  PRICE_INQUIRY_TEMPLATE,
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

function groupPriceList(priceList) {
  const groups = [];
  const byName = new Map();
  for (const item of priceList) {
    const key = `${item.category}|${item.group_name}`;
    let group = byName.get(key);
    if (!group) {
      group = { label: `Nhóm ${item.category} — ${item.group_name}`, options: [] };
      byName.set(key, group);
      groups.push(group);
    }
    group.options.push({ value: item.id, label: `${item.item_code} — ${item.name}`, category: item.category });
  }
  return groups;
}

function formatPct(value) {
  return `${parseFloat(Number(value ?? 0).toFixed(2))}%`;
}

function sumLines(lines) {
  return lines.reduce(
    (acc, l) => ({
      cost: acc.cost + Number(l.line_cost),
      floor: acc.floor + Number(l.line_floor),
      ceiling: acc.ceiling + Number(l.line_ceiling),
    }),
    { cost: 0, floor: 0, ceiling: 0 }
  );
}

function emptyLineForm() {
  return { item: "", item_name: "", unit: "", floor_pct: "", ceiling_pct: "", quantity: 1, unit_cost: "", note: "" };
}

function emptyQuotationForm(quotation) {
  return {
    note: quotation.note || "",
    lines: quotation.lines.map((l) => ({
      item_name: l.item_name,
      unit: l.unit,
      quantity: l.quantity,
      unit_cost: l.unit_cost,
      floor_pct: l.floor_pct,
      ceiling_pct: l.ceiling_pct,
      note: l.note || "",
    })),
  };
}

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
  // Lỗi riêng cho thao tác dòng báo giá — không dùng chung `error` vì trang này
  // return sớm cả trang khi `error` có giá trị, làm mất hết dữ liệu đang xem.
  const [lineError, setLineError] = useState("");
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

  const [inquiries, setInquiries] = useState([]);
  const [showNewInquiry, setShowNewInquiry] = useState(false);
  const [inquiryDescription, setInquiryDescription] = useState(PRICE_INQUIRY_TEMPLATE);
  const [inquiryImage, setInquiryImage] = useState(null);
  const [inquiryError, setInquiryError] = useState("");
  const [messageDrafts, setMessageDrafts] = useState({});
  const [priceList, setPriceList] = useState([]);
  const [lineFormFor, setLineFormFor] = useState(null);
  const [lineForms, setLineForms] = useState({});
  const [quotationForms, setQuotationForms] = useState({});

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

  async function loadInquiries() {
    try {
      const res = await apiFetch(`/api/price-inquiries/?customer=${id}`);
      setInquiries(res.results ?? res);
    } catch (err) {
      setError(err.message);
    }
  }

  async function loadPriceList() {
    try {
      const res = await apiFetch("/api/price-list-items/");
      setPriceList(res.results ?? res);
    } catch (err) {
      setError(err.message);
    }
  }

  useEffect(() => {
    loadAll();
    loadInquiries();
    loadPriceList();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  // Nạp form chỉnh sửa báo giá 1 lần khi báo giá xuất hiện — không ghi đè nếu người dùng đang gõ dở.
  useEffect(() => {
    setQuotationForms((prev) => {
      let changed = false;
      const next = { ...prev };
      for (const inq of inquiries) {
        if (inq.quotation && !next[inq.id]) {
          next[inq.id] = emptyQuotationForm(inq.quotation);
          changed = true;
        }
      }
      return changed ? next : prev;
    });
  }, [inquiries]);

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

  async function handleCreateInquiry(e) {
    e.preventDefault();
    setInquiryError("");
    try {
      const fd = new FormData();
      fd.set("customer", id);
      fd.set("description", inquiryDescription);
      if (inquiryImage) fd.set("image", inquiryImage);
      await apiUpload("/api/price-inquiries/", fd);
      setInquiryDescription(PRICE_INQUIRY_TEMPLATE);
      setInquiryImage(null);
      setShowNewInquiry(false);
      loadInquiries();
    } catch (err) {
      setInquiryError(err.message);
    }
  }

  async function handleSendMessage(inquiryId) {
    const content = (messageDrafts[inquiryId] || "").trim();
    if (!content) return;
    try {
      await apiFetch(`/api/price-inquiries/${inquiryId}/messages/`, {
        method: "POST",
        body: JSON.stringify({ content }),
      });
      setMessageDrafts((prev) => ({ ...prev, [inquiryId]: "" }));
      loadInquiries();
    } catch (err) {
      setError(err.message);
    }
  }

  function updateLineField(inquiryId, field, value) {
    setLineForms((prev) => ({ ...prev, [inquiryId]: { ...emptyLineForm(), ...prev[inquiryId], [field]: value } }));
  }

  function toggleLineForm(inquiryId) {
    setLineFormFor((prev) => (prev === inquiryId ? null : inquiryId));
    setLineForms((prev) => ({ ...prev, [inquiryId]: prev[inquiryId] || emptyLineForm() }));
    setLineError("");
  }

  async function handleAddLine(inquiryId) {
    const form = lineForms[inquiryId] || emptyLineForm();
    if (!form.item && !form.item_name) {
      setLineError("Chọn dịch vụ từ bảng giá hoặc nhập tên dịch vụ.");
      return;
    }
    if (!form.quantity || !form.unit_cost) {
      setLineError("Cần nhập Số lượng và Đơn giá vốn.");
      return;
    }
    const payload = form.item
      ? { item: Number(form.item), quantity: form.quantity, unit_cost: form.unit_cost, note: form.note || "" }
      : {
          item_name: form.item_name,
          unit: form.unit,
          floor_pct: form.floor_pct || 0,
          ceiling_pct: form.ceiling_pct || 0,
          quantity: form.quantity,
          unit_cost: form.unit_cost,
          note: form.note || "",
        };
    try {
      await apiFetch(`/api/price-inquiries/${inquiryId}/lines/`, {
        method: "POST",
        body: JSON.stringify(payload),
      });
      setLineForms((prev) => ({ ...prev, [inquiryId]: emptyLineForm() }));
      setLineError("");
      loadInquiries();
    } catch (err) {
      setLineError(err.message);
    }
  }

  async function handleDeleteLine(lineId) {
    try {
      await apiFetch(`/api/quote-lines/${lineId}/`, { method: "DELETE" });
      loadInquiries();
    } catch (err) {
      setLineError(err.message);
    }
  }

  async function handleConfirmQuote(inquiryId) {
    try {
      await apiFetch(`/api/price-inquiries/${inquiryId}/confirm-quote/`, { method: "POST" });
      setLineFormFor(null);
      loadInquiries();
    } catch (err) {
      setLineError(err.message);
    }
  }

  async function handleCreateQuotation(inquiryId) {
    try {
      await apiFetch(`/api/price-inquiries/${inquiryId}/create-quotation/`, { method: "POST" });
      loadInquiries();
    } catch (err) {
      setLineError(err.message);
    }
  }

  function updateQuotationNote(inquiryId, value) {
    setQuotationForms((prev) => ({ ...prev, [inquiryId]: { ...prev[inquiryId], note: value } }));
  }

  function updateQuotationLine(inquiryId, lineIndex, field, value) {
    setQuotationForms((prev) => {
      const form = prev[inquiryId];
      const lines = form.lines.map((l, i) => (i === lineIndex ? { ...l, [field]: value } : l));
      return { ...prev, [inquiryId]: { ...form, lines } };
    });
  }

  async function handleSaveQuotation(inquiryId, quotationId) {
    const form = quotationForms[inquiryId];
    try {
      await apiFetch(`/api/quotations/${quotationId}/`, {
        method: "PATCH",
        body: JSON.stringify(form),
      });
      loadInquiries();
    } catch (err) {
      setLineError(err.message);
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
  const pendingRequest = tierRequests.find((r) => r.status === "pending");
  const higherTiers = TIER_ORDER.slice(TIER_ORDER.indexOf(partner.tier) + 1);

  return (
    <div>
      <div className="profile-header">
        <Avatar name={partner.name} size="lg" />
        <div style={{ flex: 1, minWidth: 0 }}>
          <div className="profile-title-row">
            <Link to="/partners" className="profile-back" title="Danh sách đối tác">
              &larr;
            </Link>
            <h1>{partner.name}</h1>
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
            {higherTiers.length > 0 && (
              <span className="profile-title-spacer">
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
              </span>
            )}
          </div>
          <div className="profile-meta-row">
            <span>
              Gắn bó {partner.tenure_months} tháng · Doanh thu tích luỹ {formatMoney(partner.total_revenue)}
            </span>
            {partner.partner_type !== "supplier" && (
              <span className={overLimit ? "error" : ""}>
                · Công nợ: <b>{formatMoney(partner.debt)}</b> / {formatMoney(partner.credit_limit)}
              </span>
            )}
            {partner.note && <span>· {partner.note}</span>}
          </div>
        </div>
      </div>

      <div className="tabs">
        <button className={`tab-btn${tab === "activity" ? " active" : ""}`} onClick={() => setTab("activity")}>
          Tương tác
        </button>
        <button className={`tab-btn${tab === "inquiries" ? " active" : ""}`} onClick={() => setTab("inquiries")}>
          Hỏi giá ({inquiries.length})
        </button>
        <button className={`tab-btn${tab === "orders" ? " active" : ""}`} onClick={() => setTab("orders")}>
          Đơn hàng ({orders.length})
        </button>
      </div>

      {tab === "activity" && (
        <div>
          <div className="panel">
            <div className="page-head">
              <h2 style={{ margin: 0 }}>Lịch sử tương tác</h2>
              {summary && (
                <span className="muted" style={{ fontSize: 12.5 }}>
                  {summary.total_activities} hoạt động · Gần nhất:{" "}
                  {summary.last_activity_at ? timeAgo(summary.last_activity_at) : "—"}
                  {summary.upcoming_follow_ups > 0 && ` · 🔔 ${summary.upcoming_follow_ups} follow-up sắp tới`}
                </span>
              )}
            </div>

            <div className="quick-log-row">
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
              <input
                className="search-input quick-log-search"
                placeholder="Tìm nội dung..."
                value={filters.search}
                onChange={(e) => updateFilter("search", e.target.value)}
              />
            </div>
            {activityError && <p className="error">{activityError}</p>}

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

      {tab === "inquiries" && (
        <div className="panel">
          <div className="page-head">
            <h2 style={{ margin: 0 }}>Hỏi giá</h2>
            <button onClick={() => setShowNewInquiry((v) => !v)}>
              {showNewInquiry ? "Đóng" : "+ Tạo yêu cầu hỏi giá"}
            </button>
          </div>

          {showNewInquiry && (
            <form className="field-grid" onSubmit={handleCreateInquiry} style={{ marginBottom: 14 }}>
              <textarea
                rows={9}
                value={inquiryDescription}
                onChange={(e) => setInquiryDescription(e.target.value)}
              />
              <label>
                Hình ảnh
                <input
                  type="file"
                  accept="image/*"
                  onChange={(e) => setInquiryImage(e.target.files[0] ?? null)}
                />
              </label>
              {inquiryError && <p className="error">{inquiryError}</p>}
              <div className="modal-actions">
                <button type="button" className="secondary" onClick={() => setShowNewInquiry(false)}>
                  Huỷ
                </button>
                <button type="submit">Tạo yêu cầu</button>
              </div>
            </form>
          )}

          {inquiries.length === 0 ? (
            <p className="muted">Chưa có yêu cầu hỏi giá nào.</p>
          ) : (
            <div className="inquiry-list">
              {inquiries.map((inq) => (
                <div className="inquiry-card" key={inq.id}>
                  <div className="inquiry-head">
                    <StatusBadge status={inq.status} />
                    <span className="muted" style={{ fontSize: 12 }}>
                      #{inq.id} · {inq.created_by_name} · {formatDateTime(inq.created_at)}
                    </span>
                  </div>
                  <div className="inquiry-description">{inq.description}</div>

                  {inq.image && (
                    <a href={inq.image} target="_blank" rel="noreferrer" className="inquiry-image-link">
                      <img src={inq.image} alt="Hình ảnh hỏi giá" className="inquiry-image" />
                    </a>
                  )}

                  {inq.status === "open" && inq.quote_lines.length > 0 && (
                    <div className="inquiry-line-actions">
                      <button type="button" className="secondary" onClick={() => toggleLineForm(inq.id)}>
                        {lineFormFor === inq.id ? "Đóng" : "Thêm dịch vụ"}
                      </button>
                      <button type="button" onClick={() => handleConfirmQuote(inq.id)}>
                        Xác nhận báo giá
                      </button>
                    </div>
                  )}

                  {lineFormFor === inq.id && (
                    <div className="inquiry-line-form">
                      <select
                        value={lineForms[inq.id]?.item || ""}
                        onChange={(e) => updateLineField(inq.id, "item", e.target.value)}
                      >
                        <option value="">— Dịch vụ khác (tự nhập) —</option>
                        {groupPriceList(priceList).map((g) => (
                          <optgroup label={g.label} key={g.label}>
                            {g.options.map((o) => {
                              const groupIUsed =
                                o.category === "I" && inq.quote_lines.some((l) => l.category === "I");
                              return (
                                <option key={o.value} value={o.value} disabled={groupIUsed}>
                                  {o.label}
                                  {groupIUsed ? " (đơn đã có dịch vụ nhóm I)" : ""}
                                </option>
                              );
                            })}
                          </optgroup>
                        ))}
                      </select>
                      {!lineForms[inq.id]?.item && (
                        <input
                          className="line-item-name"
                          placeholder="Tên dịch vụ"
                          value={lineForms[inq.id]?.item_name || ""}
                          onChange={(e) => updateLineField(inq.id, "item_name", e.target.value)}
                        />
                      )}
                      <input
                        className="line-note"
                        placeholder="Mô tả"
                        value={lineForms[inq.id]?.note || ""}
                        onChange={(e) => updateLineField(inq.id, "note", e.target.value)}
                      />
                      <input
                        type="number"
                        placeholder="Số lượng"
                        style={{ width: 80 }}
                        value={lineForms[inq.id]?.quantity ?? 1}
                        onChange={(e) => updateLineField(inq.id, "quantity", e.target.value)}
                      />
                      {!lineForms[inq.id]?.item ? (
                        <input
                          placeholder="ĐVT"
                          style={{ width: 60 }}
                          value={lineForms[inq.id]?.unit || ""}
                          onChange={(e) => updateLineField(inq.id, "unit", e.target.value)}
                        />
                      ) : (
                        (() => {
                          const selectedItem = priceList.find(
                            (p) => String(p.id) === String(lineForms[inq.id].item)
                          );
                          return <input value={selectedItem?.unit || ""} disabled style={{ width: 60 }} />;
                        })()
                      )}
                      <input
                        type="number"
                        placeholder="Đơn giá vốn"
                        style={{ width: 110 }}
                        value={lineForms[inq.id]?.unit_cost || ""}
                        onChange={(e) => updateLineField(inq.id, "unit_cost", e.target.value)}
                      />
                      {!lineForms[inq.id]?.item ? (
                        <>
                          <span className="line-pct-group">
                            <span className="line-pct-label">Sàn</span>
                            <input
                              type="number"
                              className="line-pct"
                              value={lineForms[inq.id]?.floor_pct || ""}
                              onChange={(e) => updateLineField(inq.id, "floor_pct", e.target.value)}
                            />
                          </span>
                          <span className="line-pct-group">
                            <span className="line-pct-label">Trần</span>
                            <input
                              type="number"
                              className="line-pct"
                              value={lineForms[inq.id]?.ceiling_pct || ""}
                              onChange={(e) => updateLineField(inq.id, "ceiling_pct", e.target.value)}
                            />
                          </span>
                        </>
                      ) : (
                        (() => {
                          const selectedItem = priceList.find(
                            (p) => String(p.id) === String(lineForms[inq.id].item)
                          );
                          if (!selectedItem) return null;
                          return (
                            <>
                              <span className="line-pct-group">
                                <span className="line-pct-label">Sàn</span>
                                <input className="line-pct" value={formatPct(selectedItem.floor_pct)} disabled />
                              </span>
                              <span className="line-pct-group">
                                <span className="line-pct-label">Trần</span>
                                <input className="line-pct" value={formatPct(selectedItem.ceiling_pct)} disabled />
                              </span>
                            </>
                          );
                        })()
                      )}
                      <button type="button" onClick={() => handleAddLine(inq.id)}>
                        Thêm dòng
                      </button>
                    </div>
                  )}

                  {lineFormFor === inq.id && lineError && <p className="error">{lineError}</p>}

                  {inq.quote_lines.length > 0 &&
                    (() => {
                      const totals = sumLines(inq.quote_lines);
                      return (
                        <div className="table-wrap" style={{ marginBottom: 8 }}>
                          <table className="data-table inquiry-lines-table">
                            <thead>
                              <tr>
                                <th>Dịch vụ cấu thành đơn hàng</th>
                                <th>Mô tả</th>
                                <th>ĐVT</th>
                                <th>SL</th>
                                <th>Đơn giá vốn</th>
                                <th>Giá vốn</th>
                                <th>Giá sàn</th>
                                <th>Giá trần</th>
                                {inq.status === "open" && <th></th>}
                              </tr>
                            </thead>
                            <tbody>
                              {inq.quote_lines.map((l) => (
                                <tr key={l.id}>
                                  <td>{l.item_name}</td>
                                  <td className="muted">{l.note}</td>
                                  <td>{l.unit}</td>
                                  <td>{l.quantity}</td>
                                  <td>{formatMoney(l.unit_cost)}</td>
                                  <td>{formatMoney(l.line_cost)}</td>
                                  <td>{formatMoney(l.line_floor)}</td>
                                  <td>{formatMoney(l.line_ceiling)}</td>
                                  {inq.status === "open" && (
                                    <td>
                                      <button
                                        type="button"
                                        className="link-btn"
                                        onClick={() => handleDeleteLine(l.id)}
                                      >
                                        Xoá
                                      </button>
                                    </td>
                                  )}
                                </tr>
                              ))}
                            </tbody>
                            <tfoot>
                              <tr>
                                <td colSpan={5}>
                                  <b>Tổng</b>
                                </td>
                                <td>
                                  <b>{formatMoney(totals.cost)}</b>
                                </td>
                                <td>
                                  <b>{formatMoney(totals.floor)}</b>
                                </td>
                                <td>
                                  <b>{formatMoney(totals.ceiling)}</b>
                                </td>
                                {inq.status === "open" && <td></td>}
                              </tr>
                            </tfoot>
                          </table>
                        </div>
                      );
                    })()}

                  {inq.status === "quoted" && (
                    <div className="inquiry-quote-summary">
                      Giá vốn: <b>{formatMoney(inq.cost_price)}</b> · Giá sàn: <b>{formatMoney(inq.floor_price)}</b> ·
                      Giá trần: <b>{formatMoney(inq.ceiling_price)}</b>
                      <span className="muted"> — chốt bởi {inq.quoted_by_name}</span>
                      {!inq.quotation && (
                        <button type="button" className="secondary" onClick={() => handleCreateQuotation(inq.id)}>
                          Tạo báo giá
                        </button>
                      )}
                    </div>
                  )}

                  {inq.quotation && quotationForms[inq.id] && (
                    <div className="quotation-panel">
                      <div className="quotation-head">
                        <b>Báo giá</b> — Khách hàng: <b>{inq.customer_name}</b>
                      </div>
                      <textarea
                        rows={3}
                        value={quotationForms[inq.id].note}
                        onChange={(e) => updateQuotationNote(inq.id, e.target.value)}
                      />
                      <div className="table-wrap">
                        <table className="data-table quotation-lines-table">
                          <thead>
                            <tr>
                              <th>Dịch vụ</th>
                              <th>Mô tả</th>
                              <th>ĐVT</th>
                              <th>SL</th>
                              <th>Đơn giá vốn</th>
                              <th>Sàn %</th>
                              <th>Trần %</th>
                            </tr>
                          </thead>
                          <tbody>
                            {quotationForms[inq.id].lines.map((l, i) => (
                              <tr key={i}>
                                <td>
                                  <input
                                    value={l.item_name}
                                    onChange={(e) => updateQuotationLine(inq.id, i, "item_name", e.target.value)}
                                  />
                                </td>
                                <td>
                                  <input
                                    value={l.note}
                                    onChange={(e) => updateQuotationLine(inq.id, i, "note", e.target.value)}
                                  />
                                </td>
                                <td>
                                  <input
                                    style={{ width: 60 }}
                                    value={l.unit}
                                    onChange={(e) => updateQuotationLine(inq.id, i, "unit", e.target.value)}
                                  />
                                </td>
                                <td>
                                  <input
                                    type="number"
                                    style={{ width: 70 }}
                                    value={l.quantity}
                                    onChange={(e) => updateQuotationLine(inq.id, i, "quantity", e.target.value)}
                                  />
                                </td>
                                <td>
                                  <input
                                    type="number"
                                    style={{ width: 110 }}
                                    value={l.unit_cost}
                                    onChange={(e) => updateQuotationLine(inq.id, i, "unit_cost", e.target.value)}
                                  />
                                </td>
                                <td>
                                  <input
                                    type="number"
                                    style={{ width: 70 }}
                                    value={l.floor_pct}
                                    onChange={(e) => updateQuotationLine(inq.id, i, "floor_pct", e.target.value)}
                                  />
                                </td>
                                <td>
                                  <input
                                    type="number"
                                    style={{ width: 70 }}
                                    value={l.ceiling_pct}
                                    onChange={(e) => updateQuotationLine(inq.id, i, "ceiling_pct", e.target.value)}
                                  />
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                      <button type="button" onClick={() => handleSaveQuotation(inq.id, inq.quotation.id)}>
                        Lưu báo giá
                      </button>
                    </div>
                  )}

                  {inq.messages.length > 0 && (
                    <div className="inquiry-thread">
                      {inq.messages.map((m) => (
                        <div className={`inquiry-message${m.is_quote ? " quote" : ""}`} key={m.id}>
                          <b>{m.author_name}</b>
                          <span className="muted"> · {formatDateTime(m.created_at)}</span>
                          <div>{m.content}</div>
                        </div>
                      ))}
                    </div>
                  )}

                  <div className="inquiry-reply-row">
                    <input
                      placeholder="Trao đổi về báo giá..."
                      value={messageDrafts[inq.id] || ""}
                      onChange={(e) => setMessageDrafts((prev) => ({ ...prev, [inq.id]: e.target.value }))}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") {
                          e.preventDefault();
                          handleSendMessage(inq.id);
                        }
                      }}
                    />
                    <button type="button" onClick={() => handleSendMessage(inq.id)}>
                      Gửi
                    </button>
                    {inq.status === "open" && inq.quote_lines.length === 0 && (
                      <button type="button" className="secondary" onClick={() => toggleLineForm(inq.id)}>
                        {lineFormFor === inq.id ? "Đóng" : "Phân tích giá vốn"}
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
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
