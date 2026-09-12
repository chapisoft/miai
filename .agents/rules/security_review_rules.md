# NGUYÊN TẮC RÀ SOÁT BẢO MẬT VÀ AN TOÀN NỀN TẢNG AI (SECURITY REVIEW)

Tài liệu này áp dụng cho toàn bộ hoạt động lập trình, rà soát mã nguồn (Code Review), vá lỗ hổng bảo mật và nghiệm thu an ninh hệ thống AI `miai`.

---

## 1. NGUYÊN TẮC MẶC ĐỊNH TỪ CHỐI TRÊN 100% LUỒNG DỮ LIỆU (DEFAULT DENY)

1. **Kiểm tra quyền sở hữu tại điểm trả dữ liệu cuối cùng:** Không bao giờ giả định dữ liệu lấy từ mô hình hoặc cơ sở dữ liệu nội bộ đã hoàn toàn an toàn. Mọi dữ liệu nhạy cảm trước khi trả về cho Client bắt buộc phải so khớp định danh người gọi (`API Key` hoặc `JWT Token claims`).
2. **Dò vết 100% các nhánh rẽ (`if/else/return`):** Tuyệt đối không kết luận một API an toàn chỉ vì thấy có đoạn kiểm tra quyền ở nhánh phụ mà bỏ quên luồng chính.

---

## 2. AN TOÀN TRUY VẤN VÀ CHỐNG TẤN CÔNG PROMPT INJECTION

1. **Phân tích cú pháp AST bắt buộc cho Text-to-SQL:**
   * Mọi câu lệnh SQL do LLM sinh ra bắt buộc phải được kiểm tra qua `AstValidator` (`sqlparse.parse`).
   * Chỉ cho phép duy nhất câu lệnh `SELECT`. Bất kỳ câu lệnh chứa từ khóa thao tác dữ liệu (`DROP`, `DELETE`, `UPDATE`, `INSERT`, `ALTER`, `EXEC`, `UNION`, `TRUNCATE`) hoặc chứa dấu chấm phẩy phân tách nhiều câu lệnh (Stacked Queries) đều bị từ chối ngay lập tức với mã lỗi `ERR_VALIDATION_FAILED`.
2. **Lớp bảo vệ Prompt Guardrail:**
   * Kiểm tra và lọc bỏ toàn bộ các mẫu câu lệnh chứa chỉ dẫn ghi đè hệ thống (System Override, Jailbreak, "Ignore previous instructions", "Bỏ qua các chỉ dẫn trước").
   * Tự động làm mờ (Mask/Redact) các thông tin nhạy cảm (PII) như Số CCCD, Mã số thuế, Số điện thoại trước khi chuyển tiếp tới các API bên ngoài.

---

## 3. NGUYÊN TẮC BẰNG CHỨNG THỰC CHỨNG (HARD EVIDENCE OR ZERO)

* Tuyệt đối **CẤM** đánh giá "PASS" hoặc "Đã an toàn" chỉ bằng mắt thường.
* Bắt buộc phải có **kịch bản kiểm thử thực nghiệm (Unit Tests / Integration Tests / PoC)** chứng minh hệ thống chặn đứng các cuộc tấn công (gửi prompt injection, gửi SQL phá hoại, giả mạo token).
