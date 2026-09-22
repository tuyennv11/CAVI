import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { apiFetch } from "../api";
import { useAuth } from "../AuthContext";
import AddressFields from "../components/AddressFields";
import { formatMoney } from "../constants";

function emptyQuoteForm() {
  return {
    country: "",
    province: "",
    district: "",
    ward: "",
    street_address: "",
    item_name: "",
    quantity: "",
    unit: "",
    unit_cost: "",
    unit_dimensions: "",
    unit_weight_kg: "",
    total_cost: "",
    total_dimensions: "",
    total_weight_kg: "",
    shipping_cost: "",
    note: "",
  };
}

export default function CostQuoteBoard() {
  const { user } = useAuth();
  const [searchParams] = useSearchParams();
  const onlyItemId = searchParams.get("price_request_item");
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showFormFor, setShowFormFor] = useState(null);
  const [form, setForm] = useState(emptyQuoteForm());
  const [saving, setSaving] = useState(false);

  async function load() {
    setLoading(true);
    try {
      const itemsPath = onlyItemId
        ? `/api/price-inquiry-items/?id=${onlyItemId}`
        : "/api/price-inquiry-items/";
      const data = await apiFetch(itemsPath);
      setItems(data.results ?? data);
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

  async function handleAddQuote(e, itemId) {
    e.preventDefault();
    setError("");
    setSaving(true);
    try {
      await apiFetch("/api/cost-quotes/", {
        method: "POST",
        body: JSON.stringify({
          price_request_item: itemId,
          country: form.country || null,
          province: form.province || null,
          district: form.district || null,
          ward: form.ward || null,
          street_address: form.street_address,
          item_name: form.item_name,
          quantity: form.quantity || null,
          unit: form.unit,
          unit_cost: form.unit_cost || null,
          unit_dimensions: form.unit_dimensions,
          unit_weight_kg: form.unit_weight_kg || null,
          total_cost: form.total_cost || null,
          total_dimensions: form.total_dimensions,
          total_weight_kg: form.total_weight_kg || null,
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

  return (
    <div>
      <div className="page-head">
        <div>
          <h1>Trả lời yêu cầu giá</h1>
          <div className="page-head-sub">
            Cung ứng nhập báo giá vốn nội bộ trả lời từng dòng Yêu cầu giá — trước khi có báo giá NCC thật.
          </div>
        </div>
      </div>

      {error && <p className="error">{error}</p>}

      {loading ? (
        <p className="muted">Đang tải...</p>
      ) : items.length === 0 ? (
        <div className="panel">
          <p className="muted">Chưa có Yêu cầu giá nào.</p>
        </div>
      ) : (
        items.map((item) => {
          const quotes = item.cost_quotes || [];
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
                    {item.price_request_code} · {item.customer_name} — {item.assigned_to_name ?? "—"}
                  </div>
                </div>
                {canSupply() && (
                  <button
                    type="button"
                    className="secondary"
                    onClick={() => setShowFormFor(showFormFor === item.id ? null : item.id)}
                  >
                    {showFormFor === item.id ? "Đóng" : "+ Trả lời"}
                  </button>
                )}
              </div>

              {quotes.length === 0 ? (
                <p className="muted" style={{ marginTop: 10 }}>
                  Chưa có câu trả lời nào.
                </p>
              ) : (
                <div className="table-wrap" style={{ marginTop: 10 }}>
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Mặt hàng</th>
                        <th>SL / ĐVT</th>
                        <th>Giá vốn đơn vị</th>
                        <th>Tổng giá vốn</th>
                        <th>Giá vận chuyển</th>
                        <th>Điểm nhận hàng</th>
                        <th>Người trả lời</th>
                      </tr>
                    </thead>
                    <tbody>
                      {quotes.map((q) => {
                        const address = [q.street_address, q.ward_name, q.district_name, q.province_name, q.country_name]
                          .filter(Boolean)
                          .join(", ");
                        const detail = [
                          q.unit_dimensions && `KT/đv: ${q.unit_dimensions}`,
                          q.unit_weight_kg && `TL/đv: ${q.unit_weight_kg} kg`,
                          q.total_dimensions && `Tổng KT: ${q.total_dimensions}`,
                          q.total_weight_kg && `Tổng TL: ${q.total_weight_kg} kg`,
                          q.note,
                        ]
                          .filter(Boolean)
                          .join(" · ");
                        return (
                          <tr key={q.id}>
                            <td title={detail || undefined}>{q.item_name || "—"}</td>
                            <td>
                              {q.quantity ?? "—"} {q.unit}
                            </td>
                            <td>{q.unit_cost ? formatMoney(q.unit_cost) : "—"}</td>
                            <td style={{ fontWeight: 600 }}>{q.total_cost ? formatMoney(q.total_cost) : "—"}</td>
                            <td>{q.shipping_cost ? formatMoney(q.shipping_cost) : "—"}</td>
                            <td>{address || "—"}</td>
                            <td>{q.created_by_name ?? "—"}</td>
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
                    Mặt hàng
                    <input value={form.item_name} onChange={(e) => setForm({ ...form, item_name: e.target.value })} />
                  </label>
                  <label>
                    Số lượng
                    <input
                      type="number" step="0.01"
                      value={form.quantity}
                      onChange={(e) => setForm({ ...form, quantity: e.target.value })}
                    />
                  </label>
                  <label>
                    ĐVT
                    <input value={form.unit} onChange={(e) => setForm({ ...form, unit: e.target.value })} />
                  </label>
                  <label>
                    Giá vốn đơn vị
                    <input
                      type="number" step="0.01"
                      value={form.unit_cost}
                      onChange={(e) => setForm({ ...form, unit_cost: e.target.value })}
                    />
                  </label>
                  <label>
                    Tổng giá vốn
                    <input
                      type="number" step="0.01"
                      value={form.total_cost}
                      onChange={(e) => setForm({ ...form, total_cost: e.target.value })}
                    />
                  </label>
                  <label>
                    Giá vốn vận chuyển (tự tra, nhập tay)
                    <input
                      type="number" step="0.01"
                      value={form.shipping_cost}
                      onChange={(e) => setForm({ ...form, shipping_cost: e.target.value })}
                    />
                  </label>
                  <label>
                    Kích thước đơn vị
                    <input
                      value={form.unit_dimensions}
                      onChange={(e) => setForm({ ...form, unit_dimensions: e.target.value })}
                    />
                  </label>
                  <label>
                    Trọng lượng đơn vị (kg)
                    <input
                      type="number" step="0.01"
                      value={form.unit_weight_kg}
                      onChange={(e) => setForm({ ...form, unit_weight_kg: e.target.value })}
                    />
                  </label>
                  <label>
                    Tổng kích thước
                    <input
                      value={form.total_dimensions}
                      onChange={(e) => setForm({ ...form, total_dimensions: e.target.value })}
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
                    Điểm nhận hàng
                    <AddressFields value={form} onChange={(addr) => setForm({ ...form, ...addr })} />
                  </label>
                  <label>
                    Mô tả thêm
                    <textarea rows={2} value={form.note} onChange={(e) => setForm({ ...form, note: e.target.value })} />
                  </label>
                  <div className="modal-actions">
                    <button type="submit" disabled={saving}>
                      {saving ? "Đang lưu..." : "Lưu trả lời"}
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
