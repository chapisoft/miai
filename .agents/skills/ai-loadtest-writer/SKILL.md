---
name: ai-loadtest-writer
description: Kỹ năng chuyên sâu để thiết kế kịch bản và sinh mã đo kiểm tải cao (k6 / Locust / JMeter) cho các điểm cuối AI (Server-Sent Events streaming, LLM Gateway, Hybrid Search, OCR Batch Processing, Concurrency Data Integrity) trên nền tảng miai.
---

# KỸ NĂNG ĐO KIỂM HIỆU NĂNG VÀ TẢI CAO CHO HỆ THỐNG AI (AI LOADTEST WRITER)

Kỹ năng này hướng dẫn quy trình thiết kế và thực thi kịch bản đo kiểm hiệu năng chịu tải cho các API AI của dự án `miai`.

---

## 1. NGUYÊN TẮC ĐO KIỂM HIỆU NĂNG AI

1. **Đo lường đa chiều cho luồng SSE Streaming:**
   * Không chỉ đo Latency kết thúc (Total Request Time), mà **bắt buộc phải đo Time to First Token (TTFT)** (thời gian từ lúc gửi request đến khi nhận token đầu tiên qua SSE). Mục tiêu: TTFT < 300ms trên GPU cục bộ.
2. **Giám sát tải trọng phần cứng song song:**
   * Giám sát mức chiếm dụng VRAM GPU qua `nvidia-smi` (đảm bảo không vượt quá 11.0 GB).
   * Giám sát số lượng luồng CPU và Connection Pool của PostgreSQL / Redis.
3. **Bẫy toàn vẹn dữ liệu đồng thời (Concurrency Integrity):**
   * Đối soát kết quả sau khi bắn tải đồng thời 50 – 100 tác vụ phân tích Text-to-SQL hoặc bóc tách ảnh FDI để bảo đảm không xảy ra rò rỉ bộ nhớ hoặc xung đột dữ liệu.

---

## 2. MẪU KỊCH BẢN K6 CHO SSE STREAMING

```javascript
import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '30s', target: 20 }, // Tăng dần lên 20 người dùng đồng thời
    { duration: '1m', target: 20 },  // Duy trì tải 20 VUs
    { duration: '10s', target: 0 },   // Hạ tải
  ],
  thresholds: {
    http_req_duration: ['p(95)<1500'], // P95 latency < 1.5s
    http_req_failed: ['rate<0.01'],    // Tỷ lệ lỗi < 1%
  },
};

export default function () {
  const payload = JSON.stringify({
    messages: [
      { role: 'user', content: 'Tóm tắt quy trình kiểm định chất lượng sản phẩm xuất khẩu.' }
    ],
    stream: true,
    temperature: 0.7,
  });

  const params = {
    headers: {
      'Content-Type': 'application/json',
    },
    timeout: '30s',
  };

  const res = http.post('http://localhost:8000/api/v1/chat/completions', payload, params);

  check(res, {
    'status is 200': (r) => r.status === 200,
    'contains data chunk': (r) => r.body.includes('data:'),
  });

  sleep(1);
}
```
