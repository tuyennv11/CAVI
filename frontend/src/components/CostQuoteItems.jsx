import MoneyInput from "./MoneyInput";
import { formatMoney } from "../constants";

function Metric({ label, children, money = false }) {
  return <div className={`cq-metric${money ? " cq-metric-money" : ""}`}>
    <span>{label}</span><output aria-live="polite">{children}</output>
  </div>;
}

export default function CostQuoteItems({ items, updateItemRow, addItemRow, removeItemRow, previewTotals, sumItemTotals, formatWeight }) {
  const grand = sumItemTotals(items.map(previewTotals));
  const volume = (value) => value ? `${value.toLocaleString("vi-VN", { maximumFractionDigits: 3 })} m³` : "—";
  return <div className="cq-editor">
    {items.map((row, i) => {
      const total = previewTotals(row);
      const numberField = (label, field) => <label>{label}<input type="number" min="0" step="any" value={row[field]} onChange={(e) => updateItemRow(i, field, e.target.value)} /></label>;
      return <div className={`cq-line cq-line-${total.kind}`} key={i}>
        <div className="cq-product">
          <label>Mặt hàng<input placeholder="Tên mặt hàng" value={row.item_name} onChange={(e) => updateItemRow(i, "item_name", e.target.value)} /></label>
          {items.length > 1 && <button type="button" className="link-btn cq-remove" onClick={() => removeItemRow(i)}>Xoá mặt hàng {i + 1}</button>}
        </div>
        <div className="cq-quantity">
          <div className="cq-pair">
            {numberField("SL thực mua", "quantity")}
            <label>ĐVT<input placeholder="tấn, kg, kiện…" value={row.unit} onChange={(e) => updateItemRow(i, "unit", e.target.value)} /></label>
          </div>
          <Metric label="Tổng trọng lượng">{total.totalWeightKg !== null ? formatWeight(total.totalWeightKg) : "—"}</Metric>
          {total.kind === "volume" && <Metric label="Tổng thể tích">{volume(total.totalVolumeM3)}</Metric>}
        </div>
        {total.kind !== "volume" && <div className="cq-dimensions">
          <div className="cq-dimension-fields">
            {numberField("Dài", "unit_length")}{numberField("Rộng", "unit_width")}{numberField("Cao", "unit_height")}
            <label>Đơn vị<select value={row.dimension_unit} onChange={(e) => updateItemRow(i, "dimension_unit", e.target.value)}><option value="cm">cm</option><option value="m">m</option></select></label>
          </div>
          <Metric label="Tổng thể tích">{volume(total.totalVolumeM3)}</Metric>
        </div>}
        {total.kind !== "weight" && <div className="cq-weight">
          <div className="cq-pair">
            {numberField("Trọng lượng/đv", "unit_weight")}
            <label>Đơn vị<select value={row.weight_unit} onChange={(e) => updateItemRow(i, "weight_unit", e.target.value)}><option value="kg">kg</option><option value="tấn">tấn</option></select></label>
          </div>
        </div>}
        <div className="cq-price">
          <label>Giá vốn/đv<MoneyInput value={row.unit_cost} placeholder="Nhập đơn giá" onChange={(value) => updateItemRow(i, "unit_cost", value)} /></label>
          <Metric label={items.length > 1 ? "Thành tiền" : "Tổng giá vốn"} money>{total.totalCost !== null ? formatMoney(total.totalCost) : "—"}</Metric>
        </div>
      </div>;
    })}
    <div className="cq-items-footer">
      <button type="button" className="link-btn" onClick={addItemRow}>+ Thêm mặt hàng</button>
      {items.length > 1 && <div className="cq-summary">
        <Metric label="Tổng trọng lượng">{grand.totalWeightKg ? formatWeight(grand.totalWeightKg) : "—"}</Metric>
        <Metric label="Tổng thể tích">{volume(grand.totalVolumeM3)}</Metric>
        <Metric label="Tổng giá vốn" money>{items.some((row) => previewTotals(row).totalCost !== null) ? formatMoney(grand.totalCost) : "—"}</Metric>
      </div>}
    </div>
  </div>;
}
