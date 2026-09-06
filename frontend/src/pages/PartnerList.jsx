import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { apiFetch } from "../api";
import Avatar from "../components/Avatar";
import Modal from "../components/Modal";
import { formatMoney, PARTNER_TYPE_LABEL, TIER_LABEL } from "../constants";

const EMPTY_FORM = {
  name: "",
  company: "",
  phone: "",
  email: "",
  address: "",
  partner_type: "customer",
  tier: "standard",
};

export default function PartnerList() {
  const navigate = useNavigate();
  const [partners, setPartners] = useState([]);
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
      const data = await apiFetch(`/api/partners/${params}`);
      setPartners(data.results ?? data);
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
      await apiFetch("/api/partners/", { method: "POST", body: JSON.stringify(form) });
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
          <h1>Đối tác</h1>
          <div className="page-head-sub">{partners.length} đối tác đang quản lý</div>
        </div>
        <button onClick={() => setShowNew(true)}>+ Thêm đối tác</button>
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
      ) : partners.length === 0 ? (
        <div className="panel">
          <p className="muted">Chưa có đối tác nào.</p>
        </div>
      ) : (
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Đối tác</th>
                <th>Loại</th>
                <th>Hạng</th>
                <th>Công nợ</th>
                <th>Phụ trách</th>
              </tr>
            </thead>
            <tbody>
              {partners.map((p) => {
                const overLimit = Number(p.debt) > Number(p.credit_limit);
                return (
                  <tr key={p.id} className="clickable" onClick={() => navigate(`/partners/${p.id}`)}>
                    <td>
                      <div className="row-name">
                        <Avatar name={p.name} />
                        <div>
                          <div>{p.name}</div>
                          {p.company && (
                            <div className="muted" style={{ fontWeight: 400, fontSize: 12.5 }}>
                              {p.company}
                            </div>
                          )}
                        </div>
                      </div>
                    </td>
                    <td>
                      <span className="badge badge-neutral">{PARTNER_TYPE_LABEL[p.partner_type]}</span>
                    </td>
                    <td>
                      <span className={`badge badge-tier-${p.tier}`}>{TIER_LABEL[p.tier]}</span>
                    </td>
                    <td className={overLimit ? "error" : ""}>{formatMoney(p.debt)}</td>
                    <td>{p.assigned_to_detail?.username ?? "—"}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {showNew && (
        <Modal title="Thêm đối tác" onClose={() => setShowNew(false)}>
          <form className="field-grid" onSubmit={handleCreate}>
            <label>
              Tên *
              <input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
            </label>
            <label>
              Loại đối tác
              <select value={form.partner_type} onChange={(e) => setForm({ ...form, partner_type: e.target.value })}>
                {Object.entries(PARTNER_TYPE_LABEL).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Hạng
              <select value={form.tier} onChange={(e) => setForm({ ...form, tier: e.target.value })}>
                {Object.entries(TIER_LABEL).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
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
                {saving ? "Đang lưu..." : "Lưu đối tác"}
              </button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  );
}
