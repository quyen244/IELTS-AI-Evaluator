<p align="center">
  <a href="https://www.uit.edu.vn/" title="University of Information Technology" style="border: none;">
    <img src="https://i.imgur.com/WmMnSRt.png" alt="University of Information Technology (UIT)">
  </a>
</p>


<h1 align="center"><b>IELTS-AI-Evaluator (IAE)</b></h1>

# **Personal Project: IELTS-AI-Evaluator (IAE)**

> **IELTS-AI-Evaluator** là một hệ thống hỗ trợ giáo dục thông minh, sử dụng Large Language Models (LLMs) để tự động chấm điểm và nhận xét chi tiết các bài viết IELTS Writing Task 1 và Task 2. Hệ thống mô phỏng quy trình chấm điểm của giám khảo thực thụ dựa trên 4 tiêu chí chính thức (TR/TA, CC, LR, GRA), giúp thí sinh tối ưu hóa điểm số thông qua các đề xuất chỉnh sửa lỗi từ vựng, ngữ pháp và cấu trúc bài viết ngay lập tức.

<p align="center">
  <img src="thumbnail.png" width="600" alt="thumbnail">
</p>


**Technical Highlights (P0 — MVP đã chạy được):**

* **LLM cục bộ:** **Ollama + `qwen3.5:4b`**, `think=False`, structured output ép bằng JSON Schema. Chạy offline, không cần API key, chi phí biến đổi bằng 0.
* **Pipeline 6 bước:** preprocess xác định → 4 criterion evaluator (TA/TR, CC, LR, GRA) có rubric anchoring → sentence corrector → aggregation xác định → feedback synthesizer tiếng Việt.
* **LLM cho phán đoán, code cho số học:** đếm từ, TTR, trung bình, làm tròn band, length penalty, kiểm chứng trích dẫn — tất cả bằng code.
* **Đo lường tích hợp:** eval harness với gold-label dataset, 8 metric chất lượng + 12 metric hệ thống, `quote_fidelity` phát hiện feedback bịa đặt.
* **Provider-agnostic:** mọi thứ đi qua `LLMClient` Protocol — thêm OpenAI/Gemini là thêm một adapter, pipeline không đổi.
* **Demo API + CI/CD:** FastAPI wrapper (`src/backend/app.py`), Docker, CloudFormation cho EC2 GPU, GitHub Actions (test tự động + deploy thủ công) — xem [aws-deployment.md](docs/05-deployment/aws-deployment.md).

> 📖 **Toàn bộ PRD, kiến trúc, luồng hệ thống, technical spec, evaluation protocol và roadmap P0→P3 nằm trong [`docs/`](docs/README.md).**

### Chạy thử (local, CLI)

```bash
pip install -r requirements.txt
ollama pull qwen3.5:4b

python -m scripts.run_mvp --exam-id T2-001      # chấm 1 bài
python -m scripts.run_eval --out data/reports   # benchmark 10 bài + báo cáo
python -m pytest tests/ -q                      # 58 test (deterministic + API, không cần GPU)
```

### Chạy thử (Docker, local API)

```bash
docker compose up --build          # cần NVIDIA Container Toolkit cho GPU passthrough
curl http://localhost:8000/health
curl -X POST http://localhost:8000/evaluate/T2-002
```

### Deploy lên AWS

Xem [docs/05-deployment/aws-deployment.md](docs/05-deployment/aws-deployment.md) — **đọc mục chi phí trước**, template khởi tạo EC2 GPU tính phí theo giờ.

---

## **Team Information**

