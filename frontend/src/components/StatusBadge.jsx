const LABEL = {
  new: "Mới",
  processing: "Đang xử lý",
  done: "Hoàn thành",
  cancelled: "Huỷ",
};

export default function StatusBadge({ status }) {
  return <span className={`badge badge-${status}`}>{LABEL[status] ?? status}</span>;
}

export { LABEL as STATUS_LABEL };
