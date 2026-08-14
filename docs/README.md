# IELTS-AI-Evaluator — Documentation Hub

Bộ tài liệu thiết kế, kỹ thuật và triển khai cho hệ thống **IELTS-AI-Evaluator (IAE)**.

> **Trạng thái**: MVP P0 đã chạy được end-to-end trên Ollama `qwen3.5:4b` (local, `think=False`).
> **Cập nhật**: 2026-08-15

---

## Cách đọc bộ tài liệu này

| Bạn là ai | Đọc theo thứ tự |
| --- | --- |
| Product / stakeholder | [PRD](00-product/PRD.md) → [Roadmap](04-roadmap/roadmap.md) |
| Engineer mới vào team | [Architecture](01-architecture/system-architecture.md) → [Data Flow](01-architecture/data-flow.md) → [Tech Spec](02-technical/tech-spec.md) |
| Prompt / LLM engineer | [Prompt Engineering Spec](02-technical/prompt-engineering.md) → [Evaluation Protocol](03-evaluation/evaluation-protocol.md) |
| Người chạy benchmark | [Evaluation Protocol](03-evaluation/evaluation-protocol.md) → [Baseline Report](03-evaluation/mvp-baseline-report.md) |

---

## Mục lục

### 00 — Product
- [PRD.md](00-product/PRD.md) — Vấn đề, người dùng, phạm vi, yêu cầu chức năng/phi chức năng, tiêu chí thành công.

### 01 — Architecture
- [system-architecture.md](01-architecture/system-architecture.md) — Kiến trúc phân lớp, component, ranh giới module, quyết định thiết kế.
- [data-flow.md](01-architecture/data-flow.md) — Luồng nghiệp vụ end-to-end, sequence diagram, state machine của một lần chấm.

### 02 — Technical
- [tech-spec.md](02-technical/tech-spec.md) — Tech stack, cấu trúc thư mục, config, LLM client, retry/fallback, deployment.
- [data-schemas.md](02-technical/data-schemas.md) — Pydantic schema, DB schema, JSON contract giữa các tầng.
- [prompt-engineering.md](02-technical/prompt-engineering.md) — Nguyên tắc viết prompt, template chuẩn, rubric anchoring, versioning.

### 03 — Evaluation
- [evaluation-protocol.md](03-evaluation/evaluation-protocol.md) — Dataset, gold label, metrics, quy trình đo, ngưỡng chấp nhận.
- [mvp-baseline-report.md](03-evaluation/mvp-baseline-report.md) — Kết quả đo thực tế của P0 baseline.

### 04 — Roadmap
- [roadmap.md](04-roadmap/roadmap.md) — Lộ trình P0 → P3, hạng mục cải thiện có ưu tiên, exit criteria từng phase.

### 05 — ADR (Architecture Decision Records)
- [adr/0001-local-llm-first.md](adr/0001-local-llm-first.md)
- [adr/0002-drop-langchain-for-mvp.md](adr/0002-drop-langchain-for-mvp.md)
- [adr/0003-deterministic-band-aggregation.md](adr/0003-deterministic-band-aggregation.md)

---

## Quick start

```bash
# 1. Cài dependency
pip install -r requirements.txt

# 2. Kéo model (nếu chưa có)
ollama pull qwen3.5:4b

# 3. Chấm thử 1 bài
python -m scripts.run_mvp --exam-id T2-001

# 4. Chạy benchmark toàn bộ dataset + xuất báo cáo
python -m scripts.run_eval --out data/reports
```
