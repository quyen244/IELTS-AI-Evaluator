# PRD — IELTS-AI-Evaluator (IAE)

| Field | Value |
| --- | --- |
| Document owner | Nguyen Van Quyen (23521329) |
| Version | 2.0 |
| Status | Approved for P0 implementation |
| Last updated | 2026-08-15 |
| Supersedes | README.md § Overview (v1.0) |

---

## 1. Problem Statement

Thí sinh luyện IELTS Writing gặp ba nút thắt cụ thể, đo được:

| Nút thắt | Hiện trạng | Hệ quả |
| --- | --- | --- |
| **Chi phí** | 80.000–200.000 VNĐ / bài chấm bởi giáo viên | Thí sinh chỉ chấm 2–4 bài/tháng, dưới ngưỡng luyện tập hiệu quả (~12 bài/tháng) |
| **Độ trễ** | 24–72 giờ để nhận feedback | Vòng lặp học tập bị đứt; thí sinh quên bối cảnh khi viết bài |
| **Tính hành động** | Feedback thường ở mức "cần cải thiện từ vựng" | Thí sinh không biết **sửa câu nào, sửa thành gì** |

Các công cụ hiện có (Grammarly, ChatGPT thô) không giải quyết được vì: (a) không neo theo **IELTS band descriptors** chính thức, (b) không phân biệt Task 1 (report — mô tả dữ liệu) và Task 2 (essay — lập luận), (c) không đưa được bằng chứng trích dẫn từ chính bài viết.

### 1.1 Vì sao "local-first" là ràng buộc sản phẩm, không phải sở thích kỹ thuật

- Bài viết của thí sinh là **dữ liệu học tập cá nhân**; gửi lên API bên thứ ba tạo rào cản pháp lý khi triển khai cho trường học.
- Chi phí biến đổi bằng 0 cho phép mô hình freemium không giới hạn số lần chấm — đây chính là đòn bẩy giải quyết nút thắt **Chi phí**.
- Xem [ADR-0001](../adr/0001-local-llm-first.md).

---

## 2. Users & Jobs-to-be-Done

### Persona 1 — Thí sinh tự luyện (primary)
> "Tôi vừa viết xong bài, tôi muốn biết ngay mình được band mấy và **câu nào** đang kéo điểm tôi xuống."

- Trình độ hiện tại: Band 5.0–6.5, mục tiêu 6.5–7.5.
- Tần suất: 3–5 bài/tuần trong giai đoạn nước rút.
- **Thành công =** biết chính xác 3 lỗi ưu tiên sửa, có câu viết lại mẫu.

### Persona 2 — Giáo viên / trung tâm (secondary)
> "Tôi có 40 bài cần chấm. Tôi muốn máy chấm nháp trước để tôi chỉ cần review và chỉnh."

- **Thành công =** máy chấm lệch ≤ 0.5 band so với mình ở ≥ 70% số bài; tiết kiệm ≥ 50% thời gian.

### Non-user (out of scope P0–P3)
- Thí sinh luyện Speaking / Listening / Reading.
- Tổ chức khảo thí muốn dùng điểm này làm điểm chính thức. **IAE là công cụ luyện tập, không phải công cụ khảo thí.**

---

## 3. Product Scope

### 3.1 In scope (P0 — MVP)

| ID | Yêu cầu |
| --- | --- |
| F-01 | Nhận đề bài + bài viết (Task 1 hoặc Task 2), text thuần |
| F-02 | Chấm 4 tiêu chí chính thức: TA/TR, CC, LR, GRA — mỗi tiêu chí trả band 1.0–9.0 bước 0.5 |
| F-03 | Tính Overall band theo quy tắc làm tròn chính thức của IELTS |
| F-04 | Với mỗi tiêu chí: trả `evidence[]` **trích nguyên văn từ bài viết** (không được bịa) |
| F-05 | Trả danh sách lỗi câu-mức: `original → corrected`, loại lỗi, mức ảnh hưởng, giải thích tiếng Việt |
| F-06 | Trả bản tổng hợp hành động: 3 việc ưu tiên cần sửa để lên band kế tiếp |
| F-07 | Phân tích tiền xử lý xác định (word count, TTR, connective, paragraph) làm bằng chứng khách quan |
| F-08 | Chạy hoàn toàn offline trên Ollama, không cần API key |

### 3.2 In scope (P1–P3) — xem [Roadmap](../04-roadmap/roadmap.md)
FastAPI service, Streamlit UI, DB lưu lịch sử, few-shot rubric anchoring, self-consistency, calibration layer, Task 1 chart-image input.

### 3.3 Explicitly out of scope
- Chấm chữ viết tay / OCR ảnh bài viết (P4+).
- Phát hiện đạo văn, phát hiện bài do AI viết.
- Sinh bài mẫu hoàn chỉnh thay cho thí sinh (rủi ro sư phạm: thí sinh copy thay vì học).

