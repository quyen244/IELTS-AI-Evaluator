# Roadmap P0 → P3

> Mọi hạng mục dưới đây có **exit criteria đo được**. Không có mục nào "làm cho tốt hơn".
> Số liệu tham chiếu: [MVP Baseline Report](../03-evaluation/mvp-baseline-report.md).

---

## Nguyên tắc ưu tiên

Sắp xếp theo **tỉ lệ (mức cải thiện kỳ vọng) / (chi phí thực hiện)**, không theo mức độ thú vị kỹ thuật. Cụ thể:

1. **Sửa cái đo được là hỏng trước.** Nếu `quote_fidelity` thấp, đó là bug, không phải hạng mục nghiên cứu.
2. **Calibration trước khi đổi model.** Nếu `spearman_rho` cao mà `bias` lớn, một hàm tuyến tính giải quyết được — rẻ hơn nhiều so với chạy model 8B.
3. **Dataset trước khi tối ưu.** Mọi cải tiến sau P1 đều vô nghĩa nếu vẫn đo trên 10 bài nhãn tự tạo. Đây là hạng mục nhàm chán nhất và cũng quan trọng nhất.
4. **Không tối ưu latency khi chi phí biến đổi bằng 0.** Người dùng chờ 90 giây một lần vẫn tốt hơn nhiều so với chờ giáo viên 48 tiếng. Latency chỉ thành ưu tiên khi phục vụ nhiều người đồng thời.

---

## P0 — MVP (ĐÃ HOÀN THÀNH)

**Mục tiêu:** chứng minh pipeline chạy được end-to-end, hoàn toàn cục bộ, và **đo được**.

| Hạng mục | Trạng thái |
| --- | --- |
| `LLMClient` abstraction + `OllamaClient` (`think=False`, structured output, retry+repair) | ✅ |
| Preprocess xác định (word count, TTR, repeated words, cohesive devices) | ✅ |
| 4 criterion evaluator có rubric anchoring, task-aware | ✅ |
| Sentence corrector (giải thích tiếng Việt) | ✅ |
| Aggregation xác định + length penalty áp vào TA/TR | ✅ |
| Quote verification + metric `quote_fidelity` | ✅ |
| Feedback synthesizer (3 priority actions, tiếng Việt) | ✅ |
| Dataset 10 bài có gold label 4 tiêu chí | ✅ |
| Eval harness + 8 metric chất lượng + 12 metric hệ thống | ✅ |
| 41 unit test cho toàn bộ phần xác định | ✅ |
| Bộ tài liệu `docs/` | ✅ |

**Exit criteria:** pipeline chạy hết 10 bài không crash, `json_parse_rate ≥ 95%`, có `metrics.json` làm baseline để so sánh. → **Đạt.**

---

## P1 — Độ chính xác & tin cậy (2–3 tuần)

**Mục tiêu:** đưa chất lượng chấm từ "chạy được" lên "dùng được", và mở rộng nền tảng đo lường.

### P1.1 — Few-shot rubric anchoring `[ưu tiên cao nhất]`
Chèn vào prompt mỗi tiêu chí **2 bài mẫu neo** (một band thấp ~5.0, một band cao ~7.5) kèm band và justification mẫu.

*Lý do:* model nhỏ nén dải điểm về giữa vì không có mốc tham chiếu cụ thể — nó chỉ có mô tả trừu tượng. Một ví dụ cụ thể "bài này là band 5" đáng giá hơn ba dòng descriptor.
*Chi phí:* +~600 token/call, tăng latency ~15%.
*Exit:* `std_ratio` tăng về ≥ 0.75 **và** `spearman_rho` không giảm.

### P1.2 — Calibration layer
Fit hàm `final = a·raw + b` (hoặc per-criterion) trên tập gold, áp giữa `raw_overall` và `overall_band`.

