import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { apiFetch } from "../api";
import { useAuth } from "../AuthContext";
import { formatMoney } from "../constants";

const EMPTY_BID_FORM = { unit_cost: "", note: "" };

export default function SupplyBoard() {
  const { user } = useAuth();
  const [lines, setLines] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [busyId, setBusyId] = useState(null);
  const [bidForms, setBidForms] = useState({});

  async function load() {
    setLoading(true);
    try {
      const data = await apiFetch("/api/quote-lines/?inquiry__status=open");
      setLines(data.results ?? data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  function bidForm(lineId) {
    return bidForms[lineId] || EMPTY_BID_FORM;
  }

  function updateBidForm(lineId, field, value) {
    setBidForms((prev) => ({ ...prev, [lineId]: { ...bidForm(lineId), [field]: value } }));
  }

  async function handleSubmitBid(e, lineId) {
    e.preventDefault();
    setError("");
    const form = bidForm(lineId);
    if (!form.unit_cost) return;
    setBusyId(`bid-${lineId}`);
    try {
      await apiFetch("/api/quote-line-bids/", {
        method: "POST",
        body: JSON.stringify({ quote_line: lineId, unit_cost: form.unit_cost, note: form.note || "" }),
      });
      setBidForms((prev) => ({ ...prev, [lineId]: EMPTY_BID_FORM }));
      load();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusyId(null);
    }
  }

  async function handleWithdrawBid(bidId) {
    setBusyId(bidId);
    try {
      await apiFetch(`/api/quote-line-bids/${bidId}/`, { method: "DELETE" });
      load();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusyId(null);
    }
  }

  async function handleAward(lineId, bidId) {
    setBusyId(bidId);
    try {
      await apiFetch(`/api/quote-lines/${lineId}/award/`, { method: "POST", body: JSON.stringify({ bid: bidId }) });
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
          <h1>Sàn báo giá</h1>
          <div className="page-head-sub">
            Mọi Cung ứng cùng thấy các dòng dịch vụ đang cần giá vốn — chào giá cạnh tranh, Quản lý chọn giá tốt nhất.
          </div>
        </div>
      </div>

      {error && <p className="error">{error}</p>}

      {loading ? (
        <p className="muted">Đang tải...</p>
      ) : lines.length === 0 ? (
        <div className="panel">
          <p className="muted">Chưa có dòng dịch vụ nào đang mở để chào giá.</p>
        </div>
      ) : (
        lines.map((line) => {
          const lowest = line.bids.length
            ? Math.min(...line.bids.map((b) => Number(b.unit_cost)))
            : null;
          return (
            <div className="panel" key={line.id} style={{ marginBottom: 14 }}>
              <div className="row-name" style={{ justifyContent: "space-between", alignItems: "flex-start" }}>
                <div>
                  <div style={{ fontWeight: 600 }}>
                    {line.item_name} <span className="muted" style={{ fontWeight: 400 }}>x{line.quantity} {line.unit}</span>
                  </div>
                  <div className="muted" style={{ fontSize: 12.5 }}>
                    Khách hàng: <Link to={`/partners/${line.customer_id}`}>{line.customer_name}</Link> · Hỏi giá #{line.inquiry}
                  </div>
                  {line.note && <div className="muted" style={{ fontSize: 12.5 }}>{line.note}</div>}
                </div>
                <div style={{ textAlign: "right" }}>
                  <div className="muted" style={{ fontSize: 12.5 }}>Giá báo hiện tại</div>
                  <div style={{ fontWeight: 600, fontSize: 16 }}>{formatMoney(line.unit_cost)}</div>
                  {line.winning_bid && <span className="badge badge-done">Đã chọn</span>}
                  {lowest !== null && <div className="muted" style={{ fontSize: 12 }}>Thấp nhất: {formatMoney(lowest)}</div>}
                </div>
              </div>

              <div className="table-wrap" style={{ marginTop: 10 }}>
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Người chào giá</th>
                      <th>Giá vốn</th>
                      <th>Ghi chú</th>
                      <th>Thời gian</th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    {line.bids.map((bid) => (
                      <tr key={bid.id}>
                        <td>{bid.bidder_name || "—"}</td>
                        <td>{formatMoney(bid.unit_cost)}</td>
                        <td>{bid.note || "—"}</td>
                        <td>{new Date(bid.created_at).toLocaleString("vi-VN")}</td>
                        <td>
                          <div style={{ display: "flex", gap: 8 }}>
                            {user?.is_manager && line.winning_bid !== bid.id && (
                              <button
                                type="button"
                                className="secondary"
                                disabled={busyId === bid.id}
                                onClick={() => handleAward(line.id, bid.id)}
                              >
                                Chọn giá này
                              </button>
                            )}
                            {bid.bidder === user?.id && line.winning_bid !== bid.id && (
                              <button
                                type="button"
                                className="link-btn"
                                disabled={busyId === bid.id}
                                onClick={() => handleWithdrawBid(bid.id)}
                              >
                                Rút báo giá
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))}
                    {line.bids.length === 0 && (
                      <tr>
                        <td colSpan={5} className="muted">
                          Chưa có ai chào giá cho dòng này.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>

              {user?.is_supply && (
                <form
                  className="order-item-row"
                  style={{ gridTemplateColumns: "160px 1fr auto", marginTop: 10 }}
                  onSubmit={(e) => handleSubmitBid(e, line.id)}
                >
                  <input
                    type="number"
                    placeholder="Giá vốn chào"
                    required
                    value={bidForm(line.id).unit_cost}
                    onChange={(e) => updateBidForm(line.id, "unit_cost", e.target.value)}
                  />
                  <input
                    placeholder="Ghi chú (vd: giao nhanh hơn, dịch vụ tốt hơn...)"
                    value={bidForm(line.id).note}
                    onChange={(e) => updateBidForm(line.id, "note", e.target.value)}
                  />
                  <button type="submit" disabled={busyId === `bid-${line.id}`}>
                    Chào giá
                  </button>
                </form>
              )}
            </div>
          );
        })
      )}
    </div>
  );
}
