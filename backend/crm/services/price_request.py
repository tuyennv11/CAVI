"""Logic tính "Nguồn hàng" (NguonHang) tự động cho từng dòng Yêu cầu giá — tách khỏi model/view theo
đúng yêu cầu "tách rõ model/serializer/service" (mục 30 tài liệu nghiệp vụ). Hệ thống tự set, không
cho nhập tay (xem PriceRequestItem.source_status, editable=False)."""

from crm.models import PriceRequestItem


def refresh_source_status(item: PriceRequestItem) -> None:
    """Đối chiếu tồn khả dụng (mọi kho cộng lại — Yêu cầu giá chưa gắn 1 kho cụ thể nào) với số lượng
    khách cần, theo đúng 4 trường hợp mục 4 tài liệu:
    - Chưa có Hàng hoá xác định -> CHUA_XAC_DINH.
    - Tồn khả dụng >= số lượng cần -> TON_KHO (đủ hàng trong kho).
    - Tồn khả dụng <= 0 -> MUA_MOI (không có hàng).
    - Còn lại (có nhưng không đủ) -> TON_KHO_VA_MUA_BO_SUNG.
    """
    if item.product_id is None or item.quantity is None:
        item.source_status = PriceRequestItem.SourceStatus.CHUA_XAC_DINH
    else:
        available = item.product.available_stock()
        if available <= 0:
            item.source_status = PriceRequestItem.SourceStatus.MUA_MOI
        elif available >= item.quantity:
            item.source_status = PriceRequestItem.SourceStatus.TON_KHO
        else:
            item.source_status = PriceRequestItem.SourceStatus.TON_KHO_VA_MUA_BO_SUNG
    item.save(update_fields=["source_status"])
