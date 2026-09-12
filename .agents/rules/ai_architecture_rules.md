# QUY CHUẨN KIẾN TRÚC VÀ PHÁT TRIỂN NỀN TẢNG TRÍ TUỆ NHÂN TẠO (MIAI)

Tài liệu này quy định toàn bộ tiêu chuẩn kiến trúc, quy tắc lập trình và chuẩn mực thiết kế cho nền tảng Trí tuệ Nhân tạo `miai`, kế thừa và phát triển từ tài liệu nghiên cứu `docsbase/rd/deploy-ai-tool.md` và `docsbase/rd/micro-server.md`.

---

## 1. TỔNG QUAN KIẾN TRÚC VÀ TÔ PÔ HẠ TẦNG

```mermaid
%%{init: {'flowchart': {'nodeSpacing': 8, 'rankSpacing': 140, 'padding': 3, 'curve': 'basis'}}}%%
flowchart LR
    subgraph S_API_GATEWAY ["1. TẦNG TIẾP NHẬN & BẢO VỆ (API & GUARDRAILS)"]
        direction TB
        FASTAPI_CORE["FastAPI REST & Streaming Engine<br/>• Điểm cuối RESTful chuẩn hóa (/api/v1/*)<br/>• Luồng dữ liệu Server-Sent Events (SSE) & WebSocket<br/>• Tài liệu OpenAPI / Swagger 3.0 tự động"]
        SECURITY_SHIELD["Bảo vệ Đa lớp & Giám sát<br/>• Xác thực API Key & JWT Bearer Token<br/>• Chặn đứng tấn công Prompt Injection<br/>• Làm mờ thông tin cá nhân nhạy cảm PII<br/>• Nhật ký JSON chuẩn Elastic Common Schema (ECS)"]
        FASTAPI_CORE --> SECURITY_SHIELD
    end

    subgraph S_CORE_ENGINES ["2. CÁC BỘ MÁY AI CHUYÊN TRÁCH (CORE ENGINES)"]
        direction TB
        ENG_LLM["Cổng Điều phối Mô hình (LLM Gateway)<br/>• Nạp trực tiếp Ollama GPU RTX 3060 cục bộ (127.0.0.1:11434)<br/>• Hỗ trợ linh hoạt OpenAI, Gemini, DeepSeek, vLLM<br/>• Trích xuất dữ liệu có cấu trúc qua Pydantic Schema"]
        ENG_RAG["Bộ máy Tìm kiếm Lai (Hybrid RAG Engine)<br/>• Nhúng Vector dày đặc BGE-M3 (1.024 chiều)<br/>• Tìm kiếm từ khóa chính xác BM25 Sparse Search<br/>• Xếp hạng lại độ phù hợp qua BGE-Reranker-Large"]
        ENG_VISION["Bộ máy Thị giác & Bóc tách Chứng từ (Vision & OCR)<br/>• Nắn phẳng phối cảnh Homography 4 góc (5ms)<br/>• Bóc tách vùng quan tâm (ROI) biểu mẫu FDI Form Station<br/>• Bóc tách hóa đơn VAT điện tử & Bảng dự toán BoQ"]
        ENG_SQL["Trợ lý Phân tích Dữ liệu (Text-to-SQL & BI)<br/>• Tự động đọc từ điển dữ liệu (Data Dictionary)<br/>• Sinh câu truy vấn SQL tối ưu trên ClickHouse & Postgres<br/>• Sandbox AST bảo vệ: 100% Chỉ đọc (Read-Only SELECT)<br/>• Tự động sinh cấu hình biểu đồ Apache ECharts"]
        ENG_AUDIO["Bộ máy Xử lý Âm thanh & Giọng nói (Audio STT)<br/>• Bóc băng tiếng Việt siêu tốc qua Faster-Whisper CUDA<br/>• Tự động lập biên bản họp & Bảng phân công việc<br/>• Giám sát & Chấm điểm chất lượng cuộc gọi tổng đài"]
        ENG_AGENT["Động cơ Tác nhân Tự trị (Agentic Workflow)<br/>• Vòng lặp suy luận ReAct (Reasoning - Action - Observation)<br/>• Kho công cụ động mở rộng qua decorator @ai_tool<br/>• Bộ nhớ ngắn hạn Redis & Bộ nhớ dài hạn Vector Store"]
        ENG_LLM --> ENG_RAG
        ENG_RAG --> ENG_VISION
        ENG_VISION --> ENG_SQL
        ENG_SQL --> ENG_AUDIO
        ENG_AUDIO --> ENG_AGENT
    end

    SECURITY_SHIELD --> S_CORE_ENGINES
```

