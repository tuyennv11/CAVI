import { useEffect, useState } from "react";
import { apiFetch } from "../api";
import Modal from "../components/Modal";
import { CU_STATUS_LABEL, formatCurrency, KD_STATUS_LABEL, KT_STATUS_LABEL, VH_STATUS_LABEL } from "../constants";

const EMPTY_FORM = { partner: "", description: "", route: "", tracking_code: "", currency: "VND", amount: "" };

function statusBadgeClass(status, doneValue = "done") {
  if (status === doneValue || status === "recorded" || status === "gathered" || status === "shipped") return "done";
  if (status === "new") return "neutral";
  return "processing";
}

export default function Shipments() {
  const [shipments, setShipments] = useState([]);
  const [partners, setPartners] = useState([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showNew, setShowNew] = useState(false);
  const [form, setForm] = useState(EMPTY_FORM);
  const [saving, setSaving] = useState(false);

  async function load(q = "") {
    setLoading(true);
    try {
      const params = q ? `?search=${encodeURIComponent(q)}` : "";
      const data = await apiFetch(`/api/shipments/${params}`);
      setShipments(data.results ?? data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    apiFetch("/api/partners/").then((data) => setPartners(data.results ?? data));
  }, []);

  function handleSearchSubmit(e) {
    e.preventDefault();
    load(search);
  }

  async function handleCreate(e) {
    e.preventDefault();
    setSaving(true);
    try {
      await apiFetch("/api/shipments/", {
        method: "POST",
        body: JSON.stringify({ ...form, partner: Number(form.partner), amount: form.amount || 0 }),
      });
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
          <h1>Kiện hàng</h1>
          <div className="page-head-sub">{shipments.length} kiện hàng</div>
        </div>
        <button onClick={() => setShowNew(true)}>+ Tạo phiếu ghi</button>
      </div>

      <div className="toolbar">
        <form onSubmit={handleSearchSubmit} style={{ display: "flex", gap: 8, flex: 1 }}>
          <input
            className="search-input"
            placeholder="Tìm theo mã tracking, mô tả, tuyến..."
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
      ) : shipments.length === 0 ? (
        <div className="panel">
          <p className="muted">Chưa có kiện hàng nào.</p>
        </div>
      ) : (
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Kiện hàng</th>
                <th>Tuyến / Mã</th>
                <th>Số tiền</th>
                <th>KD</th>
                <th>CƯ</th>
                <th>VH</th>
                <th>KT</th>
              </tr>
            </thead>
            <tbody>
              {shipments.map((s) => (
                <tr key={s.id}>
                  <td>
                    <div style={{ fontWeight: 600 }}>{s.partner_name}</div>
                    <div className="muted" style={{ fontSize: 12.5 }}>{s.description}</div>
                  </td>
                  <td>
                    <div>{s.route}</div>
                    <div className="muted" style={{ fontSize: 12.5 }}>{s.tracking_code}</div>
                  </td>
                  <td>{formatCurrency(s.amount, s.currency)}</td>
                  <td><span className={`badge badge-${statusBadgeClass(s.kd_status)}`}>{KD_STATUS_LABEL[s.kd_status]}</span></td>
                  <td><span className={`badge badge-${statusBadgeClass(s.cu_status)}`}>{CU_STATUS_LABEL[s.cu_status]}</span></td>
                  <td><span className={`badge badge-${statusBadgeClass(s.vh_status)}`}>{VH_STATUS_LABEL[s.vh_status]}</span></td>
                  <td><span className={`badge badge-${statusBadgeClass(s.kt_status)}`}>{KT_STATUS_LABEL[s.kt_status]}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {showNew && (
        <Modal title="Tạo phiếu ghi" onClose={() => setShowNew(false)}>
          <form className="field-grid" onSubmit={handleCreate}>
            <label>
              Đối tác *
              <select required value={form.partner} onChange={(e) => setForm({ ...form, partner: e.target.value })}>
                <option value="">— Chọn đối tác —</option>
                {partners.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Hàng hoá *
              <input
                required
                value={form.description}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
              />
            </label>
            <div className="order-item-row" style={{ gridTemplateColumns: "1fr 1fr" }}>
              <input
                placeholder="Tuyến (vd: VN-CPC)"
                value={form.route}
                onChange={(e) => setForm({ ...form, route: e.target.value })}
              />
              <input
                placeholder="Mã tracking"
                value={form.tracking_code}
                onChange={(e) => setForm({ ...form, tracking_code: e.target.value })}
              />
            </div>
            <div className="order-item-row" style={{ gridTemplateColumns: "1fr 110px" }}>
              <input
                type="number"
                placeholder="Số tiền"
                value={form.amount}
                onChange={(e) => setForm({ ...form, amount: e.target.value })}
              />
              <select value={form.currency} onChange={(e) => setForm({ ...form, currency: e.target.value })}>
                <option value="VND">VNĐ</option>
                <option value="USD">USD</option>
              </select>
            </div>
            <div className="modal-actions">
              <button type="button" className="secondary" onClick={() => setShowNew(false)}>
                Huỷ
              </button>
              <button type="submit" disabled={saving}>
                {saving ? "Đang lưu..." : "Lưu phiếu ghi"}
              </button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  );
}
