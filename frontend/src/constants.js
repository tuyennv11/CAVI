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

// --- Hoạt động khách hàng (Timeline) ---
export const ACTIVITY_TYPE_GROUPS = [
  {
    label: "Tương tác",
    options: [
      { value: "call", label: "Cuộc gọi" },
      { value: "email", label: "Email" },
      { value: "message", label: "Tin nhắn" },
      { value: "meeting", label: "Gặp mặt" },
      { value: "note", label: "Ghi chú" },
    ],
  },
  {
    label: "Công việc",
    options: [
      { value: "task", label: "Công việc cần làm" },
      { value: "follow_up", label: "Follow-up" },
      { value: "appointment", label: "Lịch hẹn / cuộc họp" },
    ],
  },
  {
    label: "Kinh doanh",
    options: [
      { value: "opportunity", label: "Cơ hội kinh doanh" },
      { value: "quote", label: "Báo giá" },
      { value: "order", label: "Đơn hàng" },
      { value: "contract", label: "Hợp đồng" },
      { value: "payment", label: "Thanh toán" },
    ],
  },
  {
    label: "Chăm sóc khách hàng",
    options: [
      { value: "support_request", label: "Yêu cầu hỗ trợ" },
      { value: "complaint", label: "Khiếu nại" },
      { value: "issue_handling", label: "Xử lý sự cố" },
      { value: "post_sale_care", label: "Chăm sóc sau bán hàng" },
    ],
  },
];

export const ACTIVITY_TYPE_LABEL = Object.fromEntries(
  ACTIVITY_TYPE_GROUPS.flatMap((g) => g.options.map((o) => [o.value, o.label]))
);

// Nhóm loại nào thuộc category nào — dùng để tô màu chấm trên Timeline.
export const ACTIVITY_TYPE_CATEGORY = Object.fromEntries(
  ACTIVITY_TYPE_GROUPS.flatMap((g, i) =>
    g.options.map((o) => [o.value, ["interaction", "task", "business", "care"][i]])
  )
);

export const ACTIVITY_TASK_LIKE_TYPES = [
  "task",
  "follow_up",
  "appointment",
  "support_request",
  "complaint",
  "issue_handling",
  "post_sale_care",
];

// Các loại hoạt động dùng hàng ngày — hiện thành nút bấm nhanh thay vì phải mở form rồi chọn trong dropdown.
export const QUICK_ACTIVITY_TYPES = [
  { value: "call", label: "Cuộc gọi", icon: "📞" },
  { value: "message", label: "Tin nhắn", icon: "💬" },
  { value: "email", label: "Email", icon: "✉️" },
  { value: "meeting", label: "Gặp mặt", icon: "🤝" },
  { value: "note", label: "Ghi chú", icon: "📝" },
  { value: "task", label: "Công việc", icon: "✅" },
  { value: "follow_up", label: "Follow-up", icon: "⏰" },
];

export const ACTIVITY_STATUS_LABEL = {
  not_processed: "Chưa xử lý",
  in_progress: "Đang xử lý",
  done: "Hoàn thành",
  cancelled: "Huỷ",
};

// --- Công việc (Task) ---
export const TASK_PRIORITY_LABEL = {
  low: "Thấp",
  normal: "Bình thường",
  high: "Cao",
  urgent: "Khẩn cấp",
};

export const TASK_STATUS_LABEL = {
  todo: "Cần làm",
  in_progress: "Đang làm",
  done: "Hoàn thành",
  cancelled: "Huỷ",
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