---

## 2. NGUYÊN TẮC THIẾT KẾ CỐT LÕI

### 2.1. Cấu trúc mã nguồn Clean Architecture & Ports and Adapters
* Toàn bộ mã nguồn phải được tổ chức tách biệt rõ ràng theo từng phân tầng:
  * `src/api/`: Tiếp nhận HTTP Request, Dependency Injection, chuyển tiếp tới Engines, trả về `ApiResponse`.
  * `src/core/`: Quản lý cấu hình (`Settings`), cơ sở dữ liệu (`database.py`), bảo mật (`security.py`), lớp bảo vệ (`guardrails.py`), telemetry & logger.
  * `src/engines/`: 6 bộ máy nghiệp vụ AI độc lập, không phụ thuộc chéo vòng tròn.
  * `src/schemas/`: 100% Pydantic Schemas mô hình hóa Request/Response.

### 2.2. Nguyên tắc Zero-Hardcode và Quản trị Đối tượng
* Toàn bộ mã trạng thái, phân loại, vai trò và mã lỗi **bắt buộc phải được định nghĩa bằng Enum trong `core/constants.py`**.
* Cấm dùng chuỗi tự do (String Literal) để so sánh điều kiện.
* Dữ liệu trả về không gán giá trị giả lập; nếu chưa có dữ liệu phải để `null` hoặc danh sách rỗng `[]`.

### 2.3. Quy chuẩn Bảo vệ Dữ liệu và An toàn Mô hình
* **Prompt Injection Defense:** Tất cả đầu vào người dùng trước khi gửi tới mô hình LLM phải đi qua bộ lọc `InputGuardrail` để phát hiện và ngăn chặn các mẫu tấn công chiếm quyền điều khiển prompt (System override, Jailbreak, tiếng Việt và tiếng Anh).
* **PII Redaction:** Tự động phát hiện và làm mờ các thông tin nhạy cảm (Số CMND/CCCD, Mã số thuế, Số thẻ tín dụng, Số điện thoại) trước khi gửi tới các API bên ngoài.
* **AST SQL Sandbox:** Tất cả câu lệnh SQL sinh bởi mô hình Text-to-SQL phải được phân tích cú pháp AST bằng `sqlparse`. Chỉ cho phép duy nhất lệnh `SELECT`, cấm tuyệt đối các câu lệnh thay đổi dữ liệu (`DROP`, `DELETE`, `INSERT`, `UPDATE`, `ALTER`, `TRUNCATE`) và câu lệnh xếp chồng (Stacked Queries).

---

## 3. CHUẨN MỰC GIAO TIẾP VÀ PHẢN HỒI API

Mọi API của hệ thống phải trả về cấu trúc đối tượng chuẩn hóa `ApiResponse`:

```json
{
  "code": "SUCCESS",
  "message": "Thực thi thành công",
  "data": { ... },
  "duration_ms": 42.5
}
```

Trường hợp phát sinh lỗi:
```json
{
  "code": "ERR_VALIDATION_FAILED",
  "message": "Câu truy vấn SQL không an toàn: Chỉ cho phép lệnh SELECT đọc dữ liệu",
  "data": null,
  "duration_ms": 1.2
}
```
