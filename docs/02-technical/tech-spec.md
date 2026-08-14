# Technical Specification

---

## 1. Tech Stack

| Layer | P0 (đã build) | P1–P3 (kế hoạch) |
| --- | --- | --- |
| Runtime | Python 3.11+ (verified trên 3.14.3) | idem |
| LLM inference | **Ollama** `qwen3.5:4b` (Q4, 3.3GB) | + `qwen3.5:8b`, OpenAI GPT-4o, Gemini |
| LLM SDK | `ollama` (official Python client) | + `openai`, `google-genai` |
| Schema / validation | `pydantic` v2 | idem |
| Config | `pydantic-settings` + `.env` | idem |
| Metrics | `numpy` (thuần Python fallback nếu thiếu) | + `scipy` cho Spearman chính xác |
| API | — | FastAPI + Uvicorn |
| UI | CLI | Streamlit |
| DB | JSON file | PostgreSQL + SQLAlchemy |
| Test | `pytest` | idem + golden-file tests |

**Không dùng LangChain ở P0** — xem [ADR-0002](../adr/0002-drop-langchain-for-mvp.md).

---

## 2. Configuration

Toàn bộ config qua `src/core/config.py` (`pydantic-settings`), đọc từ `.env`, override được bằng biến môi trường.

```env
# ── LLM ────────────────────────────────────────────
LLM_PROVIDER=ollama
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=qwen3.5:4b
OLLAMA_KEEP_ALIVE=30m          # tránh cold load 110s
LLM_TEMPERATURE=0.0            # reproducibility
LLM_NUM_CTX=8192
LLM_NUM_PREDICT=1024
LLM_ENABLE_THINKING=false      # ← think=False, yêu cầu bắt buộc
LLM_MAX_RETRIES=2
LLM_TIMEOUT_S=180

# ── Pipeline ───────────────────────────────────────
PIPELINE_MAX_SENTENCE_ISSUES=12
PIPELINE_MIN_WORDS_TASK1=150
PIPELINE_MIN_WORDS_TASK2=250

# ── Paths ──────────────────────────────────────────
DATA_DIR=data
REPORTS_DIR=data/reports
```

### `enable_thinking = False` được áp ở đâu

Qwen3.5 là **hybrid reasoning model**: mặc định sinh khối `<think>…</think>` trước câu trả lời. Với structured output đã ép schema, khối này chỉ làm tăng latency (~3×) và tăng rủi ro tràn `num_predict`. Ta tắt nó ở **hai lớp phòng vệ**:

1. **Tham số API**: `client.chat(..., think=False)` — cách chính tắc của Ollama ≥ 0.9.
2. **Chat template flag**: `options={"enable_thinking": False}` — dự phòng cho template Qwen đọc biến này.

Cả hai được set trong `OllamaClient.chat()`; ứng dụng phía trên không cần biết.

**Bù cho việc mất reasoning:** schema ép model xuất `justification` (chuỗi lý giải) **trước** trường `band`. Vì decoding là tuần tự, model buộc phải "viết ra lập luận" trước khi chốt điểm — chain-of-thought hiển ngôn thay cho chain-of-thought ngầm, nhưng có cấu trúc và kiểm chứng được.

---

## 3. LLM Abstraction Layer

### 3.1 Interface

```python
class LLMClient(Protocol):
    def chat(
        self,
        messages: list[dict[str, str]],
        response_model: type[BaseModel] | None = None,
        *,
        node: str = "unknown",
        max_tokens: int | None = None,
    ) -> LLMResponse: ...
```

`LLMResponse` gồm: `content` (raw), `parsed` (Pydantic instance hoặc None), `ok`, `error`, `attempts`, `latency_s`, `prompt_tokens`, `completion_tokens`, `model`, `node`.

### 3.2 Structured output

Ollama nhận JSON Schema qua tham số `format`. Ta lấy schema thẳng từ Pydantic:

```python
schema = response_model.model_json_schema()
resp = client.chat(model=..., messages=..., format=schema, think=False, options={...})
```

