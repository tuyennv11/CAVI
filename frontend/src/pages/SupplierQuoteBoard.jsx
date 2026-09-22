import { useCallback, useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { apiFetch } from "../api";
import { useAuth } from "../AuthContext";
import { formatMoney } from "../constants";
import QuoteTerms from "../components/QuoteTerms";
import MoneyInput from "../components/MoneyInput";
import SavedCostQuote from "../components/SavedCostQuote";
import LegacySupplierQuoteBoard from "./LegacySupplierQuoteBoard";

const weight = (kg) => kg >= 1000 ? (kg / 1000).toLocaleString("vi-VN", { maximumFractionDigits: 3 }) + " tấn" : kg.toLocaleString("vi-VN") + " kg";
const money = (value) => value === null || value === undefined ? "Chưa đủ giá" : formatMoney(value);
const dateTime = (value) => new Date(value).toLocaleString("vi-VN", { dateStyle: "short", timeStyle: "short" });
function offersFor(quote) {
  const base = { quote, goods: quote.market.goods_total };
  return [{ ...base, freight: null, key: "q" + quote.id, shipping: quote.market.shipping_total, issues: quote.market.issues },
    ...(quote.freight_offers || []).filter((freight) => freight.is_live).map((freight) => ({ ...base, freight, key: "f" + freight.id, shipping: freight.total_cost, issues: freight.issues }))]
    .map((offer) => ({ ...offer, total: offer.goods !== null && offer.shipping !== null ? Number(offer.goods) + Number(offer.shipping) : null,
      group: quote.market.comparison_key ? quote.market.comparison_key + "|" + (quote.available_at || "") + "|" + (offer.freight ? offer.freight.terms + "|" + offer.freight.delivery_days : quote.delivery_terms) : null }));
}

function FreightForm({ quote, revision, onClose, onSaved }) {
  const [form, setForm] = useState({ carrier_name: "", rate: "", basis: "total", confirmed: false, valid_until: "", tax_basis: "unknown", terms: "", delivery_days: "", ...revision });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  async function submit(e) {
    e.preventDefault(); setSaving(true); setError("");
    try { await apiFetch("/api/freight-offers/", { method: "POST", body: JSON.stringify({ goods_quote: quote.id, carrier_name: form.carrier_name, rate: form.rate, basis: form.basis, confirmed: form.confirmed, valid_until: form.valid_until || null, tax_basis: form.tax_basis, terms: form.terms, delivery_days: form.delivery_days === "" ? null : form.delivery_days, supersedes: revision?.id || null }) }); onSaved(); }
    catch (err) { setError(err.message); } finally { setSaving(false); }
  }
  return <form className="market-freight-form" onSubmit={submit}>
    <div className="market-toolbar"><strong>{revision ? "Cập nhật cước bằng phiên bản mới" : "Báo giá vận chuyển"} · Nguồn #{quote.id}</strong><button type="button" className="link-btn" onClick={onClose}>Đóng</button></div>
    <p className="muted">Cước áp dụng cho toàn bộ hàng của nguồn này, từ {quote.street_address || "điểm nhận đã khai báo"} → {quote.delivery_snapshot || "chưa có điểm giao"}.</p>
    <QuoteTerms form={form} setForm={setForm} freight />
    <div className="market-terms"><label>Giá cước<MoneyInput value={form.rate} onChange={(rate) => setForm({ ...form, rate })} /></label><label>Tính theo<select value={form.basis} onChange={(e) => setForm({ ...form, basis: e.target.value })}><option value="total">Trọn gói</option><option value="kg">Đơn giá/kg</option><option value="m3">Đơn giá/m³</option></select></label></div>
    {error && <p className="error" role="alert">{error}</p>}<button disabled={saving || form.rate === ""}>{saving ? "Đang lưu…" : "Đăng cước lên sàn"}</button>
  </form>;
}

export function MarketItem({ item, user, run, busy, reload }) {
  const [detailsQuote, setDetailsQuote] = useState(null);
  const [freightFor, setFreightFor] = useState(null);
  const [revision, setRevision] = useState(null);
  const [candidate, setCandidate] = useState("");
  const [reason, setReason] = useState("");
  const supply = user?.is_manager || user?.is_supply;
  const quotes = item.cost_quotes || [];
  const liveQuotes = quotes.filter((q) => q.market.is_live);
  const offers = liveQuotes.flatMap(offersFor);
  const ready = offers.filter((o) => o.issues.length === 0 && o.total !== null);
  const selected = offers.find((o) => o.key === candidate);
  const plans = item.sourcing_plans || [];
  const approved = plans.find((p) => p.status === "approved");
  const status = approved ? "Đã chốt" : plans.some((p) => p.status === "proposed") ? "Chờ duyệt" : quotes.length > 1 ? "Đang so sánh" : "Đang tìm giá";
  const lowestGoods = (q) => {
    const peers = liveQuotes.filter((p) => p.confirmed && p.valid_until && p.market.comparison_key && p.market.comparison_key === q.market.comparison_key);
    return q.confirmed && q.valid_until && q.market.is_live && peers.length > 1 && peers.every((p) => Number(p.market.goods_total) >= Number(q.market.goods_total));
  };
  const lowestFreight = (offer) => {
    const peers = ready.filter((p) => p.quote.id === offer.quote.id && p.group === offer.group);
    return !offer.issues.length && peers.length > 1 && peers.every((p) => Number(p.shipping) >= Number(offer.shipping));
  };
  const owner = (q) => supply && (user?.is_manager || q.created_by === user?.id);
  const best = (offer) => { const group = ready.filter((o) => o.group && o.group === offer.group); return group.length > 1 && group.every((o) => o.total >= offer.total) && !offer.issues.length; };
  async function propose(e) { e.preventDefault(); if (!selected) return; const ok = await run("/api/sourcing-plans/", { price_request_item: item.id, goods_quote: selected.quote.id, freight_offer: selected.freight?.id || null, reason }); if (ok) { setCandidate(""); setReason(""); } }
  return <section className="panel market-request">
    <div className="market-toolbar"><div><strong>{item.price_request_code} · {item.product_name || item.item_name}</strong><div className="muted">{item.customer_name} · Cần {item.quantity || "—"} {item.unit} · {quotes.length} giá hàng</div></div><span className={approved ? "badge badge-done" : "badge"}>{status}</span></div>
    <p className="market-destination"><b>Điểm giao:</b> {item.price_request_delivery_address || "Chưa có địa chỉ"}</p>
    {approved && <div className="market-approved"><b>Đã chốt: {approved.snapshot.supplier} + {approved.snapshot.carrier}</b><span>{money(approved.snapshot.landed_total)} · Duyệt bởi {approved.reviewed_by_name}</span><small>{approved.snapshot.pickup} → {approved.snapshot.delivery}</small></div>}
    <div className="market-toolbar"><h3>Hàng hóa</h3>{supply && <Link className="market-add" to={"/cost-quotes?price_request_item=" + item.id + "&new=1"}>+ Báo giá hàng hóa</Link>}</div>
    {quotes.length === 0 ? <p className="muted">Chưa có nguồn hàng. Cung ứng có thể gửi giá đầu tiên.</p> : <div className="table-wrap"><table className="data-table market-table"><thead><tr><th>Nguồn hàng / Người báo</th><th>Tiền hàng</th><th>Xác nhận / Hiệu lực</th><th>Điểm nhận</th><th>Thao tác</th></tr></thead><tbody>{quotes.map((q) => <tr key={q.id} className={!q.market.is_live ? "market-inactive" : ""}>
      <td><b>{q.supplier_name || "Chưa rõ NCC"}</b><small>#{q.id} · {q.created_by_name} · {dateTime(q.created_at)}</small>{Date.now() - new Date(q.created_at).getTime() < 86400000 && <span className="badge">Mới · 24 giờ</span>}{q.supersedes && <small>Thay giá #{q.supersedes}</small>}</td>
      <td><b>{money(q.market.goods_total)}</b>{lowestGoods(q) && <small className="market-best">Tiền hàng thấp nhất nhóm</small>}<small>{q.tax_basis === "included" ? "Đã gồm thuế" : q.tax_basis === "excluded" ? "Chưa gồm thuế" : "Chưa rõ thuế"}</small></td>
      <td>{!q.market.is_live ? "Đã rút / hết hiệu lực" : q.confirmed ? "NCC xác nhận" : "Tham khảo"}<small>Đến {q.valid_until || "chưa xác định"}</small></td>
      <td>{q.street_address || "Chưa khai báo"}</td>
      <td><div className="market-actions">{supply && q.market.is_live && <button className="secondary" type="button" onClick={() => { setFreightFor(q); setRevision(null); }}>+ Báo cước</button>}{owner(q) && q.market.is_live && approved?.goods_quote !== q.id && <><Link to={"/cost-quotes?price_request_item=" + item.id + "&revise=" + q.id}>Cập nhật giá</Link><button disabled={busy} className="link-btn" onClick={() => run("/api/cost-quotes/" + q.id + "/withdraw/", {})}>Rút giá</button></>}</div><button className="link-btn" onClick={() => setDetailsQuote(detailsQuote === q.id ? null : q.id)}>Chi tiết</button></td>
    </tr>)}</tbody></table></div>}
    {detailsQuote && quotes.filter((q) => q.id === detailsQuote).map((q) => <SavedCostQuote key={q.id} quote={q} index={quotes.indexOf(q)} formatWeight={weight} deliveryAddress={q.delivery_snapshot || item.price_request_delivery_address} />)}
    <div className="market-toolbar"><h3>Vận chuyển & Tổng chi phí</h3><span className="muted">Cước gắn đúng nguồn hàng · Giá đã gồm thuế mới đủ điều kiện chốt</span></div>
    {offers.length > 0 && <div className="table-wrap"><table className="data-table market-table"><thead><tr><th>Nguồn hàng → Đơn vị vận chuyển</th><th>Cước</th><th>Tổng về điểm giao</th><th>Đánh giá / Thao tác</th></tr></thead><tbody>{offers.map((o) => <tr key={o.key}>
      <td><b>#{o.quote.id} {o.quote.supplier_name || "Nguồn hàng"}</b><small>→ {o.freight?.carrier_name || o.quote.carrier_name || "Chưa có nhà vận chuyển"}</small><small>{o.freight ? "Cước #" + o.freight.id + " · " + o.freight.created_by_name : "Cước kèm báo giá hàng"}</small></td>
      <td>{money(o.shipping)}{lowestFreight(o) && <small className="market-best">Cước thấp nhất cùng nguồn</small>}</td><td><b>{money(o.total)}</b>{best(o) && <small className="market-best">Thấp nhất nhóm tương đương</small>}</td>
      <td>{o.issues.length ? <details><summary>Chưa đủ điều kiện ({o.issues.length})</summary><ul>{o.issues.map((issue) => <li key={issue}>{issue}</li>)}</ul></details> : <span className="badge badge-done">Đủ thông tin</span>}{o.freight && owner(o.freight) && approved?.freight_offer !== o.freight.id && <div className="market-actions"><button className="link-btn" onClick={() => { setFreightFor(o.quote); setRevision(o.freight); }}>Cập nhật cước</button><button disabled={busy} className="link-btn" onClick={() => run("/api/freight-offers/" + o.freight.id + "/withdraw/", {})}>Rút cước</button></div>}</td>
    </tr>)}</tbody></table></div>}
    {quotes.some((q) => q.freight_offers?.some((f) => !f.is_live)) && <details className="market-history"><summary>Lịch sử cước đã rút / hết hiệu lực</summary>{quotes.flatMap((q) => (q.freight_offers || []).filter((f) => !f.is_live).map((f) => <p key={f.id}>Nguồn #{q.id} · Cước #{f.id} · {f.carrier_name} · {money(f.total_cost)} · {f.created_by_name} · {dateTime(f.created_at)}</p>))}</details>}
    {freightFor && <FreightForm key={freightFor.id + "-" + (revision?.id || "new")} quote={freightFor} revision={revision} onClose={() => setFreightFor(null)} onSaved={() => { setFreightFor(null); reload(); }} />}
    {!approved && ready.length > 0 && <form className="market-propose" onSubmit={propose}><h3>Đề xuất phương án</h3><label>Hàng hóa + vận chuyển<select required value={candidate} onChange={(e) => setCandidate(e.target.value)}><option value="">Chọn phương án đủ thông tin</option>{ready.map((o) => <option key={o.key} value={o.key}>#{o.quote.id} {o.quote.supplier_name} + {o.freight?.carrier_name || o.quote.carrier_name} · {money(o.total)}</option>)}</select></label><label>Lý do chọn<input required value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Giá, chất lượng, tiến độ, điều kiện…" /></label><button disabled={busy || !selected}>Gửi quản lý duyệt</button></form>}
    {plans.length > 0 && <div className="market-plans"><h3>Đề xuất & Lịch sử chốt</h3>{plans.map((p) => <div key={p.id} className="market-plan"><div><b>{p.snapshot.supplier} + {p.snapshot.carrier} · {money(p.snapshot.landed_total)}</b><p>{p.reason}</p><small>{p.created_by_name} · {dateTime(p.created_at)} · {p.status === "approved" ? "Đã chốt" : p.status === "rejected" ? "Không chọn" : "Chờ duyệt"}</small></div>{user?.is_manager && p.status === "proposed" && <div className="market-actions"><button disabled={busy} onClick={() => run("/api/sourcing-plans/" + p.id + "/approve/", {})}>Duyệt chốt</button><button disabled={busy} className="secondary" onClick={() => run("/api/sourcing-plans/" + p.id + "/reject/", {})}>Không chọn</button></div>}</div>)}</div>}
  </section>;
}

export default function SupplierQuoteBoard() {
  const { user } = useAuth(); const [params, setParams] = useSearchParams();
  const legacy = params.has("purchase_request_item") || params.get("tab") === "purchase";
  const focus = params.get("price_request_item");
  const [items, setItems] = useState([]), [error, setError] = useState(""), [loading, setLoading] = useState(true), [busy, setBusy] = useState(false), [search, setSearch] = useState("");
  const load = useCallback(async () => { try {
    let path = "/api/price-inquiry-items/" + (focus ? "?id=" + encodeURIComponent(focus) : ""), rows = [];
    while (path) { const data = await apiFetch(path); rows = rows.concat(data.results ?? data); path = data.next ? new URL(data.next, window.location.origin).pathname + new URL(data.next, window.location.origin).search : null; }
    setItems(rows); setError("");
  } catch (err) { setError(err.message); } finally { setLoading(false); } }, [focus]);
  useEffect(() => { if (legacy) return; load(); const timer = setInterval(load, 30000); return () => clearInterval(timer); }, [load, legacy]);
  async function run(path, body) { setBusy(true); setError(""); try { await apiFetch(path, { method: "POST", body: JSON.stringify(body) }); await load(); return true; } catch (err) { setError(err.message); return false; } finally { setBusy(false); } }
  return <div><div className="market-tabs"><button className={legacy ? "secondary" : ""} onClick={() => setParams({})}>Theo Yêu cầu giá</button><button className={legacy ? "" : "secondary"} onClick={() => setParams({ tab: "purchase" })}>Theo Đề nghị mua (cũ)</button></div>{legacy ? <LegacySupplierQuoteBoard /> : <>
    <div className="page-head"><div><h1>Sàn báo giá NCC</h1><div className="page-head-sub">Chung nguồn hàng, cạnh tranh giá và vận chuyển. Cung ứng đề xuất · Quản lý chốt.</div></div><button className="secondary" onClick={load}>Làm mới</button></div>
    <input className="market-search" placeholder="Tìm mã yêu cầu, khách hàng, mặt hàng…" value={search} onChange={(e) => setSearch(e.target.value)} />
    {error && <p className="error" role="alert">{error}</p>}{loading ? <p>Đang tải…</p> : items.filter((item) => [item.price_request_code, item.customer_name, item.product_name, item.item_name].join(" ").toLocaleLowerCase().includes(search.toLocaleLowerCase())).map((item) => <details className="market-request-disclosure" key={item.id} open={focus || items.length === 1 ? true : undefined}><summary><b>{item.price_request_code} · {item.product_name || item.item_name || "Chưa có tên hàng"}</b><span>{item.customer_name} · {item.cost_quotes.length} giá hàng · {item.sourcing_plans.some((p) => p.status === "approved") ? "Đã chốt" : item.sourcing_plans.some((p) => p.status === "proposed") ? "Chờ duyệt" : item.cost_quotes.length > 1 ? "Đang so sánh" : "Đang tìm giá"}</span></summary><MarketItem item={item} user={user} run={run} busy={busy} reload={load} /></details>)}
    {!loading && items.length === 0 && <p className="muted">Chưa có Yêu cầu giá.</p>}
  </>}</div>;
}
