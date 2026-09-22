export default function QuoteTerms({ form, setForm, freight = false }) {
  const set = (key, value) => setForm((old) => ({ ...old, [key]: value }));
  return <div className="market-terms">
    <label>{freight ? "Đơn vị vận chuyển" : "Nhà cung cấp"}<input required={form.confirmed || freight} value={form[freight ? "carrier_name" : "supplier_name"] || ""} onChange={(e) => set(freight ? "carrier_name" : "supplier_name", e.target.value)} placeholder={freight ? "Tên nhà vận chuyển" : "Tên NCC / nguồn hàng"} /></label>
    <label>Mức xác nhận<select value={form.confirmed ? "yes" : "no"} onChange={(e) => set("confirmed", e.target.value === "yes")}><option value="no">Giá tham khảo</option><option value="yes">NCC đã xác nhận</option></select></label>
    <label>Hiệu lực đến<input type="date" required={form.confirmed} value={form.valid_until || ""} onChange={(e) => set("valid_until", e.target.value)} /></label>
    <label>Thuế<select value={form.tax_basis || "unknown"} onChange={(e) => set("tax_basis", e.target.value)}><option value="unknown">Chưa rõ thuế</option><option value="included">Đã gồm thuế</option><option value="excluded">Chưa gồm thuế</option></select></label>
    {freight ? <>
      <label>Số ngày giao<input type="number" min="0" step="1" value={form.delivery_days ?? ""} onChange={(e) => set("delivery_days", e.target.value)} /></label>
      <label className="market-wide">Phạm vi dịch vụ<input value={form.terms || ""} onChange={(e) => set("terms", e.target.value)} placeholder="Bốc xếp, giao tận nơi, phí đã bao gồm…" /></label>
    </> : <>
      <label>Ngày có hàng<input type="date" value={form.available_at || ""} onChange={(e) => set("available_at", e.target.value)} /></label>
      <label>Thanh toán<input value={form.payment_terms || ""} onChange={(e) => set("payment_terms", e.target.value)} placeholder="Đặt cọc, công nợ…" /></label>
      <label className="market-wide">Điều kiện giao nhận<input value={form.delivery_terms || ""} onChange={(e) => set("delivery_terms", e.target.value)} placeholder="Quy cách cam kết, thời gian giao, phí bao gồm…" /></label>
    </>}
  </div>;
}
