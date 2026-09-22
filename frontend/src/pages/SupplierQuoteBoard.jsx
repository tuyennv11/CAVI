import { useCallback, useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { apiFetch } from "../api";
import { useAuth } from "../AuthContext";
import { formatMoney } from "../constants";
import QuoteTerms from "../components/QuoteTerms";
import MoneyInput from "../components/MoneyInput";
import SavedCostQuote from "../components/SavedCostQuote";
import { offersFor, isBestOffer } from "../utils/sourcingMarket";
import "./SupplierQuoteBoard.css";
import LegacySupplierQuoteBoard from "./LegacySupplierQuoteBoard";

const weight = (kg) => kg >= 1000 ? (kg / 1000).toLocaleString("vi-VN", { maximumFractionDigits: 3 }) + " tấn" : kg.toLocaleString("vi-VN") + " kg";
const money = (value) => value === null || value === undefined ? "Chưa đủ giá" : formatMoney(value);
const dateTime = (value) => new Date(value).toLocaleString("vi-VN", { dateStyle: "short", timeStyle: "short" });
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
  const [sourceId, setSourceId] = useState(() => (item.cost_quotes || []).find((q) => q.market.is_live)?.id ?? "");
  const [offerKey, setOfferKey] = useState(() => { const q = (item.cost_quotes || []).find((q) => q.market.is_live); return q ? "q" + q.id : ""; });
  const [tab, setTab] = useState("goods");
  const [sort, setSort] = useState("newest");
  const [details, setDetails] = useState(false);
  const [freightFor, setFreightFor] = useState(null);
  const [revision, setRevision] = useState(null);
  const [reason, setReason] = useState("");
  const supply = user?.is_manager || user?.is_supply;
  const quotes = item.cost_quotes || [];
  const live = quotes.filter((q) => q.market.is_live);
  const allOffers = live.flatMap(offersFor);
  const source = sourceId === null ? live[0] : live.find((q) => q.id === sourceId);
  const offers = source ? offersFor(source) : [];
  const selected = offerKey === null ? offers[0] : offers.find((o) => o.key === offerKey);
  const plans = item.sourcing_plans || [];
  const approved = plans.find((p) => p.status === "approved");
  const ready = allOffers.filter((o) => !o.issues.length && o.total !== null);
  const owner = (q) => supply && (user?.is_manager || q.created_by === user?.id);
  const choose = (q) => { setSourceId(q.id); setOfferKey("q" + q.id); setReason(""); setDetails(false); setFreightFor(null); };
  const sorted = [...live].sort((a, b) => sort === "price" ? (a.market.goods_total == null ? Infinity : Number(a.market.goods_total)) - (b.market.goods_total == null ? Infinity : Number(b.market.goods_total)) : new Date(b.created_at) - new Date(a.created_at));
  async function propose(e) {
    e.preventDefault();
    if (!selected || selected.issues.length || selected.total === null || approved || !reason.trim()) return;
    if (await run("/api/sourcing-plans/", { price_request_item: item.id, goods_quote: selected.quote.id, freight_offer: selected.freight?.id || null, reason })) { setReason(""); setTab("history"); }
  }
  return <section className="exchange-workspace">
    <header className="exchange-heading"><div><span className="exchange-eyebrow">{item.price_request_code} · {item.customer_name}</span><h2>{item.product_name || item.item_name || "Yêu cầu giá"}</h2><p>Cần {Number(item.quantity || 0).toLocaleString("vi-VN")} {item.unit}</p></div><span className={"exchange-status " + (approved ? "good" : "")}>{approved ? "Đã chốt" : plans.some((p) => p.status === "proposed") ? "Chờ quản lý duyệt" : "Đang tìm giá"}</span></header>
    <div className="exchange-delivery"><span>ĐIỂM GIAO</span>{item.price_request_delivery_address || "Chưa khai báo điểm giao"}</div>
    <div className="exchange-stats"><div><strong>{live.length}</strong><span>Nguồn đang chào</span></div><div><strong>{allOffers.filter((o) => o.shipping != null).length}</strong><span>Giá vận chuyển</span></div><div><strong>{ready.length}</strong><span>Phương án đủ thông tin</span></div></div>
    {approved && <div className="exchange-approved"><b>Đã chốt · {money(approved.snapshot.landed_total)}</b><span>{approved.snapshot.supplier} → {approved.snapshot.carrier} · Duyệt bởi {approved.reviewed_by_name}</span></div>}
    <div className="exchange-grid"><div className="exchange-book">
      <div className="exchange-tabs" role="tablist" aria-label="Bảng báo giá">{[["goods","Hàng hóa",live.length],["freight","Vận chuyển",offers.filter((o) => o.shipping != null).length],["history","Lịch sử / Duyệt",plans.filter((p) => p.status === "proposed").length]].map(([key,label,count]) => <button key={key} role="tab" aria-selected={tab === key} onClick={() => setTab(key)}>{label}{count > 0 && <span>{count}</span>}</button>)}</div>
      {tab === "goods" && <><div className="exchange-tools"><span>Chọn nguồn để so cước vận chuyển</span><select aria-label="Sắp xếp nguồn hàng" value={sort} onChange={(e) => setSort(e.target.value)}><option value="newest">Mới nhất</option><option value="price">Tiền hàng tăng dần</option></select></div>
        <div className="exchange-table-scroll"><table className="exchange-table"><thead><tr><th>Nguồn hàng</th><th className="numeric">Tiền hàng</th><th>Hiệu lực</th><th></th></tr></thead><tbody>{sorted.map((q) => <tr key={q.id} className={source?.id === q.id ? "selected" : ""}><td><b>{q.supplier_name || "Chưa rõ NCC"}</b><small>#{q.id} · {q.created_by_name}</small><small>{dateTime(q.created_at)}</small></td><td className="numeric"><strong>{money(q.market.goods_total)}</strong><small>{q.tax_basis === "included" ? "Đã gồm thuế" : q.tax_basis === "excluded" ? "Chưa gồm thuế" : "Chưa rõ thuế"}</small></td><td><span className={"exchange-status " + (q.confirmed ? "good" : "warn")}>{q.confirmed ? "Đã xác nhận" : "Tham khảo"}</span><small>{q.valid_until ? "Đến " + q.valid_until : "Chưa có hạn giá"}</small></td><td><button className="exchange-select" aria-pressed={source?.id === q.id} onClick={() => choose(q)}>{source?.id === q.id ? "Đang chọn" : "Chọn"}</button></td></tr>)}</tbody></table></div>
        {!live.length && <div className="exchange-empty">Chưa có nguồn hàng đang chào.<br/>Thêm báo giá đầu tiên để bắt đầu so sánh.</div>}
        {supply && <Link className="exchange-add" to={"/cost-quotes?price_request_item=" + item.id + "&new=1"}>+ Báo giá hàng hóa</Link>}
      </>}
      {tab === "freight" && <><div className="exchange-tools"><span>Nguồn #{source?.id || "—"} · {source?.supplier_name || "Chưa rõ NCC"}</span>{supply && source && <button className="secondary" onClick={() => { setFreightFor(source); setRevision(null); }}>+ Báo cước</button>}</div><div className="exchange-table-scroll"><table className="exchange-table"><thead><tr><th>Đơn vị vận chuyển</th><th className="numeric">Cước</th><th className="numeric">Tổng về điểm giao</th><th></th></tr></thead><tbody>{offers.map((o) => <tr key={o.key} className={selected?.key === o.key ? "selected" : ""}><td><b>{o.freight?.carrier_name || o.quote.carrier_name || "Chưa rõ đơn vị"}</b><small>{o.freight ? "Cước #" + o.freight.id + " · " + o.freight.created_by_name : "Cước kèm nguồn hàng"}</small><small>{o.issues.length ? "Cần bổ sung " + o.issues.length + " mục" : "Đủ thông tin"}</small></td><td className="numeric">{money(o.shipping)}</td><td className="numeric"><strong>{money(o.total)}</strong>{isBestOffer(o, allOffers) && <small className="exchange-best">Thấp nhất nhóm tương đương</small>}</td><td><button className="exchange-select" aria-pressed={selected?.key === o.key} onClick={() => { setOfferKey(o.key); setReason(""); }}>{selected?.key === o.key ? "Đang chọn" : "Chọn"}</button></td></tr>)}</tbody></table></div>{!source && <div className="exchange-empty">Chọn một nguồn hàng còn hiệu lực để xem cước.</div>}</>}
      {tab === "history" && <div className="exchange-history"><h3>Đề xuất & quyết định</h3>{!plans.length && <p className="muted">Chưa có đề xuất gửi quản lý.</p>}{plans.map((p) => <article key={p.id}><div className="market-toolbar"><b>{p.snapshot.supplier} + {p.snapshot.carrier}</b><strong>{money(p.snapshot.landed_total)}</strong></div><p>{p.reason}</p><small>{p.created_by_name} · {dateTime(p.created_at)} · {p.status === "approved" ? "Đã chốt" : p.status === "rejected" ? "Không chọn" : "Chờ duyệt"}</small>{user?.is_manager && p.status === "proposed" && <div className="market-actions"><button disabled={busy} onClick={() => run("/api/sourcing-plans/" + p.id + "/approve/", {})}>Duyệt chốt</button><button className="secondary" disabled={busy} onClick={() => run("/api/sourcing-plans/" + p.id + "/reject/", {})}>Không chọn</button></div>}</article>)}<h3>Giá đã rút / hết hiệu lực</h3>{!quotes.some((q) => !q.market.is_live || q.freight_offers?.some((f) => !f.is_live)) && <p className="muted">Chưa có lịch sử thay đổi giá.</p>}{quotes.map((q) => <div key={q.id}>{!q.market.is_live && <details><summary>Hàng #{q.id} · {q.supplier_name || "Chưa rõ NCC"} · {money(q.market.goods_total)}</summary><SavedCostQuote quote={q} index={quotes.indexOf(q)} formatWeight={weight} deliveryAddress={q.delivery_snapshot || item.price_request_delivery_address} /></details>}{(q.freight_offers || []).filter((f) => !f.is_live).map((f) => <p key={f.id}>Cước #{f.id} · Nguồn #{q.id} · {f.carrier_name} · {money(f.total_cost)}<small>{f.created_by_name} · {dateTime(f.created_at)}</small></p>)}</div>)}</div>}
    </div>
    <aside className="exchange-ticket"><div className="exchange-ticket-title"><span>PHƯƠNG ÁN ĐANG XEM</span><span>VND</span></div>{selected ? <>
      <h3>{source.supplier_name || "Chưa rõ NCC"}</h3><p className="exchange-carrier">→ {selected.freight?.carrier_name || source.carrier_name || "Chưa có đơn vị vận chuyển"}</p>
      <dl className="exchange-breakdown"><div><dt>Tiền hàng</dt><dd>{money(selected.goods)}</dd></div><div><dt>Vận chuyển</dt><dd>{money(selected.shipping)}</dd></div></dl>
      <div className="exchange-total"><span>{selected.issues.length ? "TỔNG TẠM TÍNH" : "TỔNG VỀ ĐIỂM GIAO"}</span><strong>{money(selected.total)}</strong>{isBestOffer(selected, allOffers) && <small>Thấp nhất trong nhóm cùng điều kiện</small>}</div>
      <div className="exchange-route"><span>Điểm nhận</span><p>{[source.street_address, source.ward_name, source.district_name, source.province_name, source.country_name].filter(Boolean).join(", ") || "Chưa khai báo"}</p><span>Điểm giao</span><p>{source.delivery_snapshot || item.price_request_delivery_address || "Chưa khai báo"}</p></div>
      <div className="exchange-route"><span>Điều kiện nguồn hàng</span><p>Có hàng: {source.available_at || "Chưa rõ"} · {source.payment_terms || "Chưa rõ thanh toán"}</p><p>{source.delivery_terms || "Chưa rõ điều kiện giao"}</p>{selected.freight && <><span>Điều kiện vận chuyển</span><p>{selected.freight.terms || "Chưa khai báo"} · {selected.freight.delivery_days == null ? "Chưa rõ thời gian" : selected.freight.delivery_days + " ngày"}</p></>}</div><button className="exchange-detail" onClick={() => setDetails(!details)}>{details ? "Ẩn" : "Xem"} chi tiết hàng hóa & điều kiện</button>
      {selected.issues.length ? <div className="exchange-checklist"><b>Cần bổ sung {selected.issues.length} mục</b><ul>{selected.issues.map((issue) => <li key={issue}>{issue}</li>)}</ul></div> : <p className="exchange-ready">✓ Đủ thông tin để gửi duyệt</p>}
      <div className="exchange-ticket-actions">{supply && <button className="secondary" onClick={() => { setFreightFor(source); setRevision(null); }}>+ Báo cước cho nguồn này</button>}{owner(source) && approved?.goods_quote !== source.id && <div><Link to={"/cost-quotes?price_request_item=" + item.id + "&revise=" + source.id}>Cập nhật giá hàng</Link><button disabled={busy} className="link-btn" onClick={() => run("/api/cost-quotes/" + source.id + "/withdraw/", {})}>Rút giá</button></div>}{selected.freight && owner(selected.freight) && approved?.freight_offer !== selected.freight.id && <div><button className="link-btn" onClick={() => { setFreightFor(source); setRevision(selected.freight); }}>Cập nhật cước</button><button disabled={busy} className="link-btn" onClick={() => run("/api/freight-offers/" + selected.freight.id + "/withdraw/", {})}>Rút cước</button></div>}</div>
      {!approved && <form className="exchange-propose" onSubmit={propose}><label>Lý do chọn<textarea value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Giá, chất lượng, thời gian giao…" required /></label><button disabled={busy || !!selected.issues.length || selected.total === null || !reason.trim()}>Gửi quản lý duyệt</button></form>}
    </> : <div className="exchange-empty">{sourceId !== null || offerKey !== null ? "Giá đã chọn không còn hiệu lực. Hãy chọn lại nguồn hàng hoặc cước trong bảng." : "Chọn nguồn hàng và cước để xem chi phí, điều kiện và gửi quản lý duyệt."}</div>}</aside></div>
    {details && source && <div className="exchange-expanded"><SavedCostQuote quote={source} index={quotes.indexOf(source)} formatWeight={weight} deliveryAddress={source.delivery_snapshot || item.price_request_delivery_address} /></div>}
    {freightFor && <FreightForm key={freightFor.id + "-" + (revision?.id || "new")} quote={freightFor} revision={revision} onClose={() => setFreightFor(null)} onSaved={() => { setFreightFor(null); reload(); }} />}
  </section>;
}

export default function SupplierQuoteBoard() {
  const { user } = useAuth(); const [params, setParams] = useSearchParams();
  const legacy = params.has("purchase_request_item") || params.get("tab") === "purchase";
  const focus = params.get("price_request_item");
  const [items, setItems] = useState([]), [error, setError] = useState(""), [loading, setLoading] = useState(true), [busy, setBusy] = useState(false), [search, setSearch] = useState("");
  const [updated, setUpdated] = useState(null);
  const load = useCallback(async () => { try {
    let path = "/api/price-inquiry-items/", rows = [];
    while (path) { const data = await apiFetch(path); rows = rows.concat(data.results ?? data); path = data.next ? new URL(data.next, window.location.origin).pathname + new URL(data.next, window.location.origin).search : null; }
    setItems(rows); setUpdated(new Date());
  } catch (err) { setError(err.message); } finally { setLoading(false); } }, []);
  useEffect(() => { if (legacy) return; load(); const timer = setInterval(load, 30000); return () => clearInterval(timer); }, [load, legacy]);
  async function run(path, body) { setBusy(true); setError(""); try { await apiFetch(path, { method: "POST", body: JSON.stringify(body) }); await load(); return true; } catch (err) { setError(err.message); return false; } finally { setBusy(false); } }
  const visible = items.filter((i) => [i.price_request_code,i.customer_name,i.product_name,i.item_name].join(" ").toLocaleLowerCase().includes(search.toLocaleLowerCase()));
  const active = focus ? items.find((i) => String(i.id) === focus) : visible[0];
  return <div className="exchange-page"><div className="exchange-page-head"><div><h1>Sàn báo giá NCC</h1><p>Cùng nguồn hàng · So giá vận chuyển · Quản lý chốt</p></div><div className="exchange-page-controls"><select aria-label="Loại sàn" value={legacy ? "purchase" : "inquiry"} onChange={(e) => setParams(e.target.value === "purchase" ? { tab:"purchase" } : {})}><option value="inquiry">Theo yêu cầu giá</option><option value="purchase">Đề nghị mua (cũ)</option></select><button className="secondary" onClick={() => { setError(""); load(); }}>Làm mới</button></div></div>{legacy ? <LegacySupplierQuoteBoard /> : <>
    {error && <p className="error" role="alert">{error}</p>}<div className="exchange-shell"><nav className="exchange-watchlist" aria-label="Danh sách yêu cầu giá"><div className="exchange-watchlist-title">YÊU CẦU GIÁ <span>{items.length}</span></div><input aria-label="Tìm yêu cầu" placeholder="Tìm mã, hàng, khách hàng…" value={search} onChange={(e) => setSearch(e.target.value)} /><div className="exchange-watchlist-items">{visible.map((i) => <button key={i.id} className={active?.id === i.id ? "active" : ""} aria-current={active?.id === i.id ? "true" : undefined} onClick={() => setParams({ price_request_item:String(i.id) })}><span>{i.price_request_code}<small>{i.sourcing_plans?.some((p) => p.status === "approved") ? "Đã chốt" : "Đang mở"}</small></span><b>{i.product_name || i.item_name || "Chưa có tên hàng"}</b><small>{i.customer_name} · {(i.cost_quotes || []).filter((q) => q.market.is_live).length} nguồn</small></button>)}</div>{!visible.length && <p className="exchange-empty">{loading ? "Đang tải…" : "Không có yêu cầu phù hợp."}</p>}<div className="exchange-updated">Cập nhật mỗi 30 giây{updated && <small>Lần cuối {updated.toLocaleTimeString("vi-VN")}</small>}</div></nav><div className="exchange-content">{active ? <MarketItem key={active.id} item={active} user={user} run={run} busy={busy} reload={load} /> : <div className="exchange-empty">{loading ? "Đang tải bảng giá…" : "Chọn một yêu cầu trong danh sách để xem báo giá."}</div>}</div></div>
  </>}</div>;
}
