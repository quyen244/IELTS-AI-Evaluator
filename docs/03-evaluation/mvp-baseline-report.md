# MVP Baseline Report — P0

| | |
| --- | --- |
| Run ID | `20260815-030603-a6f7` |
| Model | `qwen3.5:4b` (Q4, 3.3 GB) via Ollama |
| Config | `temperature=0.0` · `enable_thinking=False` · `num_ctx=8192` · `seed=42` |
| Versions | `pipeline-v1.0` · `prompt-v1.0` · `rubric-v1.0` |
| Dataset | 10 bài (5 Task 1 + 5 Task 2), gold band 4.5–8.0 |
| Hardware | GTX 1660 Ti 6 GB · 100% GPU offload · ~46 tok/s warm |
| Wall clock | 1054 s cho 10 bài (60 LLM call) |

---

## 1. Đọc nhanh

Baseline **vượt toàn bộ ngưỡng P0** và vượt khá xa. Nhưng con số quan trọng nhất không phải MAE.

| Metric | Kết quả | Ngưỡng P0 | Ngưỡng P2 |
| --- | --- | --- | --- |
| `spearman_rho` | **0.877** | ≥ 0.6 | ≥ 0.85 ✅ **đã đạt mức P2** |
| `MAE_overall` | **0.45** | ≤ 1.0 ✅ | ≤ 0.5 ✅ **đã đạt mức P2** |
| `within_0.5` | **90%** | ≥ 40% ✅ | ≥ 70% ✅ |
| `within_1.0` | **100%** | ≥ 75% ✅ | — |
| `bias` | **+0.35** | \|bias\| ≤ 0.5 ✅ | \|bias\| ≤ 0.2 ❌ |
| `std_ratio` | **0.949** | — | — |
| `json_parse_rate` | **100%** | ≥ 95% ✅ | ≥ 99.5% ✅ |
| `quote_fidelity` | **77.0%** | ≥ 80% ❌ | ≥ 95% ❌ |
| `p95_latency` | **120.7 s** | ≤ 180 s ✅ | ≤ 60 s ❌ |

**Ba kết luận:**

1. **Model xếp hạng bài viết rất tốt** (`rho = 0.877`). Nó phân biệt được bài band 4.5 với bài band 8.0 một cách nhất quán. Đây là năng lực khó dạy nhất và nó đã có sẵn.
2. **Sai lệch còn lại chủ yếu là lệch thang, không phải lệch phán đoán** (`bias = +0.35`, và 8/10 bài lệch đúng `+0.5`). Đây là dạng lỗi mà một hàm calibration sửa được — rẻ.
3. **Điểm hỏng thật là `quote_fidelity = 77%`.** Gần một phần tư trích dẫn model đưa ra không tồn tại nguyên văn trong bài viết. Đây là **bug duy nhất trong báo cáo này**, và nó nằm ở phần quan trọng nhất với người học.

### Cảnh báo bắt buộc về ý nghĩa các con số

`MAE = 0.45` **không** có nghĩa hệ thống chính xác 0.45 band so với giám khảo IELTS thật. Nó có nghĩa hệ thống lệch 0.45 band so với **nhãn do chính tác giả dự án gán**. Ba giới hạn cụ thể:

- **n = 10.** Quá nhỏ để có ý nghĩa thống kê. Một bài đổi kết quả làm MAE dịch 0.05–0.1.
- **Bài viết được soạn để thể hiện band rõ ràng.** Bài band 4.5 có lỗi ngữ pháp dày đặc, bài band 8.0 viết rất tốt. Bài thật của thí sinh mập mờ hơn nhiều — đặc biệt ở khoảng 6.0–7.0 nơi phần lớn thí sinh thực sự nằm. **Dataset này dễ hơn thực tế.**
- **Bài viết và nhãn cùng do một người soạn.** Có rủi ro nhãn phản ánh *ý định* hơn là *văn bản*, và model đang khớp với những tín hiệu mà tác giả cố tình cài vào.

