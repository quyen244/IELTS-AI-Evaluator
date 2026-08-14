# Evaluation Protocol

> Tài liệu này định nghĩa **cách đo**. Kết quả đo nằm ở [mvp-baseline-report.md](mvp-baseline-report.md).

---

## 1. Vì sao cần protocol trước khi cần kết quả

Một hệ thống chấm điểm bằng LLM không thể cải thiện bằng cảm tính. Nếu không có bộ đo cố định, mọi thay đổi prompt đều "có vẻ tốt hơn". Protocol này cố định ba thứ: **dataset**, **metric**, **quy trình**. Chỉ khi cả ba cố định thì con số giữa hai lần chạy mới so sánh được.

---

## 2. Dataset

### 2.1 Thành phần
`data/exams/` — 10 bài: 5 Task 1 (Academic) + 5 Task 2, phủ dải band 4.5 → 8.5.

| ID | Task | Dạng đề | Số từ | Gold overall | Gold theo tiêu chí | Tin cậy |
| --- | --- | --- | --- | --- | --- | --- |
| T1-001 | 1 | Line graph | 140 | 5.0 | TA 5.5 · CC 5.0 · LR 4.5 · GRA 4.5 | medium |
| T1-002 | 1 | Bar chart | 169 | 7.0 | TA 7.5 · CC 7.0 · LR 7.0 · GRA 7.0 | medium |
| T1-003 | 1 | Table | 154 | 7.5 | TA 8.0 · CC 7.5 · LR 7.5 · GRA 7.5 | medium |
| T1-004 | 1 | Process diagram | 195 | 8.0 | TA 8.0 · CC 8.5 · LR 8.0 · GRA 8.0 | medium |
| T1-005 | 1 | Pie chart | **104** ⚠ | 4.5 | TA 4.5 · CC 5.0 · LR 4.0 · GRA 4.0 | medium |
| T2-001 | 2 | Opinion (agree/disagree) | 311 | 5.5 | TR 5.5 · CC 6.0 · LR 5.5 · GRA 5.0 | medium |
| T2-002 | 2 | Discuss both views | 297 | 6.5 | TR 6.5 · CC 7.0 · LR 6.5 · GRA 6.5 | medium |
| T2-003 | 2 | Problem–solution | 293 | 7.5 | TR 7.5 · CC 7.5 · LR 8.0 · GRA 7.5 | medium |
| T2-004 | 2 | Two-part question | 318 | 8.0 | TR 8.0 · CC 8.0 · LR 8.5 · GRA 8.0 | medium |
| T2-005 | 2 | Advantages–disadvantages | **183** ⚠ | 4.5 | TR 4.5 · CC 5.0 · LR 4.5 · GRA 4.0 | medium |

⚠ = dưới ngưỡng số từ tối thiểu. Hai bài này tồn tại có chủ đích để kiểm chứng nhánh **length penalty**.

**Ràng buộc nội tại của dataset:** `gold.overall` luôn bằng `round_to_half(mean(4 tiêu chí))` — có unit test kiểm tra (`test_dataset_loads_and_is_internally_consistent`). Nếu nhãn không thoả quy tắc này thì chính dataset đang mâu thuẫn với quy tắc tổng hợp mà pipeline bị đem ra đo.

### 2.2 Nguồn gold label và giới hạn phải nói rõ

Các bài viết mẫu được **soạn có chủ đích** để thể hiện đặc trưng ngôn ngữ của từng band (lỗi ngữ pháp, độ đa dạng từ vựng, chất lượng lập luận, cấu trúc đoạn tương ứng). Gold label là **ước lượng chuyên môn dựa trên band descriptor chính thức**, không phải điểm do giám khảo IELTS được chứng nhận chấm.

**Hệ quả bắt buộc phải chấp nhận:**
- Con số MAE ở đây đo **độ khớp với nhãn tham chiếu của chúng ta**, không phải "độ chính xác so với IELTS thật". Không được phát biểu "hệ thống chính xác X% so với giám khảo".
- Dataset 10 bài quá nhỏ để có ý nghĩa thống kê. Khoảng tin cậy rất rộng; chênh lệch MAE < 0.2 giữa hai phiên bản **không** là bằng chứng cải thiện.
- Vì cả bài viết lẫn nhãn đều do cùng một quá trình soạn ra, có rủi ro nhãn phản ánh *ý định* hơn là *thực tế văn bản*.

**Vì thế dataset này chỉ phục vụ đúng một mục đích:** phát hiện lỗi hệ thống thô (pipeline chết, JSON fail, bias lệch hẳn một phía, không phân biệt được bài band 4 với bài band 8) và so sánh *tương đối* giữa các phiên bản pipeline. Để có tuyên bố về độ chính xác, P2 phải có ≥ 100 bài chấm bởi người có chứng chỉ — xem [Roadmap](../04-roadmap/roadmap.md).

### 2.3 Mở rộng dataset (P2)
Nguồn ưu tiên: bài viết công khai kèm điểm của Cambridge IELTS official sample answers; bài đã chấm của trung tâm (có xin phép); IELTS Writing corpora học thuật. Cần ≥ 2 người chấm độc lập/bài để đo inter-rater agreement — nếu người còn không đồng ý với nhau thì không có cơ sở đòi hỏi model đồng ý với người.

---

## 3. Metrics

### 3.1 Chất lượng chấm điểm

