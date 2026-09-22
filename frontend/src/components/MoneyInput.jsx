// Ô nhập tiền: gõ số thường, tự hiện dấu chấm ngăn cách nghìn + hậu tố "đ" ngay trong ô — value/
// onChange vẫn truyền/nhận chuỗi số thô (không dấu chấm) để nơi dùng khỏi phải tự parse lại.
export default function MoneyInput({ value, onChange, placeholder, style }) {
  function handleChange(e) {
    const digits = e.target.value.replace(/\D/g, "");
    onChange(digits);
  }

  const display = value ? Number(value).toLocaleString("vi-VN") : "";

  return (
    <div className="money-input" style={style}>
      <input type="text" inputMode="numeric" value={display} placeholder={placeholder} onChange={handleChange} />
      <span className="money-input-suffix">đ</span>
    </div>
  );
}
