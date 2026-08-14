# Prompt Engineering Specification

---

## 1. Bảy nguyên tắc

### P1 — Một prompt, một nhiệm vụ
Không có prompt nào chấm quá một tiêu chí. Prompt gộp làm ba việc tệ cùng lúc: tràn context, không đo được lỗi thuộc tiêu chí nào, và khiến model "kéo" điểm các tiêu chí về giống nhau (halo effect).

### P2 — Bằng chứng khách quan đi trước phán xét
Mọi prompt chấm điểm đều được inject `TextFeatures` đã tính bằng code:
```
OBJECTIVE TEXT STATISTICS (computed programmatically — treat as ground truth):
- Word count: 287 (minimum required: 250) ✓
- Paragraphs: 4 | Sentences: 16 | Avg sentence length: 17.9 words
- Type-token ratio: 0.58 | Unique words: 166
- Most repeated content words: exploration(6), government(5), money(4)
- Cohesive devices found: however, as a result, on the one hand, in conclusion
```
Model 4B đếm từ sai thường xuyên. Đưa sẵn số đếm đúng loại bỏ hẳn một lớp lỗi thay vì hy vọng model làm đúng.

### P3 — Rubric anchoring hiển ngôn
Prompt chứa band descriptor của **đúng tiêu chí đang chấm**, band 4 → 9, viết ngắn gọn để không nuốt context. Không có neo, model 4B dồn mọi bài về band 6–6.5 (central tendency bias). Rubric là **dữ liệu** trong `src/llm/rubrics/`, không phải chuỗi hardcode trong Python.

