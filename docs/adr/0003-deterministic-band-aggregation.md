# ADR-0003: Overall band và penalty tính bằng code, không bằng LLM

**Trạng thái:** Accepted · 2026-08-15

## Bối cảnh

Có hai cách tính overall band:
- **A:** Đưa 4 band cho LLM, bảo nó tính overall và cân nhắc word count.
- **B:** Code tính trung bình, áp penalty, làm tròn.

## Quyết định

Phương án **B**. LLM không bao giờ được sinh ra `overall_band`.

## Lý do

1. **Đây là số học thuần tuý.** Trung bình 4 số, trừ penalty, làm tròn về bội 0.5. Code đúng 100%; LLM 4B đúng khoảng 90–95%. Chấp nhận 5% sai ở nơi có thể đạt 0% là lãng phí.
2. **Quy tắc làm tròn IELTS có bẫy.** `.25` làm tròn **lên** `.5`, `.75` làm tròn **lên** `1.0`. Python `round()` dùng banker's rounding (`round(6.25, 1)` không cho kết quả như kỳ vọng) — nên ngay cả code cũng phải viết cẩn thận bằng `floor(x*2 + 0.5)/2`. Càng không có lý do giao cho model.
3. **Penalty phụ thuộc word count**, mà word count đã được đếm chính xác ở Stage 0. Để LLM tự đếm lại rồi tự phạt là tạo ra hai điểm hỏng nối tiếp.

   Bổ sung quan trọng: penalty được áp vào **band của TA/TR**, không áp vào overall. Giám khảo thật hấp thụ lỗi thiếu độ dài vào Task Achievement/Response; trừ thêm ở overall là phạt hai lần. Đi kèm, prompt TA/TR phải được dặn hiển ngôn không tự trừ vì độ dài — nếu không, ta lại phạt hai lần theo một đường khác (model trừ một lần, code trừ lần nữa).
4. **Testable.** `round_to_half` và `compute_penalty` là hàm thuần → unit test bao phủ 100%, chạy trong mili-giây, không cần GPU.
5. **Auditable.** Kết quả tách rõ `raw_overall`, `penalty_applied`, `overall_band`. Nhìn là biết điểm thấp vì model chấm thấp hay vì bài thiếu chữ.

## Nguyên tắc tổng quát rút ra

> **LLM cho phán đoán, code cho số học.**

Áp dụng nhất quán toàn hệ thống: đếm từ, tính TTR, đếm câu/đoạn, phát hiện từ lặp, kiểm chứng trích dẫn, tính trung bình, làm tròn, áp penalty — **tất cả bằng code**. LLM chỉ làm việc nó thực sự giỏi: đánh giá chất lượng ngôn ngữ và giải thích.

Mỗi lần dời một nhiệm vụ từ cột "LLM" sang cột "code", ta xoá vĩnh viễn một nguồn lỗi thay vì làm nó nhỏ đi.

## Hệ quả

**Tích cực:** overall band chính xác tuyệt đối; penalty nhất quán; audit được; test được không cần GPU; sau này chèn calibration layer vào đúng một chỗ (giữa `raw` và `final`).

**Tiêu cực:** không mô phỏng được sự "linh hoạt" của giám khảo thật (đôi khi giám khảo cân nhắc tổng thể chứ không trung bình máy móc). Chấp nhận: tính nhất quán quan trọng hơn với công cụ luyện tập.