---

## 4. Functional Requirements (chi tiết)

### FR-1: Task-aware evaluation
Hệ thống **phải** dùng bộ rubric khác nhau cho Task 1 và Task 2:

| Tiêu chí | Task 1 | Task 2 |
| --- | --- | --- |
| 1 | **Task Achievement** — có overview không? có số liệu chính xác không? có so sánh đúng không? | **Task Response** — có trả lời đúng dạng câu hỏi không? có position rõ ràng không? có phát triển ý không? |
| 2 | Coherence & Cohesion | Coherence & Cohesion |
| 3 | Lexical Resource (ngôn ngữ mô tả xu hướng/dữ liệu) | Lexical Resource (ngôn ngữ lập luận/học thuật) |
| 4 | Grammatical Range & Accuracy | Grammatical Range & Accuracy |

Word count tối thiểu: Task 1 = 150, Task 2 = 250. Dưới ngưỡng → **penalty bắt buộc, áp dụng bằng code chứ không giao cho LLM** (xem [ADR-0003](../adr/0003-deterministic-band-aggregation.md)).

### FR-2: Evidence grounding (bắt buộc)
Mọi nhận định của LLM phải kèm `quote` là **substring xuất hiện nguyên văn** trong bài viết. Hệ thống chạy `verify_quote()` sau khi parse; quote không khớp bị đánh dấu `hallucinated=true` và **bị loại khỏi feedback hiển thị cho người dùng**, đồng thời ghi vào metric `quote_fidelity`.

> Đây là yêu cầu sản phẩm, không phải tối ưu kỹ thuật: feedback bịa đặt làm thí sinh mất niềm tin và sửa sai chỗ.

### FR-3: Structured output contract
Mọi output LLM phải là JSON hợp lệ theo schema Pydantic. Không parse prose. Không regex trên văn bản tự do. Xem [data-schemas.md](../02-technical/data-schemas.md).

### FR-4: Deterministic aggregation
Overall band **không** do LLM tính. Code tính theo công thức chính thức: trung bình 4 tiêu chí, làm tròn về 0.5 gần nhất (`.25 → làm tròn lên .5`, `.75 → làm tròn lên 1.0`).

### FR-5: Bilingual feedback
- Phân tích kỹ thuật (evidence, band, error type): **tiếng Anh** (thuật ngữ IELTS chuẩn).
- Giải thích & hướng dẫn sửa: **tiếng Việt** (đối tượng người dùng là thí sinh Việt Nam).

---

## 5. Non-Functional Requirements

| ID | Yêu cầu | Ngưỡng P0 | Ngưỡng P2 |
| --- | --- | --- | --- |
| NFR-01 | Latency mỗi bài (warm model, GPU 6GB) | ≤ 180 s | ≤ 60 s |
| NFR-02 | Tỉ lệ parse JSON thành công | ≥ 95% | ≥ 99.5% |
| NFR-03 | Quote fidelity (quote khớp nguyên văn) | ≥ 80% | ≥ 95% |
| NFR-04 | MAE band tổng so với gold label | ≤ 1.0 | ≤ 0.5 |
| NFR-05 | Tỉ lệ bài lệch ≤ 0.5 band ("within-half") | ≥ 40% | ≥ 70% |
| NFR-06 | Chi phí biến đổi / bài | 0 VNĐ | 0 VNĐ |
| NFR-07 | Không có network egress khi chấm | Bắt buộc | Bắt buộc |
| NFR-08 | Reproducibility: cùng input + seed → cùng output | Bắt buộc (`temperature=0`) | Bắt buộc |

### Phần cứng tham chiếu (baseline machine)
GTX 1660 Ti 6GB VRAM · qwen3.5:4b (Q4, 3.3GB) · 100% GPU offload · ~46 tok/s warm · cold load ~110s → **bắt buộc preload model với `keep_alive`**.

---

## 6. Success Metrics

### 6.1 Model quality (đo bằng harness, xem [Evaluation Protocol](../03-evaluation/evaluation-protocol.md))

| Metric | Định nghĩa | Target P0 | **Đo được P0** | Target P3 |
| --- | --- | --- | --- | --- |
| `MAE_overall` | Mean absolute error của overall band | ≤ 1.0 | **0.45** ✅ | ≤ 0.4 |
| `within_0.5` | % bài lệch ≤ 0.5 band | ≥ 40% | **90%** ✅ | ≥ 75% |
| `within_1.0` | % bài lệch ≤ 1.0 band | ≥ 75% | **100%** ✅ | ≥ 95% |
| `MAE_per_criterion` | MAE từng tiêu chí | ≤ 1.2 | **0.40–0.75** ✅ | ≤ 0.5 |
| `rank_corr` | Spearman ρ giữa band dự đoán và gold | ≥ 0.6 | **0.877** ✅ | ≥ 0.85 |
| `bias` | Sai số có dấu (dương = chấm rộng tay) | \|bias\| ≤ 0.5 | **+0.35** ✅ | \|bias\| ≤ 0.2 |

