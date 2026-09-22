import { Fragment, useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { apiFetch } from "../api";
import { useAuth } from "../AuthContext";
import AddressFields from "../components/AddressFields";
import { formatMoney } from "../constants";

function emptyItemRow() {
  return {
    item_name: "",
    quantity: "",
    unit: "",
    unit_cost: "",
    unit_dimensions: "",
    unit_weight_kg: "",
    total_cost: "",
    total_dimensions: "",
    total_weight_kg: "",
  };
}

function emptyQuoteForm() {
  return {
    country: "",
    province: "",
    district: "",
    ward: "",
    street_address: "",
    shipping_cost: "",
    note: "",
    items: [emptyItemRow()],
  };
}

export default function CostQuoteBoard() {
  const { user } = useAuth();
  const [searchParams] = useSearchParams();
  const onlyItemId = searchParams.get("price_request_item");
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [expandedId, setExpandedId] = useState(onlyItemId ? Number(onlyItemId) : null);
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

  function prefillForm(item) {
    // Mặt hàng/Số lượng/ĐVT lấy sẵn từ dòng Yêu cầu giá gốc — Cung ứng vẫn sửa được, và có thể
    // thêm mặt hàng khác vào cùng câu trả lời (vd gộp chung 1 chuyến hàng).
    setForm({
      ...emptyQuoteForm(),
      items: [
        {
          ...emptyItemRow(),
          item_name: item.product_name || item.item_name || "",
          quantity: item.quantity ?? "",
          unit: item.unit || "",
        },
      ],
    });
  }

  function toggleExpanded(item) {
    if (expandedId === item.id) {
      setExpandedId(null);
      return;
    }
    setExpandedId(item.id);
    if (canSupply()) prefillForm(item);
  }

  function updateItemRow(index, field, value) {
    setForm((prev) => ({
      ...prev,
      items: prev.items.map((row, i) => (i === index ? { ...row, [field]: value } : row)),
    }));
  }

  function addItemRow() {
    setForm((prev) => ({ ...prev, items: [...prev.items, emptyItemRow()] }));
  }

  function removeItemRow(index) {
    setForm((prev) => ({ ...prev, items: prev.items.filter((_, i) => i !== index) }));
  }

  async function handleAddQuote(e, item) {
    e.preventDefault();
    setError("");
    setSaving(true);
    try {
      await apiFetch("/api/cost-quotes/", {
        method: "POST",
        body: JSON.stringify({
          price_request_item: item.id,
          country: form.country || null,
          province: form.province || null,
          district: form.district || null,
          ward: form.ward || null,
          street_address: form.street_address,
          shipping_cost: form.shipping_cost || null,
          note: form.note,
          items: form.items.map((it) => ({
            item_name: it.item_name,
            quantity: it.quantity || null,
            unit: it.unit,
            unit_cost: it.unit_cost || null,
            unit_dimensions: it.unit_dimensions,
            unit_weight_kg: it.unit_weight_kg || null,
            total_cost: it.total_cost || null,
            total_dimensions: it.total_dimensions,
            total_weight_kg: it.total_weight_kg || null,
          })),
        }),
      });
      prefillForm(item);
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
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Mã YCG</th>
                <th>Khách hàng</th>
                <th>Mặt hàng</th>
                <th>SL / ĐVT</th>
                <th>Phụ trách</th>
                <th>Câu trả lời</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => {
                const quotes = item.cost_quotes || [];
                const isExpanded = expandedId === item.id;
                return (
                  <Fragment key={item.id}>
                    <tr className="clickable" onClick={() => toggleExpanded(item)}>
                      <td>{item.price_request_code}</td>
                      <td className="ellipsis-cell" title={item.customer_name}>
                        {item.customer_name}
                      </td>
                      <td className="ellipsis-cell" title={item.product_name || item.item_name}>
                        {item.product_name || item.item_name || "—"}
                      </td>
                      <td>{item.quantity ? `${item.quantity} ${item.unit || ""}` : "—"}</td>
                      <td>{item.assigned_to_name ?? "—"}</td>
                      <td>
                        {quotes.length > 0 ? (
                          <span className="badge badge-done">{quotes.length}</span>
                        ) : (
                          <span className="muted">0</span>
                        )}
                      </td>
                    </tr>
                    {isExpanded && (
                      <tr>
                        <td colSpan={6} style={{ background: "var(--surface-muted)", padding: "14px 16px" }}>
                          {quotes.length === 0 ? (
                            <p className="muted" style={{ margin: "0 0 10px" }}>
                              Chưa có câu trả lời nào.
                            </p>
                          ) : (
                            quotes.map((q) => {
                              const address = [
                                q.street_address, q.ward_name, q.district_name, q.province_name, q.country_name,
                              ]
                                .filter(Boolean)
                                .join(", ");
                              return (
                                <div key={q.id} className="panel" style={{ marginBottom: 10, padding: "10px 14px" }}>
                                  {(q.items || []).map((it) => (
                                    <div key={it.id} className="wrap-row-view">
                                      <b>{it.item_name || "—"}</b>
                                      <span>{it.quantity ? `${it.quantity} ${it.unit || ""}` : "—"}</span>
                                      {it.unit_cost && <span>Giá vốn/đv: {formatMoney(it.unit_cost)}</span>}
                                      {it.unit_dimensions && <span>KT/đv: {it.unit_dimensions}</span>}
                                      {it.unit_weight_kg && <span>TL/đv: {it.unit_weight_kg} kg</span>}
                                      {it.total_cost && (
                                        <span style={{ fontWeight: 600 }}>Tổng giá vốn: {formatMoney(it.total_cost)}</span>
                                      )}
                                      {it.total_dimensions && <span>Tổng KT: {it.total_dimensions}</span>}
                                      {it.total_weight_kg && <span>Tổng TL: {it.total_weight_kg} kg</span>}
                                    </div>
                                  ))}
                                  <div className="muted wrap-row-view" style={{ fontSize: 12 }}>
                                    <span>Giá vận chuyển: {q.shipping_cost ? formatMoney(q.shipping_cost) : "—"}</span>
                                    <span>Điểm nhận hàng: {address || "—"}</span>
                                    <span>Người trả lời: {q.created_by_name ?? "—"}</span>
                                    {q.note && <span>{q.note}</span>}
                                  </div>
                                </div>
                              );
                            })
                          )}

                          {canSupply() && (
                            <form
                              onSubmit={(e) => handleAddQuote(e, item)}
                              onClick={(e) => e.stopPropagation()}
                              style={{ marginTop: 12 }}
                            >
                              {form.items.map((row, i) => (
                                <div className="wrap-row" key={i}>
                                  <label style={{ minWidth: 160, flex: "1 1 160px" }}>
                                    Mặt hàng
                                    <input
                                      value={row.item_name}
                                      onChange={(e) => updateItemRow(i, "item_name", e.target.value)}
                                    />
                                  </label>
                                  <label style={{ width: 70 }}>
                                    SL
                                    <input
                                      type="number" step="0.01"
                                      value={row.quantity}
                                      onChange={(e) => updateItemRow(i, "quantity", e.target.value)}
                                    />
                                  </label>
                                  <label style={{ width: 70 }}>
                                    ĐVT
                                    <input value={row.unit} onChange={(e) => updateItemRow(i, "unit", e.target.value)} />
                                  </label>
                                  <label style={{ width: 100 }}>
                                    Giá vốn/đv
                                    <input
                                      type="number" step="0.01"
                                      value={row.unit_cost}
                                      onChange={(e) => updateItemRow(i, "unit_cost", e.target.value)}
                                    />
                                  </label>
                                  <label style={{ width: 100 }}>
                                    KT/đv
                                    <input
                                      value={row.unit_dimensions}
                                      onChange={(e) => updateItemRow(i, "unit_dimensions", e.target.value)}
                                    />
                                  </label>
                                  <label style={{ width: 90 }}>
                                    TL/đv (kg)
                                    <input
                                      type="number" step="0.01"
                                      value={row.unit_weight_kg}
                                      onChange={(e) => updateItemRow(i, "unit_weight_kg", e.target.value)}
                                    />
                                  </label>
                                  <label style={{ width: 100 }}>
                                    Tổng giá vốn
                                    <input
                                      type="number" step="0.01"
                                      value={row.total_cost}
                                      onChange={(e) => updateItemRow(i, "total_cost", e.target.value)}
                                    />
                                  </label>
                                  <label style={{ width: 100 }}>
                                    Tổng KT
                                    <input
                                      value={row.total_dimensions}
                                      onChange={(e) => updateItemRow(i, "total_dimensions", e.target.value)}
                                    />
                                  </label>
                                  <label style={{ width: 90 }}>
                                    Tổng TL (kg)
                                    <input
                                      type="number" step="0.01"
                                      value={row.total_weight_kg}
                                      onChange={(e) => updateItemRow(i, "total_weight_kg", e.target.value)}
                                    />
                                  </label>
                                  {form.items.length > 1 && (
                                    <button
                                      type="button"
                                      className="link-btn"
                                      style={{ marginBottom: 8 }}
                                      onClick={() => removeItemRow(i)}
                                    >
                                      Xoá
                                    </button>
                                  )}
                                </div>
                              ))}
                              <button type="button" className="link-btn" style={{ marginTop: 8 }} onClick={addItemRow}>
                                + Thêm mặt hàng
                              </button>

                              <div className="field-grid-cols" style={{ marginTop: 12 }}>
                                <label>
                                  Giá vốn vận chuyển
                                  <input
                                    type="number" step="0.01"
                                    placeholder="Tự tra, nhập tay — chung cho cả chuyến"
                                    value={form.shipping_cost}
                                    onChange={(e) => setForm({ ...form, shipping_cost: e.target.value })}
                                  />
                                </label>
                                <label className="span-all">
                                  Điểm nhận hàng
                                  <AddressFields value={form} onChange={(addr) => setForm({ ...form, ...addr })} />
                                </label>
                                <label className="span-all">
                                  Mô tả thêm
                                  <textarea
                                    rows={2}
                                    value={form.note}
                                    onChange={(e) => setForm({ ...form, note: e.target.value })}
                                  />
                                </label>
                              </div>
                              <div className="modal-actions">
                                <button type="submit" disabled={saving}>
                                  {saving ? "Đang lưu..." : "Lưu trả lời"}
                                </button>
                              </div>
                            </form>
                          )}
                        </td>
                      </tr>
                    )}
                  </Fragment>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
