import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { apiFetch } from "../api";
import Avatar from "../components/Avatar";
import Modal from "../components/Modal";
import StatusBadge from "../components/StatusBadge";
import { formatMoney, OUTCOME_LABEL, PARTNER_TYPE_LABEL, TIER_LABEL, TIER_REQUEST_STATUS_LABEL } from "../constants";

function timeAgo(iso) {
  const diffMs = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diffMs / 60000);
  if (mins < 1) return "vừa xong";
  if (mins < 60) return `${mins} phút trước`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours} giờ trước`;
  return new Date(iso).toLocaleDateString("vi-VN");
}

const EMPTY_ITEM = { description: "", quantity: 1, unit_price: 0, unit_cost: 0 };
const TIER_ORDER = ["standard", "vip", "super_vip"];

export default function PartnerDetail() {
  const { id } = useParams();
  const [partner, setPartner] = useState(null);
  const [contacts, setContacts] = useState([]);
  const [orders, setOrders] = useState([]);
  const [tierRequests, setTierRequests] = useState([]);
  const [note, setNote] = useState("");
  const [contactPerson, setContactPerson] = useState("");
  const [outcome, setOutcome] = useState("pending");
  const [error, setError] = useState("");
  const [tab, setTab] = useState("activity");
  const [showNewOrder, setShowNewOrder] = useState(false);
  const [items, setItems] = useState([{ ...EMPTY_ITEM }]);
  const [paid, setPaid] = useState(false);
  const [onPlatform, setOnPlatform] = useState(false);
  const [showTierRequest, setShowTierRequest] = useState(false);
  const [requestedTier, setRequestedTier] = useState("vip");
  const [requestReason, setRequestReason] = useState("");

  async function loadAll() {
    try {
      const [p, contactList, orderList, requestList] = await Promise.all([
        apiFetch(`/api/partners/${id}/`),
        apiFetch(`/api/partners/${id}/contacts/`),
        apiFetch(`/api/orders/?customer=${id}`),
        apiFetch(`/api/tier-requests/?partner=${id}`),
      ]);
      setPartner(p);
      setContacts(contactList);
      setOrders(orderList.results ?? orderList);
      setTierRequests(requestList.results ?? requestList);
    } catch (err) {
      setError(err.message);
    }
  }

  useEffect(() => {
    loadAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  async function handleAddNote(e) {
    e.preventDefault();
    if (!note.trim()) return;
    try {
      await apiFetch(`/api/partners/${id}/contacts/`, {
        method: "POST",
        body: JSON.stringify({ note, contact_person: contactPerson, outcome }),
      });
      setNote("");
      setContactPerson("");
      setOutcome("pending");
      loadAll();
    } catch (err) {
      setError(err.message);
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

  const timeline = [
    ...contacts.map((c) => ({
      type: "contact",
      at: c.created_at,
      node: (
        <>
          <b>{c.created_by_name}</b> liên hệ {c.contact_person && <>với <b>{c.contact_person}</b></>} —{" "}
          <span className="muted">{OUTCOME_LABEL[c.outcome]}</span>: {c.note}
        </>
      ),
    })),
    ...orders.map((o) => ({
      type: "order",
      at: o.created_at,
      node: (
        <>
          Tạo đơn hàng <b>#{o.id}</b> — {formatMoney(o.total)}
        </>
      ),
    })),
  ].sort((a, b) => new Date(b.at) - new Date(a.at));

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
        <div className="panel">
          <form className="field-grid" onSubmit={handleAddNote} style={{ marginBottom: 18 }}>
            <div className="order-item-row" style={{ gridTemplateColumns: "1fr 160px" }}>
              <input
                placeholder="Người liên hệ (vd: Anh Nam)"
                value={contactPerson}
                onChange={(e) => setContactPerson(e.target.value)}
              />
              <select value={outcome} onChange={(e) => setOutcome(e.target.value)}>
                {Object.entries(OUTCOME_LABEL).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </div>
            <textarea
              rows={2}
              placeholder="Ghi lại nội dung vừa liên hệ..."
              value={note}
              onChange={(e) => setNote(e.target.value)}
            />
            <div style={{ display: "flex", justifyContent: "flex-end" }}>
              <button type="submit">Lưu ghi chú</button>
            </div>
          </form>

          {timeline.length === 0 ? (
            <p className="muted">Chưa có hoạt động nào.</p>
          ) : (
            <ul className="activity-list">
              {timeline.map((item, i) => (
                <li className="activity-item" key={i}>
                  <span className={`activity-dot ${item.type}`} />
                  <span className="activity-text">{item.node}</span>
                  <span className="activity-time">{timeAgo(item.at)}</span>
                </li>
              ))}
            </ul>
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
