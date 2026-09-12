---
name: fdi-vision-station
description: Kỹ năng chuyên sâu để thiết kế, hiệu chuẩn và vận hành Trạm thu thập dữ liệu biểu mẫu rảnh tay tại hiện trường nhà máy FDI, ứng dụng thuật toán nắn phẳng phối cảnh Homography 4 góc (5ms), giải mã QR định danh và bóc tách vùng quan tâm (ROI) đa ngữ (Việt - Anh - Trung - Hàn - Nhật).
---

# KỸ NĂNG VẬN HÀNH VÀ BÓC TÁCH BIỂU MẪU FDI (FDI VISION STATION)

Kỹ năng này hướng dẫn quy trình cấu hình, hiệu chuẩn trạm chụp và bóc tách dữ liệu biểu mẫu công nghiệp FDI.

---

## 1. QUY TRÌNH HIỆU CHUẨN TRẠM CHỤP HIỆN TRƯỜNG

1. **Thiết lập phần cứng trạm làm việc:**
   * Cố định máy chụp tài liệu đứng góc 90 độ so với thảm cao su đen mờ chống lóa.
   * Bật đèn LED vòm khuếch tán để triệt tiêu bóng đổ.
   * Kết nối bàn đạp chân USB (Foot Pedal) để kích hoạt chế độ chụp rảnh tay.

2. **Hiệu chuẩn tọa độ nắn phẳng Homography:**
   * Lấy 4 điểm góc của thảm tài liệu `src_points = [(x0, y0), (x1, y1), (x2, y2), (x3, y3)]`.
   * Thiết lập `dst_points` về kích thước A4 chuẩn `(1654, 2338)` pixels.
   * Tính ma trận biến đổi phối cảnh 3x3 qua `cv2.getPerspectiveTransform` (thời gian tính toán < 5ms).

---

## 2. QUY TRÌNH ĐỊNH NGHĨA VÀ BÓC TÁCH MẪU BIỂU MẪU MỚI

1. **Tạo mẫu mã QR định danh biểu mẫu:**
   * Cấu trúc chuỗi QR in góc trên phải: `<MÃ_CHỨNG_TỪ>|<MÃ_FDI>|<MÃ_BIỂU_MẪU_PHIÊN_BẢN>`.
   * Ví dụ: `PXK-2026-001|FDI-SAMSUNG-VN|FORM_V1`.

2. **Khai báo tọa độ các trường dữ liệu ROI (Bounding Boxes):**
   ```python
   FDI_SAMPLE_TEMPLATE = [
       RoiFieldDefinition(
           field_name="actual_weight_kg",
           bbox=[0.65, 0.42, 0.88, 0.48], # [x_min, y_min, x_max, y_max] chuẩn hóa
           data_type="DECIMAL",
           language="VI"
       ),
       RoiFieldDefinition(
           field_name="driver_signature",
           bbox=[0.70, 0.82, 0.95, 0.94],
           data_type="SIGNATURE",
           language="VI"
       )
   ]
   ```

3. **Thực thi bóc tách và ghi CSDL:**
   * Gửi ảnh đã nắn phẳng qua `RoiExtractor.extract_fields(image, template)`.
   * Dữ liệu bóc tách được chuẩn hóa và lưu trữ trực tiếp vào CSDL qua API `/api/v1/vision/fdi/extract`.