Đây là **constrained decoding** ở tầng runtime — mạnh hơn nhiều so với "yêu cầu model trả JSON" trong prompt. Nhưng nó **không** đảm bảo *nội dung* hợp lệ (band có thể là 6.3, quote có thể bịa), nên vẫn cần validate và coerce ở tầng ứng dụng.

### 3.3 Retry & repair

```
attempt 1: gửi prompt gốc
  ├ parse ok  → trả về
  └ parse fail → attempt 2: gửi lại + append message:
                  "Your previous output failed validation: {error}.
                   Return ONLY valid JSON matching the schema."
       ├ parse ok  → trả về, ghi attempts=2
       └ parse fail → attempt 3 (tương tự) → nếu vẫn fail: ok=False
```

Không retry vô hạn, không retry với `temperature` cao hơn (phá reproducibility). Node gọi phải tự xử lý `ok=False`.

### 3.4 Value coercion

Sau parse thành công vẫn áp:

| Kiểm tra | Hành động |
| --- | --- |
| `band` ngoài `[1.0, 9.0]` | clamp |
| `band` không phải bội 0.5 | snap về bội 0.5 gần nhất, set `coerced=true` |
| `confidence` ngoài `[0,1]` | clamp |
| `evidence` rỗng | giữ nguyên, nhưng đếm vào `empty_evidence_rate` |

---

## 4. Pipeline Implementation

### 4.1 Preprocess — thuật toán

| Feature | Thuật toán |
| --- | --- |
| `word_count` | `len(re.findall(r"\b[\w'-]+\b", text))` |
| `sentence_count` | split theo `[.!?]+` + lọc mảnh rỗng |
| `paragraph_count` | split theo `\n\s*\n` |
| `type_token_ratio` | `len(set(lower_words)) / len(words)` |
| `repeated_content_words` | đếm word ∉ STOPWORDS, độ dài ≥ 4, tần suất ≥ 3, lấy top 10 |
| `cohesive_devices_found` | đối chiếu với danh sách ~60 discourse marker |

Danh sách stopword và cohesive device nằm trong `src/pipeline/lexicon.py` — dữ liệu, sửa được độc lập.

### 4.2 Aggregation — quy tắc chính xác

```python
# Bước 1: penalty word-count, áp vào ĐÚNG tiêu chí TA/TR
deficit = max(0, (min_words - word_count) / min_words)
penalty = 1.0 if deficit > 0.40 else (0.5 if deficit > 0.15 else 0.0)
ta_band = clamp(ta_raw - penalty, 1.0, 9.0)     # chỉ TA/TR, không đụng CC/LR/GRA

# Bước 2: trung bình rồi làm tròn
raw   = mean([b for b in criteria_bands if b is not None])
final = round_to_half(clamp(raw, 1.0, 9.0))
```

**Penalty áp vào TA/TR, không áp vào overall.** Giám khảo thật hấp thụ lỗi thiếu độ dài vào Task Achievement/Response chứ không trừ riêng ở điểm tổng; trừ ở cả hai nơi là phạt học viên hai lần cho cùng một lỗi. Tương ứng, prompt của TA/TR được dặn hiển ngôn **không** tự trừ điểm vì độ dài (`LENGTH_RULE_SCORED` trong `builders.py`) — nếu không, model trừ một lần và code trừ lần nữa.

`round_to_half` dùng quy tắc IELTS: `.25 → lên .5`, `.75 → lên 1.0`, implement bằng `math.floor(x*2 + 0.5)/2` để tránh banker's rounding của Python (`round(6.25, 1)` không cho `6.5`).

> **Vì sao penalty do code áp:** đây là quy tắc số học tuyệt đối. Giao cho LLM nghĩa là chấp nhận xác suất nó đếm sai từ rồi phạt sai — một lỗi hoàn toàn tránh được.

### 4.3 Quote verification

