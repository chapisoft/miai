# QUY CHUẨN NẠP VÀ PHỤC VỤ MÔ HÌNH TRÍ TUỆ NHÂN TẠO (MODEL SERVING)

Tài liệu này đặc tả quy chuẩn nạp, phân bổ tài nguyên phần cứng và phục vụ mô hình AI trên máy chủ `micro-server` (GPU NVIDIA RTX 3060 12GB GDDR6, CPU Xeon 32 luồng, 62GB RAM), dựa trên tài liệu nghiên cứu `docsbase/rd/deploy-ai-tool.md` và `docsbase/rd/micro-server.md`.

---

## 1. MA TRẬN MÔ HÌNH VÀ PHÂN BỔ BỘ NHỚ VRAM

| Nhóm bài toán | Tên mô hình khuyến nghị | Định dạng lượng tử | VRAM chiếm dụng | Bộ xử lý mục tiêu | Tốc độ đáp ứng |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Trợ lý Hội thoại & Suy luận** | `Qwen2.5:7b-instruct` | Q4_K_M | ~5.2 GB | GPU CUDA | 45 – 65 token/giây |
| **Thị giác máy & OCR** | `Qwen2.5-VL:7b-instruct` | Q4_K_M | ~5.5 GB | GPU CUDA | 1.2 – 1.8 giây/trang |
| **Phân tích Dữ liệu & Text-to-SQL** | `Qwen2.5-Coder:7b` | Q4_K_M | ~5.2 GB | GPU CUDA | 50 – 70 token/giây |
| **Bóc băng Giọng nói (STT)** | `Faster-Whisper Large-v3` | Float16 / Int8 | ~3.1 GB | GPU CUDA | Nhanh gấp 8 – 10 lần thời gian thực |
| **Nhúng Vector Ngữ nghĩa (RAG)** | `BAAI/bge-m3` | Float32 / FP16 | ~2.2 GB | CPU / GPU | < 25 mili-giây / đoạn văn |
| **Xếp hạng lại Ngữ nghĩa (Rerank)** | `BAAI/bge-reranker-large` | FP16 | ~1.8 GB | CPU / GPU | < 40 mili-giây / 10 đoạn văn |

---

## 2. NGUYÊN TẮC ĐIỀU PHỐI VRAM AN TOÀN

1. **Giới hạn trần an toàn VRAM:** Tổng mức chiếm dụng VRAM không được vượt quá **11.0 GB / 12.0 GB (91%)** để tránh tràn bộ nhớ GPU (Out-of-Memory / CUDA OOM).
2. **Cơ chế nạp luân phiên (Dynamic Hot-Swapping):**
   * Ollama quản lý tự động việc nạp/hạ mô hình vào VRAM với thời gian giữ mô hình trong bộ nhớ `keep_alive = 5m`.
   * Đối với tác vụ nặng kết hợp (ví dụ vừa bóc băng âm thanh Faster-Whisper vừa suy luận LLM), ưu tiên giải phóng VRAM của Whisper sau khi hoàn thành phiên xử lý batch.
3. **Bộ nhớ RAM hệ thống cho Vector & Cache:**
   * PostgreSQL `pgvector` sử dụng HNSW Index lưu trữ trực tiếp trên RAM hệ thống (tận dụng 49GB RAM trống của máy chủ).
   * Redis Cache lưu trữ kết quả truy vấn đệm và trạng thái tác nhân ReAct.

---

## 3. CỔNG GIAO TIẾP VÀ DỊCH VỤ NGOÀI

* **Ollama Local Engine:** `http://127.0.0.1:11434`
* **PostgreSQL pgvector:** Cổng `5432` (hoặc `5433` qua Docker)
* **Redis Cache:** Cổng `6379` (hoặc `6380` qua Docker)
* **Open WebUI (Giao diện quản trị):** `http://127.0.0.1:3001`
* **Cloud AI Fallback:** Khi máy chủ quá tải hoặc khi có yêu cầu từ cấu hình hệ thống, Cổng điều phối LLM (`LLMGatewayFactory`) tự động chuyển tiếp an toàn sang OpenAI API (`gpt-4o-mini`), Google Gemini API (`gemini-2.0-flash`) hoặc vLLM Cluster.