Vì vậy: dùng các con số này để **so sánh giữa các phiên bản pipeline**. Không dùng để tuyên bố độ chính xác. Xem [P2.1 trong roadmap](../04-roadmap/roadmap.md).

---

## 2. Kết quả từng bài

| Exam | Gold | Pred | Sai số | Raw | Penalty | Quote fidelity |
| --- | --- | --- | --- | --- | --- | --- |
| T1-001 | 5.0 | 5.0 | **0.0** | 4.75 | 0.0 | 0.83 |
| T1-002 | 7.0 | 7.5 | +0.5 | 7.375 | 0.0 | 0.50 |
| T1-003 | 7.5 | 8.0 | +0.5 | 7.75 | 0.0 | 0.85 |
| T1-004 | 8.0 | 7.5 | −0.5 | 7.25 | 0.0 | 1.00 |
| T1-005 | 4.5 | 5.0 | +0.5 | 4.75 | **0.5** | 0.50 |
| T2-001 | 5.5 | 6.0 | +0.5 | 6.0 | 0.0 | 0.46 |
| T2-002 | 6.5 | **7.5** | **+1.0** | 7.5 | 0.0 | 0.91 |
| T2-003 | 7.5 | 8.0 | +0.5 | 7.75 | 0.0 | 1.00 |
| T2-004 | 8.0 | 8.0 | **0.0** | 7.75 | 0.0 | 0.75 |
| T2-005 | 4.5 | 5.0 | +0.5 | 4.875 | **0.5** | 1.00 |

**Quan sát:** 7/10 bài lệch đúng `+0.5`, 1 bài lệch `−0.5`, 2 bài đúng chính xác. Phân bố này rất đều — đúng dấu hiệu của lệch thang đo hệ thống chứ không phải phán đoán ngẫu nhiên. Chỉ có T2-002 lệch `+1.0`.

**Length penalty hoạt động đúng.** T1-005 (104/150 từ) và T2-005 (183/250 từ) đều nhận `−0.5` áp vào TA/TR. Không bài nào đủ dài bị phạt nhầm.

---

## 3. Phân tích theo tiêu chí

| Tiêu chí | n | MAE | bias | within_0.5 | std_ratio |
| --- | --- | --- | --- | --- | --- |
| TA (Task 1) | 5 | 0.40 | **−0.20** | 0.80 | 1.033 |
| TR (Task 2) | 5 | 0.40 | +0.40 | 0.80 | 1.065 |
| CC | 10 | 0.45 | **−0.35** | 0.70 | 1.018 |
| LR | 10 | 0.50 | +0.10 | 0.80 | **0.709** |
| **GRA** | 10 | **0.75** | **+0.65** | **0.50** | 0.868 |

### GRA là tiêu chí yếu nhất — và lý do đáng chú ý

`bias = +0.65` nghĩa là model **chấm ngữ pháp rộng tay một cách hệ thống**. Nó nhìn thấy lỗi (sentence corrector bắt được chúng chính xác — xem § 5) nhưng **không quy đổi mật độ lỗi thành band đủ thấp**. Rubric GRA đã hướng dẫn "đếm câu error-free", nhưng model không thực sự đếm.

Đây chính là dạng vấn đề mà nguyên tắc kiến trúc của dự án đã giải quyết ở chỗ khác: **việc đếm nên do code làm.** Sentence corrector đã trả về danh sách lỗi có cấu trúc. Đưa `error_count / sentence_count` vào prompt GRA như một dữ kiện khách quan — đúng cách đã làm với word count — là hướng sửa rõ ràng và rẻ. Điều này đòi hỏi đảo thứ tự pipeline: chạy corrector **trước** GRA.

### LR nén dải điểm (`std_ratio = 0.709`)

