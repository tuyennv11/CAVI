import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { apiFetch } from "../api";

const STATUS_LABEL = {
  new: "Mới",
  processing: "Đang xử lý",
  done: "Hoàn thành",
  cancelled: "Huỷ",
};

export default function CustomerDetail() {
  const { id } = useParams();
  const [customer, setCustomer] = useState(null);
  const [contacts, setContacts] = useState([]);
  const [orders, setOrders] = useState([]);
  const [note, setNote] = useState("");
  const [error, setError] = useState("");
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
      loadAll();
    } catch (err) {
      setError(err.message);
    }
  }

  if (error) return <p className="error">{error}</p>;
  if (!customer) return <p>Đang tải...</p>;

  return (
    <div className="page">
      <p>
        <Link to="/customers">&larr; Danh sách khách hàng</Link>
      </p>
      <h1>{customer.name}</h1>
      <div className="customer-meta">
        <span>{customer.company}</span>
        <span>{customer.phone}</span>
        <span>{customer.email}</span>
        <span>{customer.address}</span>
      </div>

      <section className="card">
        <h2>Lịch sử chăm sóc</h2>
        <form className="note-form" onSubmit={handleAddNote}>
          <textarea
            placeholder="Ghi lại nội dung vừa liên hệ với khách..."
            value={note}
            onChange={(e) => setNote(e.target.value)}
          />
          <button type="submit">Lưu ghi chú</button>
        </form>
        <ul className="log-list">
          {contacts.map((c) => (
            <li key={c.id}>
              <span className="log-date">{new Date(c.created_at).toLocaleString("vi-VN")}</span>
              <span className="log-author">{c.created_by_name}</span>
              <p>{c.note}</p>
            </li>
          ))}
          {contacts.length === 0 && <p className="muted">Chưa có lịch sử chăm sóc.</p>}
        </ul>
      </section>

      <section className="card">
        <div className="page-head">
          <h2>Đơn hàng</h2>
          <button onClick={() => setShowNewOrder((v) => !v)}>{showNewOrder ? "Đóng" : "+ Tạo đơn hàng"}</button>
        </div>

        {showNewOrder && (
          <form className="order-form" onSubmit={handleCreateOrder}>
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
            <button type="submit">Lưu đơn hàng</button>
          </form>
        )}

        <ul className="order-list">
          {orders.map((o) => (
            <li key={o.id}>
              <span>Đơn #{o.id}</span>
              <span className={`status status-${o.status}`}>{STATUS_LABEL[o.status]}</span>
              <span>{Number(o.total).toLocaleString("vi-VN")} đ</span>
            </li>
          ))}
          {orders.length === 0 && <p className="muted">Chưa có đơn hàng.</p>}
        </ul>
      </section>
    </div>
  );
}
