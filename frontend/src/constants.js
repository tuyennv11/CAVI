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
