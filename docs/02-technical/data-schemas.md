# Data Schemas & Contracts

Nguồn chân lý: `src/core/schemas.py`. Tài liệu này giải thích **vì sao** schema có hình dạng như vậy.

---

## 1. Enum & kiểu nền

```python
TaskType   = "task1" | "task2"
Criterion  = "TA" | "TR" | "CC" | "LR" | "GRA"
Impact     = "negligible" | "minor" | "moderate" | "major" | "critical"
Polarity   = "positive" | "negative"
Band       = float  # 1.0..9.0, bội của 0.5
```

`TA` chỉ dùng cho Task 1, `TR` chỉ cho Task 2 — cùng vị trí trong rubric nhưng khác nội dung, nên tách enum thay vì dùng chung một tên mơ hồ.

---

## 2. Input

### `ExamItem`
```python
class GoldLabel(BaseModel):
    overall: float
    criteria: dict[str, float]      # {"TR": 6.0, "CC": 6.5, ...}
    source: str                     # xuất xứ nhãn
    confidence: Literal["high","medium","low"]

class ExamItem(BaseModel):
    exam_id: str                    # T1-001 / T2-003
    task_type: TaskType
    task_variant: str               # academic | general | ""
    topic: str
    prompt: str                     # đề bài nguyên văn
    chart_description: str | None   # Task 1: mô tả dữ liệu biểu đồ bằng text
    essay: str                      # bài viết mẫu để chấm
    gold: GoldLabel | None
    notes: str | None
```

> `chart_description` tồn tại vì P0 là text-only. Bài Task 1 thật có biểu đồ; ta mô tả dữ liệu bằng text để model có cái đối chiếu tính chính xác số liệu. Khi lên multimodal (P3), field này thành fallback.

> `gold.confidence` là field bắt buộc phải nghĩ tới, không phải trang trí. Dataset tự tạo có nhãn không chắc chắn; metric tính trên nhãn `low` phải được báo cáo tách biệt.

### `TextFeatures`
```python
class TextFeatures(BaseModel):
    word_count: int
    sentence_count: int
    paragraph_count: int
    avg_sentence_length: float
    unique_words: int
    type_token_ratio: float
    repeated_content_words: list[tuple[str, int]]
    cohesive_devices_found: list[str]
    meets_min_words: bool
    min_words_required: int
```

---

## 3. LLM output contract

### `Evidence`
```python
class Evidence(BaseModel):
    quote: str          # PHẢI là trích nguyên văn từ bài viết
    comment: str
    polarity: Polarity
    verified: bool = False    # do code set, không do LLM
```
`verified` mặc định `False` và **LLM không được phép set** — nó do `QuoteVerifier` gán sau. Nếu để LLM tự khai "tôi đã trích đúng", ta chỉ đo được sự tự tin của model chứ không đo được sự thật.

### `CriterionResult`
```python
class CriterionResult(BaseModel):
    criterion: Criterion
    justification: str        # ← ĐỨNG TRƯỚC band, có chủ đích
    band: float
    confidence: float
    evidence: list[Evidence]
    strengths: list[str]
    weaknesses: list[str]
    improvements: list[str]
    coerced: bool = False
    degraded: bool = False
```

**Thứ tự field là quyết định kỹ thuật, không phải thẩm mỹ.** JSON schema giữ thứ tự property, và constrained decoding sinh token tuần tự. Đặt `justification` trước `band` buộc model lập luận rồi mới chốt điểm. Đảo lại thì `justification` chỉ là lời biện hộ hậu nghiệm cho con số đã lỡ sinh ra. Đây là cách lấy lại lợi ích của chain-of-thought sau khi đã tắt `think`.

### `SentenceIssue`
```python
class SentenceIssue(BaseModel):
    original: str                # trích nguyên văn
    corrected: str
    error_types: list[str]       # grammar | word choice | collocation | word form | typo | punctuation | article | tense
    impact: Impact
    explanation_vi: str          # giải thích tiếng Việt
    verified: bool = False
```

### `FeedbackSummary`
```python
class PriorityAction(BaseModel):
    action: str                  # tiếng Việt, mệnh lệnh, cụ thể
    criterion: Criterion
    expected_gain: str           # "+0.5 LR"
    example: str                 # ví dụ sửa cụ thể lấy từ bài

class FeedbackSummary(BaseModel):
    summary_vi: str
    priority_actions: list[PriorityAction]   # đúng 3
    next_band_gap: str
```

---

## 4. Output tổng

