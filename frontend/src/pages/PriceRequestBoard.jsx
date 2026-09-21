import { Fragment, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { apiFetch } from "../api";
import ImageThumb from "../components/ImageThumb";
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
                const addressDetail = [r.district_name, r.ward_name, r.street_address].filter(Boolean).join(", ");
                const address = [r.country_name, r.province_name, addressDetail].filter(Boolean).join(" · ");
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
                        <td colSpan={7} style={{ background: "var(--surface-muted)", padding: "6px 16px" }}>
                          <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: "4px 18px", fontSize: 13 }}>
                            <span className="muted">Mã: {r.code}</span>
                            {r.description && <span>{r.description}</span>}
                            {r.items.map((it) => (
                              <span key={it.id} style={{ display: "flex", alignItems: "center", gap: 6 }}>
                                {r.items.length > 1 && <b>{it.product_name || it.item_name}</b>}
                                <span className={`badge badge-source-${it.source_status}`}>
                                  {SOURCE_STATUS_LABEL[it.source_status] ?? it.source_status}
                                </span>
                                <ImageThumb src={it.image} size={22} />
                              </span>
                            ))}
                            <Link
                              className="link-btn"
                              to={`/partners/${r.customer}?tab=inquiries&inquiry=${r.id}`}
                              onClick={(e) => e.stopPropagation()}
                            >
                              Xem trong đối tác →
                            </Link>
                          </div>
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
