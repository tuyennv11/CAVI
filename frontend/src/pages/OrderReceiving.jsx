import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { apiFetch } from "../api";
import StatusBadge from "../components/StatusBadge";
import { formatMoney } from "../constants";

async function fetchAllPendingOrders() {
  let path = "/api/orders/pending-receipt/";
  let all = [];
  while (path) {
    const data = await apiFetch(path);
    all = all.concat(data.results ?? data);
    if (data.next) {
      const u = new URL(data.next);
      path = u.pathname + u.search;
    } else {
      path = null;
    }
  }
  return all;
}

export default function OrderReceiving() {
  const [orders, setOrders] = useState([]);
  const [actualForms, setActualForms] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [busyId, setBusyId] = useState(null);

  async function load() {
    try {
      const data = await fetchAllPendingOrders();
      setOrders(data);
      setActualForms((prev) => {
        const next = { ...prev };
        for (const o of data) {
          if (!next[o.id]) {
            next[o.id] = Object.fromEntries(
              o.items.map((it) => [it.id, it.actual_quantity ?? it.quantity])
            );
          }
        }
        return next;
      });
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  function updateActual(orderId, itemId, value) {
    setActualForms((prev) => ({
      ...prev,
      [orderId]: { ...prev[orderId], [itemId]: value },
    }));
  }

  async function handleRecordActual(orderId) {
    setBusyId(orderId);
    setError("");
    try {
      const form = actualForms[orderId] || {};
      const items = Object.entries(form).map(([id, actual_quantity]) => ({
        id: Number(id),
        actual_quantity,
      }));
      await apiFetch(`/api/orders/${orderId}/record-actual/`, {
        method: "POST",
        body: JSON.stringify({ items }),
      });
      load();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusyId(null);
    }
  }

  async function handleConfirm(orderId) {
    setBusyId(orderId);
    setError("");
    try {
      await apiFetch(`/api/orders/${orderId}/confirm-received/`, { method: "POST" });
      load();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusyId(null);
    }
  }

  if (loading) return <p className="muted">Đang tải...</p>;

  return (
    <div>
      <div className="page-head">
        <div>
          <h1>Chờ nhận hàng</h1>
          <div className="page-head-sub">
            Vận hành ghi nhận số lượng thực nhận cho phiếu nhận hàng, Kinh doanh xác nhận lại thì phiếu
            mới chính thức thành đơn hàng — {orders.length} phiếu đang chờ.
          </div>
        </div>
      </div>

      {error && <p className="error">{error}</p>}

      {orders.length === 0 ? (
        <p className="muted">Không có phiếu nào đang chờ nhận hàng.</p>
      ) : (
        orders.map((o) => (
          <div className="panel" key={o.id} style={{ marginBottom: 12 }}>
            <div className="quotation-head">
              <b>Phiếu #{o.id}</b> —{" "}
              <Link to={`/partners/${o.customer}?tab=orders`}>{o.customer_name}</Link>{" "}
              <StatusBadge status={o.status} /> · Tổng: <b>{formatMoney(o.total)}</b>
              {o.received_by_name && (
                <span className="muted"> — Vận hành ghi nhận bởi {o.received_by_name}</span>
              )}
            </div>
            <div className="table-wrap">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Mô tả</th>
                    <th>SL dự kiến</th>
                    <th>SL thực nhận</th>
                  </tr>
                </thead>
                <tbody>
                  {o.items.map((it) => (
                    <tr key={it.id}>
                      <td>{it.description}</td>
                      <td>{it.quantity}</td>
                      <td>
                        <input
                          type="number"
                          style={{ width: 90 }}
                          value={actualForms[o.id]?.[it.id] ?? ""}
                          onChange={(e) => updateActual(o.id, it.id, e.target.value)}
                        />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="quotation-actions">
              <button type="button" disabled={busyId === o.id} onClick={() => handleRecordActual(o.id)}>
                {o.status === "pending_confirmation" ? "Ghi nhận lại" : "Ghi nhận đã nhận hàng"}
              </button>
              {o.status === "pending_confirmation" && (
                <button type="button" disabled={busyId === o.id} onClick={() => handleConfirm(o.id)}>
                  Xác nhận — chốt thành đơn hàng
                </button>
              )}
            </div>
          </div>
        ))
      )}
    </div>
  );
}
