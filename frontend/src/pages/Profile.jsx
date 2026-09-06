import { useEffect, useState } from "react";
import { apiFetch } from "../api";
import Avatar from "../components/Avatar";

export default function Profile() {
  const [profile, setProfile] = useState(null);
  const [form, setForm] = useState({ job_title: "", company_code: "" });
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  async function load() {
    try {
      const data = await apiFetch("/api/hr/profile/me/");
      setProfile(data);
      setForm({ job_title: data.job_title, company_code: data.company_code });
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
      const data = await apiFetch("/api/hr/profile/me/", { method: "PATCH", body: JSON.stringify(form) });
      setProfile(data);
      setSaved(true);
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  if (error) return <p className="error">{error}</p>;
  if (!profile) return <p className="muted">Đang tải...</p>;

  return (
    <div>
      <div className="page-head">
        <h1>Cá nhân</h1>
      </div>

      <div className="profile-header">
        <Avatar name={profile.full_name} size="lg" />
        <div>
          <h1>{profile.full_name}</h1>
          <div className="company">
            {profile.company_code} · {profile.job_title || "Chưa cập nhật chức vụ"}
          </div>
          <div className="profile-pills" style={{ marginTop: 10 }}>
            <span className="profile-pill">👤 {profile.username}</span>
            <span className="profile-pill">✉️ {profile.email}</span>
          </div>
        </div>
      </div>

      <div className="panel">
        <h2>Cập nhật hồ sơ</h2>
        <form className="field-grid" onSubmit={handleSave} style={{ maxWidth: 380 }}>
          <label>
            Mã công ty
            <input
              value={form.company_code}
              onChange={(e) => setForm({ ...form, company_code: e.target.value })}
            />
          </label>
          <label>
            Chức vụ
            <input value={form.job_title} onChange={(e) => setForm({ ...form, job_title: e.target.value })} />
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
