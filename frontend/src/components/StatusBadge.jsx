const LABEL = {
  new: "Mới",
  processing: "Đang xử lý",
  done: "Hoàn thành",
  cancelled: "Huỷ",
  not_processed: "Chưa xử lý",
  in_progress: "Đang xử lý",
  todo: "Cần làm",
  open: "Đang hỏi giá",
  quoted: "Đã chốt giá",
  pending_receipt: "Chờ vận hành nhận hàng",
  pending_confirmation: "Chờ Kinh doanh xác nhận",
  // Trạng thái quy trình của Yêu cầu giá (crm.PriceRequest.Status) — thay cho open/quoted/cancelled cũ.
  cho_cung_ung: "Chờ Cung ứng",
  da_kiem_tra_nguon_hang: "Đã kiểm tra nguồn hàng",
  cho_tinh_gia: "Chờ tính giá",
  cho_duyet: "Chờ duyệt giá",
  da_duyet: "Đã duyệt giá",
  da_gui_khach: "Đã gửi khách",
  khach_dong_y: "Khách đồng ý",
  khach_tu_choi: "Khách từ chối",
  dang_thuong_luong: "Đang thương lượng",
  huy: "Huỷ",
};

export default function StatusBadge({ status }) {
  return <span className={`badge badge-${status}`}>{LABEL[status] ?? status}</span>;
}

export { LABEL as STATUS_LABEL };
