# ADR-0002: Không dùng LangChain ở P0

**Trạng thái:** Accepted · 2026-08-15

## Bối cảnh

Code hiện có (`src/llm/prompts/writing_task_2/lexical_resources/*.py`) dùng `ChatPromptTemplate` và `PydanticOutputParser` của LangChain. Khi dựng lại môi trường phát hiện:

- Môi trường chạy Python 3.14.3; hệ sinh thái LangChain chưa ổn định trên phiên bản này.
- `ollama` SDK chính thức đã hỗ trợ **native**: `format=<json_schema>` (constrained decoding) và `think=False`.
- `PydanticOutputParser` hoạt động bằng cách nhét mô tả schema vào prompt rồi parse text đầu ra — **yếu hơn** constrained decoding ở tầng runtime của Ollama.

## Quyết định

P0 gọi thẳng `ollama` SDK qua một lớp adapter mỏng `OllamaClient` implement `LLMClient` Protocol. Không dùng LangChain.

## Lý do

1. **Thứ LangChain cung cấp mà ta cần, Ollama đã cung cấp tốt hơn.** Structured output ép ở tầng decoding chặt hơn ép ở tầng prompt.
2. **Orchestration của ta là 6 bước tuyến tính.** LCEL giải quyết bài toán compose phức tạp; ta không có bài toán đó. Thêm một tầng trừu tượng chỉ để nối 6 hàm là thêm một tầng phải debug.
3. **Telemetry ta cần rất cụ thể** (attempts, quote fidelity, token/node). Tự viết ~80 dòng và kiểm soát hoàn toàn, thay vì uốn callback system của LangChain.
4. **Ít dependency = ít vỡ.** Đồ án phải chạy được trên máy người chấm.

## Hệ quả

**Tích cực:** dependency tối thiểu (`ollama`, `pydantic`, `pydantic-settings`); đường đi từ prompt tới HTTP request nhìn thấy được toàn bộ; telemetry đúng nhu cầu.

**Tiêu cực:** tự viết retry/parse/telemetry; không có LangSmith tracing; nếu sau này cần agent/tool-calling phức tạp có thể phải viết lại.

**Đường lùi:** vì mọi thứ đi qua `LLMClient` Protocol, thêm một `LangChainClient` sau này là thêm một file — pipeline không đổi.

## Việc phải làm

Các prompt LangChain cũ trong `src/llm/prompts/writing_task_2/lexical_resources/` được giữ lại làm tham chiếu lịch sử nhưng **không nằm trong pipeline P0**. Nội dung có giá trị của chúng (phân loại L1/L2/L3, cách phân tích collocation) đã được chuyển vào rubric LR và prompt criterion mới.
