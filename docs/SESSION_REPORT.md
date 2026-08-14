# Báo cáo công việc — IELTS-AI-Evaluator P0

**Ngày:** 2026-08-15

---

## 1. Tài liệu (`docs/`) — 13 file

PRD, kiến trúc hệ thống, data flow, tech spec, data schemas, prompt engineering spec, evaluation protocol, roadmap P0→P3, 3 ADR (quyết định kỹ thuật), báo cáo baseline.

## 2. Đề thi mẫu (`data/exams/`) — 10 bài

5 Task 1 + 5 Task 2, có gold label 4 tiêu chí, phủ band 4.5–8.0. 2 bài cố tình thiếu từ để test length penalty.

## 3. Pipeline MVP — chạy trên Ollama `qwen3.5:4b`, `think=False`

15 module: LLM client (structured output, retry), preprocess xác định, 4 criterion evaluator (rubric anchoring), sentence corrector, aggregation xác định, feedback synthesizer tiếng Việt. Nguyên tắc: **LLM phán đoán, code làm số học** (đếm từ, tính band, làm tròn, kiểm chứng trích dẫn).

51 unit test, tất cả pass.

## 4. Kết quả đo được (10 bài, 60 LLM call, ~18 phút)

| Metric | Kết quả | Đánh giá |
|---|---|---|
| Spearman ρ | **0.877** | Model xếp hạng bài rất tốt |
| MAE / within 0.5 / within 1.0 | 0.45 / 90% / 100% | Vượt ngưỡng P0 |
| JSON parse rate | 100% | Không lỗi |
| **Quote fidelity** | **77%** | ❌ Điểm hỏng duy nhất |

**7/8 NFR đạt.** Vấn đề thật: 23% trích dẫn bị model "sửa" luôn lỗi của học viên trong lúc trích — làm mất chính bằng chứng cần chỉ ra. Đã có lưới an toàn (loại bỏ trước khi hiển thị) nhưng cần sửa gốc bằng cách trích theo `sentence_index` thay vì chép văn bản (roadmap P1.1).

Bias lệch khác dấu giữa các tiêu chí (CC −0.35 vs GRA +0.65) → calibration phải làm riêng từng tiêu chí, không thể dùng 1 hàm chung.

## 5. Hạ tầng

- `.claude/settings.json` + hook `auto-commit.sh`: tự commit + push khi thay đổi đủ lớn, tác giả `23521329@gm.uit.edu.vn`, không gắn tên Claude.
- **6 commit đang chờ push** (Git Credential Manager không tự xác thực được từ hook) — cần chạy `git push` thủ công 1 lần để đăng nhập.

## 6. Việc cần làm tiếp (ưu tiên theo dữ liệu đo được)

1. Sửa trích dẫn theo chỉ số câu (fix quote_fidelity)
2. Đưa mật độ lỗi vào prompt GRA (tiêu chí yếu nhất)
3. Mở rộng dataset lên 40–50 bài
4. Calibration theo từng tiêu chí
