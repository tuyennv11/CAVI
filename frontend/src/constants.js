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
      { value: "order", label: "Phiếu nhận hàng" },
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

// Kết quả — thang cố định để chọn nhanh thay vì gõ tay.
export const ACTIVITY_RESULT_OPTIONS = [
  "10/100",
  "20/100",
  "30/100",
  "40/100",
  "50/100",
  "60/100",
  "70/100",
  "80/100",
  "90/100",
  "100/100",
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

// --- Hỏi giá (Price Inquiry) ---
export const PRICE_INQUIRY_STATUS_LABEL = {
  open: "Đang hỏi giá",
  quoted: "Đã chốt giá",
  cancelled: "Huỷ",
};

export const PRICE_INQUIRY_TEMPLATE = `Tên hàng:
Số lượng: (Kiện / Pallet / Thùng / Bao / Container...)
Kích thước / Tổng thể tích:
Cân nặng / Tổng trọng lượng:
Hình thức vận chuyển: Chính ngạch VN -> Tiểu ngạch Cam ( Vận chuyển nội địa/ Chính ngạch VN -> Chính ngạch Lào ...)
Điểm lấy hàng:
Điểm giao hàng:
Giá trị hàng hóa:
Ghi chú: `;

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

export const DEPARTMENT_LABEL = {
  sales: "Kinh doanh",
  supply: "Cung ứng",
  operations: "Vận hành",
  accounting: "Kế toán",
  hr: "Nhân sự",
  management: "Quản lý",
};

export const GENDER_LABEL = {
  male: "Nam",
  female: "Nữ",
  other: "Khác",
};

export const WORK_STATUS_LABEL = {
  active: "Đang làm",
  on_leave: "Tạm nghỉ",
  resigned: "Đã nghỉ",
};

export const EMPLOYMENT_TYPE_LABEL = {
  official: "Chính thức",
  probation: "Thử việc",
  collaborator: "Cộng tác viên",
};

export const EMPLOYEE_DOC_TYPE_LABEL = {
  id_card: "CCCD/CMND",
  work_contract: "Hợp đồng lao động",
  contract_appendix: "Phụ lục hợp đồng",
  degree: "Bằng cấp",
  certificate: "Chứng chỉ",
  other: "Khác",
};

export const PAYMENT_METHOD_LABEL = {
  bank_transfer: "Chuyển khoản",
  cash: "Tiền mặt",
};

export const BONUS_PENALTY_TYPE_LABEL = {
  bonus: "Thưởng",
  penalty: "Phạt",
  commission: "Hoa hồng",
};

export const EDUCATION_LEVEL_LABEL = {
  postgrad: "Sau đại học",
  university: "Đại học",
  college: "Cao đẳng",
  vocational: "Trung cấp",
  high_school: "THPT",
  other: "Khác",
};