```python
class EvaluationResult(BaseModel):
    exam_id: str | None
    task_type: TaskType
    overall_band: float          # ← code tính
    raw_overall: float           # trung bình chưa làm tròn
    length_penalty: float        # penalty đã áp vào TA/TR
    partial: bool                # True nếu thiếu ≥1 tiêu chí
    criteria: dict[str, ScoredCriterion]
    sentence_issues: list[VerifiedSentenceIssue]
    feedback: FeedbackSummary | None
    features: TextFeatures
    pipeline_version: str
    prompt_version: str
    model: str
    telemetry: RunTelemetry
    disclaimer: str              # cảnh báo bắt buộc (PRD R6)
```

`ScoredCriterion` là bản mở rộng phía output của `CriterionResult`: thêm `raw_band`, `length_penalty`, `verified` trên từng evidence, và các cờ `coerced` / `degraded`. Tách hai loại là có chủ đích — `CriterionResult` là thứ **LLM được phép sinh**, `ScoredCriterion` là thứ **hệ thống khẳng định** sau khi đã kiểm chứng. Gộp chúng lại sẽ mở đường cho model tự khai `verified=true`.

`overall_band`, `raw_overall`, `length_penalty`, và `ScoredCriterion.raw_band` tách rời nhau để **audit được**: nhìn vào kết quả là biết ngay điểm thấp do model chấm thấp hay do penalty word-count.

---

## 5. Telemetry

```python
class CallRecord(BaseModel):
    node: str
    model: str
    ok: bool
    attempts: int
    latency_s: float
    prompt_tokens: int
    completion_tokens: int
    error: str | None

class RunTelemetry(BaseModel):
    run_id: str
    started_at: str
    total_latency_s: float
    calls: list[CallRecord]
    total_prompt_tokens: int
    total_completion_tokens: int
    json_parse_failures: int
    quotes_total: int
    quotes_verified: int

    @property
    def quote_fidelity(self) -> float: ...
```

---

## 6. Database schema (P1)

```sql
CREATE TABLE essays (
    id              UUID PRIMARY KEY,
    user_id         UUID REFERENCES users(id),
    task_type       VARCHAR(8)  NOT NULL,
    task_variant    VARCHAR(16),
    prompt          TEXT        NOT NULL,
    content         TEXT        NOT NULL,
    word_count      INT         NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE evaluations (
    id              UUID PRIMARY KEY,
    essay_id        UUID REFERENCES essays(id) ON DELETE CASCADE,
    overall_band    NUMERIC(2,1) NOT NULL,
    raw_overall     NUMERIC(3,2) NOT NULL,
    penalty_applied NUMERIC(2,1) NOT NULL DEFAULT 0,
    partial         BOOLEAN      NOT NULL DEFAULT false,
    model_name      VARCHAR(64)  NOT NULL,
    pipeline_version VARCHAR(32) NOT NULL,   -- so sánh version được
    prompt_version  VARCHAR(32)  NOT NULL,
    latency_s       NUMERIC(6,2),
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE TABLE evaluation_criteria (
    id              BIGSERIAL PRIMARY KEY,
    evaluation_id   UUID REFERENCES evaluations(id) ON DELETE CASCADE,
    criterion       VARCHAR(4)   NOT NULL,
    band            NUMERIC(2,1),
    confidence      NUMERIC(3,2),
    justification   TEXT,
    payload         JSONB        NOT NULL,   -- evidence/strengths/weaknesses/improvements
    UNIQUE (evaluation_id, criterion)
);

CREATE TABLE sentence_issues (
    id              BIGSERIAL PRIMARY KEY,
    evaluation_id   UUID REFERENCES evaluations(id) ON DELETE CASCADE,
    original        TEXT NOT NULL,
    corrected       TEXT NOT NULL,
    error_types     TEXT[] NOT NULL,
    impact          VARCHAR(16) NOT NULL,
    explanation_vi  TEXT,
    verified        BOOLEAN NOT NULL DEFAULT false
);

CREATE INDEX idx_essays_user_created ON essays(user_id, created_at DESC);
CREATE INDEX idx_eval_essay          ON evaluations(essay_id);
CREATE INDEX idx_eval_version        ON evaluations(pipeline_version, prompt_version);
```

**`pipeline_version` + `prompt_version` trên bảng `evaluations` là điều kiện bắt buộc để cải tiến có kỷ luật.** Không có chúng, sau ba tháng ta sẽ có một đống điểm số không biết sinh ra bởi phiên bản nào và không so sánh được với nhau.
