import { Fragment, useEffect, useRef, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { apiDownload, apiFetch, apiUpload, API_URL } from "../api";
import { useAuth } from "../AuthContext";
import AddressFields from "../components/AddressFields";
import Avatar from "../components/Avatar";
import CompanyCheckboxes from "../components/CompanyCheckboxes";
import ImageThumb from "../components/ImageThumb";
import StatusBadge from "../components/StatusBadge";
import {
  ACTIVITY_TYPE_CATEGORY,
  formatMoney,
  partnerTypeLabel,
  PRICE_INQUIRY_TEMPLATE,
  SOURCE_STATUS_LABEL,
  TIER_LABEL,
} from "../constants";

function timeAgo(iso) {
  const diffMs = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diffMs / 60000);
  if (mins < 1) return "vừa xong";
  if (mins < 60) return `${mins} phút trước`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours} giờ trước`;
  return new Date(iso).toLocaleDateString("vi-VN");
}

function formatDateTime(iso) {
  if (!iso) return "";
  return new Date(iso).toLocaleString("vi-VN", { dateStyle: "short", timeStyle: "short" });
}

// Hẹn có giờ cụ thể (vd "15h gọi lại") thì quá hạn tính đúng theo giờ đó; hẹn chỉ có ngày
// (vd "thứ 4 tuần sau") thì coi như còn hạn tới hết ngày hôm đó.
function isFollowUpOverdue(followUpDate, followUpTime) {
  if (!followUpDate) return false;
  const target = new Date(`${followUpDate}T${followUpTime || "23:59:59"}`);
  return target < new Date();
}

function formatFollowUp(followUpDate, followUpTime) {
  const d = new Date(followUpDate).toLocaleDateString("vi-VN");
  return followUpTime ? `lúc ${followUpTime.slice(0, 5)} ${d}` : d;
}

function nowDateStr() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

function nowTimeStr() {
  const d = new Date();
  return `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
}

const EMPTY_ITEM = { description: "", quantity: 1, unit_price: 0, unit_cost: 0 };

const EMPTY_FILTERS = {
  search: "",
};

function formatPct(value) {
  return `${parseFloat(Number(value ?? 0).toFixed(2))}%`;
}

const EMPTY_PRICE_REQUEST_ITEM = { product: "", item_name: "", quantity: 1, unit: "", image: null };

function emptyAddress() {
  return { country: "", province: "", district: "", ward: "", street_address: "" };
}

function emptyActivityForm(currentUserId) {
  return {
    activity_type: "note",
    performed_by: currentUserId ?? "",
    activity_date: nowDateStr(),
    activity_time: nowTimeStr(),
    content: "",
    follow_up_date: "",
    follow_up_time: "",
    attachment: null,
  };
}

