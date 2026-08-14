# ADR-0001: Local LLM (Ollama) là mặc định, cloud API là tuỳ chọn

**Trạng thái:** Accepted · 2026-08-15

## Bối cảnh

README v1.0 mô tả hệ thống dựa trên GPT-4o và Gemini 1.5 Pro. Điều này tạo ba vấn đề:

1. **Chi phí biến đổi.** Pipeline 6 call/bài, ~3000 token/bài. Với GPT-4o, 1000 bài/tháng ≈ chi phí không nhỏ cho một dự án cá nhân — và chính "chi phí" là nút thắt số 1 mà sản phẩm định giải quyết.
2. **Dữ liệu.** Bài viết của học viên là dữ liệu cá nhân. Gửi lên bên thứ ba tạo rào cản khi triển khai cho trường học.
3. **Không đo được nếu không có key.** Người review/chấm đồ án không có API key thì không chạy được hệ thống.

## Quyết định

Ollama + `qwen3.5:4b` là **đường chạy mặc định**. Toàn bộ pipeline phải chạy được end-to-end với zero API key. Cloud provider là adapter tuỳ chọn phía sau cùng interface `LLMClient`.

## Hệ quả

**Tích cực**
- Chi phí biến đổi = 0 → cho phép chấm không giới hạn, đúng với luận điểm sản phẩm.
- Không có network egress → giải quyết vấn đề dữ liệu ở gốc.
- Reproducible: `temperature=0` + model cố định cục bộ → so sánh phiên bản có ý nghĩa.
- Ai clone repo cũng chạy được.

**Tiêu cực — phải chấp nhận và đo**
- Model 4B **kém hơn đáng kể** GPT-4o ở nhận định ngôn ngữ tinh tế. Chất lượng chấm ban đầu sẽ thấp hơn. Đây là cái giá đã biết trước, không phải bất ngờ.
- Cần GPU (hoặc chấp nhận latency CPU rất cao).
- Cold load ~110s cần xử lý ở tầng vận hành.

**Giảm thiểu**
- Kiến trúc provider-agnostic: nếu đo cho thấy 4B không đủ, đổi sang 8B hoặc cloud chỉ là đổi adapter.
- Bù chất lượng model bằng kỹ thuật kiến trúc: preprocessing xác định, rubric anchoring, justification-first, quote verification. Những thứ này nâng model nhỏ lên nhiều hơn là nâng model lớn.

## Phương án đã cân nhắc và loại

| Phương án | Vì sao loại |
| --- | --- |
| Cloud-only (GPT-4o) | Mâu thuẫn với chính vấn đề sản phẩm đang giải quyết (chi phí) |
| Hybrid: local nháp + cloud tinh | Phức tạp gấp đôi khi chưa biết local có đủ hay không. Hoãn tới P3. |
| Fine-tune model nhỏ ngay từ đầu | Chưa có dữ liệu. Fine-tune trước khi có baseline là tối ưu hoá mù. |
