import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { apiFetch } from "../api";
import { useAuth } from "../AuthContext";
import { formatMoney } from "../constants";

function emptyQuoteForm() {
  return {
    supplier: "",
    unit_price: "",
    quantity: "",
    unit: "",
    pickup_point: "",
    total_packages: "",
    package_dimensions: "",
    total_cbm: "",
    total_weight_kg: "",
    available_at: "",
    payment_terms: "",
    delivery_terms: "",
    shipping_cost: "",
    note: "",
  };
}

export default function SupplierQuoteBoard() {
  const { user } = useAuth();
  const [searchParams] = useSearchParams();
  const onlyItemId = searchParams.get("purchase_request_item");
  const [items, setItems] = useState([]);
  const [suppliers, setSuppliers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showFormFor, setShowFormFor] = useState(null);
  const [form, setForm] = useState(emptyQuoteForm());
  const [saving, setSaving] = useState(false);
  const [selectionNoteDraft, setSelectionNoteDraft] = useState({});

  async function load() {
    setLoading(true);
    try {
      const itemsPath = onlyItemId
        ? `/api/purchase-request-items/?id=${onlyItemId}`
        : "/api/purchase-request-items/";
      const [i, s] = await Promise.all([
        apiFetch(itemsPath),
        apiFetch("/api/partners/?is_supplier=true"),
      ]);
      setItems(i.results ?? i);
      setSuppliers(s.results ?? s);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [onlyItemId]);

  function canSupply() {
    return user?.is_manager || user?.is_supply;
  }

  function canSelectFor(item) {
    if (user?.is_manager) return true;
    return (item.price_requests || []).some((pr) => pr.assigned_to_id === user?.profile_id);
  }

  async function handleAddQuote(e, itemId) {
    e.preventDefault();
    setError("");
    setSaving(true);
    try {
      await apiFetch("/api/supplier-quotes/", {
        method: "POST",
        body: JSON.stringify({
          purchase_request_item: itemId,
          supplier: Number(form.supplier),
          unit_price: form.unit_price,
          quantity: form.quantity,
          unit: form.unit,
          pickup_point: form.pickup_point,
          total_packages: form.total_packages || null,
          package_dimensions: form.package_dimensions,
          total_cbm: form.total_cbm || null,
          total_weight_kg: form.total_weight_kg || null,
          available_at: form.available_at || null,
          payment_terms: form.payment_terms,
          delivery_terms: form.delivery_terms,
          shipping_cost: form.shipping_cost || null,
          note: form.note,
        }),
      });
      setForm(emptyQuoteForm());
      setShowFormFor(null);
      load();
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  async function handleSelect(quote, isCheapest) {
    setError("");
    const note = selectionNoteDraft[quote.id] || "";
    if (!isCheapest && !note.trim()) {
      setError("Giá này không phải giá thấp nhất — cần nhập lý do trước khi chọn.");
      return;
    }
    try {
      await apiFetch(`/api/supplier-quotes/${quote.id}/select/`, {
        method: "POST",
        body: JSON.stringify({ selection_note: note }),
      });
      setSelectionNoteDraft((prev) => ({ ...prev, [quote.id]: "" }));
      load();
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div>
      <div className="page-head">
        <div>
          <h1>Sàn báo giá NCC</h1>
          <div className="page-head-sub">
            Cung ứng nhập báo giá của các NCC để so sánh — Kinh doanh phụ trách Yêu cầu giá liên quan chọn giá.
          </div>
        </div>
      </div>

      {error && <p className="error">{error}</p>}

      {loading ? (
        <p className="muted">Đang tải...</p>
      ) : items.length === 0 ? (
        <div className="panel">
          <p className="muted">Chưa có Đề nghị mua nào cần báo giá.</p>
        </div>
      ) : (
        items.map((item) => {
          const quotes = item.supplier_quotes || [];
          const cheapestId = quotes.length
            ? quotes.reduce((a, b) => (a.landed_unit_cost <= b.landed_unit_cost ? a : b)).id
            : null;
          const allowSelect = canSelectFor(item);
          return (
            <div className="panel" key={item.id} style={{ marginBottom: 14 }}>
              <div className="row-name" style={{ justifyContent: "space-between", alignItems: "flex-start" }}>
                <div>
                  <div style={{ fontWeight: 600 }}>
                    {item.product_name || item.item_name}{" "}
                    <span className="muted" style={{ fontWeight: 400 }}>
                      x{item.quantity} {item.unit}
                    </span>
                  </div>
                  <div className="muted" style={{ fontSize: 12.5 }}>
                    {item.purchase_request_code} ·{" "}
                    {(item.price_requests || [])
                      .map((pr) => `${pr.code} (${pr.customer_name} — ${pr.assigned_to_name ?? "—"})`)
                      .join(", ") || "Chưa gắn Yêu cầu giá nào"}
                  </div>
                </div>
                {canSupply() && (
                  <button
                    type="button"
                    className="secondary"
                    onClick={() => setShowFormFor(showFormFor === item.id ? null : item.id)}
                  >
                    {showFormFor === item.id ? "Đóng" : "+ Báo giá"}
                  </button>
                )}
              </div>

              {quotes.length === 0 ? (
                <p className="muted" style={{ marginTop: 10 }}>
                  Chưa có báo giá nào.
                </p>
              ) : (
                <div className="table-wrap" style={{ marginTop: 10 }}>
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>NCC</th>
                        <th>Đơn giá</th>
                        <th>Vận chuyển</th>
                        <th>Giá quy đổi/đv</th>
                        <th>Điểm nhận hàng</th>
                        <th>Ngày có hàng</th>
                        <th></th>
                      </tr>
                    </thead>
                    <tbody>
                      {quotes.map((q) => {
                        const detail = [
                          q.total_packages ? `${q.total_packages} kiện` : null,
                          q.package_dimensions,
                          q.total_cbm ? `${q.total_cbm} CBM` : null,
                          q.total_weight_kg ? `${q.total_weight_kg} kg` : null,
                          q.payment_terms && `TT: ${q.payment_terms}`,
                          q.delivery_terms && `Giao nhận: ${q.delivery_terms}`,
                          q.note,
                        ]
                          .filter(Boolean)
                          .join(" · ");
                        return (
                          <tr key={q.id}>
                            <td title={detail || undefined}>
                              {q.supplier_name}
                              {q.is_selected && (
                                <span className="badge badge-done" style={{ marginLeft: 6 }}>
                                  Đã chọn
                                </span>
                              )}
                            </td>
                            <td>{formatMoney(q.unit_price)}</td>
                            <td>{q.shipping_cost ? formatMoney(q.shipping_cost) : "—"}</td>
                            <td style={{ fontWeight: 600 }}>{formatMoney(q.landed_unit_cost)}</td>
                            <td>{q.pickup_point || "—"}</td>
                            <td>{q.available_at || "—"}</td>
                            <td>
                              {allowSelect && !q.is_selected && (
                                <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                                  {q.id !== cheapestId && (
                                    <input
                                      placeholder="Lý do (bắt buộc nếu không phải giá thấp nhất)"
                                      style={{ fontSize: 12 }}
                                      value={selectionNoteDraft[q.id] || ""}
                                      onChange={(e) =>
                                        setSelectionNoteDraft((prev) => ({ ...prev, [q.id]: e.target.value }))
                                      }
                                    />
                                  )}
                                  <button
                                    type="button"
                                    className="secondary"
                                    onClick={() => handleSelect(q, q.id === cheapestId)}
                                  >
                                    Chọn giá này
                                  </button>
                                </div>
                              )}
                              {q.is_selected && q.selection_note && (
                                <span className="muted" style={{ fontSize: 12 }} title={q.selection_note}>
                                  Có lý do
                                </span>
                              )}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}

              {showFormFor === item.id && (
                <form className="field-grid" onSubmit={(e) => handleAddQuote(e, item.id)} style={{ marginTop: 10 }}>
                  <label>
                    Nhà cung cấp *
                    <select required value={form.supplier} onChange={(e) => setForm({ ...form, supplier: e.target.value })}>
                      <option value="">— Chọn NCC —</option>
                      {suppliers.map((s) => (
                        <option key={s.id} value={s.id}>
                          {s.name}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    Đơn giá hàng *
                    <input
                      type="number" step="0.01" required
                      value={form.unit_price}
                      onChange={(e) => setForm({ ...form, unit_price: e.target.value })}
                    />
                  </label>
                  <label>
                    Số lượng *
                    <input
                      type="number" step="0.01" required
                      value={form.quantity}
                      onChange={(e) => setForm({ ...form, quantity: e.target.value })}
                    />
                  </label>
                  <label>
                    Đơn vị
                    <input value={form.unit} onChange={(e) => setForm({ ...form, unit: e.target.value })} />
                  </label>
                  <label>
                    Điểm nhận hàng
                    <input
                      placeholder="Nơi NCC giao tới / kho nào"
                      value={form.pickup_point}
                      onChange={(e) => setForm({ ...form, pickup_point: e.target.value })}
                    />
                  </label>
                  <label>
                    Giá vận chuyển (tự tra, nhập tay)
                    <input
                      type="number" step="0.01"
                      value={form.shipping_cost}
                      onChange={(e) => setForm({ ...form, shipping_cost: e.target.value })}
                    />
                  </label>
                  <label>
                    Tổng số kiện
                    <input
                      type="number"
                      value={form.total_packages}
                      onChange={(e) => setForm({ ...form, total_packages: e.target.value })}
                    />
                  </label>
                  <label>
                    Kích thước kiện
                    <input
                      value={form.package_dimensions}
                      onChange={(e) => setForm({ ...form, package_dimensions: e.target.value })}
                    />
                  </label>
                  <label>
                    Tổng CBM
                    <input
                      type="number" step="0.01"
                      value={form.total_cbm}
                      onChange={(e) => setForm({ ...form, total_cbm: e.target.value })}
                    />
                  </label>
                  <label>
                    Tổng trọng lượng (kg)
                    <input
                      type="number" step="0.01"
                      value={form.total_weight_kg}
                      onChange={(e) => setForm({ ...form, total_weight_kg: e.target.value })}
                    />
                  </label>
                  <label>
                    Thời gian có hàng
                    <input
                      type="date"
                      value={form.available_at}
                      onChange={(e) => setForm({ ...form, available_at: e.target.value })}
                    />
                  </label>
                  <label>
                    Điều kiện thanh toán
                    <input
                      value={form.payment_terms}
                      onChange={(e) => setForm({ ...form, payment_terms: e.target.value })}
                    />
                  </label>
                  <label>
                    Điều kiện giao nhận
                    <input
                      value={form.delivery_terms}
                      onChange={(e) => setForm({ ...form, delivery_terms: e.target.value })}
                    />
                  </label>
                  <label>
                    Ghi chú
                    <textarea rows={2} value={form.note} onChange={(e) => setForm({ ...form, note: e.target.value })} />
                  </label>
                  <div className="modal-actions">
                    <button type="submit" disabled={saving}>
                      {saving ? "Đang lưu..." : "Lưu báo giá"}
                    </button>
                  </div>
                </form>
              )}
            </div>
          );
        })
      )}
    </div>
  );
}