*Lý do:* nếu `rho` cao mà `bias` lệch, đây là cách rẻ nhất để thu MAE. Điểm chèn đã có sẵn trong `aggregate.py`.
*Bắt buộc:* fit trên tập train, đo trên tập test tách biệt. Fit và đo trên cùng 10 bài chỉ tạo ra ảo giác cải thiện.
*Exit:* `MAE_overall` giảm ≥ 0.2 trên tập **held-out**.

### P1.3 — Mở rộng dataset lên 40–50 bài
Phủ đều band 4.0–9.0, cả hai task, nhiều dạng đề. Chia train/test.

*Lý do:* 10 bài không đủ để phân biệt cải thiện thật với nhiễu. Đây là điều kiện tiên quyết cho P1.2 và mọi thứ sau đó.
*Exit:* ≥ 40 bài, ≥ 5 bài mỗi nửa band trong khoảng 5.0–8.0.

### P1.4 — Đo tính ổn định
Chạy `temperature=0.3`, N=5 lần/bài, báo cáo độ lệch chuẩn band.
*Lý do:* biết được kết quả nhạy đến mức nào là điều kiện để hiểu ý nghĩa của mọi con số khác.
*Exit:* có số liệu `band_std` trong `metrics.json`.

### P1.5 — FastAPI + Streamlit + PostgreSQL
Đưa pipeline ra khỏi CLI. Schema DB đã thiết kế sẵn ([data-schemas.md § 6](../02-technical/data-schemas.md)).
*Exit:* nộp bài qua UI, xem kết quả, xem lịch sử.

---

## P2 — Chất lượng đánh giá thật (4–6 tuần)

**Mục tiêu:** chuyển từ "khớp với nhãn của chính mình" sang "khớp với người chấm thật".

### P2.1 — Gold label từ người có chứng chỉ `[chặn mọi tuyên bố về độ chính xác]`
≥ 100 bài, ≥ 2 người chấm độc lập/bài, đo inter-rater agreement.

*Lý do:* đây là nợ kỹ thuật lớn nhất hiện tại. Cho đến khi trả xong, **không được** phát biểu bất kỳ con số độ chính xác nào so với IELTS thật. Và nếu hai người chấm không đồng ý với nhau, ta biết được giới hạn trên của những gì model có thể đạt được.
*Exit:* có tập ≥ 100 bài với inter-rater agreement được công bố.

### P2.2 — Self-consistency voting
Chạy mỗi criterion N=3 lần ở `temperature≈0.4`, lấy median band.
*Chi phí:* latency ×3. Chấp nhận được vì chi phí tiền tệ vẫn bằng 0.
*Exit:* `MAE` giảm ≥ 0.15 và `band_std` (từ P1.4) giảm ≥ 30%.

### P2.3 — A/B model 4B vs 8B vs cloud
Chạy cùng harness, cùng dataset, ba cấu hình. Trả lời câu hỏi Q4 trong PRD bằng dữ liệu.
*Exit:* có bảng so sánh MAE/rho/latency/VRAM → quyết định model mặc định.

### P2.4 — Rubric chấm chất lượng feedback
Sản phẩm thật là feedback, không phải con số. Cần rubric người-chấm 5 tiêu chí: đúng, cụ thể, khả thi, đúng ưu tiên, dễ hiểu. Chấm mẫu ≥ 30 bài.
*Exit:* điểm trung bình ≥ 4/5 ở cả 5 tiêu chí.

### P2.5 — Kiểm chứng độ đúng của câu sửa
Đối chiếu `corrected` với grammar checker + review tay trên mẫu.
*Lý do:* baseline đã cho thấy model thỉnh thoảng đưa giải thích ngữ pháp **sai** (xem [Baseline Report § Chất lượng nội dung](../03-evaluation/mvp-baseline-report.md)). Sửa sai tệ hơn không sửa, vì học viên tin và học theo.
*Exit:* ≥ 95% câu sửa được xác nhận đúng; có cơ chế hạ `impact` hoặc ẩn khi không chắc.

### P2.6 — Async + job queue
`POST /evaluate` trả `job_id` ngay, chấm nền. Cần thiết khi nhiều người dùng đồng thời.

---

## P3 — Mở rộng & sư phạm (2–3 tháng)

