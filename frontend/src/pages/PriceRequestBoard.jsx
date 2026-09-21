import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { apiFetch } from "../api";
import StatusBadge from "../components/StatusBadge";
import { SOURCE_STATUS_LABEL } from "../constants";

const STATUS_FILTERS = [
  ["", "Tất cả trạng thái"],
  ["cho_cung_ung", "Chờ Cung ứng"],
  ["da_kiem_tra_nguon_hang", "Đã kiểm tra nguồn hàng"],
  ["cho_tinh_gia", "Chờ tính giá"],
  ["cho_duyet", "Chờ duyệt giá"],
  ["da_duyet", "Đã duyệt giá"],
  ["da_gui_khach", "Đã gửi khách"],
  ["khach_dong_y", "Khách đồng ý"],
  ["khach_tu_choi", "Khách từ chối"],
  ["dang_thuong_luong", "Đang thương lượng"],
  ["huy", "Huỷ"],
];

function formatDateTime(iso) {
  if (!iso) return "";
  return new Date(iso).toLocaleString("vi-VN", { dateStyle: "short", timeStyle: "short" });
}

export default function PriceRequestBoard() {
  const [requests, setRequests] = useState([]);
  const [status, setStatus] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function load(statusValue) {
    setLoading(true);
    try {
      const params = statusValue ? `?status=${statusValue}` : "";
      const data = await apiFetch(`/api/price-inquiries/${params}`);
      setRequests(data.results ?? data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load(status);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status]);

  return (
    <div>
      <div className="page-head">
        <div>
          <h1>Yêu cầu giá</h1>
          <div className="page-head-sub">
            Toàn bộ yêu cầu giá của mọi đối tác — bấm vào 1 yêu cầu để xem chi tiết, xem Nguồn hàng và trao đổi.
          </div>
        </div>
        <select value={status} onChange={(e) => setStatus(e.target.value)}>
          {STATUS_FILTERS.map(([value, label]) => (
            <option key={value || "all"} value={value}>
              {label}
            </option>
          ))}
        </select>
      </div>

      {error && <p className="error">{error}</p>}

      {loading ? (
        <p className="muted">Đang tải...</p>
      ) : requests.length === 0 ? (
        <div className="panel">
          <p className="muted">Chưa có yêu cầu giá nào.</p>
        </div>
      ) : (
        <div className="inquiry-list">
          {requests.map((r) => (
            <div className="inquiry-card" key={r.id}>
              <div className="inquiry-head">
                <StatusBadge status={r.status} />
                <span className="muted" style={{ fontSize: 12 }}>
                  {r.code} · <Link to={`/partners/${r.customer}`}>{r.customer_name}</Link> ·{" "}
                  {r.assigned_to_detail?.full_name ?? r.created_by_name} · {formatDateTime(r.created_at)}
                </span>
              </div>
              {r.description && <div className="inquiry-description">{r.description}</div>}

              <div className="table-wrap" style={{ marginBottom: 8 }}>
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Sản phẩm</th>
                      <th>SL</th>
                      <th>ĐVT</th>
                      <th>Nguồn hàng</th>
                    </tr>
                  </thead>
                  <tbody>
                    {r.items.map((it) => (
                      <tr key={it.id}>
                        <td>{it.product_name || it.item_name}</td>
                        <td>{it.quantity}</td>
                        <td>{it.unit}</td>
                        <td>
                          <span className={`badge badge-source-${it.source_status}`}>
                            {SOURCE_STATUS_LABEL[it.source_status] ?? it.source_status}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <Link className="link-btn" to={`/partners/${r.customer}?tab=inquiries&inquiry=${r.id}`}>
                Xem chi tiết trong hồ sơ đối tác →
              </Link>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