### P4 — `justification` trước `band`
Xem [data-schemas.md § 3](data-schemas.md#3-llm-output-contract). Đây là cơ chế thay thế cho `think=True` đã tắt.

### P5 — Trích dẫn nguyên văn, không diễn giải
```
Every `quote` MUST be copied character-for-character from the essay.
Do NOT paraphrase, correct, or shorten it. If you cannot find an exact
supporting quote, omit that evidence item rather than inventing one.
```
Bổ trợ bằng `QuoteVerifier` phía code — chỉ dặn trong prompt là không đủ.

### P6 — Ngôn ngữ có chủ đích
Phân tích kỹ thuật bằng **tiếng Anh** (thuật ngữ IELTS chuẩn, model quen hơn). Giải thích cho học viên bằng **tiếng Việt**. Đánh dấu rõ trong prompt field nào dùng ngôn ngữ nào, nếu không model sẽ trộn lẫn.

### P7 — Structured output là tầng runtime, không phải lời cầu xin trong prompt
Ta truyền JSON Schema qua tham số `format` của Ollama (constrained decoding). Prompt vẫn nhắc ngắn gọn về ngữ nghĩa các field, nhưng **không** phải viết "Return ONLY valid JSON, no markdown, no prose!!!" — runtime đã lo hình dạng; prompt chỉ lo nội dung.

---

## 2. Cấu trúc chuẩn của một prompt chấm tiêu chí

```text
[SYSTEM]
You are a certified IELTS Writing examiner with 10+ years of experience
assessing {task_label}. You apply the official band descriptors strictly
and consistently. You are neither lenient nor harsh — you are accurate.

[USER]
## CRITERION UNDER ASSESSMENT
{criterion_full_name} ({criterion_code})

## OFFICIAL BAND DESCRIPTORS
{rubric_text}                       ← từ src/llm/rubrics/

## EXAM PROMPT
{exam_prompt}
{chart_description}                 ← chỉ Task 1

## STUDENT ESSAY
<<<ESSAY
{essay}
ESSAY

## OBJECTIVE TEXT STATISTICS (computed programmatically — ground truth)
{features_block}

## YOUR TASK
1. Write `justification`: 3–5 sentences in English explaining which band
   descriptor the essay matches and why. Reference the descriptors explicitly.
2. Then assign `band` (1.0–9.0, multiples of 0.5) consistent with (1).
3. Provide 2–4 `evidence` items. Each `quote` MUST be copied verbatim
   from the essay between the ESSAY markers.
4. List `strengths`, `weaknesses`, and `improvements` (English, concise).
5. `confidence`: 0.0–1.0, how certain you are of this band.

## CRITICAL RULES
- Never invent a quote. Omit an evidence item rather than fabricate it.
- Do not assess other criteria — only {criterion_code}.
- Use the word count given above; do not re-count.
```

**Dấu phân định `<<<ESSAY … ESSAY`** không phải trang trí: nó ngăn nội dung bài viết của học viên bị đọc như chỉ dẫn (prompt injection ngẫu nhiên — thí sinh hoàn toàn có thể viết một câu trông giống mệnh lệnh) và cho model một mốc rõ ràng để trích dẫn nguyên văn.

---

## 3. Rubric compression

Band descriptor chính thức của IELTS rất dài. Nhồi cả bốn tiêu chí × 9 band vào prompt sẽ ngốn ~4000 token. Chiến lược:

| Cách | Token | Dùng khi |
| --- | --- | --- |
| Full official text | ~1000/tiêu chí | Không dùng ở P0 |
| **Compressed band 4–9, 2–3 dòng/band** | **~250/tiêu chí** | **P0 hiện tại** |
| Compressed + 2 few-shot anchor essay | ~900/tiêu chí | P1 |

Bản nén giữ đúng **các từ khoá phân biệt band** (ví dụ LR: *"limited"* B4 → *"adequate but limited"* B5 → *"sufficient, some less common"* B6 → *"sufficient flexibility and precision"* B7 → *"wide resource, skilful"* B8). Nén sai các từ khoá này là làm hỏng khả năng phân biệt band của model.

---

## 4. Prompt versioning

Mỗi prompt module khai báo:
```python
PROMPT_VERSION = "criterion-v1.0"
```
`PROMPT_VERSION` đi vào `RunTelemetry` và (P1) vào cột `prompt_version` của DB. Quy tắc: **đổi nội dung prompt → bump version → chạy lại `run_eval` → so `metrics.json`.** Không có ngoại lệ. Sửa prompt mà không đo là thay đổi mù.

| Version | Thay đổi | MAE_overall |
| --- | --- | --- |
| `criterion-v1.0` | Baseline P0: rubric nén + features + justification-first | xem [Baseline Report](../03-evaluation/mvp-baseline-report.md) |

---

## 5. Anti-pattern đã loại bỏ khỏi codebase cũ

| Anti-pattern (bản cũ) | Vấn đề | Đã thay bằng |
| --- | --- | --- |
| `[PASTE ESSAY HERE]` trong `synonyms_paraphrase.py` | Placeholder thủ công, không phải template variable → prompt gửi đi với chữ literal đó | `{essay}` template variable |
| Ví dụ JSON dùng nháy đơn (`'correct sentence'`) trong `vocab_suggestion.py` | Không phải JSON hợp lệ; dạy model sinh JSON sai | JSON Schema qua `format=` |
| Tên field có khoảng trắng: `'level_impact '` | Trailing space → parse ra key sai | Pydantic field name |
| Output là **Markdown table** trong string (`vocab_table_analysis`) | Không parse được về dữ liệu; không tính metric được; không lưu DB được | `list[Evidence]` có cấu trúc |
| Rubric tiếng Việt trộn tiếng Anh trong cùng band descriptor | Model phải dịch trước khi so khớp → nhiễu | Rubric tiếng Anh, giải thích tiếng Việt tách riêng |
| Không có neo rubric (chỉ "act as examiner") | Central tendency bias, mọi bài ~6.0 | Band descriptor 4–9 hiển ngôn |
| Không kiểm chứng trích dẫn | Feedback bịa đặt không bị phát hiện | `QuoteVerifier` + metric |

---

## 6. Prompt cho Sentence Corrector

Điểm khác biệt: cần **giới hạn số lượng** và **ưu tiên theo tác động**.

```text
Identify at most {max_issues} sentence-level problems, ordered by how much
they damage the band score (most damaging first). Prefer errors that affect
meaning or accuracy over stylistic preferences. Do not list the same error
pattern more than twice — instead note it once and mark impact accordingly.
```

Không có giới hạn này, bài band 4 sinh ra 40 issue và người học không biết bắt đầu từ đâu — feedback quá tải cũng vô dụng như không có feedback.

---

## 7. Prompt cho Feedback Synthesizer

Node này **không nhận lại essay gốc**. Nó chỉ nhận `CriterionResult` đã cấu trúc + `SentenceIssue` đã lọc. Ba lý do:
1. Tiết kiệm ~400 token/call.
2. Ép model tổng hợp từ phân tích đã có thay vì chấm lại từ đầu (sẽ mâu thuẫn với band đã chốt).
3. Không thể bịa quote mới vì không có văn bản gốc để bịa từ đó.

Yêu cầu đầu ra: đúng **3** `priority_actions`, sắp theo `expected_gain` giảm dần, mỗi action phải có `example` lấy từ `weaknesses`/`sentence_issues` đã có.