```python
def normalize(s): 
    # hạ chữ thường, gộp whitespace, chuẩn hoá ' ' " " – — về ASCII
```
Rồi kiểm tra `normalize(quote) in normalize(essay)`. Ngưỡng: exact substring. Không dùng fuzzy match ở P0 — fuzzy sẽ giấu vấn đề thay vì phơi bày nó; ta cần con số `quote_fidelity` trung thực để biết model tệ đến đâu.

---

## 5. Vận hành & hiệu năng

### 5.1 Số đo tham chiếu (GTX 1660 Ti 6GB, qwen3.5:4b Q4)

| Chỉ số | Giá trị đo được |
| --- | --- |
| Cold load model | ~110 s |
| Warm generation | ~46 tok/s, 100% GPU offload |
| Prompt eval | ~0.2 s cho prompt ngắn |
| VRAM chiếm | ~3.3 GB / 6 GB |

### 5.2 Hệ quả vận hành

1. **Bắt buộc warm-up.** `Pipeline.__init__` gọi một request rỗng để nạp model. Không có bước này, bài đầu tiên mất thêm 110s và mọi số đo latency đều vô nghĩa.
2. **`keep_alive=30m`.** Mặc định Ollama unload sau 5 phút → benchmark chạy ngắt quãng sẽ dính cold load giữa chừng.
3. **`num_ctx=8192` là đủ.** Bài Task 2 ~300 từ ≈ 400 token; prompt + rubric ≈ 1200 token; output ≈ 800 token. Còn rất nhiều biên. Tăng `num_ctx` chỉ tốn VRAM vô ích.
4. **Song song hoá 4 criterion không giúp gì trên 1 GPU** — Ollama serialize request trên cùng model. Chỉ có ích khi có nhiều GPU hoặc chấm nhiều bài đồng thời (batching mức bài, không mức node).

---

## 6. Chạy hệ thống

```bash
# Chấm một bài trong dataset
python -m scripts.run_mvp --exam-id T2-001

# Chấm bài của bạn
python -m scripts.run_mvp --task-type task2 \
    --prompt-file my_prompt.txt --essay-file my_essay.txt

# Benchmark toàn dataset (10 bài) + xuất báo cáo
python -m scripts.run_eval --out data/reports

# Benchmark một tập con
python -m scripts.run_eval --filter task2 --limit 3
```

---

## 7. Deployment (P1+)

```text
┌──────────────┐   HTTP    ┌──────────────┐   HTTP    ┌──────────────┐
│  Streamlit   │ ────────► │   FastAPI    │ ────────► │    Ollama    │
│    :8501     │           │    :8000     │           │    :11434    │
└──────────────┘           └──────┬───────┘           └──────────────┘
                                  │
                           ┌──────▼───────┐
                           │  PostgreSQL  │
                           │    :5432     │
                           └──────────────┘
```

Cả bốn service đóng gói bằng `docker compose`. Container Ollama cần `--gpus all` và mount volume model để không pull lại mỗi lần build.

**Endpoint dự kiến:**

| Method | Path | Mô tả |
| --- | --- | --- |
| POST | `/api/v1/evaluate` | Nộp bài, chấm đồng bộ (P1) / trả `job_id` (P2) |
| GET | `/api/v1/evaluations/{id}` | Lấy kết quả |
| GET | `/api/v1/users/{id}/history` | Lịch sử & tiến trình |
| GET | `/health` | Liveness + trạng thái model đã nạp |
| GET | `/metrics` | Telemetry tổng hợp |

---

## 8. Testing Strategy

| Loại | Phạm vi | Ghi chú |
| --- | --- | --- |
| Unit | `round_to_half`, penalty, preprocess features, quote normalize | Thuần xác định — **phải** đạt 100% pass, không flaky |
| Contract | Mọi Pydantic schema round-trip; schema JSON hợp lệ với Ollama | Bắt lỗi schema sớm |
| Golden | 3 bài mẫu × output đã duyệt tay | Chỉ so *cấu trúc* và *khoảng band*, không so từng chữ (LLM output không ổn định tuyệt đối) |
| Regression | Chạy `run_eval` và so `metrics.json` với baseline | Cổng chặn: không cho merge nếu `MAE_overall` tệ đi > 0.15 |