| No. | Student ID | Full Name | Role | Github | Email |
| --- | --- | --- | --- | --- | --- |
| 1 | 23521329 | Nguyen Van Quyen | Developer | [quyen244](https://github.com/quyen244) | 23521329@gm.uit.edu.vn |

---

## **Table of Contents**

* [Overview](https://www.google.com/search?q=%23overview)
* [System Architecture](https://www.google.com/search?q=%23system-architecture)
* [Evaluation Methodology](https://www.google.com/search?q=%23evaluation-methodology)
* [Tech Stack](https://www.google.com/search?q=%23tech-stack)
* [Database Schema](https://www.google.com/search?q=%23database-schema)
* [Features](https://www.google.com/search?q=%23features)
* [Installation & Usage](https://www.google.com/search?q=%23installation--usage)
* [API Documentation](https://www.google.com/search?q=%23api-documentation)

---

## **Overview**

### **Problem Statement**

Việc luyện viết IELTS thường gặp khó khăn do chi phí thuê giáo viên chấm bài cao và thời gian phản hồi chậm. Thí sinh thường không biết rõ bài viết của mình đang ở mức Band nào và cần cải thiện cụ thể ở những lỗi sai nào về từ vựng hay cấu trúc câu.

### **Solution**

**IAE** cung cấp một giải pháp chấm bài tự động với độ chính xác cao:

1. **Scoring:** Dự đoán điểm Band cho từng tiêu chí và điểm Overall.
2. **Lexical Resource Analysis:** Phân tích độ đa dạng từ vựng, collocations và synonyms.
3. **Grammar Correction:** Phát hiện lỗi ngữ pháp, lỗi chính tả và gợi ý câu viết lại tốt hơn.
4. **Actionable Feedback:** Đưa ra lời khuyên cụ thể để nâng Band dựa trên điểm yếu hiện tại.

---

## **System Architecture**

```text
┌─────────────────────────────────────────────────────────────┐
│                   User Interface Layer                      │
│            (Streamlit Dashboard / Web Client)               │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                  API Layer (FastAPI)                        │
│  - Task Identification (Task 1 vs Task 2)                   │
│  - Evaluation Orchestrator                                  │
│  - Data Persistence (PostgreSQL)                            │
└────────────────────┬──────────────────────────────────────┬─┘
                     │                                      │
    ┌────────────────▼──────────────┐      ┌────────────────▼──────────────┐
    │      LLM Evaluation Engine    │      │        Database Layer        │
    │  - Prompt Engineering         │      │  - User Essays & Band Scores │
    │  - Multi-agent Scoring (LR,GR)│      │  - Detailed Feedback Storage │
    └────────────────┬──────────────┘      └────────────────┬──────────────┘
                     │                                      │
    ┌────────────────▼──────────────────────────────────────▼──────────────┐
    │                    Utilities & Scoring Logic                         │
    └──────────────────────────────────────────────────────────────────────┘

```

---

## **Evaluation Methodology**

Hệ thống đánh giá bài viết dựa trên khung tiêu chí chuẩn của IELTS:

* **Task Response (Task 2) / Task Achievement (Task 1):** Đánh giá việc trả lời đầy đủ yêu cầu đề bài.
* **Coherence and Cohesion:** Đánh giá tính mạch lạc và khả năng sử dụng các từ nối.
* **Lexical Resource:** Phân tích vốn từ vựng, độ tự nhiên và lỗi dùng từ (JSON Output).
* **Grammatical Range and Accuracy:** Kiểm tra tính chính xác và sự đa dạng của các cấu trúc câu phức.

---

## **Tech Stack**

| Category | P0 (đã build) | P1+ (kế hoạch) |
| --- | --- | --- |
| **LLM runtime** | Ollama (local) | + OpenAI / Gemini adapter |
| **AI Model** | `qwen3.5:4b` (Q4, 3.3GB) | + `qwen3.5:8b`, cloud models |
| **Orchestration** | Ollama SDK + Pydantic ([tại sao không LangChain](docs/adr/0002-drop-langchain-for-mvp.md)) | — |
| **Schema / Validation** | Pydantic v2, pydantic-settings | idem |
| **Backend** | CLI | FastAPI, Uvicorn |
| **Frontend** | CLI | Streamlit |
| **Database** | JSON file | PostgreSQL + SQLAlchemy |
| **Test** | pytest (41 test) | + golden-file, regression gate |

---

## **Features**

* ✅ **Automated Scoring**: Chấm điểm tức thì từ Band 1.0 đến 9.0.
* ✅ **Detailed Lexical Feedback**: Xuất báo cáo JSON chi tiết về từ vựng (Correct sentence, impact level, error types).
* ✅ **Synonym Suggestions**: Gợi ý các từ đồng nghĩa nâng cao để tăng điểm Lexical Resource.
* ✅ **Support Task 1 & 2**: Nhận diện và chấm điểm riêng biệt cho từng loại bài viết (Report & Essay).
* ✅ **History Tracking**: Lưu trữ lịch sử bài viết để theo dõi sự tiến bộ theo thời gian sản.

---

## **Database Schema**

### **Essays Table**

Lưu trữ thông tin bài viết của thí sinh:

* `id`: Định danh duy nhất.
* `task_type`: Task 1 hoặc Task 2.
* `prompt`: Đề bài.
* `content`: Nội dung bài viết.
* `overall_band`: Điểm tổng kết.

### **Evaluation_Details Table**

Lưu trữ nhận xét chi tiết:

* `essay_id`: Foreign key liên kết với bảng Essays.
* `criterion`: Tên tiêu chí (LR, GRA, CC, TR).
* `score`: Điểm cho tiêu chí đó.
* `feedback_json`: Dữ liệu JSON chi tiết về các lỗi và gợi ý sửa đổi.

---

## **Installation & Usage**

### **1. Setup Environment**

```bash
git clone https://github.com/quyen244/IELTS-AI-Evaluator.git
cd IELTS-AI-Evaluator
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

```

### **2. Environment Variables**

Tạo file `.env` và thêm các khóa sau:

```env
GOOGLE_API_KEY=your_gemini_key_here
OPENAI_API_KEY=your_openai_key_here
DATABASE_URL=postgresql://user:password@localhost/dbname

```

### **3. Run Application**

```bash
# Start Backend
python -m uvicorn src.api.main:app --reload

# Start Frontend
streamlit run src/frontend/app.py

```

---

## **Contact**

* **Developer**: Nguyen Van Quyen
* **Github**: [@quyen244](https://github.com/quyen244)
* **Email**: 23521329@gm.uit.edu.vn

**Last Updated**: March 2026
**Status**: 🚀 In Progress

---
