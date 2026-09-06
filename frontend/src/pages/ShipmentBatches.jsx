import { useEffect, useState } from "react";
import { apiFetch } from "../api";
import Modal from "../components/Modal";
import { BATCH_STATUS_LABEL } from "../constants";

export default function ShipmentBatches() {
  const [batches, setBatches] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showNew, setShowNew] = useState(false);
  const [route, setRoute] = useState("");
  const [saving, setSaving] = useState(false);

  async function load() {
    setLoading(true);
    try {
      const data = await apiFetch("/api/shipment-batches/");
      setBatches(data.results ?? data);
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
      await apiFetch("/api/shipment-batches/", { method: "POST", body: JSON.stringify({ route }) });
      setRoute("");
      setShowNew(false);
      load();
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  async function updateStatus(id, status) {
    try {
      await apiFetch(`/api/shipment-batches/${id}/`, { method: "PATCH", body: JSON.stringify({ status }) });
      load();
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div>
      <div className="page-head">
        <div>
          <h1>Quản lý vận hành</h1>
          <div className="page-head-sub">Các chuyến gom hàng</div>
        </div>
        <button onClick={() => setShowNew(true)}>+ Tạo chuyến</button>
      </div>

      {error && <p className="error">{error}</p>}

      {loading ? (
        <p className="muted">Đang tải...</p>
      ) : batches.length === 0 ? (
        <div className="panel">
          <p className="muted">Chưa có chuyến gom hàng nào.</p>
        </div>
      ) : (
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Tuyến</th>
                <th>Số kiện</th>
                <th>Trạng thái</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {batches.map((b) => (
                <tr key={b.id}>
                  <td>{b.route}</td>
                  <td>
                    <span className="badge badge-neutral">{b.shipment_count}</span>
                  </td>
                  <td>
                    <span className={`badge badge-${b.status === "shipped" ? "done" : b.status === "gathered" ? "new" : "processing"}`}>
                      {BATCH_STATUS_LABEL[b.status]}
                    </span>
                  </td>
                  <td>
                    {b.status === "gathering" && (
                      <button onClick={() => updateStatus(b.id, "gathered")}>Đánh dấu đã gom đủ</button>
                    )}
                    {b.status === "gathered" && (
                      <button onClick={() => updateStatus(b.id, "shipped")}>Đánh dấu đã gửi</button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {showNew && (
        <Modal title="Tạo chuyến gom hàng" onClose={() => setShowNew(false)}>
          <form className="field-grid" onSubmit={handleCreate}>
            <label>
              Tuyến *
              <input required placeholder="vd: VN-CPC" value={route} onChange={(e) => setRoute(e.target.value)} />
            </label>
            <div className="modal-actions">
              <button type="button" className="secondary" onClick={() => setShowNew(false)}>
                Huỷ
              </button>
              <button type="submit" disabled={saving}>
                {saving ? "Đang lưu..." : "Tạo chuyến"}
              </button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  );
}