| Hạng mục | Nội dung | Exit criteria |
| --- | --- | --- |
| **P3.1 Multimodal Task 1** | Nhận ảnh biểu đồ trực tiếp thay vì `chart_description` | Độ chính xác trích số liệu ≥ 90% so với ground truth |
| **P3.2 Fine-tune LoRA** | Fine-tune model 4B trên dataset đã chấm (cần P2.1) | MAE giảm ≥ 0.2 so với prompt-only trên held-out |
| **P3.3 Theo dõi tiến bộ** | Biểu đồ band theo thời gian, phát hiện lỗi tái diễn qua nhiều bài | Người dùng thấy được xu hướng và top 3 lỗi dai dẳng |
| **P3.4 Sinh bài luyện cá nhân hoá** | Đề xuất đề bài / bài tập nhắm vào điểm yếu cụ thể | Có A/B test cho thấy cải thiện band thật |
| **P3.5 Hybrid routing** | Bài "khó" (confidence thấp, các tiêu chí lệch nhau nhiều) chuyển sang model mạnh hơn | MAE giảm mà chi phí trung bình vẫn thấp |
| **P3.6 Task 1 General Training** | Thư từ (formal/semi-formal/informal) — rubric khác | Có rubric + ≥ 10 bài mẫu |

---

## Bảng ưu tiên tổng hợp

| # | Hạng mục | Phase | Tác động | Chi phí | Ưu tiên |
| --- | --- | --- | --- | --- | --- |
| 1 | Few-shot rubric anchoring | P1.1 | Cao | Thấp | 🔴 Ngay |
| 2 | Mở rộng dataset 40–50 bài | P1.3 | Cao (điều kiện tiên quyết) | Trung bình | 🔴 Ngay |
| 3 | Calibration layer | P1.2 | Cao | Thấp | 🔴 Ngay |
| 4 | Đo tính ổn định | P1.4 | Trung bình (hiểu biết) | Thấp | 🟠 Sớm |
| 5 | Gold label chuyên gia | P2.1 | Rất cao (mở khoá mọi tuyên bố) | Cao | 🟠 Sớm |
| 6 | Kiểm chứng câu sửa | P2.5 | Cao (rủi ro sư phạm) | Trung bình | 🟠 Sớm |
| 7 | FastAPI + UI + DB | P1.5 | Trung bình (sản phẩm) | Trung bình | 🟡 Kế tiếp |
| 8 | Self-consistency | P2.2 | Trung bình | Thấp | 🟡 Kế tiếp |
| 9 | A/B model | P2.3 | Trung bình | Thấp | 🟡 Kế tiếp |
| 10 | Rubric chất lượng feedback | P2.4 | Cao (giá trị thật) | Cao | 🟡 Kế tiếp |
| 11 | Multimodal / fine-tune / routing | P3 | Cao | Rất cao | 🟢 Sau |

---

## Những gì cố tình KHÔNG làm

| Không làm | Lý do |
| --- | --- |
| Tối ưu latency ở P1 | Chi phí biến đổi bằng 0, một người dùng. Chờ 90s vẫn hơn chờ giáo viên 48h. Chỉ thành vấn đề khi có tải thật. |
| Chạy song song 4 criterion | Ollama serialize request trên cùng model, một GPU. Không có lợi ích cho tới khi batching ở mức nhiều bài. |
| Fine-tune trước P2.1 | Chưa có dữ liệu đáng tin. Fine-tune trên nhãn tự tạo là học thuộc thiên kiến của chính mình. |
| Thêm LangChain trở lại | Chưa gặp bài toán nào nó giải mà ta chưa giải được ([ADR-0002](../adr/0002-drop-langchain-for-mvp.md)). |
| Tăng `num_ctx` lên 32K | Prompt hiện dùng < 2500 token. Chỉ tốn VRAM. |
| Sinh bài mẫu hoàn chỉnh cho học viên | Rủi ro sư phạm: học viên copy thay vì học ([PRD § 3.3](../00-product/PRD.md)). |
