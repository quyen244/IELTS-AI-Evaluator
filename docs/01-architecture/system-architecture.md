# System Architecture

> Kiến trúc mục tiêu và kiến trúc P0 hiện tại. Phần nào đã build được đánh dấu ✅, phần nào chưa đánh dấu 🔜.

---

## 1. Nguyên tắc kiến trúc

Bốn nguyên tắc chi phối mọi quyết định dưới đây:

1. **LLM chỉ làm việc mà LLM giỏi.** Nhận định ngôn ngữ, phát hiện lỗi, giải thích → LLM. Đếm từ, tính trung bình, làm tròn band, áp penalty → **code xác định**. Giao số học cho LLM là nguồn lỗi rẻ tiền nhất và cũng dễ loại bỏ nhất.
2. **Contract-first giữa các tầng.** Mỗi node LLM có Pydantic schema đầu ra. Tầng trên không bao giờ đọc văn bản tự do của tầng dưới.
3. **Mỗi node một trách nhiệm, một call.** Không có "mega-prompt" chấm cả 4 tiêu chí. Lý do: dễ đo lỗi từng tiêu chí, dễ thay riêng lẻ, tránh tràn context, và cho phép chạy song song sau này.
4. **Provider-agnostic.** Toàn bộ pipeline gọi qua một interface `LLMClient`. Đổi Ollama → OpenAI → Gemini chỉ là đổi adapter, không đụng pipeline.

---

## 2. Sơ đồ phân lớp

```text
┌───────────────────────────────────────────────────────────────────────┐
│  L4  PRESENTATION                                                     │
│  ┌──────────────────┐  ┌──────────────────┐  ┌─────────────────────┐  │
│  │ Streamlit UI 🔜  │  │ CLI (scripts/) ✅│  │ Notebook (lab) ✅   │  │
│  └──────────────────┘  └──────────────────┘  └─────────────────────┘  │
└──────────────────────────────┬────────────────────────────────────────┘
                               │  EvaluationRequest / EvaluationResult
┌──────────────────────────────▼────────────────────────────────────────┐
│  L3  SERVICE / API                                    (FastAPI 🔜)    │
│  POST /api/v1/evaluate · GET /api/v1/evaluations/{id} · /health       │
│  Trách nhiệm: validate input, auth, rate-limit, persist, trả result   │
└──────────────────────────────┬────────────────────────────────────────┘
                               │
┌──────────────────────────────▼────────────────────────────────────────┐
│  L2  ORCHESTRATION — EvaluationPipeline ✅                            │
│                                                                       │
│   Stage 0 ── Preprocess (deterministic, 0 LLM call)                   │
│   Stage 1 ── 4 × CriterionEvaluator  (TA/TR · CC · LR · GRA)          │
│   Stage 2 ── SentenceCorrector       (lỗi mức câu)                    │
│   Stage 3 ── Aggregate (deterministic: overall band + penalty)        │
│   Stage 4 ── FeedbackSynthesizer     (kế hoạch hành động, tiếng Việt) │
│   Cross-cutting ── QuoteVerifier · RunTelemetry                       │
└──────────────────────────────┬────────────────────────────────────────┘
                               │  ChatRequest / parsed Pydantic model
┌──────────────────────────────▼────────────────────────────────────────┐
│  L1  LLM ABSTRACTION — LLMClient (Protocol) ✅                        │
│  ┌───────────────────┐ ┌────────────────┐ ┌────────────────────────┐  │
│  │ OllamaClient ✅   │ │ OpenAIClient 🔜│ │ GeminiClient 🔜        │  │
│  │ think=False       │ │                │ │                        │  │
│  │ format=<schema>   │ │                │ │                        │  │
│  └───────────────────┘ └────────────────┘ └────────────────────────┘  │
│  Chức năng chung: structured output · retry+repair · telemetry        │
└──────────────────────────────┬────────────────────────────────────────┘
                               │
┌──────────────────────────────▼────────────────────────────────────────┐
│  L0  INFRASTRUCTURE                                                   │
│  Ollama runtime (localhost:11434) ✅ · PostgreSQL 🔜 · File store ✅  │
└───────────────────────────────────────────────────────────────────────┘
```

