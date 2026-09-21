import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { apiFetch } from "../api";
import { useAuth } from "../AuthContext";
import Avatar from "../components/Avatar";
import CompanyCheckboxes from "../components/CompanyCheckboxes";
import Modal from "../components/Modal";
import PhoneInput from "../components/PhoneInput";
import { TIER_LABEL } from "../constants";

// LIVI không tách Khách hàng/Nhà cung cấp thành 2 danh mục riêng — 1 đối tác dùng chung 1 dữ liệu,
// is_customer/is_supplier chỉ còn là cờ nội bộ phục vụ vài chỗ lọc (vd chọn NCC khi nhập kho),
// mặc định luôn bật cả 2 khi tạo mới qua app, không bắt người dùng chọn tay.
function emptyForm(activeCompanyId) {
  return {
    name: "",
    contact_person: "",
    phone: "",
    note: "",
    is_customer: true,
    is_supplier: true,
    companies: activeCompanyId ? [Number(activeCompanyId)] : [],
  };
}

export default function PartnerList() {
  const navigate = useNavigate();
  const { activeCompanyId } = useAuth();
  const [partners, setPartners] = useState([]);
  const [companies, setCompanies] = useState([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [showNew, setShowNew] = useState(false);
  const [form, setForm] = useState(emptyForm(activeCompanyId));
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
    apiFetch("/api/companies/").then(setCompanies).catch(() => {});
  }, []);

  function handleSearchSubmit(e) {
    e.preventDefault();
    load(search);
  }

  function openNew() {
    setForm(emptyForm(activeCompanyId));
    setShowNew(true);
  }

  async function handleCreate(e) {
    e.preventDefault();
    setError("");
    if (form.companies.length === 0) {
      setError("Phải tick ít nhất 1 công ty.");
      return;
    }
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

  return (
    <div>
      <div className="page-head">
        <div>
          <h1>Đối tác</h1>
          <div className="page-head-sub">{partners.length} đối tác</div>
        </div>
        <button onClick={openNew}>+ Thêm đối tác</button>
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
                <th>Công ty</th>
                <th>Hạng</th>
                <th>Phụ trách</th>
              </tr>
            </thead>
            <tbody>
              {partners.map((p) => {
                return (
                  <tr key={p.id} className="clickable" onClick={() => navigate(`/partners/${p.id}`)}>
                    <td>
                      <div className="row-name">
                        <Avatar name={p.name} />
                        <div>
                          <div>{p.name}</div>
                          {p.contact_person && (
                            <div className="muted" style={{ fontWeight: 400, fontSize: 12.5 }}>
                              {p.contact_person}
                            </div>
                          )}
                        </div>
                      </div>
                    </td>
                    <td>
                      {(p.companies_detail || []).map((c) => (
                        <span className="badge badge-neutral" key={c.id} style={{ marginRight: 4 }}>
                          {c.code}
                        </span>
                      ))}
                    </td>
                    <td>
                      {p.tier_override ? (
                        <span className={`badge badge-tier-${p.tier_override}`}>{TIER_LABEL[p.tier_override]}</span>
                      ) : (
                        "—"
                      )}
                    </td>
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
              Thuộc công ty
              <CompanyCheckboxes
                companies={companies}
                selected={form.companies}
                onChange={(companies) => setForm({ ...form, companies })}
              />
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
              <PhoneInput value={form.phone} onChange={(phone) => setForm({ ...form, phone })} />
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