Model không phân biệt đủ mạnh giữa từ vựng band 5 và band 8 — nó kéo mọi bài về giữa. Đây đúng là triệu chứng central tendency bias mà few-shot anchoring ([P1.1](../04-roadmap/roadmap.md)) nhắm tới. Đáng chú ý là các tiêu chí khác **không** bị (`std_ratio ≈ 1.0`), nên vấn đề khu trú ở rubric LR chứ không phải ở model nói chung.

### CC lệch ngược chiều (`bias = −0.35`)

CC là tiêu chí duy nhất model chấm **chặt hơn** gold. Nó phạt nặng các connector máy móc ("Firstly/Secondly"). Rubric CC nêu rõ đặc điểm này là dấu hiệu band 6, và model dường như áp dụng nó cứng nhắc hơn dự định.

**Hệ quả cho calibration:** vì CC lệch âm còn TR/GRA lệch dương, **calibration phải theo từng tiêu chí, không thể dùng một hàm toàn cục** — một hàm chung sẽ triệt tiêu lẫn nhau và không sửa được gì. Đây là câu trả lời bằng dữ liệu cho câu hỏi mở Q2 trong PRD.

---

## 4. Chất lượng hệ thống

| Metric | Giá trị | Nhận xét |
| --- | --- | --- |
| `json_parse_rate` | **100%** (60/60) | Constrained decoding qua `format=<schema>` hoạt động hoàn hảo |
| `first_attempt_parse_rate` | **100%** | Không call nào cần retry |
| `empty_evidence_rate` | **0%** | Mọi tiêu chí đều có evidence |
| `degraded_rate` | **0%** | Không node nào hỏng |
| `quote_fidelity` | **77.0%** (144/187) | ❌ **Dưới ngưỡng — xem § 5** |
| `p50 / p95 latency` | 102.5 s / 120.7 s | Trong ngưỡng P0, xa ngưỡng P2 |
| `tokens_per_essay` | 10,782 (72.0k prompt + 35.8k completion tổng) | |

**`json_parse_rate = 100%` xác nhận [ADR-0002](../adr/0002-drop-langchain-for-mvp.md).** Ép schema ở tầng runtime mạnh hơn hẳn so với `PydanticOutputParser` nhét mô tả schema vào prompt rồi parse text. Rủi ro R3 trong PRD coi như đã đóng.

`enable_thinking=False` không gây hại: chất lượng phán đoán vẫn cao (`rho = 0.877`) nhờ cơ chế `justification`-trước-`band`.

---

## 5. Điểm hỏng: hallucinated quotes

**43/187 trích dẫn (23%) không khớp nguyên văn bài viết.**

Phân bố rất không đều — và sự không đều đó chỉ ra nguyên nhân:

| Nhóm bài | Quote fidelity |
| --- | --- |
| T2-003, T2-005, T1-004 | 100% |
| T2-002 | 91% |
| T1-003, T1-001 | 83–85% |
| T2-004 | 75% |
| **T1-002, T1-005, T2-001** | **46–50%** |

Ba bài tệ nhất có đặc điểm chung: model **sửa lỗi của học viên ngay trong lúc trích dẫn**. Với T1-005 và T2-001 (bài nhiều lỗi), model có xu hướng chuẩn hoá ngữ pháp khi chép lại — trích "the pie charts show" trong khi bài viết "the two pie chart show". Với T1-002 (bài tốt), model rút gọn câu dài thay vì chép nguyên.

**Vì sao điều này nghiêm trọng hơn sai số band.** Một bài bị chấm lệch 0.5 band vẫn hữu ích. Một feedback trích dẫn câu mà học viên không hề viết thì:
- làm học viên mất niềm tin vào toàn bộ kết quả;
- và tệ hơn, khi model "sửa" lỗi trong lúc trích, nó **xoá mất chính lỗi mà nó định chỉ ra** — học viên đọc thấy câu đúng và không hiểu vấn đề ở đâu.