---

## 3. Thành phần chi tiết

### 3.1 Stage 0 — Preprocess (`src/pipeline/preprocess.py`) ✅

Chạy **trước** mọi LLM call, không tốn token, kết quả được **nhét vào prompt làm bằng chứng khách quan**.

| Feature | Vì sao cần |
| --- | --- |
| `word_count` | LLM 4B đếm từ rất tệ. Penalty dưới ngưỡng phải dựa trên số đếm thật. |
| `sentence_count`, `avg_sentence_length` | Tín hiệu cho GRA (câu quá ngắn → thiếu complex structures) |
| `paragraph_count` | Tín hiệu cho CC (bài 1 đoạn → CC tối đa band 5) |
| `type_token_ratio`, `unique_words` | Tín hiệu khách quan cho LR (lặp từ) |
| `repeated_content_words` | Đưa thẳng vào prompt LR — LLM không phải tự đếm |
| `cohesive_devices_found` | Tín hiệu cho CC; phát hiện lạm dụng ("Firstly/Secondly/Finally" máy móc) |

> **Đây là bước có tỉ lệ giá trị/chi phí cao nhất toàn hệ thống.** Nó biến những câu hỏi mà model nhỏ trả lời sai thành dữ kiện có sẵn trong prompt.

### 3.2 Stage 1 — Criterion Evaluators ✅

4 evaluator độc lập, cùng interface, khác `criterion` + rubric + task type:

```
CriterionEvaluator(criterion, task_type)
    input : exam_prompt, essay, TextFeatures
    output: CriterionResult { band, confidence, evidence[], strengths[],
                              weaknesses[], improvements[] }
```

Rubric band descriptors được inject vào prompt từ `src/llm/rubrics/`. **Không hardcode rubric trong code Python** — rubric là dữ liệu, không phải logic, và cần sửa được mà không deploy lại.

### 3.3 Stage 2 — SentenceCorrector ✅
Trả `SentenceIssue[]`: `original`, `corrected`, `error_types[]`, `impact`, `explanation_vi`.
Giới hạn `MAX_ISSUES` để tránh output dài vô hạn trên bài yếu.

### 3.4 Stage 3 — Aggregator (deterministic) ✅
Xem [ADR-0003](../adr/0003-deterministic-band-aggregation.md).

### 3.5 Stage 4 — FeedbackSynthesizer ✅
Nhận **kết quả đã cấu trúc** của Stage 1–3 (không nhận lại essay gốc → tiết kiệm context), sinh:
- `summary_vi` — nhận xét tổng quan 3–5 câu
- `priority_actions[]` — đúng 3 việc, xếp theo tác động lên band
- `next_band_gap` — cần làm gì để lên band kế tiếp

### 3.6 Cross-cutting

**QuoteVerifier** — normalize whitespace/quote-mark rồi kiểm tra substring. Quote không khớp → `verified=false`, bị lọc khỏi output người dùng, được đếm vào `quote_fidelity`.

**RunTelemetry** — mọi call ghi lại: node, model, latency, prompt/eval tokens, số lần retry, parse ok/fail. Đây là cơ sở dữ liệu cho toàn bộ [Baseline Report](../03-evaluation/mvp-baseline-report.md).

---

## 4. Cấu trúc thư mục mục tiêu