| Metric | Công thức | Ý nghĩa |
| --- | --- | --- |
| `MAE_overall` | `mean(\|pred − gold\|)` | Sai số trung bình, band |
| `RMSE_overall` | `sqrt(mean((pred−gold)²))` | Phạt nặng sai số lớn — phát hiện outlier |
| `bias` | `mean(pred − gold)` | **Dấu quan trọng**: dương = chấm rộng tay, âm = chấm chặt |
| `within_0.5` | `% (\|pred−gold\| ≤ 0.5)` | Tỉ lệ "chấp nhận được với người học" |
| `within_1.0` | `% (\|pred−gold\| ≤ 1.0)` | Tỉ lệ "không sai nghiêm trọng" |
| `spearman_rho` | Tương quan hạng | **Chỉ số quan trọng nhất ở giai đoạn đầu** |
| `MAE_per_criterion` | MAE cho TA/TR, CC, LR, GRA | Chỉ ra tiêu chí nào yếu nhất → biết sửa prompt nào |
| `pred_std / gold_std` | Tỉ lệ độ lệch chuẩn | < 1 ⇒ model nén dải điểm (central tendency bias) |

### 3.2 Vì sao `spearman_rho` quan trọng hơn `MAE`

`bias` và `MAE` cao **nhưng** `rho` cao ⇒ model xếp hạng đúng, chỉ lệch thang đo ⇒ sửa được bằng một hàm calibration tuyến tính, chi phí gần bằng 0.

`rho` thấp ⇒ model không phân biệt được bài tốt và bài kém ⇒ calibration vô dụng, phải sửa prompt/rubric/model. Đắt.

Vì vậy khi đọc báo cáo, **đọc `rho` trước, `MAE` sau**.

`pred_std / gold_std` bổ trợ: nếu tỉ lệ này ≈ 0.4 thì model đang nén mọi bài về giữa dải — triệu chứng điển hình của model nhỏ thiếu rubric anchoring.

### 3.3 Chất lượng hệ thống

| Metric | Định nghĩa | Ngưỡng P0 |
| --- | --- | --- |
| `json_parse_rate` | % call parse thành công (kể cả sau retry) | ≥ 95% |
| `first_attempt_parse_rate` | % call parse ngay lần đầu | theo dõi |
| `quote_fidelity` | % quote khớp nguyên văn essay | ≥ 80% |
| `empty_evidence_rate` | % CriterionResult có `evidence` rỗng | ≤ 10% |
| `p50_latency_s` / `p95_latency_s` | Latency mỗi bài (warm) | p95 ≤ 180 s |
| `tokens_per_essay` | prompt + completion | theo dõi |
| `degraded_rate` | % lần chấm có ≥1 node hỏng | ≤ 5% |

---

## 4. Quy trình chạy

```bash
# 1. Đảm bảo Ollama chạy và model đã nạp
ollama serve            # nếu chưa chạy
ollama pull qwen3.5:4b

# 2. Chạy harness — TỰ ĐỘNG warm-up trước khi tính giờ
python -m scripts.run_eval --out data/reports

# 3. Kết quả
data/reports/{run_id}/raw_results.json   # đầy đủ, để audit
data/reports/{run_id}/metrics.json       # để so version
data/reports/{run_id}/report.md          # để đọc
```

### Điều kiện đo hợp lệ (bắt buộc)

1. **Warm-up trước khi tính giờ.** Cold load ~110s. Không warm-up thì bài đầu tiên làm hỏng p50/p95.
2. **`temperature = 0`.** Không có điều này thì hai lần chạy cho hai kết quả và không kết luận được gì.
3. **`keep_alive ≥ 30m`** để model không bị unload giữa chừng.
4. **Một run = một `pipeline_version` + một `prompt_version`.** Ghi cả hai vào `metrics.json`.
5. **Không sửa dataset giữa các lần so sánh.** Đổi dataset thì mọi so sánh lịch sử mất hiệu lực.

---

## 5. Cổng chấp nhận (regression gate)

Trước khi merge thay đổi ảnh hưởng tới chất lượng chấm:

| Điều kiện | Hành động |
| --- | --- |
| `MAE_overall` tệ đi > 0.15 | **Chặn merge** |
| `spearman_rho` giảm > 0.10 | **Chặn merge** |
| `json_parse_rate` < 95% | **Chặn merge** |
| `quote_fidelity` giảm > 5 điểm % | Chặn merge trừ khi có lý do được ghi nhận |
| `p95_latency` tăng > 50% | Cần lý do trong PR |

---

## 6. Những gì protocol này **chưa** đo (nợ kỹ thuật đã biết)

| Chưa đo | Vì sao quan trọng | Kế hoạch |
| --- | --- | --- |
| **Chất lượng feedback** (feedback có hữu ích không) | Đây mới là giá trị sản phẩm thật; band số chỉ là vỏ | P2: rubric chấm feedback bởi người, 5 tiêu chí (đúng, cụ thể, khả thi, đúng ưu tiên, dễ hiểu) |
| **Độ đúng của câu sửa** (`corrected` có thực sự đúng không) | Sửa sai còn tệ hơn không sửa | P2: đối chiếu với grammar checker + review tay trên mẫu |
| **Tính ổn định** (chạy lại nhiều lần với temp>0) | Đo độ nhạy của kết quả | P1: chạy N=5, báo cáo độ lệch chuẩn band |
| **Công bằng theo chủ đề** (bias theo topic) | Model có thể chấm cao hơn ở chủ đề quen | P3: cần dataset lớn hơn |
| **Inter-rater agreement của gold** | Nhãn hiện tại chỉ một nguồn | P2 |
