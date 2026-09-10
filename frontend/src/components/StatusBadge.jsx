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
};

export default function StatusBadge({ status }) {
  return <span className={`badge badge-${status}`}>{LABEL[status] ?? status}</span>;
}

export { LABEL as STATUS_LABEL };