> Chi tiết và **các cảnh báo bắt buộc về ý nghĩa của những con số này** (n=10, nhãn tự tạo, dataset dễ hơn thực tế): [MVP Baseline Report](../03-evaluation/mvp-baseline-report.md).

> **`rank_corr` quan trọng hơn `MAE` ở giai đoạn đầu.** Nếu hệ thống xếp hạng đúng bài tốt/bài kém nhưng lệch đều một khoảng cố định, ta sửa được bằng **calibration layer** (P2) — rẻ. Nếu xếp hạng sai, phải sửa prompt/model — đắt.

### 6.2 System quality
`json_parse_rate`, `quote_fidelity`, `p50/p95_latency`, `tokens_per_essay`.

### 6.3 Product (P3+, cần người dùng thật)
Retention tuần 4, số bài nộp / user / tuần, % user tự báo cáo "feedback hữu ích" ≥ 4/5.

---

## 7. Key Risks & Mitigations

| # | Rủi ro | Mức độ | Giảm thiểu | Trạng thái sau P0 |
| --- | --- | --- | --- | --- |
| R1 | **Model 4B chấm không chuẩn**, dồn về band trung bình (central tendency bias) | Cao | Đo `bias` + `rank_corr` riêng; calibration layer; few-shot anchor | ⬇️ **Hạ xuống Thấp.** `std_ratio = 0.949` — không nén dải. Chỉ LR bị (0.709). |
| R2 | **Hallucinated quotes** — LLM bịa câu không có trong bài | Cao | `verify_quote()` bắt buộc; loại quote sai trước khi hiển thị (FR-2) | ⬆️ **Nâng lên rủi ro số 1.** Đo được 23% quote bịa. Lưới an toàn hoạt động nhưng cần sửa gốc (P1.1). |
| R3 | **JSON parse fail** | Trung bình | Dùng `format=<json_schema>` native của Ollama + retry có phản hồi lỗi | ✅ **Đóng.** `json_parse_rate = 100%`, không call nào cần retry. |
| R4 | **Gold label không đáng tin** (dataset tự tạo) | Cao | Ghi rõ nguồn và mức tin cậy từng nhãn; tuyệt đối không tuyên bố độ chính xác tuyệt đối; P2 cần đối chiếu người chấm thật |
| R5 | **Latency cold start 110s** làm hỏng trải nghiệm | Trung bình | `keep_alive="30m"` + warm-up call khi khởi động service |
| R6 | Người dùng coi điểm IAE là điểm IELTS thật | Trung bình | Disclaimer bắt buộc trên mọi output: "Điểm tham khảo cho mục đích luyện tập" |
| R7 | Context window 8K không đủ cho pipeline nhiều bước | Thấp | Mỗi node là 1 call độc lập, chỉ nhận đúng context cần thiết — không nhồi cả lịch sử |

---

## 8. Assumptions

1. Người dùng nhập bài viết dạng **text**, không phải ảnh (P0).
2. Bài viết bằng tiếng Anh; hệ thống không xử lý bài viết lẫn tiếng Việt.
3. Ollama chạy sẵn trên `localhost:11434`.
4. Gold label trong `data/exams/` là **ước lượng chuyên môn**, dùng để đo *tương đối* giữa các phiên bản pipeline, không phải chuẩn khảo thí.

---

## 9. Open Questions

| # | Câu hỏi | Cần quyết trước phase |
| --- | --- | --- |
| Q1 | Có cần chấm cả bài Task 1 có biểu đồ (multimodal) không, hay chỉ nhận mô tả text của biểu đồ? | P2 |
| Q2 | ~~Calibration nên là hàm tuyến tính toàn cục hay per-criterion?~~ | ✅ **Đã trả lời bằng dữ liệu P0: bắt buộc per-criterion.** Bias ngược chiều giữa các tiêu chí (CC −0.35, TA −0.20, LR +0.10, TR +0.40, GRA +0.65) — một hàm toàn cục sẽ để chúng triệt tiêu lẫn nhau. |
| Q3 | Có lưu bài viết của user vào DB không (privacy) — opt-in hay opt-out? | P1 |
| Q4 | Model 4B có đủ không, hay cần lên 7B/8B? | ⏸️ **Hoãn.** `rho = 0.877` với 4B ⇒ năng lực phán đoán không phải nút thắt hiện tại. Đánh giá lại sau khi xong P1.1–P1.4. |
