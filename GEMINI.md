# QUY TẮC PHÁT TRIỂN DỰ ÁN NỀN TẢNG AI (MIAI)

Tài liệu này là quy chuẩn chỉ dẫn kiến trúc, lập trình, kiểm thử và vận hành cho nền tảng Trí tuệ Nhân tạo `miai`, kế thừa các tiêu chuẩn kỹ thuật từ `docsbase`.

---

## 1. QUY TẮC BẮT BUỘC ÁP DỤNG

Mọi hoạt động phân tích, lập trình, cấu hình và kiểm thử trong workspace `miai` phải tuân thủ nghiêm ngặt:

1. **Nguyên tắc ngôn ngữ và định dạng:**
   * Tiếng Việt chuyên nghiệp, mạch lạc, tự nhiên.
   * **Tuyệt đối không chèn/đệm tiếng Anh kèm theo không cần thiết** (không viết dạng song ngữ, không mở ngoặc đơn dịch nghĩa bên cạnh từ tiếng Việt thông thường).
   * **Bảo lưu tuyệt đối các thuật ngữ chuyên ngành chuẩn quốc tế:** `FastAPI`, `Ollama`, `CUDA`, `VRAM`, `Hybrid RAG`, `BM25`, `BGE-M3`, `Faster-Whisper`, `ReAct`, `Token`, `Schema`, `AST Sandbox`, `ClickHouse`, `PostgreSQL`, `pgvector`, `Redis`, `uv`, `pytest`, `Docker`, `OpenAPI`, `Homography`, `ROI`.
   * **Trực quan:** Sơ đồ Flowchart LR 2 cột 4:3, ký tự Unicode (`×`, `→`) thay cho LaTeX `$`.
2. **Quy chuẩn Kiến trúc Nền tảng AI:** Tuân thủ Clean Architecture, Ports and Adapters, 6 bộ máy chuyên trách tại [.agents/rules/ai_architecture_rules.md](file:///.agents/rules/ai_architecture_rules.md), sử dụng kỹ năng `ai-engine-developer` tại [.agents/skills/ai-engine-developer/SKILL.md](file:///.agents/skills/ai-engine-developer/SKILL.md).
3. **Quy chuẩn Nạp & Phục vụ Mô hình AI:** Tuân thủ ma trận phân bổ VRAM an toàn (< 11GB) và cơ chế nạp luân phiên tại [.agents/rules/ai_model_serving_rules.md](file:///.agents/rules/ai_model_serving_rules.md).
4. **Quy chuẩn Thị giác máy & Bóc tách biểu mẫu FDI:** Tuân thủ luồng nắn phẳng Homography 4 góc (5ms), QR định danh (3ms) và trích xuất ROI đa ngữ tại [.agents/rules/fdi_vision_rules.md](file:///.agents/rules/fdi_vision_rules.md), sử dụng kỹ năng `fdi-vision-station` tại [.agents/skills/fdi-vision-station/SKILL.md](file:///.agents/skills/fdi-vision-station/SKILL.md).
5. **Quy chuẩn Bảo mật & AST Sandbox:** Tuân thủ Default Deny, Prompt Injection Defense, PII Masking và AST Read-Only SELECT validation tại [.agents/rules/security_review_rules.md](file:///.agents/rules/security_review_rules.md).
6. **Quy chuẩn Đo kiểm Tải & Hiệu năng AI:** Tuân thủ đo lường TTFT < 300ms, giám sát VRAM và bẫy toàn vẹn dữ liệu đồng thời, sử dụng kỹ năng `ai-loadtest-writer` tại [.agents/skills/ai-loadtest-writer/SKILL.md](file:///.agents/skills/ai-loadtest-writer/SKILL.md).
7. **Quy chuẩn Bằng chứng thực chứng (Hard Evidence or Zero):** Mọi tính năng mới hoặc bản sửa lỗi bắt buộc phải có Unit Tests trong `src/tests/` và chạy pass 100% bằng lệnh `uv run pytest`.

---

## 2. CẤU TRÚC MÃ NGUỒN VÀ ĐIỀU HƯỚNG DỰ ÁN

```
miai/
├── .agents/                              # Kho quy tắc và kỹ năng của hệ thống
│   ├── rules/                            # Quy chuẩn kiến trúc, mô hình, thị giác và bảo mật
│   └── skills/                           # Kỹ năng mở rộng bộ máy AI, trạm FDI và đo kiểm tải
├── .gitignore                            # Loại trừ môi trường ảo và tệp cache
├── GEMINI.md                             # Quy tắc phát triển dự án
├── README.md                             # Tài liệu tổng quan kiến trúc
└── src/                                  # Toàn bộ mã nguồn, cấu hình và kịch bản thực thi
    ├── .env                              # Biến môi trường cục bộ
    ├── .env.example                      # Mẫu biến môi trường
    ├── Dockerfile                        # Tệp đóng gói Docker container
    ├── docker-compose.yml                # Cấu hình dịch vụ hạ tầng (Postgres pgvector, Redis)
    ├── main.py                           # Điểm khởi chạy ứng dụng FastAPI
    ├── pyproject.toml                    # Cấu hình gói và phụ thuộc miai
    ├── pyrightconfig.json                # Cấu hình kiểm tra kiểu dữ liệu
    ├── requirements.txt                  # Danh mục phụ thuộc dạng pip
    ├── uv.lock                           # Khóa phiên bản gói uv
    ├── api/                              # Tầng giao tiếp RESTful API V1
    ├── core/                             # Tầng cấu hình, bảo mật, telemetry & responses
    ├── engines/                          # 6 bộ máy AI (LLM, RAG, Vision, SQL, Audio, Agent)
    ├── schemas/                          # Pydantic Schemas dữ liệu
    └── tests/                            # Toàn bộ kịch bản kiểm thử tự động
```