export default function PartnerDetail() {
  const { id } = useParams();
  const { user: currentUser } = useAuth();
  const [partner, setPartner] = useState(null);
  const [orders, setOrders] = useState([]);
  const [orderLabelForms, setOrderLabelForms] = useState({});
  const [error, setError] = useState("");
  // Lỗi riêng cho thao tác dòng báo giá — không dùng chung `error` vì trang này
  // return sớm cả trang khi `error` có giá trị, làm mất hết dữ liệu đang xem.
  const [lineError, setLineError] = useState("");
  const [searchParams, setSearchParams] = useSearchParams();
  const [tab, setTab] = useState(() => searchParams.get("tab") || "activity");
  const highlightInquiryId = searchParams.get("inquiry");

  // Đổi tab phải đồng bộ lên URL (?tab=...) — trước đây chỉ đổi state, nên lỡ F5 giữa chừng là mất
  // tab đang xem, quay về tab mặc định "Tương tác" (đã có người phản ánh mất luôn form đang điền).
  function selectTab(t) {
    setTab(t);
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      next.set("tab", t);
      return next;
    });
  }
  const [showNewOrder, setShowNewOrder] = useState(false);
  const [showAddressEdit, setShowAddressEdit] = useState(false);
  const [addressForm, setAddressForm] = useState(null);
  const [addressSaving, setAddressSaving] = useState(false);
  const [companies, setCompanies] = useState([]);
  const [showCompaniesEdit, setShowCompaniesEdit] = useState(false);
  const [companiesForm, setCompaniesForm] = useState([]);
  const [companiesSaving, setCompaniesSaving] = useState(false);
  // Nội dung mô tả lô hàng cho phiếu tạo tay — giống hệt mẫu Mô tả bên Hỏi giá, để Vận hành có đủ
  // thông tin xử lý (đơn tạo từ báo giá thì copy sẵn từ Hỏi giá gốc, không cần nhập lại — xem
  // QuotationViewSet.create_order phía backend).
  const [orderDescription, setOrderDescription] = useState(PRICE_INQUIRY_TEMPLATE);
  const [orderImage, setOrderImage] = useState(null);
  const [items, setItems] = useState([{ ...EMPTY_ITEM }]);
  const [paid, setPaid] = useState(false);
  const [onPlatform, setOnPlatform] = useState(false);

  const [activities, setActivities] = useState([]);
  const [summary, setSummary] = useState(null);
  const [filters, setFilters] = useState(EMPTY_FILTERS);
  const [activityForm, setActivityForm] = useState(() => emptyActivityForm(currentUser?.id));
  const [activityError, setActivityError] = useState("");
  const activityContentRef = useRef(null);

  const [inquiries, setInquiries] = useState([]);
  const [expandedInquiryId, setExpandedInquiryId] = useState(null);
  const [showNewInquiry, setShowNewInquiry] = useState(false);
  const [inquiryAddress, setInquiryAddress] = useState(emptyAddress());
  const [inquiryItems, setInquiryItems] = useState([{ ...EMPTY_PRICE_REQUEST_ITEM }]);
  const [inquiryDescription, setInquiryDescription] = useState("");
  const [inquiryError, setInquiryError] = useState("");
  const [messageDrafts, setMessageDrafts] = useState({});
  const [estimatedCostDrafts, setEstimatedCostDrafts] = useState({});
  const [products, setProducts] = useState([]);

  // Cảnh báo trước khi rời trang (đóng tab/F5) nếu form Yêu cầu giá đang mở và đã có nội dung —
  // reload sẽ xoá sạch state React (kể cả ảnh đã chọn, trình duyệt không giữ được qua lần tải lại),
  // nên nhắc trước để không mất dữ liệu do bấm nhầm.
  useEffect(() => {
    const hasDraft =
      showNewInquiry &&
      (inquiryDescription ||
        inquiryAddress.country ||
        inquiryItems.some((it) => it.item_name || it.product || it.image));
    if (!hasDraft) return;
    function handleBeforeUnload(e) {
      e.preventDefault();
      e.returnValue = "";
    }
    window.addEventListener("beforeunload", handleBeforeUnload);
    return () => window.removeEventListener("beforeunload", handleBeforeUnload);
  }, [showNewInquiry, inquiryDescription, inquiryAddress, inquiryItems]);

  async function loadAll() {
    try {
      const [p, orderList] = await Promise.all([
        apiFetch(`/api/partners/${id}/`),
        apiFetch(`/api/orders/?customer=${id}`),
      ]);
      setPartner(p);
      setOrders(orderList.results ?? orderList);
      setAddressForm((prev) => prev || { address: p.address || "" });
    } catch (err) {
      setError(err.message);
    }
  }

  async function loadActivities() {
    try {
      const params = new URLSearchParams();
      Object.entries(filters).forEach(([k, v]) => {
        if (v) params.set(k, v);
      });
      const qs = params.toString();
      const [list, sum] = await Promise.all([
        apiFetch(`/api/partners/${id}/activities/${qs ? `?${qs}` : ""}`),
        apiFetch(`/api/partners/${id}/activities/summary/`),
      ]);
      setActivities(list);
      setSummary(sum);
    } catch (err) {
      setError(err.message);
    }
  }

  async function markFollowUpDone(activityId) {
    try {
      await apiFetch(`/api/activities/${activityId}/`, {
        method: "PATCH",
        body: JSON.stringify({ follow_up_done: true }),
      });
      loadActivities();
    } catch (err) {
      setError(err.message);
    }
  }

  async function loadInquiries() {
    try {
      const res = await apiFetch(`/api/price-inquiries/?customer=${id}`);
      setInquiries(res.results ?? res);
    } catch (err) {
      setError(err.message);
    }
  }

  async function loadProducts() {
    try {
      const res = await apiFetch("/api/products/");
      setProducts(res.results ?? res);
    } catch (err) {
      setError(err.message);
    }
  }

  useEffect(() => {
    loadAll();
    loadInquiries();
    loadProducts();
    apiFetch("/api/companies/").then(setCompanies).catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  // Nạp form điền thông tin bill (điểm lấy/giao, khối lượng, COD) 1 lần khi đơn xuất hiện.
  useEffect(() => {
    setOrderLabelForms((prev) => {
      let changed = false;
      const next = { ...prev };
      for (const o of orders) {
        if (!next[o.id]) {
          next[o.id] = {
            pickup_point: o.pickup_point || "",
            delivery_point: o.delivery_point || "",
            weight_kg: o.weight_kg || "",
            cod_amount: o.cod_amount || "",
          };
          changed = true;
        }
      }
      return changed ? next : prev;
    });
  }, [orders]);

  useEffect(() => {
    loadActivities();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id, filters]);

  // Đến từ link duyệt đề xuất (?tab=inquiries&inquiry=<id>) — cuộn tới đúng Yêu cầu giá liên quan
  // và mở sẵn chi tiết (giờ danh sách thu gọn theo mặc định, không mở sẵn thì chỉ thấy dòng trống).
  useEffect(() => {
    if (!highlightInquiryId || inquiries.length === 0) return;
    setExpandedInquiryId(Number(highlightInquiryId));
    const el = document.getElementById(`inquiry-${highlightInquiryId}`);
    el?.scrollIntoView({ behavior: "smooth", block: "center" });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [inquiries.length, highlightInquiryId]);

  function updateFilter(field, value) {
    setFilters((prev) => ({ ...prev, [field]: value }));
  }

  function updateActivityField(field, value) {
    setActivityForm((prev) => ({ ...prev, [field]: value }));
  }

  async function handleAddActivity(e) {
    e.preventDefault();
    setActivityError("");
    if (activityForm.follow_up_date && !activityForm.follow_up_time) {
      setActivityError("Hẹn nhắc lại cần chọn giờ chính xác.");
      return;
    }
    try {
      const fd = new FormData();
      fd.set("activity_type", activityForm.activity_type);
      const activityAt =
        activityForm.activity_date && activityForm.activity_time
          ? new Date(`${activityForm.activity_date}T${activityForm.activity_time}`).toISOString()
          : new Date().toISOString();
      fd.set("activity_at", activityAt);
      if (activityForm.performed_by) fd.set("performed_by", activityForm.performed_by);
      if (activityForm.content) fd.set("content", activityForm.content);
      if (activityForm.follow_up_date) {
        fd.set("follow_up_date", activityForm.follow_up_date);
        fd.set("follow_up_time", activityForm.follow_up_time);
      }
      if (activityForm.attachment) fd.set("attachment", activityForm.attachment);

      await apiUpload(`/api/partners/${id}/activities/`, fd);
      setActivityForm(emptyActivityForm(currentUser?.id));
      activityContentRef.current?.focus();
      loadActivities();
    } catch (err) {
      setActivityError(err.message);
    }
  }

  function updateInquiryItem(index, field, value) {
    setInquiryItems((prev) => prev.map((it, i) => (i === index ? { ...it, [field]: value } : it)));
  }

  async function handleCreateInquiry(e) {
    e.preventDefault();
    setInquiryError("");
    const filledItems = inquiryItems.filter((it) => it.product || it.item_name);
    if (filledItems.length === 0) {
      setInquiryError("Cần ít nhất 1 dòng sản phẩm.");
      return;
    }
    const items = filledItems.map((it) => ({
      product: it.product ? Number(it.product) : null,
      item_name: it.item_name,
      quantity: it.quantity,
      unit: it.unit,
    }));
    try {
      const created = await apiFetch("/api/price-inquiries/", {
        method: "POST",
        body: JSON.stringify({
          customer: Number(id),
          ...inquiryAddress,
          description: inquiryDescription,
          items,
        }),
      });
      // Ảnh chọn sẵn ở form (chưa có Id lúc đó) — up ngay sau khi dòng sản phẩm đã có Id, để người
      // dùng chỉ cần bấm "Tạo yêu cầu" 1 lần là xong, không phải quay lại tìm dòng để đính ảnh.
      await Promise.all(
        filledItems.map((it, i) => {
          const createdItem = created.items[i];
          if (!it.image || !createdItem) return null;
          const fd = new FormData();
          fd.set("image", it.image);
          return apiUpload(`/api/price-inquiry-items/${createdItem.id}/`, fd, "PATCH");
        })
      );
      setInquiryAddress(emptyAddress());
      setInquiryItems([{ ...EMPTY_PRICE_REQUEST_ITEM }]);
      setInquiryDescription("");
      setShowNewInquiry(false);
      loadInquiries();
    } catch (err) {
      setInquiryError(err.message);
    }
  }

  async function handleSendMessage(inquiryId) {
    const content = (messageDrafts[inquiryId] || "").trim();
    if (!content) return;
    try {
      await apiFetch(`/api/price-inquiries/${inquiryId}/messages/`, {
        method: "POST",
        body: JSON.stringify({ content }),
      });
      setMessageDrafts((prev) => ({ ...prev, [inquiryId]: "" }));
      loadInquiries();
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleUploadItemImage(itemId, file) {
    if (!file) return;
    setInquiryError("");
    const fd = new FormData();
    fd.set("image", file);
    try {
      await apiUpload(`/api/price-inquiry-items/${itemId}/`, fd, "PATCH");
      loadInquiries();
    } catch (err) {
      setInquiryError(err.message);
    }
  }

  async function handleCreatePurchaseRequest(itemId) {
    setInquiryError("");
    try {
      await apiFetch(`/api/price-inquiry-items/${itemId}/create-purchase-request/`, { method: "POST" });
      loadInquiries();
    } catch (err) {
      setInquiryError(err.message);
    }
  }

  async function handleSaveEstimatedCost(itemId, value) {
    setInquiryError("");
    try {
      await apiFetch(`/api/price-inquiry-items/${itemId}/`, {
        method: "PATCH",
        body: JSON.stringify({ estimated_cost_price: value === "" ? null : value }),
      });
      loadInquiries();
    } catch (err) {
      setInquiryError(err.message);
    }
  }

  async function handleSaveAddress() {
    setAddressSaving(true);
    try {
      const updated = await apiFetch(`/api/partners/${id}/`, { method: "PATCH", body: JSON.stringify(addressForm) });
      setPartner(updated);
      setShowAddressEdit(false);
    } catch (err) {
      setError(err.message);
    } finally {
      setAddressSaving(false);
    }
  }

  function openCompaniesEdit() {
    setCompaniesForm((partner.companies_detail || []).map((c) => c.id));
    setShowCompaniesEdit(true);
  }

  async function handleSaveCompanies() {
    if (companiesForm.length === 0) {
      setError("Phải tick ít nhất 1 công ty.");
      return;
    }
    setCompaniesSaving(true);
    try {
      const updated = await apiFetch(`/api/partners/${id}/`, {
        method: "PATCH",
        body: JSON.stringify({ companies: companiesForm }),
      });
      setPartner(updated);
      setShowCompaniesEdit(false);
    } catch (err) {
      setError(err.message);
    } finally {
      setCompaniesSaving(false);
    }
  }

  function updateOrderLabelField(orderId, field, value) {
    setOrderLabelForms((prev) => ({ ...prev, [orderId]: { ...prev[orderId], [field]: value } }));
  }

  async function handleSaveOrderLabel(orderId) {
    const form = orderLabelForms[orderId];
    try {
      await apiFetch(`/api/orders/${orderId}/`, {
        method: "PATCH",
        body: JSON.stringify({
          pickup_point: form.pickup_point,
          delivery_point: form.delivery_point,
          weight_kg: form.weight_kg || null,
          cod_amount: form.cod_amount || null,
        }),
      });
      loadAll();
    } catch (err) {
      // Không dùng `error` dùng chung toàn trang — trang này return sớm cả trang khi `error` có
      // giá trị (xem lineError ở trên), sẽ xoá mất cả tab Phiếu nhận hàng đang xem.
      setLineError(err.message);
    }
  }

  async function handlePrintOrderLabel(orderId) {
    try {
      await apiDownload(`/api/orders/${orderId}/label/`, `phieu-${String(orderId).padStart(6, "0")}.pdf`);
    } catch (err) {
      setLineError(err.message);
    }
  }

  function updateItem(index, field, value) {
    setItems((prev) => prev.map((it, i) => (i === index ? { ...it, [field]: value } : it)));
  }

  async function handleCreateOrder(e) {
    e.preventDefault();
    try {
      // Không set status — để mặc định pending_receipt, đơn tạo tay cũng phải qua đúng quy trình
      // Vận hành ghi nhận thực tế + Kinh doanh xác nhận, không có ngoại lệ.
      const order = await apiFetch("/api/orders/", {
        method: "POST",
        body: JSON.stringify({
          customer: Number(id),
          description: orderDescription,
          items,
          paid,
          on_platform: onPlatform,
        }),
      });
      if (orderImage) {
        const fd = new FormData();
        fd.set("image", orderImage);
        await apiUpload(`/api/orders/${order.id}/`, fd, "PATCH");
      }
      setItems([{ ...EMPTY_ITEM }]);
      setOrderDescription(PRICE_INQUIRY_TEMPLATE);
      setOrderImage(null);
      setPaid(false);
      setOnPlatform(false);
      setShowNewOrder(false);
      selectTab("orders");
      loadAll();
    } catch (err) {
      // Không dùng `error` dùng chung toàn trang — sẽ xoá mất cả trang khi có lỗi (xem lineError).
      setLineError(err.message);
    }
  }

  if (error) return <p className="error">{error}</p>;
  if (!partner) return <p className="muted">Đang tải...</p>;

  return (
    <div>
      <div className="profile-header">
        <Avatar name={partner.name} size="lg" />
        <div style={{ flex: 1, minWidth: 0 }}>
          <div className="profile-title-row">
            <Link to="/partners" className="profile-back" title="Danh sách đối tác">
              &larr;
            </Link>
            <h1>{partner.name}</h1>
            <span className="badge badge-neutral">{partnerTypeLabel(partner)}</span>
            {partner.tier_override && (
              <span className={`badge badge-tier-${partner.tier_override}`}>{TIER_LABEL[partner.tier_override]}</span>
            )}
            {partner.contact_person && <span className="profile-pill">👤 {partner.contact_person}</span>}
            {partner.phone && <span className="profile-pill">📞 {partner.phone}</span>}
            {partner.assigned_to_detail && (
              <span className="profile-pill">Phụ trách: {partner.assigned_to_detail.full_name}</span>
            )}
          </div>
          <div className="profile-meta-row">
            {partner.note && <span>{partner.note}</span>}
          </div>
          <div className="profile-meta-row">
            {showAddressEdit ? (
              <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
                <input
                  placeholder="Địa chỉ"
                  value={addressForm.address}
                  onChange={(e) => setAddressForm({ ...addressForm, address: e.target.value })}
                  style={{ minWidth: 260 }}
                />
                <button type="button" disabled={addressSaving} onClick={handleSaveAddress}>
                  {addressSaving ? "Đang lưu..." : "Lưu địa chỉ"}
                </button>
                <button type="button" className="secondary" onClick={() => setShowAddressEdit(false)}>
                  Huỷ
                </button>
              </div>
            ) : (
              <span className="muted" style={{ fontSize: 12.5 }}>
                📍 {partner.address || "Chưa có địa chỉ"}{" "}
                <button type="button" className="link-btn" onClick={() => setShowAddressEdit(true)}>
                  Sửa
                </button>
              </span>
            )}
          </div>
          <div className="profile-meta-row">
            {showCompaniesEdit ? (
              <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
                <CompanyCheckboxes companies={companies} selected={companiesForm} onChange={setCompaniesForm} />
                <button type="button" disabled={companiesSaving} onClick={handleSaveCompanies}>
                  {companiesSaving ? "Đang lưu..." : "Lưu công ty"}
                </button>
                <button type="button" className="secondary" onClick={() => setShowCompaniesEdit(false)}>
                  Huỷ
                </button>
              </div>
            ) : (
              <span className="muted" style={{ fontSize: 12.5, display: "flex", alignItems: "center", gap: 6 }}>
                🏢{" "}
                {(partner.companies_detail || []).map((c) => (
                  <span className="badge badge-neutral" key={c.id}>
                    {c.code}
                  </span>
                ))}
                <button type="button" className="link-btn" onClick={openCompaniesEdit}>
                  Sửa
                </button>
              </span>
            )}
          </div>
        </div>
      </div>

      <div className="tabs">
        <button className={`tab-btn${tab === "activity" ? " active" : ""}`} onClick={() => selectTab("activity")}>
          Tương tác
        </button>
        <button className={`tab-btn${tab === "inquiries" ? " active" : ""}`} onClick={() => selectTab("inquiries")}>
          Yêu cầu giá ({inquiries.length})
        </button>
        <button className={`tab-btn${tab === "orders" ? " active" : ""}`} onClick={() => selectTab("orders")}>
          Phiếu nhận hàng ({orders.length})
        </button>
      </div>

      {tab === "activity" && (
        <div>
          <div className="panel">
            <div className="page-head">
              <h2 style={{ margin: 0 }}>Lịch sử tương tác</h2>
              {summary && (
                <span className="muted" style={{ fontSize: 12.5 }}>
                  {summary.total_activities} hoạt động · Gần nhất:{" "}
                  {summary.last_activity_at ? timeAgo(summary.last_activity_at) : "—"}
                  {summary.upcoming_follow_ups > 0 && ` · 🔔 ${summary.upcoming_follow_ups} follow-up sắp tới`}
                </span>
              )}
            </div>

            <div className="quick-log-row">
              <form className="quick-log-bar" onSubmit={handleAddActivity}>
                <div className="quick-log-group">
                  <input
                    type="date"
                    className="quick-log-date"
                    title="Ngày"
                    required
                    value={activityForm.activity_date}
                    onChange={(e) => updateActivityField("activity_date", e.target.value)}
                  />
                  <input
                    type="time"
                    className="quick-log-time"
                    title="Giờ"
                    required
                    value={activityForm.activity_time}
                    onChange={(e) => updateActivityField("activity_time", e.target.value)}
                  />
                </div>
                <input
                  ref={activityContentRef}
                  required
                  className="quick-log-input"
                  placeholder="Ghi nhanh hoạt động với khách... (VD: Đã gọi cho anh Nam báo giá lô hàng T9)"
                  value={activityForm.content}
                  onChange={(e) => updateActivityField("content", e.target.value)}
                />
                <div className="quick-log-group quick-log-followup">
                  <span className="quick-log-group-icon" title="Hẹn nhắc lại">
                    🔔
                  </span>
                  <input
                    type="date"
                    className="quick-log-date"
                    title="Hẹn nhắc lại — ngày"
                    value={activityForm.follow_up_date}
                    onChange={(e) => updateActivityField("follow_up_date", e.target.value)}
                  />
                  <input
                    type="time"
                    className="quick-log-time"
                    title="Hẹn nhắc lại — giờ chính xác"
                    value={activityForm.follow_up_time}
                    onChange={(e) => updateActivityField("follow_up_time", e.target.value)}
                  />
                </div>
                <label className="quick-log-file" title="Đính kèm file">
                  📎
                  <input
                    type="file"
                    hidden
                    onChange={(e) => updateActivityField("attachment", e.target.files[0] ?? null)}
                  />
                </label>
                <button type="submit" className="quick-log-submit">
                  Lưu
                </button>
              </form>
              <input
                className="search-input quick-log-search"
                placeholder="Tìm nội dung..."
                value={filters.search}
                onChange={(e) => updateFilter("search", e.target.value)}
              />
            </div>
            {activityError && <p className="error">{activityError}</p>}

            {activities.length === 0 ? (
              <p className="muted">Chưa có hoạt động nào.</p>
            ) : (
              <ul className="timeline">
                {activities.map((a) => {
                  const category = ACTIVITY_TYPE_CATEGORY[a.activity_type] ?? "interaction";
                  const overdue = !a.follow_up_done && isFollowUpOverdue(a.follow_up_date, a.follow_up_time);
                  return (
                    <li className="timeline-item" key={a.id}>
                      <div className="timeline-marker">
                        <span className={`timeline-dot cat-${category}`} />
                      </div>
                      <div className="timeline-body">
                        <div className="timeline-row">
                          <span className="timeline-time">{formatDateTime(a.activity_at)}</span>
                          <span className="timeline-content-text">{a.content || a.title}</span>
                          {a.follow_up_date && (
                            <span
                              className={`timeline-followup${overdue ? " overdue" : ""}${
                                a.follow_up_done ? " done" : ""
                              }`}
                            >
                              🔔 Nhắc hẹn {formatFollowUp(a.follow_up_date, a.follow_up_time)}
                              {overdue ? " (quá hạn)" : ""}
                              {a.follow_up_done ? " ✓ đã nhắc" : ""}
                            </span>
                          )}
                          {a.follow_up_date && !a.follow_up_done && (
                            <button
                              type="button"
                              className="link-btn timeline-link"
                              onClick={() => markFollowUpDone(a.id)}
                            >
                              Đánh dấu đã nhắc
                            </button>
                          )}
                          {a.related_order_label && (
                            <button type="button" className="link-btn timeline-link" onClick={() => selectTab("orders")}>
                              {a.related_order_label}
                            </button>
                          )}
                          {a.related_reference && <span className="badge badge-neutral">{a.related_reference}</span>}
                          {a.attachment && (
                            <a
                              className="timeline-link"
                              href={`${API_URL}${a.attachment}`}
                              target="_blank"
                              rel="noreferrer"
                            >
                              📎 Tệp đính kèm
                            </a>
                          )}
                        </div>
                        {a.contact_person && (
                          <div className="timeline-meta">
                            <span>Liên hệ: {a.contact_person}</span>
                          </div>
                        )}
                        {a.result && (
                          <div className="timeline-result">
                            Kết quả: <b>{a.result}</b>
                          </div>
                        )}
                        {a.note && <div className="timeline-note">Ghi chú: {a.note}</div>}
                      </div>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
        </div>
      )}

      {tab === "inquiries" && (
        <div className="panel">
          <div className="page-head">
            <h2 style={{ margin: 0 }}>Yêu cầu giá</h2>
            <button onClick={() => setShowNewInquiry((v) => !v)}>
              {showNewInquiry ? "Đóng" : "+ Tạo yêu cầu giá"}
            </button>
          </div>

          {showNewInquiry && (
            <form className="field-grid" onSubmit={handleCreateInquiry} style={{ marginBottom: 14 }}>
              <label>Điểm giao hàng</label>
              <AddressFields value={inquiryAddress} onChange={setInquiryAddress} />

              <label>Sản phẩm</label>
              {inquiryItems.map((it, i) => (
                <div className="order-item-row" style={{ gridTemplateColumns: "1.5fr 1fr 80px 80px 90px 32px" }} key={i}>
                  <select
                    value={it.product}
                    onChange={(e) => {
                      updateInquiryItem(i, "product", e.target.value);
                      const p = products.find((x) => String(x.id) === e.target.value);
                      if (p) {
                        updateInquiryItem(i, "item_name", p.name);
                        updateInquiryItem(i, "unit", p.unit);
                      }
                    }}
                  >
                    <option value="">— Chọn hàng hoá (nếu có) —</option>
                    {products.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.sku} — {p.name} (tồn: {p.stock_on_hand})
                      </option>
                    ))}
                  </select>
                  <input
                    placeholder="Tên hàng"
                    value={it.item_name}
                    onChange={(e) => updateInquiryItem(i, "item_name", e.target.value)}
                    required
                  />
                  <input
                    type="number"
                    min="0"
                    step="0.01"
                    placeholder="SL"
                    value={it.quantity}
                    onChange={(e) => updateInquiryItem(i, "quantity", e.target.value)}
                  />
                  <input
                    placeholder="ĐVT"
                    value={it.unit}
                    onChange={(e) => updateInquiryItem(i, "unit", e.target.value)}
                  />
                  <label className="link-btn" style={{ cursor: "pointer", fontSize: 12, textAlign: "center" }}>
                    {it.image ? (
                      <img
                        src={URL.createObjectURL(it.image)}
                        alt=""
                        style={{ width: 28, height: 28, objectFit: "cover", borderRadius: 6, verticalAlign: "middle" }}
                      />
                    ) : (
                      "+ Ảnh"
                    )}
                    <input
                      type="file"
                      accept="image/*"
                      hidden
                      onChange={(e) => updateInquiryItem(i, "image", e.target.files[0] || null)}
                    />
                  </label>
                  {inquiryItems.length > 1 && (
                    <button
                      type="button"
                      className="link-btn"
                      onClick={() => setInquiryItems(inquiryItems.filter((_, x) => x !== i))}
                    >
                      Xoá
                    </button>
                  )}
                </div>
              ))}
              <button
                type="button"
                className="link-btn"
                onClick={() => setInquiryItems([...inquiryItems, { ...EMPTY_PRICE_REQUEST_ITEM }])}
              >
                + Thêm sản phẩm
              </button>

              <label>
                Mô tả thêm
                <textarea
                  rows={3}
                  value={inquiryDescription}
                  onChange={(e) => setInquiryDescription(e.target.value)}
                />
              </label>
              {inquiryError && <p className="error">{inquiryError}</p>}
              <div className="modal-actions">
                <button type="button" className="secondary" onClick={() => setShowNewInquiry(false)}>
                  Huỷ
                </button>
                <button type="submit">Tạo yêu cầu</button>
              </div>
            </form>
          )}

          {inquiries.length === 0 ? (
            <p className="muted">Chưa có yêu cầu giá nào.</p>
          ) : (
            <div className="table-wrap">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Trạng thái</th>
                    <th>Mã</th>
                    <th>Sản phẩm</th>
                    <th>Giao tới</th>
                    <th>Phụ trách</th>
                    <th>Ngày tạo</th>
                  </tr>
                </thead>
                <tbody>
                  {inquiries.map((inq) => {
                    const address = [inq.street_address, inq.ward_name, inq.district_name, inq.province_name, inq.country_name]
                      .filter(Boolean)
                      .join(", ");
                    const itemsSummary = inq.items.map((it) => it.product_name || it.item_name).filter(Boolean).join(", ");
                    const isExpanded = expandedInquiryId === inq.id;
                    return (
                      <Fragment key={inq.id}>
                        <tr
                          className={`clickable${String(inq.id) === highlightInquiryId ? " highlighted" : ""}`}
                          id={`inquiry-${inq.id}`}
                          onClick={() => setExpandedInquiryId(isExpanded ? null : inq.id)}
                        >
                          <td>
                            <StatusBadge status={inq.status} />
                          </td>
                          <td>{inq.code}</td>
                          <td className="ellipsis-cell" title={itemsSummary}>
                            {itemsSummary || "—"}
                          </td>
                          <td className="ellipsis-cell" title={address}>
                            {address || "—"}
                          </td>
                          <td>{inq.assigned_to_detail?.full_name ?? inq.created_by_name}</td>
                          <td>{formatDateTime(inq.created_at)}</td>
                        </tr>
                        {isExpanded && (
                          <tr>
                            <td colSpan={6} style={{ background: "var(--surface-muted)", padding: "6px 16px" }}>
                              <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: "4px 18px", fontSize: 13, marginBottom: 6 }}>
                                {inq.description && <span>{inq.description}</span>}
                                {inq.items.map((it) => (
                                  <span key={it.id} style={{ display: "flex", alignItems: "center", gap: 6 }}>
                                    {inq.items.length > 1 && <b>{it.product_name || it.item_name}</b>}
                                    <span className={`badge badge-source-${it.source_status}`}>
                                      {SOURCE_STATUS_LABEL[it.source_status] ?? it.source_status}
                                    </span>
                                    {(currentUser?.is_manager || currentUser?.is_supply) ? (
                                      <span style={{ display: "flex", alignItems: "center", gap: 4 }}>
                                        <span className="muted" style={{ fontSize: 11.5 }}>Giá vốn tạm tính:</span>
                                        <input
                                          type="number"
                                          step="0.01"
                                          placeholder="—"
                                          style={{ width: 100, fontSize: 12, padding: "3px 6px" }}
                                          value={estimatedCostDrafts[it.id] ?? it.estimated_cost_price ?? ""}
                                          onChange={(e) =>
                                            setEstimatedCostDrafts((prev) => ({ ...prev, [it.id]: e.target.value }))
                                          }
                                          onBlur={(e) => {
                                            if (e.target.value !== (it.estimated_cost_price ?? "").toString()) {
                                              handleSaveEstimatedCost(it.id, e.target.value);
                                            }
                                          }}
                                        />
                                      </span>
                                    ) : (
                                      it.estimated_cost_price && (
                                        <span className="muted" style={{ fontSize: 11.5 }}>
                                          Giá vốn tạm tính: {formatMoney(it.estimated_cost_price)}
                                        </span>
                                      )
                                    )}
                                    <ImageThumb src={it.image} size={22} />
                                    <label className="link-btn" style={{ cursor: "pointer", fontSize: 11.5 }}>
                                      {it.image ? "Đổi ảnh" : "+ Ảnh"}
                                      <input
                                        type="file"
                                        accept="image/*"
                                        hidden
                                        onChange={(e) => {
                                          handleUploadItemImage(it.id, e.target.files[0]);
                                          e.target.value = "";
                                        }}
                                      />
                                    </label>
                                    {(it.source_status === "mua_moi" || it.source_status === "ton_kho_va_mua_bo_sung") && (
                                      it.purchase_request_item_id ? (
                                        <Link
                                          className="link-btn"
                                          to={`/supplier-quotes?purchase_request_item=${it.purchase_request_item_id}`}
                                          style={{ fontSize: 11.5 }}
                                        >
                                          Xem trên Sàn báo giá NCC →
                                        </Link>
                                      ) : (
                                        (currentUser?.is_manager || currentUser?.is_supply) && (
                                          <button
                                            type="button"
                                            className="link-btn"
                                            style={{ fontSize: 11.5 }}
                                            onClick={() => handleCreatePurchaseRequest(it.id)}
                                          >
                                            Tạo đề nghị mua
                                          </button>
                                        )
                                      )
                                    )}
                                  </span>
                                ))}
                              </div>

                              {inq.messages.length > 0 && (
                                <div className="inquiry-thread">
                                  {inq.messages.map((m) => (
                                    <div className={`inquiry-message${m.is_quote ? " quote" : ""}`} key={m.id}>
                                      <b>{m.author_name}</b>
                                      <span className="muted"> · {formatDateTime(m.created_at)}</span>
                                      <div>{m.content}</div>
                                    </div>
                                  ))}
                                </div>
                              )}

                              <div className="inquiry-reply-row" onClick={(e) => e.stopPropagation()}>
                                <input
                                  placeholder="Trao đổi..."
                                  value={messageDrafts[inq.id] || ""}
                                  onChange={(e) => setMessageDrafts((prev) => ({ ...prev, [inq.id]: e.target.value }))}
                                  onKeyDown={(e) => {
                                    if (e.key === "Enter") {
                                      e.preventDefault();
                                      handleSendMessage(inq.id);
                                    }
                                  }}
                                />
                                <button type="button" onClick={() => handleSendMessage(inq.id)}>
                                  Gửi
                                </button>
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
      )}

      {tab === "orders" && (
        <div className="panel">
          <div className="page-head" style={{ marginBottom: 14 }}>
            <h2 style={{ margin: 0 }}>Danh sách phiếu nhận hàng</h2>
            <button onClick={() => setShowNewOrder((v) => !v)}>{showNewOrder ? "Đóng" : "+ Tạo phiếu nhận hàng"}</button>
          </div>

          {lineError && <p className="error">{lineError}</p>}

          {showNewOrder && (
            <form className="field-grid" onSubmit={handleCreateOrder} style={{ marginBottom: 12 }}>
              <textarea
                rows={9}
                value={orderDescription}
                onChange={(e) => setOrderDescription(e.target.value)}
              />
              <label>
                Hình ảnh
                <input type="file" accept="image/*" onChange={(e) => setOrderImage(e.target.files[0] ?? null)} />
              </label>
              {items.map((it, i) => (
                <div className="order-item-row" style={{ gridTemplateColumns: "1fr 70px 110px 110px" }} key={i}>
                  <input
                    placeholder="Mô tả hàng/dịch vụ"
                    value={it.description}
                    onChange={(e) => updateItem(i, "description", e.target.value)}
                    required
                  />
                  <input
                    type="number"
                    min="0"
                    step="0.01"
                    placeholder="SL"
                    value={it.quantity}
                    onChange={(e) => updateItem(i, "quantity", e.target.value)}
                  />
                  <input
                    type="number"
                    min="0"
                    step="0.01"
                    placeholder="Giá bán"
                    value={it.unit_price}
                    onChange={(e) => updateItem(i, "unit_price", e.target.value)}
                  />
                  <input
                    type="number"
                    min="0"
                    step="0.01"
                    placeholder="Giá vốn"
                    value={it.unit_cost}
                    onChange={(e) => updateItem(i, "unit_cost", e.target.value)}
                  />
                </div>
              ))}
              <button type="button" className="link-btn" onClick={() => setItems([...items, { ...EMPTY_ITEM }])}>
                + Thêm dòng
              </button>
              <div style={{ display: "flex", gap: 20 }}>
                <label style={{ flexDirection: "row", alignItems: "center", gap: 6 }}>
                  <input type="checkbox" checked={paid} onChange={(e) => setPaid(e.target.checked)} /> Đã thanh toán
                </label>
                <label style={{ flexDirection: "row", alignItems: "center", gap: 6 }}>
                  <input
                    type="checkbox"
                    checked={onPlatform}
                    onChange={(e) => setOnPlatform(e.target.checked)}
                  />{" "}
                  Qua sàn
                </label>
              </div>
              <div className="modal-actions">
                <button type="submit">Lưu phiếu nhận hàng</button>
              </div>
            </form>
          )}

          {orders.length === 0 ? (
            <p className="muted">Chưa có phiếu nhận hàng.</p>
          ) : (
            <div className="table-wrap">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Phiếu nhận hàng</th>
                    <th>Trạng thái</th>
                    <th>Thanh toán</th>
                    <th>Doanh thu</th>
                    <th>Lợi nhuận gộp</th>
                    <th>Khoảng giá sàn – trần</th>
                    <th>Điểm lấy hàng</th>
                    <th>Điểm giao hàng</th>
                    <th>KL (kg)</th>
                    <th>COD</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {orders.map((o) => {
                    const form = orderLabelForms[o.id] || {
                      pickup_point: "",
                      delivery_point: "",
                      weight_kg: "",
                      cod_amount: "",
                    };
                    return (
                      <tr key={o.id}>
                        <td>#{o.id}</td>
                        <td>
                          <StatusBadge status={o.status} />
                        </td>
                        <td>
                          <span className={`badge ${o.paid ? "badge-done" : "badge-processing"}`}>
                            {o.paid ? "Đã trả" : "Chưa trả"}
                          </span>
                        </td>
                        <td>{formatMoney(o.total)}</td>
                        <td>{formatMoney(o.gross_profit)}</td>
                        <td style={{ fontSize: 12 }}>
                          {o.floor_price != null ? (
                            <>
                              {formatMoney(o.floor_price)} – {formatMoney(o.ceiling_price)}
                              <div className="muted">
                                ({formatPct(o.floor_pct)} – {formatPct(o.ceiling_pct)})
                              </div>
                            </>
                          ) : (
                            <span className="muted">—</span>
                          )}
                        </td>
                        <td>
                          <input
                            style={{ width: 110 }}
                            value={form.pickup_point}
                            onChange={(e) => updateOrderLabelField(o.id, "pickup_point", e.target.value)}
                          />
                        </td>
                        <td>
                          <input
                            style={{ width: 110 }}
                            value={form.delivery_point}
                            onChange={(e) => updateOrderLabelField(o.id, "delivery_point", e.target.value)}
                          />
                        </td>
                        <td>
                          <input
                            type="number"
                            style={{ width: 60 }}
                            value={form.weight_kg}
                            onChange={(e) => updateOrderLabelField(o.id, "weight_kg", e.target.value)}
                          />
                        </td>
                        <td>
                          <input
                            type="number"
                            style={{ width: 90 }}
                            value={form.cod_amount}
                            onChange={(e) => updateOrderLabelField(o.id, "cod_amount", e.target.value)}
                          />
                        </td>
                        <td>
                          <div style={{ display: "flex", gap: 6 }}>
                            <button type="button" className="link-btn" onClick={() => handleSaveOrderLabel(o.id)}>
                              Lưu
                            </button>
                            <button
                              type="button"
                              className="link-btn"
                              onClick={() => handlePrintOrderLabel(o.id)}
                            >
                              In bill
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

    </div>
  );
}
