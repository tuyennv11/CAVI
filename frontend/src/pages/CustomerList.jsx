import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { apiFetch } from "../api";
import Avatar from "../components/Avatar";
import Modal from "../components/Modal";

const EMPTY_FORM = { name: "", company: "", phone: "", email: "", address: "" };

export default function CustomerList() {
  const navigate = useNavigate();
  const [customers, setCustomers] = useState([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [showNew, setShowNew] = useState(false);
  const [form, setForm] = useState(EMPTY_FORM);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  async function load(q = "") {
    setLoading(true);
    try {
      const params = q ? `?search=${encodeURIComponent(q)}` : "";
      const data = await apiFetch(`/api/customers/${params}`);
      setCustomers(data.results ?? data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  function handleSearchSubmit(e) {
    e.preventDefault();
    load(search);
  }

  async function handleCreate(e) {
    e.preventDefault();
    setError("");
    setSaving(true);
    try {
      await apiFetch("/api/customers/", { method: "POST", body: JSON.stringify(form) });
      setForm(EMPTY_FORM);
      setShowNew(false);
      load(search);
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
          <h1>Khách hàng</h1>
          <div className="page-head-sub">{customers.length} khách hàng đang quản lý</div>
        </div>
        <button onClick={() => setShowNew(true)}>+ Thêm khách hàng</button>
      </div>

      <div className="toolbar">
        <form onSubmit={handleSearchSubmit} style={{ display: "flex", gap: 8, flex: 1 }}>
          <input
            className="search-input"
            placeholder="Tìm theo tên, công ty, SĐT, email..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <button type="submit" className="secondary">
            Tìm
          </button>
        </form>
      </div>

      {error && <p className="error">{error}</p>}

      {loading ? (
        <p className="muted">Đang tải...</p>
      ) : customers.length === 0 ? (
        <div className="panel">
          <p className="muted">Chưa có khách hàng nào.</p>
        </div>
      ) : (
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Khách hàng</th>
                <th>Điện thoại</th>
                <th>Phụ trách</th>
                <th>Đơn hàng</th>
              </tr>
            </thead>
            <tbody>
              {customers.map((c) => (
                <tr key={c.id} className="clickable" onClick={() => navigate(`/customers/${c.id}`)}>
                  <td>
                    <div className="row-name">
                      <Avatar name={c.name} />
                      <div>
                        <div>{c.name}</div>
                        {c.company && <div className="muted" style={{ fontWeight: 400, fontSize: 12.5 }}>{c.company}</div>}
                      </div>
                    </div>
                  </td>
                  <td>{c.phone || "—"}</td>
                  <td>{c.assigned_to_detail?.username ?? "—"}</td>
                  <td>
                    <span className="badge badge-neutral">{c.order_count}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {showNew && (
        <Modal title="Thêm khách hàng" onClose={() => setShowNew(false)}>
          <form className="field-grid" onSubmit={handleCreate}>
            <label>
              Tên khách hàng *
              <input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
            </label>
            <label>
              Công ty
              <input value={form.company} onChange={(e) => setForm({ ...form, company: e.target.value })} />
            </label>
            <label>
              Số điện thoại
              <input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
            </label>
            <label>
              Email
              <input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
            </label>
            <label>
              Địa chỉ
              <input value={form.address} onChange={(e) => setForm({ ...form, address: e.target.value })} />
            </label>
            {error && <p className="error">{error}</p>}
            <div className="modal-actions">
              <button type="button" className="secondary" onClick={() => setShowNew(false)}>
                Huỷ
              </button>
              <button type="submit" disabled={saving}>
                {saving ? "Đang lưu..." : "Lưu khách hàng"}
              </button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  );
}
