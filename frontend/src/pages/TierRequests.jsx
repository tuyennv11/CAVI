import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { apiFetch } from "../api";
import { useAuth } from "../AuthContext";
import { TIER_LABEL, TIER_REQUEST_STATUS_LABEL } from "../constants";

export default function TierRequests() {
  const { user } = useAuth();
  const [requests, setRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [busyId, setBusyId] = useState(null);

  async function load() {
    setLoading(true);
    try {
      const data = await apiFetch("/api/tier-requests/");
      setRequests(data.results ?? data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function handleAction(id, action) {
    setBusyId(id);
    try {
      await apiFetch(`/api/tier-requests/${id}/${action}/`, { method: "POST" });
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
          <h1>Yêu cầu nâng hạng</h1>
          <div className="page-head-sub">
            {user?.is_manager ? "Duyệt hoặc từ chối yêu cầu nâng hạng đối tác" : "Các yêu cầu bạn đã gửi"}
          </div>
        </div>
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
                <th>Đối tác</th>
                <th>Xin lên hạng</th>
                <th>Lý do</th>
                <th>Người xin</th>
                <th>Trạng thái</th>
                {user?.is_manager && <th></th>}
              </tr>
            </thead>
            <tbody>
              {requests.map((r) => (
                <tr key={r.id}>
                  <td>
                    <Link to={`/partners/${r.partner}`}>{r.partner_name}</Link>
                  </td>
                  <td>
                    <span className={`badge badge-tier-${r.requested_tier}`}>{TIER_LABEL[r.requested_tier]}</span>
                  </td>
                  <td style={{ maxWidth: 320 }}>{r.reason}</td>
                  <td>{r.requested_by_name}</td>
                  <td>
                    <span className={`badge badge-${r.status === "approved" ? "done" : r.status === "rejected" ? "cancelled" : "processing"}`}>
                      {TIER_REQUEST_STATUS_LABEL[r.status]}
                    </span>
                  </td>
                  {user?.is_manager && (
                    <td>
                      {r.status === "pending" && (
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
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