```text
IELTS-AI-Evaluator/
├── docs/                          # ← bộ tài liệu này
├── data/
│   ├── exams/                     # 5 Task 1 + 5 Task 2 + gold labels
│   │   ├── task1/T1-001.json ...
│   │   ├── task2/T2-001.json ...
│   │   └── index.json
│   └── reports/                   # output của eval harness (gitignored)
├── src/
│   ├── core/
│   │   ├── config.py              # Settings (pydantic-settings)
│   │   ├── schemas.py             # toàn bộ Pydantic contract
│   │   └── telemetry.py
│   ├── llm/
│   │   ├── base.py                # LLMClient Protocol + LLMResponse
│   │   ├── ollama_client.py       # adapter Ollama (think=False)
│   │   ├── registry.py            # factory theo provider
│   │   ├── rubrics/               # band descriptors (data, không phải code)
│   │   └── prompts/
│   │       ├── common/
│   │       ├── writing_task_1/
│   │       └── writing_task_2/
│   ├── pipeline/
│   │   ├── preprocess.py
│   │   ├── nodes/                 # criterion.py · corrector.py · synthesizer.py
│   │   ├── aggregate.py
│   │   ├── verify.py
│   │   └── pipeline.py            # orchestrator
│   ├── evaluation/
│   │   ├── dataset.py
│   │   ├── metrics.py
│   │   └── harness.py
│   ├── backend/                   # 🔜 FastAPI
│   └── frontend/                  # 🔜 Streamlit
├── scripts/
│   ├── run_mvp.py                 # chấm 1 bài
│   └── run_eval.py                # benchmark toàn dataset
└── tests/
```

---

## 5. Quyết định thiết kế then chốt

| # | Quyết định | Lý do | Đánh đổi |
| --- | --- | --- | --- |
| D1 | **Bỏ LangChain ở P0** | Python 3.14 chưa có wheel ổn định cho toàn bộ chain LangChain; `ollama` SDK hỗ trợ `format=<json_schema>` và `think=False` native — mọi thứ ta cần. Bớt một tầng trừu tượng nghĩa là bớt một tầng phải debug. | Mất LCEL, callback tracing sẵn có. Ta tự viết telemetry (~80 dòng). Xem [ADR-0002](../adr/0002-drop-langchain-for-mvp.md). |
| D2 | **1 node = 1 LLM call** | Đo được lỗi từng tiêu chí; thay/A-B từng node độc lập | 6 call/bài thay vì 1 → chậm hơn. Chấp nhận vì latency biên là 0đ chi phí. |
| D3 | **`think=False`** | Qwen3.5 mặc định sinh reasoning trace dài → tăng latency ~3× mà JSON đầu ra không tốt hơn khi đã có structured format ép schema | Mất chain-of-thought ngầm. Bù bằng **explicit reasoning field trong schema** (`justification` đứng *trước* `band`) — xem [Prompt Spec](../02-technical/prompt-engineering.md) § Field ordering. |
| D4 | **Overall band tính bằng code** | Đúng tuyệt đối, có thể test unit, áp được penalty word-count | Không có |
| D5 | **Rubric là file dữ liệu** | Sửa rubric không cần đụng code; version được | Thêm một bước load |
| D6 | **`temperature=0` mặc định** | Reproducibility là điều kiện tiên quyết để đo cải tiến | Giảm đa dạng feedback. P2 dùng `temperature>0` có chủ đích cho self-consistency voting. |

---

## 6. Điểm mở rộng đã tính trước

| Muốn thêm | Chạm vào |
| --- | --- |
| Provider mới (OpenAI/Gemini) | Thêm 1 file trong `src/llm/`, đăng ký ở `registry.py`. Pipeline **không đổi**. |
| Tiêu chí chấm mới | Thêm rubric file + 1 dòng trong danh sách criteria |
| Task 1 Academic vs General | Thêm biến thể rubric theo `task_variant`, prompt template dùng chung |
| Self-consistency (P2) | Bọc `CriterionEvaluator` bằng decorator chạy N lần + vote median. Không sửa node. |
| Calibration (P2) | Thêm 1 hàm trong `aggregate.py`, sau `raw_band`, trước `final_band` |
| Chạy song song 4 criterion | Đổi vòng `for` trong `pipeline.py` thành `asyncio.gather`. Các node vốn đã không phụ thuộc nhau. |
