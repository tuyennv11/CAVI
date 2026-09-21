import { Fragment, useEffect, useState } from "react";
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
  const [expandedId, setExpandedId] = useState(null);

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
            Toàn bộ yêu cầu giá của mọi đối tác — bấm vào 1 dòng để xem chi tiết, xem Nguồn hàng.
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
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Trạng thái</th>
                <th>Khách hàng</th>
                <th>Sản phẩm</th>
                <th>SL / ĐVT</th>
                <th>Giao tới</th>
                <th>Phụ trách</th>
                <th>Ngày tạo</th>
              </tr>
            </thead>
            <tbody>
              {requests.map((r) => {
                const itemsSummary = r.items.map((it) => it.product_name || it.item_name).filter(Boolean).join(", ");
                const qtySummary = r.items.map((it) => [it.quantity, it.unit].filter(Boolean).join(" ")).filter(Boolean).join(", ");
                const addressDetail = [r.street_address, r.ward_name, r.district_name, r.province_name].filter(Boolean).join(", ");
                const address = [r.country_name, addressDetail].filter(Boolean).join(" · ");
                const isExpanded = expandedId === r.id;
                return (
                  <Fragment key={r.id}>
                    <tr className="clickable" onClick={() => setExpandedId(isExpanded ? null : r.id)}>
                      <td>
                        <StatusBadge status={r.status} />
                      </td>
                      <td className="ellipsis-cell" title={r.customer_name}>
                        {r.customer_name}
                      </td>
                      <td className="ellipsis-cell" title={itemsSummary}>
                        {itemsSummary || "—"}
                      </td>
                      <td className="ellipsis-cell" title={qtySummary}>
                        {qtySummary || "—"}
                      </td>
                      <td className="ellipsis-cell" title={address}>
                        {address || "—"}
                      </td>
                      <td>{r.assigned_to_detail?.full_name ?? r.created_by_name}</td>
                      <td>{formatDateTime(r.created_at)}</td>
                    </tr>
                    {isExpanded && (
                      <tr>
                        <td colSpan={7} style={{ background: "var(--surface-muted)" }}>
                          <div className="muted" style={{ fontSize: 12, marginBottom: 6 }}>
                            Mã: {r.code}
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
                                  <th>Hình ảnh</th>
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
                                    <td>
                                      {it.image ? (
                                        <a href={it.image} target="_blank" rel="noreferrer">
                                          <img
                                            src={it.image}
                                            alt=""
                                            style={{ width: 32, height: 32, objectFit: "cover", borderRadius: 6, border: "1px solid var(--line)" }}
                                          />
                                        </a>
                                      ) : (
                                        "—"
                                      )}
                                    </td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>

                          <Link
                            className="link-btn"
                            to={`/partners/${r.customer}?tab=inquiries&inquiry=${r.id}`}
                            onClick={(e) => e.stopPropagation()}
                          >
                            Xem chi tiết trong hồ sơ đối tác →
                          </Link>
                        </td>
                      </tr>
                    )}
                  </Fragment>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
