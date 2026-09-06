export const PARTNER_TYPE_LABEL = {
  customer: "Khách hàng",
  supplier: "Nhà cung cấp",
  both: "Khách hàng - NCC",
};

export const TIER_LABEL = {
  standard: "Thường",
  vip: "VIP",
  super_vip: "Siêu VIP",
};

export const OUTCOME_LABEL = {
  pending: "Đang chờ",
  success: "Thành công",
  not_closed: "Không chốt",
  received: "Đã nhận",
};

export const TIER_REQUEST_STATUS_LABEL = {
  pending: "Đang chờ",
  approved: "Đã duyệt",
  rejected: "Từ chối",
};

export function formatMoney(v) {
  return Number(v).toLocaleString("vi-VN") + " đ";
}

export function formatCurrency(v, currency) {
  const num = Number(v).toLocaleString("vi-VN");
  return currency === "USD" ? `${num} USD` : `${num} đ`;
}

export const APPROVAL_STATUS_LABEL = {
  pending: "Chờ duyệt",
  approved: "Đã duyệt",
  rejected: "Từ chối",
  paid: "Đã chi",
};

export const APPROVAL_STATUS_BADGE = {
  pending: "processing",
  approved: "new",
  rejected: "cancelled",
  paid: "done",
};

export const KD_STATUS_LABEL = {
  new: "Mới tạo",
  pending_review: "Chờ phòng ban duyệt",
  done: "Hoàn tất",
};

export const CU_STATUS_LABEL = {
  new: "Mới tạo",
  in_progress: "Chờ cung ứng",
  done: "Hoàn tất",
};

export const VH_STATUS_LABEL = {
  new: "Mới tạo",
  pending: "Chờ ghi nhận",
  gathering: "Đang gom hàng",
  gathered: "Đã gom hàng đủ",
  shipped: "Đã gửi",
};

export const KT_STATUS_LABEL = {
  not_recorded: "Chưa ghi nhận DT",
  recorded: "Đã ghi nhận DT",
};

export const BATCH_STATUS_LABEL = {
  gathering: "Đang gom hàng",
  gathered: "Đã gom hàng đủ",
  shipped: "Đã gửi",
};
