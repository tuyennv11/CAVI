import { Fragment, useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { apiFetch } from "../api";
import { useAuth } from "../AuthContext";
import AddressFields from "../components/AddressFields";
import MoneyInput from "../components/MoneyInput";
import { formatMoney } from "../constants";

const WEIGHT_DISPLAY_THRESHOLD_KG = 1000;

function emptyItemRow() {
  return {
    item_name: "",
    quantity: "",
    unit: "",
    unit_cost: "",
    unit_length: "",
    unit_width: "",
    unit_height: "",
    dimension_unit: "cm",
    unit_weight: "",
    weight_unit: "kg",
  };
}

function emptyQuoteForm() {
  return {
    country: "",
    province: "",
    district: "",
    ward: "",
    street_address: "",
    shipping_rate: "",
    shipping_rate_basis: "kg",
    note: "",
    items: [emptyItemRow()],
  };
}

// Quy đổi giá trị nhập (theo đơn vị đang chọn trên form) về đơn vị chuẩn lưu trong DB (cm/kg).
function toCm(value, unit) {
  const n = Number(value);
  if (!value || Number.isNaN(n)) return null;
  return unit === "m" ? n * 100 : n;
}
function toKg(value, unit) {
  const n = Number(value);
  if (!value || Number.isNaN(n)) return null;
  return unit === "tấn" ? n * 1000 : n;
}

function formatWeight(kg) {
  if (kg === null || kg === undefined || Number.isNaN(kg)) return "—";
  return kg >= WEIGHT_DISPLAY_THRESHOLD_KG
    ? `${(kg / 1000).toLocaleString("vi-VN", { maximumFractionDigits: 2 })} tấn`
    : `${kg.toLocaleString("vi-VN", { maximumFractionDigits: 2 })} kg`;
}

// Khi ĐVT của mặt hàng đã tự là đơn vị khối lượng/thể tích (tấn, kg, khối/m3...), SL chính là
// Tổng trọng lượng/Tổng kích thước luôn — không cần nhân với 1 "đơn vị/đv" nhập tay riêng nữa (đó
// là trường hợp còn lại, vd ĐVT là "thùng"/"kiện" thì mới cần Dài×Rộng×Cao hoặc Trọng lượng/đv).
function unitKind(unit) {
  const u = (unit || "").trim().toLowerCase();
  if (!u) return "other";
  if (u.includes("khối") || u.includes("khoi") || u.includes("m3") || u.includes("m³")) return "volume";
  if (u.includes("kg") || u.includes("tấn") || u.includes("tan") || u.includes("ký")) return "weight";
  return "other";
}
function weightPerUnitKg(unit) {
  const u = (unit || "").trim().toLowerCase();
  return u.includes("tấn") || u.includes("tan") ? 1000 : 1;
}

// SL/ĐVT đã chốt là đơn vị khối lượng thì hiện Tổng trọng lượng đúng nguyên đơn vị đó (khớp với
// ĐVT, không tự chuyển đổi kg/tấn theo ngưỡng nữa).
function formatWeightDisplay(unit, quantity, totalWeightKg) {
  if (totalWeightKg === null || totalWeightKg === undefined) return "—";
  if (unitKind(unit) === "weight" && quantity) {
    return `${Number(quantity).toLocaleString("vi-VN", { maximumFractionDigits: 2 })} ${unit}`;
  }
  return formatWeight(Number(totalWeightKg));
}

// Xem trước Tổng giá vốn/Tổng kích thước/Tổng trọng lượng ngay khi đang gõ — CostQuoteItem model
// tính lại y hệt công thức này ở backend (property, không cho nhập tay) sau khi lưu.
function previewTotals(row) {
  const quantity = Number(row.quantity) || 0;
  const unitCost = Number(row.unit_cost) || 0;
  const kind = unitKind(row.unit);

  const totalCost = quantity && row.unit_cost ? quantity * unitCost : null;

  const totalWeightKg =
    kind === "weight"
      ? quantity
        ? quantity * weightPerUnitKg(row.unit)
        : null
      : (() => {
          const weightKg = toKg(row.unit_weight, row.weight_unit);
          return quantity && weightKg ? quantity * weightKg : null;
        })();

  const totalVolumeM3 =
    kind === "volume"
      ? quantity || null
      : (() => {
          const lengthCm = toCm(row.unit_length, row.dimension_unit);
          const widthCm = toCm(row.unit_width, row.dimension_unit);
          const heightCm = toCm(row.unit_height, row.dimension_unit);
          return quantity && lengthCm && widthCm && heightCm
            ? quantity * (lengthCm / 100) * (widthCm / 100) * (heightCm / 100)
            : null;
        })();

  return { totalCost, totalVolumeM3, totalWeightKg, kind };
}

// Cộng dồn Tổng giá vốn/kích thước/trọng lượng của TẤT CẢ mặt hàng trong 1 câu trả lời — dùng cho
// cả xem trước lúc nhập (previewTotals mỗi dòng) lẫn hiện lại câu trả lời đã lưu (total_* từ API).
function sumItemTotals(totalsList) {
  return totalsList.reduce(
    (acc, t) => ({
      totalCost: acc.totalCost + (t.totalCost || 0),
      totalVolumeM3: acc.totalVolumeM3 + (t.totalVolumeM3 || 0),
      totalWeightKg: acc.totalWeightKg + (t.totalWeightKg || 0),
    }),
    { totalCost: 0, totalVolumeM3: 0, totalWeightKg: 0 },
  );
}

// Tổng giá vốn vận chuyển: NCC báo trọn gói (basis "total") thì lấy thẳng Giá cước; báo theo đơn
// giá/kg hoặc /m3 thì nhân với tổng trọng lượng/thể tích cộng dồn mọi mặt hàng — y hệt công thức
// CostQuote.shipping_cost tính lại ở backend sau khi lưu.
function previewShippingCost(form) {
  if (!form.shipping_rate) return null;
  if (form.shipping_rate_basis === "total") return Number(form.shipping_rate);
  const total = form.items.reduce((sum, row) => {
    const { totalWeightKg, totalVolumeM3 } = previewTotals(row);
    const value = form.shipping_rate_basis === "m3" ? totalVolumeM3 : totalWeightKg;
    return sum + (value || 0);
  }, 0);
  return total ? Number(form.shipping_rate) * total : null;
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
    // Mặt hàng/Số lượng/ĐVT lấy sẵn từ Yêu cầu giá gốc — Cung ứng sửa lại thành số thực mua sau khi
    // kiểm tra nguồn hàng (số ban đầu chỉ là số khách hỏi). Khi ĐVT đã tự là đơn vị khối lượng/thể
    // tích (tấn, kg, khối/m3...) thì Tổng trọng lượng/Tổng kích thước lấy thẳng từ SL này luôn, xem
    // unitKind().
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
          shipping_rate: form.shipping_rate || null,
          shipping_rate_basis: form.shipping_rate_basis,
          note: form.note,
          items: form.items.map((it) => {
            const kind = unitKind(it.unit);
            return {
              item_name: it.item_name,
              quantity: it.quantity || null,
              unit: it.unit,
              unit_cost: it.unit_cost || null,
              // ĐVT đã là khối (m3) thì 1 đơn vị = đúng 1 m3 (100x100x100cm) để Tổng kích thước ở
              // backend (SL × Dài×Rộng×Cao quy m3) ra thẳng bằng SL, khỏi bắt nhập lại kích thước.
              unit_length_cm: kind === "volume" ? 100 : toCm(it.unit_length, it.dimension_unit),
              unit_width_cm: kind === "volume" ? 100 : toCm(it.unit_width, it.dimension_unit),
              unit_height_cm: kind === "volume" ? 100 : toCm(it.unit_height, it.dimension_unit),
              // ĐVT đã là khối lượng (kg/tấn) thì "trọng lượng/đv" chính là quy đổi của 1 đơn vị đó
              // ra kg, để Tổng trọng lượng ở backend (SL × trọng lượng/đv) ra thẳng bằng SL.
              unit_weight_kg: kind === "weight" ? weightPerUnitKg(it.unit) : toKg(it.unit_weight, it.weight_unit),
            };
          }),
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
                        <td colSpan={6} style={{ background: "var(--surface-muted)", padding: "12px 16px" }}>
                          {quotes.length === 0 ? null : (
                            <>
                              <div className="cost-section-label">Câu trả lời đã có</div>
                              {quotes.map((q) => {
                                const address = [
                                  q.street_address, q.ward_name, q.district_name, q.province_name, q.country_name,
                                ]
                                  .filter(Boolean)
                                  .join(", ");
                                return (
                                  <div key={q.id} className="cost-quote-card">
                                    {(q.items || []).map((it) => {
                                      const kind = unitKind(it.unit);
                                      const dims = [it.unit_length_cm, it.unit_width_cm, it.unit_height_cm]
                                        .filter((v) => v !== null && v !== undefined)
                                        .join(" × ");
                                      return (
                                        <div key={it.id} className="cost-quote-item">
                                          <b>{it.item_name || "—"}</b>
                                          <span>{it.quantity ? `${it.quantity} ${it.unit || ""}` : "—"}</span>
                                          {it.unit_cost && <span>Giá vốn/đv: {formatMoney(it.unit_cost)}</span>}
                                          {kind !== "volume" && dims && <span>KT/đv: {dims} cm</span>}
                                          {kind !== "weight" && it.unit_weight_kg && <span>TL/đv: {it.unit_weight_kg} kg</span>}
                                          {it.total_cost && (
                                            <span className="highlight">Tổng giá vốn: {formatMoney(it.total_cost)}</span>
                                          )}
                                          {it.total_volume_m3 && (
                                            <span>
                                              Tổng KT: {Number(it.total_volume_m3).toLocaleString("vi-VN", { maximumFractionDigits: 3 })} m3
                                            </span>
                                          )}
                                          {it.total_weight_kg && (
                                            <span>Tổng TL: {formatWeightDisplay(it.unit, it.quantity, Number(it.total_weight_kg))}</span>
                                          )}
                                        </div>
                                      );
                                    })}
                                    {(q.items || []).length > 1 &&
                                      (() => {
                                        const grand = sumItemTotals(
                                          (q.items || []).map((it) => ({
                                            totalCost: Number(it.total_cost) || 0,
                                            totalVolumeM3: Number(it.total_volume_m3) || 0,
                                            totalWeightKg: Number(it.total_weight_kg) || 0,
                                          })),
                                        );
                                        return (
                                          <div className="cost-grand-total">
                                            <span>
                                              Tổng giá vốn (mọi mặt hàng): <b>{grand.totalCost ? formatMoney(grand.totalCost) : "—"}</b>
                                            </span>
                                            <span>
                                              Tổng kích thước:{" "}
                                              <b>
                                                {grand.totalVolumeM3
                                                  ? `${grand.totalVolumeM3.toLocaleString("vi-VN", { maximumFractionDigits: 3 })} m3`
                                                  : "—"}
                                              </b>
                                            </span>
                                            <span>
                                              Tổng trọng lượng: <b>{grand.totalWeightKg ? formatWeight(grand.totalWeightKg) : "—"}</b>
                                            </span>
                                          </div>
                                        );
                                      })()}
                                    <div className="cost-quote-meta">
                                      <span>Điểm nhận hàng: {address || "—"}</span>
                                      {q.shipping_rate && q.shipping_rate_basis !== "total" && (
                                        <span>
                                          Giá cước: {formatMoney(q.shipping_rate)}/{q.shipping_rate_basis}
                                        </span>
                                      )}
                                      <span className="highlight">
                                        Tổng giá vốn vận chuyển: {q.shipping_cost ? formatMoney(q.shipping_cost) : "—"}
                                      </span>
                                      <span>Người trả lời: {q.created_by_name ?? "—"}</span>
                                      {q.note && <span>{q.note}</span>}
                                    </div>
                                  </div>
                                );
                              })}
                            </>
                          )}

                          {canSupply() && (
                            <form onSubmit={(e) => handleAddQuote(e, item)} onClick={(e) => e.stopPropagation()}>
                              <div className="cost-item-card">
                                {form.items.map((row, i) => {
                                  const { kind } = previewTotals(row);
                                  const showLabel = i === 0;
                                  return (
                                    <div className="cost-item-fields" key={i}>
                                      <label style={{ minWidth: 160, flex: "1 1 160px" }}>
                                        {showLabel && "Mặt hàng"}
                                        <input
                                          placeholder="Tên mặt hàng"
                                          value={row.item_name}
                                          onChange={(e) => updateItemRow(i, "item_name", e.target.value)}
                                        />
                                      </label>
                                      <label style={{ width: 80 }}>
                                        {showLabel && "SL thực mua"}
                                        <input
                                          type="number" step="0.01"
                                          placeholder="vd: 5"
                                          value={row.quantity}
                                          onChange={(e) => updateItemRow(i, "quantity", e.target.value)}
                                        />
                                      </label>
                                      <label style={{ width: 80 }}>
                                        {showLabel && "ĐVT"}
                                        <input
                                          placeholder="vd: thùng"
                                          value={row.unit}
                                          onChange={(e) => updateItemRow(i, "unit", e.target.value)}
                                        />
                                      </label>
                                      {kind !== "volume" && (
                                        <>
                                          <label style={{ width: 70 }}>
                                            {showLabel && "Dài"}
                                            <input
                                              type="number" step="0.01"
                                              value={row.unit_length}
                                              onChange={(e) => updateItemRow(i, "unit_length", e.target.value)}
                                            />
                                          </label>
                                          <label style={{ width: 70 }}>
                                            {showLabel && "Rộng"}
                                            <input
                                              type="number" step="0.01"
                                              value={row.unit_width}
                                              onChange={(e) => updateItemRow(i, "unit_width", e.target.value)}
                                            />
                                          </label>
                                          <label style={{ width: 70 }}>
                                            {showLabel && "Cao"}
                                            <input
                                              type="number" step="0.01"
                                              value={row.unit_height}
                                              onChange={(e) => updateItemRow(i, "unit_height", e.target.value)}
                                            />
                                          </label>
                                          <label style={{ width: 72 }}>
                                            {showLabel && "Đơn vị"}
                                            <select
                                              value={row.dimension_unit}
                                              onChange={(e) => updateItemRow(i, "dimension_unit", e.target.value)}
                                            >
                                              <option value="cm">cm</option>
                                              <option value="m">m</option>
                                            </select>
                                          </label>
                                        </>
                                      )}

                                      {kind !== "weight" && (
                                        <>
                                          <label style={{ width: 95 }}>
                                            {showLabel && "Trọng lượng/đv"}
                                            <input
                                              type="number" step="0.01"
                                              value={row.unit_weight}
                                              onChange={(e) => updateItemRow(i, "unit_weight", e.target.value)}
                                            />
                                          </label>
                                          <label style={{ width: 72 }}>
                                            {showLabel && "Đơn vị"}
                                            <select
                                              value={row.weight_unit}
                                              onChange={(e) => updateItemRow(i, "weight_unit", e.target.value)}
                                            >
                                              <option value="kg">kg</option>
                                              <option value="tấn">tấn</option>
                                            </select>
                                          </label>
                                        </>
                                      )}

                                      <label style={{ width: 110 }}>
                                        {showLabel && "Giá vốn/đv"}
                                        <MoneyInput
                                          value={row.unit_cost}
                                          onChange={(v) => updateItemRow(i, "unit_cost", v)}
                                        />
                                      </label>

                                      {form.items.length > 1 && (
                                        <button
                                          type="button"
                                          className="link-btn"
                                          style={{ alignSelf: "center" }}
                                          onClick={() => removeItemRow(i)}
                                        >
                                          Xoá
                                        </button>
                                      )}
                                    </div>
                                  );
                                })}
                              </div>
                              {(() => {
                                const grand = sumItemTotals(form.items.map(previewTotals));
                                return (
                                  <div className="cost-item-fields cost-grand-total" style={{ gap: "8px 12px" }}>
                                    <div style={{ minWidth: 160, flex: "1 1 160px" }}>
                                      <button type="button" className="link-btn" onClick={addItemRow}>
                                        + Thêm mặt hàng
                                      </button>
                                    </div>
                                    <div style={{ width: 80 }} />
                                    <div style={{ width: 80 }} />
                                    {/* Thẳng cột với Dài+Rộng+Cao+Đơn vị (70+70+70+72 + 3 khoảng cách 12px) */}
                                    <div className="cost-total-box" style={{ width: 318 }}>
                                      Tổng kích thước:{" "}
                                      {grand.totalVolumeM3
                                        ? `${grand.totalVolumeM3.toLocaleString("vi-VN", { maximumFractionDigits: 3 })} m3`
                                        : "—"}
                                    </div>
                                    {/* Thẳng cột với Trọng lượng/đv + Đơn vị (95+72 + 1 khoảng cách 12px) */}
                                    <div className="cost-total-box" style={{ width: 179 }}>
                                      Tổng trọng lượng: {grand.totalWeightKg ? formatWeight(grand.totalWeightKg) : "—"}
                                    </div>
                                    {/* Thẳng cột với Giá vốn/đv */}
                                    <div className="cost-total-box" style={{ width: 110 }}>
                                      Tổng giá vốn: {grand.totalCost ? formatMoney(grand.totalCost) : "—"}
                                    </div>
                                  </div>
                                );
                              })()}

                              <div className="cost-item-card" style={{ marginTop: 6 }}>
                                <div className="cost-item-fields">
                                  <label style={{ flexBasis: "100%" }}>
                                    <span>
                                      Điểm nhận hàng (nơi NCC giao tới)
                                      {item.price_request_delivery_address && (
                                        <span className="muted" style={{ fontWeight: 400, fontSize: 11 }}>
                                          {" "}
                                          — giao tới khách (theo Yêu cầu giá): {item.price_request_delivery_address}
                                        </span>
                                      )}
                                    </span>
                                    <AddressFields value={form} onChange={(addr) => setForm({ ...form, ...addr })} />
                                  </label>
                                  <label style={{ width: 150 }}>
                                    {form.shipping_rate_basis === "total" ? "Tổng giá vốn vận chuyển" : "Giá cước vận chuyển"}
                                    <MoneyInput
                                      placeholder="Tự tra, nhập tay"
                                      value={form.shipping_rate}
                                      onChange={(v) => setForm({ ...form, shipping_rate: v })}
                                    />
                                  </label>
                                  <label style={{ width: 130 }}>
                                    Tính theo
                                    <select
                                      value={form.shipping_rate_basis}
                                      onChange={(e) => setForm({ ...form, shipping_rate_basis: e.target.value })}
                                    >
                                      <option value="kg">Đơn giá/kg</option>
                                      <option value="m3">Đơn giá/m3</option>
                                      <option value="total">Tổng cố định</option>
                                    </select>
                                  </label>
                                  {form.shipping_rate_basis !== "total" && (
                                    <label style={{ minWidth: 150, flex: "1 1 150px" }}>
                                      Tổng giá vốn vận chuyển
                                      <div style={{ padding: "7px 0", fontSize: 13, fontWeight: 700 }}>
                                        {previewShippingCost(form) !== null ? formatMoney(previewShippingCost(form)) : "—"}
                                        <span
                                          className="muted"
                                          style={{ fontWeight: 400, fontSize: 11, marginLeft: 6 }}
                                        >
                                          (= Giá cước × tổng {form.shipping_rate_basis === "m3" ? "kích thước" : "trọng lượng"})
                                        </span>
                                      </div>
                                    </label>
                                  )}
                                </div>
                              </div>

                              <div style={{ display: "flex", gap: 10, alignItems: "flex-start", marginTop: 6 }}>
                                <textarea
                                  rows={1}
                                  placeholder="Mô tả thêm (không bắt buộc)"
                                  style={{ flex: 1, resize: "vertical" }}
                                  value={form.note}
                                  onChange={(e) => setForm({ ...form, note: e.target.value })}
                                />
                                <button type="submit" disabled={saving} style={{ flexShrink: 0 }}>
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
