import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { apiFetch } from "../api";
import Avatar from "../components/Avatar";
import StatusBadge from "../components/StatusBadge";

function timeAgo(iso) {
  const diffMs = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diffMs / 60000);
  if (mins < 1) return "vừa xong";
  if (mins < 60) return `${mins} phút trước`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours} giờ trước`;
  return new Date(iso).toLocaleDateString("vi-VN");
}

export default function CustomerDetail() {
  const { id } = useParams();
  const [customer, setCustomer] = useState(null);
  const [contacts, setContacts] = useState([]);
  const [orders, setOrders] = useState([]);
  const [note, setNote] = useState("");
  const [error, setError] = useState("");
  const [tab, setTab] = useState("activity");
  const [showNewOrder, setShowNewOrder] = useState(false);
  const [items, setItems] = useState([{ description: "", quantity: 1, unit_price: 0 }]);

  async function loadAll() {
    try {
      const [c, contactList, orderList] = await Promise.all([
        apiFetch(`/api/customers/${id}/`),
        apiFetch(`/api/customers/${id}/contacts/`),
        apiFetch(`/api/orders/?customer=${id}`),
      ]);
      setCustomer(c);
      setContacts(contactList);
      setOrders(orderList.results ?? orderList);
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
      await apiFetch(`/api/customers/${id}/contacts/`, { method: "POST", body: JSON.stringify({ note }) });
      setNote("");
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
        body: JSON.stringify({ customer: Number(id), status: "new", items }),
      });
      setItems([{ description: "", quantity: 1, unit_price: 0 }]);
      setShowNewOrder(false);
      setTab("orders");
      loadAll();
    } catch (err) {
      setError(err.message);
    }
  }

  if (error) return <p className="error">{error}</p>;
  if (!customer) return <p className="muted">Đang tải...</p>;

  const timeline = [
    ...contacts.map((c) => ({ type: "contact", at: c.created_at, node: (
      <>
        <b>{c.created_by_name}</b> đã ghi chú chăm sóc: {c.note}
      </>
    ) })),
    ...orders.map((o) => ({ type: "order", at: o.created_at, node: (
      <>
        Tạo đơn hàng <b>#{o.id}</b> — {Number(o.total).toLocaleString("vi-VN")} đ
      </>
    ) })),
  ].sort((a, b) => new Date(b.at) - new Date(a.at));

  return (
    <div>
      <p style={{ marginBottom: 16 }}>
        <Link to="/customers">&larr; Danh sách khách hàng</Link>
      </p>

      <div className="profile-header">
        <Avatar name={customer.name} size="lg" />
        <div>
          <h1>{customer.name}</h1>
          {customer.company && <div className="company">{customer.company}</div>}
          <div className="profile-pills">
            {customer.phone && <span className="profile-pill">📞 {customer.phone}</span>}
            {customer.email && <span className="profile-pill">✉️ {customer.email}</span>}
            {customer.address && <span className="profile-pill">📍 {customer.address}</span>}
            {customer.assigned_to_detail && (
              <span className="profile-pill">👤 Phụ trách: {customer.assigned_to_detail.username}</span>
            )}
          </div>
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
            <textarea
              rows={2}
              placeholder="Ghi lại nội dung vừa liên hệ với khách..."
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
                <div className="order-item-row" key={i}>
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
                    placeholder="Đơn giá"
                    value={it.unit_price}
                    onChange={(e) => updateItem(i, "unit_price", e.target.value)}
                  />
                </div>
              ))}
              <button
                type="button"
                className="link-btn"
                onClick={() => setItems([...items, { description: "", quantity: 1, unit_price: 0 }])}
              >
                + Thêm dòng
              </button>
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
                    <th>Tổng tiền</th>
                  </tr>
                </thead>
                <tbody>
                  {orders.map((o) => (
                    <tr key={o.id}>
                      <td>#{o.id}</td>
                      <td>
                        <StatusBadge status={o.status} />
                      </td>
                      <td>{Number(o.total).toLocaleString("vi-VN")} đ</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
