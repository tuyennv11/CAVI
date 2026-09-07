import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { apiFetch } from "../api";
import Avatar from "../components/Avatar";
import Modal from "../components/Modal";
import { formatMoney, PARTNER_TYPE_LABEL, TIER_LABEL } from "../constants";

const TABS = [
  { key: "customer", label: "Khách hàng" },
  { key: "supplier", label: "Nhà cung cấp" },
];

function emptyForm(partnerType) {
  return { name: "", contact_person: "", phone: "", note: "", partner_type: partnerType };
}

export default function PartnerList() {
  const navigate = useNavigate();
  const [tab, setTab] = useState("customer");
  const [partners, setPartners] = useState([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [showNew, setShowNew] = useState(false);
  const [form, setForm] = useState(emptyForm("customer"));
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

  function openNew() {
    setForm(emptyForm(tab));
    setShowNew(true);
  }

  async function handleCreate(e) {
    e.preventDefault();
    setError("");
    setSaving(true);
    try {
      await apiFetch("/api/partners/", { method: "POST", body: JSON.stringify(form) });
      setShowNew(false);
      load(search);
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  const visible = partners.filter((p) => p.partner_type === tab || p.partner_type === "both");

  return (
    <div>
      <div className="page-head">
        <div>
          <h1>Đối tác</h1>
          <div className="page-head-sub">{visible.length} {tab === "customer" ? "khách hàng" : "nhà cung cấp"}</div>
        </div>
        <button onClick={openNew}>+ Thêm {tab === "customer" ? "khách hàng" : "nhà cung cấp"}</button>
      </div>

      <div className="tabs">
        {TABS.map((t) => (
          <button key={t.key} className={`tab-btn${tab === t.key ? " active" : ""}`} onClick={() => setTab(t.key)}>
            {t.label}
          </button>
        ))}
      </div>

      <div className="toolbar">
        <form onSubmit={handleSearchSubmit} style={{ display: "flex", gap: 8, flex: 1 }}>
          <input
            className="search-input"
            placeholder="Tìm theo tên, người liên hệ, SĐT..."
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
      ) : visible.length === 0 ? (
        <div className="panel">
          <p className="muted">Chưa có {tab === "customer" ? "khách hàng" : "nhà cung cấp"} nào.</p>
        </div>
      ) : (
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Đối tác</th>
                {tab === "customer" && <th>Hạng</th>}
                {tab === "customer" && <th>Công nợ</th>}
                <th>Phụ trách</th>
              </tr>
            </thead>
            <tbody>
              {visible.map((p) => {
                const overLimit = Number(p.debt) > Number(p.credit_limit);
                return (
                  <tr key={p.id} className="clickable" onClick={() => navigate(`/partners/${p.id}`)}>
                    <td>
                      <div className="row-name">
                        <Avatar name={p.name} />
                        <div>
                          <div>
                            {p.name}
                            {p.partner_type === "both" && (
                              <span className="badge badge-neutral" style={{ marginLeft: 8 }}>
                                {PARTNER_TYPE_LABEL.both}
                              </span>
                            )}
                          </div>
                          {p.contact_person && (
                            <div className="muted" style={{ fontWeight: 400, fontSize: 12.5 }}>
                              {p.contact_person}
                            </div>
                          )}
                        </div>
                      </div>
                    </td>
                    {tab === "customer" && (
                      <td>
                        <span className={`badge badge-tier-${p.tier}`}>{TIER_LABEL[p.tier]}</span>
                      </td>
                    )}
                    {tab === "customer" && (
                      <td className={overLimit ? "error" : ""}>{formatMoney(p.debt)}</td>
                    )}
                    <td>{p.assigned_to_detail?.username ?? "—"}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {showNew && (
        <Modal title={`Thêm ${tab === "customer" ? "khách hàng" : "nhà cung cấp"}`} onClose={() => setShowNew(false)}>
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
              Người liên hệ
              <input
                placeholder="vd: Anh Nam"
                value={form.contact_person}
                onChange={(e) => setForm({ ...form, contact_person: e.target.value })}
              />
            </label>
            <label>
              Số điện thoại
              <input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
            </label>
            <label>
              Mô tả thêm
              <textarea rows={2} value={form.note} onChange={(e) => setForm({ ...form, note: e.target.value })} />
            </label>
            {error && <p className="error">{error}</p>}
            <div className="modal-actions">
              <button type="button" className="secondary" onClick={() => setShowNew(false)}>
                Huỷ
              </button>
              <button type="submit" disabled={saving}>
                {saving ? "Đang lưu..." : "Lưu"}
              </button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  );
}
