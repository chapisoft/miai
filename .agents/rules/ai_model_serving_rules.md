# QUY CHUẨN NẠP VÀ PHỤC VỤ MÔ HÌNH TRÍ TUỆ NHÂN TẠO (MODEL SERVING)

Tài liệu này đặc tả quy chuẩn nạp, phân bổ tài nguyên phần cứng và phục vụ mô hình AI trên máy chủ `micro-server` (GPU NVIDIA RTX 3060 12GB GDDR6, CPU Xeon 32 luồng, 62GB RAM), dựa trên tài liệu nghiên cứu `docsbase/rd/deploy-ai-tool.md` và `docsbase/rd/micro-server.md`.

---

## 1. MA TRẬN MÔ HÌNH VÀ PHÂN BỔ BỘ NHỚ VRAM

| Nhóm bài toán | Tên mô hình khuyến nghị | Bộ máy phục vụ | Định dạng lượng tử | Mức chiếm dụng VRAM | Bộ xử lý mục tiêu | Tốc độ đáp ứng |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Trợ lý Hội thoại & Suy luận LLM** | `Qwen/Qwen2.5-7B-Instruct-AWQ` | **vLLM Engine** (PagedAttention) | AWQ 4-bit | **~9.5 GB** (util 0.85) | GPU CUDA | 55 – 70 token/giây (16 luồng song song) |
| **Sinh trắc học Khuôn mặt** | `UniFace (SCRFD + AdaFace + MiniFASNet)` | ONNX Runtime | FP32 / INT8 | **0 MB** (Tiết kiệm VRAM) | 32 luồng CPU Xeon | < 25 mili-giây / khuôn mặt |
| **Nhúng Vector Ngữ nghĩa (RAG)** | `BAAI/bge-m3 (1.024-dim)` | Deterministic CPU Generator | Float32 | **0 MB** (Tiết kiệm VRAM) | 32 luồng CPU Xeon | < 10 mili-giây / đoạn văn |
| **Thị giác máy & OCR** | `Qwen2.5-VL:7b-instruct` | Ollama (Hot-swap Fallback) | Q4_K_M | ~5.5 GB | GPU CUDA | 1.2 – 1.8 giây/trang |
| **Phân tích Dữ liệu & Text-to-SQL** | `Qwen/Qwen2.5-7B-Instruct-AWQ` | **vLLM Engine** | AWQ 4-bit | Dùng chung vLLM Pool | GPU CUDA | 50 – 70 token/giây |
| **Bóc băng Giọng nói (STT)** | `Faster-Whisper Large-v3` | Faster-Whisper CTranslate2 | Float16 / Int8 | ~3.1 GB | GPU CUDA (Batch) | Nhanh gấp 8 – 10 lần thời gian thực |

---

## 2. NGUYÊN TẮC ĐIỀU PHỐI VRAM VÀ HIỆU NĂNG AN TOÀN

1. **Kiến trúc Phục vụ Tập trung qua vLLM PagedAttention:**
   * vLLM quản trị tập trung bộ nhớ đệm KV Cache với `gpu-memory-utilization = 0.85` (~9.5 GB VRAM trên RTX 3060 12GB).
   * Cơ chế **Continuous Batching** cho phép xử lý đồng thời 12 – 16 luồng người dùng cùng lúc mà không gây đơ nghẽn đơn luồng.
2. **Bảo toàn VRAM GPU nhờ Điều phối CPU Đa luồng:**
   * Bộ máy Sinh trắc học UniFace và bộ máy tạo Vector BGE-M3 được vận hành hoàn toàn trên 32 luồng CPU Intel Xeon và 62GB RAM hệ thống, bảo toàn 100% tài nguyên GPU cho vLLM.
3. **Cơ chế Dự phòng Đa tầng (Multi-Provider Fallback):**
   * Khi cụm vLLM cục bộ quá tải hoặc cần nạp tác vụ đặc thù, Cổng điều phối LLM (`LLMFactory`) tự động chuyển đổi an toàn sang Ollama nội bộ (`http://127.0.0.1:11434`) hoặc các cổng đám mây (OpenAI, Gemini, DeepSeek).
4. **Bộ nhớ CSDL và Cache Phân tán:**
   * PostgreSQL `pgvector` sử dụng HNSW Index lưu trữ trực tiếp trên RAM hệ thống.
   * Redis Cache lưu trữ kết quả truy vấn đệm và trạng thái tác nhân ReAct.

---

## 3. CỔNG GIAO TIẾP VÀ DỊCH VỤ MẠNG TRÊN MICRO-SERVER

* **vLLM High-Throughput Engine:** `http://127.0.0.1:8002` (cục bộ máy chủ) hoặc `http://vllm-engine:8000/v1` (mạng nội bộ container).
* **Ứng dụng miai Backend:** `http://127.0.0.1:8006` (cục bộ máy chủ) hoặc `https://miai.microtec.vn`.
* **PostgreSQL pgvector:** Cổng `5433` (Docker container `miai-pgvector`).
* **Redis Cache:** Cổng `6380` (Docker container `miai-redis`).
* **Open WebUI (Giao diện Chat & Quản trị):** `http://127.0.0.1:3001`.
* **Ollama Local Engine (Legacy / Dự phòng):** `http://127.0.0.1:11434`.
