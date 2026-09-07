import { useState } from "react";
import { COUNTRY_CODES, formatPhone, parsePhone } from "../countryCodes";

// Ô nhập số điện thoại chuẩn quốc tế: chọn mã vùng riêng + gõ số riêng,
// ghép lại thành 1 chuỗi (vd "+84 912345678") qua onChange.
export default function PhoneInput({ value, onChange, placeholder }) {
  const parsed = parsePhone(value);
  const [dial, setDial] = useState(parsed.dial);
  const [local, setLocal] = useState(parsed.local);

  function handleDialChange(newDial) {
    setDial(newDial);
    onChange(formatPhone(newDial, local));
  }

  function handleLocalChange(newLocal) {
    const digitsOnly = newLocal.replace(/[^\d]/g, "");
    setLocal(digitsOnly);
    onChange(formatPhone(dial, digitsOnly));
  }

  return (
    <div className="phone-input">
      <select
        className="phone-input-dial"
        value={dial}
        onChange={(e) => handleDialChange(e.target.value)}
        aria-label="Mã vùng"
      >
        {COUNTRY_CODES.map((c) => (
          <option key={c.code} value={c.dial}>
            {c.flag} {c.dial} {c.name}
          </option>
        ))}
      </select>
      <input
        type="tel"
        inputMode="numeric"
        placeholder={placeholder || "912 345 678"}
        value={local}
        onChange={(e) => handleLocalChange(e.target.value)}
      />
    </div>
  );
}
