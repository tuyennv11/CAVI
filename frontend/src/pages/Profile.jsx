import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { apiFetch, apiUpload } from "../api";
import AddressFields from "../components/AddressFields";
import Avatar from "../components/Avatar";
import { EDUCATION_LEVEL_LABEL, GENDER_LABEL } from "../constants";

const DATE_FIELDS = ["date_of_birth"];

export default function Profile() {
  const [profile, setProfile] = useState(null);
  const [form, setForm] = useState(null);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  async function load() {
    try {
      const data = await apiFetch("/api/hr/profile/me/");
      setProfile(data);
      setForm({
        company_code: data.company_code || "",
        preferred_name: data.preferred_name || "",
        gender: data.gender || "",
        phone: data.phone || "",
        date_of_birth: data.date_of_birth || "",
        id_number: data.id_number || "",
        country: data.country || "",
        province: data.province || "",
        district: data.district || "",
        ward: data.ward || "",
        street_address: data.street_address || "",
        education_level: data.education_level || "",
        major: data.major || "",
        skills: data.skills || "",
      });
    } catch (err) {
      setError(err.message);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function handleSave(e) {
    e.preventDefault();
    setSaving(true);
    setSaved(false);
    try {
      const payload = { ...form };
      ["country", "province", "district", "ward", ...DATE_FIELDS].forEach((k) => {
        if (payload[k] === "") payload[k] = null;
      });
      const data = await apiFetch("/api/hr/profile/me/", { method: "PATCH", body: JSON.stringify(payload) });
      setProfile(data);
      setSaved(true);
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  async function handleAvatarChange(e) {
    const file = e.target.files[0];
    if (!file) return;
    const fd = new FormData();
    fd.set("avatar", file);
    try {
      const data = await apiUpload("/api/hr/profile/me/", fd, "PATCH");
      setProfile(data);
    } catch (err) {
      setError(err.message);
    }
  }

  if (error) return <p className="error">{error}</p>;
  if (!profile || !form) return <p className="muted">Đang tải...</p>;

  return (
    <div>
      <div className="page-head">
        <h1>Cá nhân</h1>
      </div>

      <div className="profile-header">
        <label style={{ cursor: "pointer" }}>
          <Avatar name={profile.full_name} photo={profile.avatar} size="lg" />
          <input type="file" accept="image/*" hidden onChange={handleAvatarChange} />
        </label>
        <div>
          <h1>{profile.preferred_name || profile.full_name}</h1>
          <div className="company">
            {profile.employee_code} · {profile.job_title || "Chưa cập nhật chức vụ"}
          </div>
          <div className="profile-pills" style={{ marginTop: 10 }}>
            <span className="profile-pill">👤 {profile.username}</span>
            <span className="profile-pill">✉️ {profile.email}</span>
          </div>
          <Link to={`/employees/${profile.id}`} className="muted" style={{ display: "inline-block", marginTop: 8, fontSize: 12.5 }}>
            Xem hồ sơ đầy đủ (gồm cả Lương, chỉ mình bạn xem được) →
          </Link>
        </div>
      </div>

      <div className="panel">
        <h2>Cập nhật hồ sơ</h2>
        <form className="field-grid" onSubmit={handleSave} style={{ maxWidth: 520 }}>
          <label>
            Mã công ty
            <input
              value={form.company_code}
              onChange={(e) => setForm({ ...form, company_code: e.target.value })}
            />
          </label>
          <label>
            Tên thường gọi
            <input value={form.preferred_name} onChange={(e) => setForm({ ...form, preferred_name: e.target.value })} />
          </label>
          <label>
            Giới tính
            <select value={form.gender} onChange={(e) => setForm({ ...form, gender: e.target.value })}>
              <option value="">—</option>
              {Object.entries(GENDER_LABEL).map(([v, l]) => (
                <option key={v} value={v}>
                  {l}
                </option>
              ))}
            </select>
          </label>
          <label>
            Ngày sinh
            <input type="date" value={form.date_of_birth} onChange={(e) => setForm({ ...form, date_of_birth: e.target.value })} />
          </label>
          <label>
            Số điện thoại
            <input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
          </label>
          <label>
            Số CCCD/CMND
            <input value={form.id_number} onChange={(e) => setForm({ ...form, id_number: e.target.value })} />
          </label>
          <label>
            Địa chỉ
            <AddressFields value={form} onChange={(addr) => setForm({ ...form, ...addr })} />
          </label>
          <label>
            Trình độ
            <select value={form.education_level} onChange={(e) => setForm({ ...form, education_level: e.target.value })}>
              <option value="">—</option>
              {Object.entries(EDUCATION_LEVEL_LABEL).map(([v, l]) => (
                <option key={v} value={v}>
                  {l}
                </option>
              ))}
            </select>
          </label>
          <label>
            Chuyên môn
            <input value={form.major} onChange={(e) => setForm({ ...form, major: e.target.value })} />
          </label>
          <label>
            Kỹ năng
            <textarea rows={2} placeholder="Cách nhau bằng dấu phẩy" value={form.skills} onChange={(e) => setForm({ ...form, skills: e.target.value })} />
          </label>
          <div className="modal-actions">
            {saved && <span className="muted" style={{ alignSelf: "center", fontSize: 12.5 }}>Đã lưu</span>}
            <button type="submit" disabled={saving}>
              {saving ? "Đang lưu..." : "Lưu"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
