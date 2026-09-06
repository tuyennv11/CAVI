import { useEffect, useState } from "react";
import { apiFetch } from "../api";
import { useAuth } from "../AuthContext";
import Modal from "../components/Modal";

function formatDate(iso) {
  return new Date(iso).toLocaleString("vi-VN");
}

export default function Notices() {
  const { user } = useAuth();
  const [notices, setNotices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showNew, setShowNew] = useState(false);
  const [form, setForm] = useState({ code: "", title: "", body: "" });
  const [saving, setSaving] = useState(false);

  async function load() {
    setLoading(true);
    try {
      const data = await apiFetch("/api/notices/");
      setNotices(data.results ?? data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function handleCreate(e) {
    e.preventDefault();
    setSaving(true);
    try {
      await apiFetch("/api/notices/", { method: "POST", body: JSON.stringify(form) });
      setForm({ code: "", title: "", body: "" });
      setShowNew(false);
      load();
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div>
      <div className="page-head">
        <div>
          <h1>Thông báo nội bộ</h1>
          <div className="page-head-sub">{notices.length} thông báo</div>
        </div>
        {user?.is_manager && <button onClick={() => setShowNew(true)}>+ Đăng thông báo</button>}
      </div>

      {error && <p className="error">{error}</p>}

      {loading ? (
        <p className="muted">Đang tải...</p>
      ) : notices.length === 0 ? (
        <div className="panel">
          <p className="muted">Chưa có thông báo nào.</p>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {notices.map((n) => (
            <div className="panel" key={n.id}>
              {n.code && (
                <div className="muted" style={{ fontSize: 12, fontFamily: "monospace", marginBottom: 4 }}>
                  {n.code}
                </div>
              )}
              <h2 style={{ margin: "0 0 8px" }}>{n.title}</h2>
              {n.body && <p style={{ whiteSpace: "pre-wrap", margin: "0 0 10px" }}>{n.body}</p>}
              <div className="muted" style={{ fontSize: 12.5 }}>
                {n.created_by_name} · {formatDate(n.created_at)}
              </div>
            </div>
          ))}
        </div>
      )}

      {showNew && (
        <Modal title="Đăng thông báo" onClose={() => setShowNew(false)}>
          <form className="field-grid" onSubmit={handleCreate}>
            <label>
              Số hiệu
              <input
                placeholder="vd: CAVI-TB-2026-05"
                value={form.code}
                onChange={(e) => setForm({ ...form, code: e.target.value })}
              />
            </label>
            <label>
              Tiêu đề *
              <input required value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
            </label>
            <label>
              Nội dung
              <textarea rows={5} value={form.body} onChange={(e) => setForm({ ...form, body: e.target.value })} />
            </label>
            <div className="modal-actions">
              <button type="button" className="secondary" onClick={() => setShowNew(false)}>
                Huỷ
              </button>
              <button type="submit" disabled={saving}>
                {saving ? "Đang đăng..." : "Đăng thông báo"}
              </button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  );
}
