# Sàn báo giá theo Yêu cầu giá

- `CostQuote` là nguồn dữ liệu chung cho màn hình trả lời và sàn. Không sao chép sang `SupplierQuote` (luồng Đề nghị mua cũ vẫn có tab riêng).
- Mỗi `CostQuote` là một phương án trọn bộ các dòng hàng của một nguồn. Giá thiếu đơn giá được xem là chưa đủ thông tin, không phải bằng 0.
- `FreightOffer` gắn với đúng phiên bản `CostQuote`, vận chuyển toàn bộ các dòng của nguồn đó. Tạo hoặc cập nhật giá cước không được chuyển sang nguồn khác.
- Giá hàng và cước có thể lưu dưới dạng tham khảo. Đề xuất/chốt yêu cầu xác nhận NCC, hiệu lực, thuế đã bao gồm, địa chỉ, thời gian và điều kiện dịch vụ. Cước kèm trong giá hàng dùng chung xác nhận/hiệu lực/thuế và điều kiện giao nhận của giá hàng.
- Giá được cập nhật bằng POST với `supersedes`. Giá gốc trở thành không hoạt động nhưng giữ nguyên các dòng và người gửi. Không hỗ trợ PATCH/DELETE để tránh mất lịch sử.
- Cung ứng chỉ sửa/rút giá của mình; quản lý được quản lý mọi giá trong công ty đang chọn. Mọi quan hệ ghi vào phải thuộc phạm vi công ty được phép.
- `SourcingPlan` lưu đề xuất và ảnh chụp chi phí, tuyến, điều kiện. Chỉ quản lý chốt. Khoá dòng yêu cầu và unique constraint bảo đảm mỗi dòng yêu cầu có tối đa một phương án đã chốt. Giá mới không thay phương án đó.
- Trước duyệt kiểm tra lại hiệu lực, trạng thái và địa chỉ giao. Địa chỉ giao thay đổi yêu cầu báo lại giá. Dữ liệu cũ chưa có thông tin xác nhận vẫn hiện trên sàn nhưng cần tạo phiên bản đầy đủ để chốt.
- Dấu giá thấp nhất chỉ áp dụng cho nhóm cùng hàng, quy cách, đơn vị, số lượng, thuế, thanh toán và giao nhận. So sánh tổng chi phí còn đối chiếu ngày có hàng và điều kiện/thời gian cước. Không tự quy đổi hoặc xếp hạng các nhóm không tương đương.
- Phiên bản này chọn một nguồn hàng trọn bộ và một cước phù hợp, chưa gộp nhiều nguồn thành chuyến nhiều điểm lấy, chưa tạo đơn mua tự động từ phương án chốt.

Kiểm tra: `python manage.py test crm.tests_sourcing_market crm.tests_supplier_quote crm.tests_price_request crm.tests_navigation`.
