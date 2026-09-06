import { useEffect, useState } from "react";
import { apiFetch } from "../api";
import { useAuth } from "../AuthContext";
import Modal from "../components/Modal";
import { APPROVAL_STATUS_BADGE, APPROVAL_STATUS_LABEL, formatCurrency } from "../constants";

const TABS = [
  { key: "settlement", label: "Quyết toán" },
  { key: "proposal", label: "Đề xuất / Trình ký" },
];

const EMPTY_FORM = { category: "", title: "", note: "", amount: "", currency: "VND" };

export default function ApprovalsPage() {
  const { user } = useAuth();
  const [tab, setTab] = useState("settlement");
  const [requests, setRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [busyId, setBusyId] = useState(null);
  const [showNew, setShowNew] = useState(false);
  const [form, setForm] = useState(EMPTY_FORM);
  const [saving, setSaving] = useState(false);

  async function load() {
    setLoading(true);
    try {
      const data = await apiFetch(`/api/approval-requests/?request_type=${tab}`);
      setRequests(data.results ?? data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tab]);

  async function handleCreate(e) {
    e.preventDefault();
    setSaving(true);
    try {
      const body = { request_type: tab, ...form };
      if (!body.amount) delete body.amount;
      await apiFetch("/api/approval-requests/", { method: "POST", body: JSON.stringify(body) });
      setForm(EMPTY_FORM);
      setShowNew(false);
      load();
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  async function handleAction(id, action) {
    setBusyId(id);
    try {
      await apiFetch(`/api/approval-requests/${id}/${action}/`, { method: "POST" });
      load();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div>
      <div className="page-head">
        <div>
          <h1>Ký duyệt</h1>
          <div className="page-head-sub">Quyết toán chi tiền và đề xuất trình ký</div>
        </div>
        <button onClick={() => setShowNew(true)}>+ Tạo yêu cầu</button>
      </div>

      <div className="tabs">
        {TABS.map((t) => (
          <button key={t.key} className={`tab-btn${tab === t.key ? " active" : ""}`} onClick={() => setTab(t.key)}>
            {t.label}
          </button>
        ))}
      </div>

      {error && <p className="error">{error}</p>}

      {loading ? (
        <p className="muted">Đang tải...</p>
      ) : requests.length === 0 ? (
        <div className="panel">
          <p className="muted">Chưa có yêu cầu nào.</p>
        </div>
      ) : (
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Tiêu đề</th>
                <th>Danh mục</th>
                {tab === "settlement" && <th>Số tiền</th>}
                <th>Người tạo</th>
                <th>Trạng thái</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {requests.map((r) => (
                <tr key={r.id}>
                  <td>
                    <div style={{ fontWeight: 600 }}>{r.title}</div>
                    {r.note && <div className="muted" style={{ fontSize: 12.5 }}>{r.note}</div>}
                  </td>
                  <td>{r.category || "—"}</td>
                  {tab === "settlement" && <td>{r.amount ? formatCurrency(r.amount, r.currency) : "—"}</td>}
                  <td>{r.requested_by_name}</td>
                  <td>
                    <span className={`badge badge-${APPROVAL_STATUS_BADGE[r.status]}`}>
                      {APPROVAL_STATUS_LABEL[r.status]}
                    </span>
                  </td>
                  <td>
                    {user?.is_manager && r.status === "pending" && (
                      <div style={{ display: "flex", gap: 8 }}>
                        <button disabled={busyId === r.id} onClick={() => handleAction(r.id, "approve")}>
                          Duyệt
                        </button>
                        <button
                          className="secondary"
                          disabled={busyId === r.id}
                          onClick={() => handleAction(r.id, "reject")}
                        >
                          Từ chối
                        </button>
                      </div>
                    )}
                    {user?.is_manager && tab === "settlement" && r.status === "approved" && (
                      <button disabled={busyId === r.id} onClick={() => handleAction(r.id, "mark_paid")}>
                        Đánh dấu đã chi
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {showNew && (
        <Modal title={`Tạo yêu cầu ${tab === "settlement" ? "quyết toán" : "đề xuất"}`} onClose={() => setShowNew(false)}>
          <form className="field-grid" onSubmit={handleCreate}>
            <label>
              Tiêu đề *
              <input required value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
            </label>
            <label>
              Danh mục
              <input
                placeholder={tab === "settlement" ? "vd: Chi phí phúc lợi NV" : "vd: Ký duyệt hợp đồng"}
                value={form.category}
                onChange={(e) => setForm({ ...form, category: e.target.value })}
              />
            </label>
            {tab === "settlement" && (
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
            )}
            <label>
              Ghi chú
              <textarea rows={3} value={form.note} onChange={(e) => setForm({ ...form, note: e.target.value })} />
            </label>
            <div className="modal-actions">
              <button type="button" className="secondary" onClick={() => setShowNew(false)}>
                Huỷ
              </button>
              <button type="submit" disabled={saving}>
                {saving ? "Đang gửi..." : "Gửi yêu cầu"}
              </button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  );
}