**Cơ chế phòng vệ đã hoạt động đúng.** `QuoteVerifier` phát hiện toàn bộ 43 trường hợp, đánh dấu `verified=false` và loại chúng khỏi feedback hiển thị (FR-2). Người dùng không bao giờ nhìn thấy trích dẫn bịa. Nhưng nó là **lưới an toàn, không phải cách sửa** — mỗi quote bị loại là một nhận xét mất đi.

**Hướng sửa (P1, ưu tiên cao):** yêu cầu model trả về **chỉ số câu** (`sentence_index`) thay vì chép lại văn bản; code tra ngược ra câu nguyên văn. Việc này biến trích dẫn từ một tác vụ sinh văn bản (model có thể sai) thành một tác vụ chọn chỉ mục (model khó sai hơn nhiều), và loại bỏ hoàn toàn khả năng bịa. Đây lại là một lần áp dụng nguyên tắc "LLM phán đoán, code thao tác dữ liệu".

---

## 6. So với ngưỡng PRD

| NFR | Ngưỡng P0 | Đo được | |
| --- | --- | --- | --- |
| NFR-01 latency ≤ 180 s | | 120.7 s (p95) | ✅ |
| NFR-02 parse rate ≥ 95% | | 100% | ✅ |
| NFR-03 quote fidelity ≥ 80% | | 77.0% | ❌ |
| NFR-04 MAE ≤ 1.0 | | 0.45 | ✅ |
| NFR-05 within_0.5 ≥ 40% | | 90% | ✅ |
| NFR-06 chi phí = 0 | | 0 | ✅ |
| NFR-07 không network egress | | không | ✅ |
| NFR-08 reproducible | | `temp=0`, `seed=42` | ✅ |

**7/8 đạt.** Mục trượt duy nhất là `quote_fidelity`, và nó đúng là hạng mục cần sửa trước.

---

## 7. Việc cần làm tiếp, theo thứ tự

| # | Việc | Vì sao | Kỳ vọng |
| --- | --- | --- | --- |
| 1 | **Trích dẫn theo `sentence_index`** thay vì chép text | Điểm hỏng duy nhất; ảnh hưởng trực tiếp tới giá trị sư phạm | `quote_fidelity` → ~100% |
| 2 | **Đưa mật độ lỗi vào prompt GRA** (chạy corrector trước GRA) | GRA là tiêu chí tệ nhất (MAE 0.75, bias +0.65) vì model không đếm | `MAE_GRA` → ~0.4 |
| 3 | **Mở rộng dataset lên 40–50 bài, tách train/test** | n=10 không đủ để kết luận; là điều kiện tiên quyết của #4 | Khoảng tin cậy thu hẹp |
| 4 | **Calibration theo từng tiêu chí** (không dùng hàm toàn cục) | Dữ liệu cho thấy CC lệch −0.35 còn TR/GRA lệch +0.4/+0.65 | `bias` → ~0, `MAE` → ~0.3 |
| 5 | **Few-shot anchoring cho riêng LR** | Chỉ LR bị nén dải (`std_ratio` 0.709); các tiêu chí khác ≈ 1.0 | `std_ratio_LR` → ~0.9 |
| 6 | **Gold label từ người có chứng chỉ** | Cho tới khi có, mọi con số ở đây chỉ so sánh nội bộ được | Mở khoá tuyên bố về độ chính xác |

**Không nên làm bây giờ:** đổi lên model 8B, self-consistency, tối ưu latency. Model 4B đã cho `rho = 0.877` — năng lực phán đoán không phải nút thắt. Nút thắt là kỹ thuật (trích dẫn), là dữ kiện đưa vào prompt (đếm lỗi), và là dataset. Đổi model bây giờ sẽ tốn tài nguyên để sửa thứ không hỏng.

---

## 8. Tái lập kết quả

```bash
ollama pull qwen3.5:4b
python -m scripts.run_eval --out data/reports
```

Với `temperature=0` và `seed=42`, kết quả tái lập được. So sánh `metrics.json` mới với `data/reports/20260815-030603-a6f7/metrics.json` để đo tác động của mọi thay đổi.
