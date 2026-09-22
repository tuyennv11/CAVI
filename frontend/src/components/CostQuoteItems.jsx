import MoneyInput from "./MoneyInput";
import { formatMoney } from "../constants";

function Metric({ label, children, money = false }) {
  return <div className={money ? "cq-total cq-total-money" : "cq-total"}>
    <span>{label}</span><output aria-live="polite">{children}</output>
  </div>;
}

export default function CostQuoteItems({ items, updateItemRow, addItemRow, removeItemRow, previewTotals, sumItemTotals, formatWeight }) {
  const totals = items.map(previewTotals);
  const grand = sumItemTotals(totals);
  const showDimensions = totals.some((total) => total.kind !== "volume");
  const showWeight = totals.some((total) => total.kind !== "weight");
  const middleColumns = (showDimensions ? 4 : 0) + (showWeight ? 2 : 0);
  return <div className="cq-editor">
    <table className="cq-table" style={{ minWidth: showDimensions && showWeight ? 1100 : 920 }} aria-label="Mặt hàng báo giá vốn">
      <colgroup>
        <col className="cq-col-product" /><col className="cq-col-quantity" /><col className="cq-col-unit" />
        {showDimensions && <><col className="cq-col-dimension" /><col className="cq-col-dimension" /><col className="cq-col-dimension" /><col className="cq-col-unit" /></>}
        {showWeight && <><col className="cq-col-weight" /><col className="cq-col-unit" /></>}
        <col className="cq-col-price" /><col className="cq-col-amount" /><col className="cq-col-remove" />
      </colgroup>
      <thead><tr>
        <th scope="col">Mặt hàng</th><th scope="col">SL thực mua</th><th scope="col">ĐVT</th>
        {showDimensions && <><th scope="col">Dài</th><th scope="col">Rộng</th><th scope="col">Cao</th><th scope="col">Đơn vị</th></>}
        {showWeight && <><th scope="col">Trọng lượng/đv</th><th scope="col">Đơn vị</th></>}
        <th scope="col">Giá vốn/đv</th><th scope="col" className="cq-amount">Thành tiền</th><th scope="col"><span className="cq-sr-only">Thao tác</span></th>
      </tr></thead>
      <tbody>{items.map((row, i) => {
        const total = totals[i];
        const label = (name) => name + " mặt hàng " + (i + 1);
        const numberInput = (name, field) => <input aria-label={label(name)} type="number" min="0" step="any" value={row[field]} onChange={(e) => updateItemRow(i, field, e.target.value)} />;
        return <tr key={i}>
          <td><input aria-label={label("Tên")} placeholder="Tên mặt hàng" value={row.item_name} onChange={(e) => updateItemRow(i, "item_name", e.target.value)} /></td>
          <td>{numberInput("Số lượng", "quantity")}</td>
          <td><input aria-label={label("ĐVT")} placeholder="ĐVT" value={row.unit} onChange={(e) => updateItemRow(i, "unit", e.target.value)} /></td>
          {showDimensions && (total.kind !== "volume" ? <>
            <td>{numberInput("Dài", "unit_length")}</td><td>{numberInput("Rộng", "unit_width")}</td><td>{numberInput("Cao", "unit_height")}</td>
            <td><select aria-label={label("Đơn vị kích thước")} value={row.dimension_unit} onChange={(e) => updateItemRow(i, "dimension_unit", e.target.value)}><option value="cm">cm</option><option value="m">m</option></select></td>
          </> : <td colSpan={4} className="cq-not-needed" title="Thể tích được tính từ số lượng và ĐVT">—</td>)}
          {showWeight && (total.kind !== "weight" ? <>
            <td>{numberInput("Trọng lượng/đv", "unit_weight")}</td>
            <td><select aria-label={label("Đơn vị trọng lượng")} value={row.weight_unit} onChange={(e) => updateItemRow(i, "weight_unit", e.target.value)}><option value="kg">kg</option><option value="tấn">tấn</option></select></td>
          </> : <td colSpan={2} className="cq-not-needed" title="Trọng lượng được tính từ số lượng và ĐVT">—</td>)}
          <td><label><span className="cq-sr-only">{label("Giá vốn/đv")}</span><MoneyInput value={row.unit_cost} placeholder="Đơn giá" onChange={(value) => updateItemRow(i, "unit_cost", value)} /></label></td>
          <td className="cq-amount"><output aria-live="polite">{total.totalCost !== null ? formatMoney(total.totalCost) : "—"}</output></td>
          <td>{items.length > 1 && <button type="button" className="cq-remove" aria-label={label("Xoá")} title={label("Xoá")} onClick={() => removeItemRow(i)}>×</button>}</td>
        </tr>;
      })}</tbody>
      <tfoot><tr>
        <td><button type="button" className="link-btn" onClick={addItemRow}>+ Thêm mặt hàng</button></td>
        <td colSpan={2}><Metric label="Tổng trọng lượng">{grand.totalWeightKg ? formatWeight(grand.totalWeightKg) : "—"}</Metric></td>
        <td colSpan={middleColumns}><Metric label="Tổng thể tích">{grand.totalVolumeM3 ? grand.totalVolumeM3.toLocaleString("vi-VN", { maximumFractionDigits: 3 }) + " m³" : "—"}</Metric></td>
        <td colSpan={2}><Metric label="Tổng giá vốn" money>{totals.some((total) => total.totalCost !== null) ? formatMoney(grand.totalCost) : "—"}</Metric></td>
        <td />
      </tr></tfoot>
    </table>
  </div>;
}
