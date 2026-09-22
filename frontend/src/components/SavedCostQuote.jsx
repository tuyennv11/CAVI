import { formatMoney } from "../constants";

const hasValue = (value) => value !== null && value !== undefined && value !== "";
const number = (value, digits = 3) => hasValue(value)
  ? Number(value).toLocaleString("vi-VN", { maximumFractionDigits: digits }) : "—";

export default function SavedCostQuote({ quote, index, formatWeight, deliveryAddress }) {
  const rows = quote.items || [];
  const sum = (field) => rows.reduce((total, row) => total + (Number(row[field]) || 0), 0);
  const total = (field, format) => rows.some((row) => hasValue(row[field])) ? format(sum(field)) : "—";
  const address = [quote.street_address, quote.ward_name, quote.district_name, quote.province_name, quote.country_name].filter(Boolean).join(", ");
  return <section className="cq-saved">
    <header className="cq-saved-head">
      <strong>Câu trả lời {index + 1}</strong>
      <span>Người trả lời: {quote.created_by_name || "—"}</span>
    </header>
    <div className="cq-saved-scroll">
      <table className="cq-saved-table" aria-label={`Mặt hàng trong câu trả lời ${index + 1}`}>
        <thead><tr><th scope="col">Mặt hàng</th><th scope="col">Số lượng</th><th scope="col">Giá vốn/đv</th><th scope="col">Trọng lượng</th><th scope="col">Thể tích</th><th scope="col">Thành tiền</th></tr></thead>
        <tbody>{rows.map((row) => <tr key={row.id}>
          <td><strong>{row.item_name || "—"}</strong></td>
          <td>{number(row.quantity)} {row.unit}</td>
          <td>{hasValue(row.unit_cost) ? formatMoney(row.unit_cost) : "—"}</td>
          <td>{hasValue(row.total_weight_kg) ? formatWeight(Number(row.total_weight_kg)) : "—"}</td>
          <td>{hasValue(row.total_volume_m3) ? `${number(row.total_volume_m3)} m³` : "—"}</td>
          <td><strong>{hasValue(row.total_cost) ? formatMoney(row.total_cost) : "—"}</strong></td>
        </tr>)}</tbody>
        <tfoot><tr>
          <th scope="row" colSpan={3}>Tổng tiền hàng</th>
          <td>{total("total_weight_kg", formatWeight)}</td>
          <td>{total("total_volume_m3", (value) => `${number(value)} m³`)}</td>
          <td className="cq-saved-total">{total("total_cost", formatMoney)}</td>
        </tr></tfoot>
      </table>
    </div>
    <div className="cq-saved-shipping">
      <div className="cq-saved-route">
        <div><span className="cq-saved-label">Điểm nhận hàng</span><p>{address || "Chưa có địa chỉ"}</p></div>
        <div><span className="cq-saved-label">Điểm giao hàng · Theo Yêu cầu giá</span><p>{deliveryAddress || "Chưa có địa chỉ giao hàng"}</p></div>
      </div>
      <div><span className="cq-saved-label">Giá cước</span><p>{hasValue(quote.shipping_rate) ? `${formatMoney(quote.shipping_rate)}${quote.shipping_rate_basis === "total" ? " · Trọn gói" : `/${quote.shipping_rate_basis === "m3" ? "m³" : "kg"}`}` : "—"}</p></div>
      <div className="cq-saved-freight"><span className="cq-saved-label">Tổng giá vốn vận chuyển</span><p>{hasValue(quote.shipping_cost) ? formatMoney(quote.shipping_cost) : "—"}</p></div>
    </div>
    {quote.note && <p className="cq-saved-note"><span className="cq-saved-label">Ghi chú: </span>{quote.note}</p>}
    <details className="cq-packing">
      <summary>Chi tiết kích thước & trọng lượng đơn vị</summary>
      <div className="cq-saved-scroll"><table className="cq-saved-table" aria-label="Chi tiết quy cách">
        <thead><tr><th scope="col">Mặt hàng</th><th scope="col">Dài × Rộng × Cao (cm)</th><th scope="col">Trọng lượng/đv (kg)</th></tr></thead>
        <tbody>{rows.map((row) => <tr key={row.id}>
          <td>{row.item_name || "—"}</td>
          <td>{[row.unit_length_cm, row.unit_width_cm, row.unit_height_cm].map((value) => number(value)).join(" × ")}</td>
          <td>{number(row.unit_weight_kg)}</td>
        </tr>)}</tbody>
      </table></div>
    </details>
  </section>;
}
