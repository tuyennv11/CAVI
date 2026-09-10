import { useEffect, useState } from "react";
import { apiFetch } from "../api";

// Chọn Quốc gia → Tỉnh/Thành → Quận/Huyện → Phường/Xã theo tầng (chọn cấp trên mới hiện cấp dưới),
// dùng chung ở mọi nơi cần địa chỉ chuẩn (Hồ sơ nhân viên, sau này Đối tác/điểm giao hàng...).
// `value`: { country, province, district, ward, street_address } (id hoặc "" nếu chưa chọn).
export default function AddressFields({ value, onChange }) {
  const [countries, setCountries] = useState([]);
  const [provinces, setProvinces] = useState([]);
  const [districts, setDistricts] = useState([]);
  const [wards, setWards] = useState([]);

  useEffect(() => {
    apiFetch("/api/geo/countries/").then(setCountries);
  }, []);

  useEffect(() => {
    if (!value.country) {
      setProvinces([]);
      return;
    }
    apiFetch(`/api/geo/provinces/?country=${value.country}`).then(setProvinces);
  }, [value.country]);

  useEffect(() => {
    if (!value.province) {
      setDistricts([]);
      return;
    }
    apiFetch(`/api/geo/districts/?province=${value.province}`).then(setDistricts);
  }, [value.province]);

  useEffect(() => {
    if (!value.district) {
      setWards([]);
      return;
    }
    apiFetch(`/api/geo/wards/?district=${value.district}`).then(setWards);
  }, [value.district]);

  return (
    <div className="address-fields">
      <select
        value={value.country || ""}
        onChange={(e) => onChange({ ...value, country: e.target.value, province: "", district: "", ward: "" })}
      >
        <option value="">— Quốc gia —</option>
        {countries.map((c) => (
          <option key={c.id} value={c.id}>
            {c.name}
          </option>
        ))}
      </select>
      <select
        value={value.province || ""}
        disabled={!value.country || provinces.length === 0}
        onChange={(e) => onChange({ ...value, province: e.target.value, district: "", ward: "" })}
      >
        <option value="">— Tỉnh/Thành phố —</option>
        {provinces.map((p) => (
          <option key={p.id} value={p.id}>
            {p.name}
          </option>
        ))}
      </select>
      <select
        value={value.district || ""}
        disabled={!value.province || districts.length === 0}
        onChange={(e) => onChange({ ...value, district: e.target.value, ward: "" })}
      >
        <option value="">— Quận/Huyện —</option>
        {districts.map((d) => (
          <option key={d.id} value={d.id}>
            {d.name}
          </option>
        ))}
      </select>
      <select
        value={value.ward || ""}
        disabled={!value.district || wards.length === 0}
        onChange={(e) => onChange({ ...value, ward: e.target.value })}
      >
        <option value="">— Phường/Xã —</option>
        {wards.map((w) => (
          <option key={w.id} value={w.id}>
            {w.name}
          </option>
        ))}
      </select>
      <input
        placeholder="Số nhà, đường"
        value={value.street_address || ""}
        onChange={(e) => onChange({ ...value, street_address: e.target.value })}
      />
    </div>
  );
}
