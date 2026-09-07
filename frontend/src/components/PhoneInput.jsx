import { useState } from "react";
import { COUNTRY_CODES, DEFAULT_LEN, formatPhone, parsePhone } from "../countryCodes";

function findCountry(dial) {
  return COUNTRY_CODES.find((c) => c.dial === dial) || COUNTRY_CODES[0];
}

// Ô nhập số điện thoại chuẩn quốc tế: chọn mã vùng riêng + gõ số riêng,
// giới hạn đúng số chữ số theo chuẩn quốc gia đó, ghép lại thành 1 chuỗi
// (vd "+84 912345678") qua onChange.
export default function PhoneInput({ value, onChange, placeholder }) {
  const parsed = parsePhone(value);
  const [dial, setDial] = useState(parsed.dial);
  const [local, setLocal] = useState(parsed.local);

  const country = findCountry(dial);
  const [min, max] = country.len || DEFAULT_LEN;

  // Số chữ số "thật" (bỏ đúng 1 số 0 đầu nếu có) — đây là con số đem so với chuẩn quốc gia.
  const significantLength = local.replace(/^0/, "").length;
  const tooShort = local.length > 0 && significantLength < min;

  function handleDialChange(newDial) {
    const newCountry = findCountry(newDial);
    const [, newMax] = newCountry.len || DEFAULT_LEN;
    const hasLeadingZero = local.startsWith("0");
    const cappedLocal = local.slice(0, newMax + (hasLeadingZero ? 1 : 0));
    setDial(newDial);
    setLocal(cappedLocal);
    onChange(formatPhone(newDial, cappedLocal));
  }

  function handleLocalChange(raw) {
    let digits = raw.replace(/\D/g, "");
    const hasLeadingZero = digits.startsWith("0");
    const maxAllowed = max + (hasLeadingZero ? 1 : 0);
    if (digits.length > maxAllowed) digits = digits.slice(0, maxAllowed);
    setLocal(digits);
    onChange(formatPhone(dial, digits));
  }

  return (
    <div>
      <div className="phone-input">
        <select
          className="phone-input-dial"
          value={dial}
          onChange={(e) => handleDialChange(e.target.value)}
          aria-label="Mã vùng"
        >
          {COUNTRY_CODES.map((c) => (
            <option key={c.code} value={c.dial}>
              {c.name} {c.dial}
            </option>
          ))}
        </select>
        <input
          type="tel"
          inputMode="numeric"
          placeholder={placeholder || "912345678"}
          value={local}
          onChange={(e) => handleLocalChange(e.target.value)}
        />
      </div>
      <div className={`phone-input-hint${tooShort ? " error" : ""}`}>
        {tooShort
          ? `${country.name} cần ${min === max ? min : `${min}-${max}`} chữ số, đang nhập ${significantLength}`
          : `${country.name}: ${min === max ? `${min} chữ số` : `${min}-${max} chữ số`} (chưa tính số 0 đầu)`}
      </div>
    </div>
  );
}
