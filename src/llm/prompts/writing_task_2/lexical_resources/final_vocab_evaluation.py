


instructions = """


### IELTS Task 2: Lexical Resource Final Summary Prompt (JSON)

**Role**: Senior IELTS Examiner.
**Task**: Provide a final, comprehensive evaluation of the student's Lexical Resource in JSON format.

**Instructions**:

1. **Synthesize**: Use the previous analyses (Synonyms, Word Forms, Range) to create this summary.
2. **Band Scale (Vietnamese)**: Categorize the student's performance from Band 4 to 8 using these exact descriptors:
* **4**: Hạn chế và chưa đủ, lặp từ thường xuyên, không paraphrase.
* **5**: Đủ dùng nhưng còn hạn chế, hay lặp từ, lỗi chính tả/word form gây khó hiểu.
* **6**: Đủ để truyền đạt ý nghĩa, có cố gắng dùng từ ít phổ biến nhưng còn sai sót.
* **7**: Vốn từ rộng, sử dụng linh hoạt các cụm từ ít phổ biến (less common), có sự chính xác cao.
* **8**: Vốn từ phong phú, sử dụng linh hoạt và chính xác các thuật ngữ chuyên sâu, tự nhiên.


3. **Constraint**: Return **ONLY** a valid JSON object. No prose, no intro/outro.

**JSON Schema**:

```json
{
  "overall_evaluation": {
    "strengths": ["String 1", "String 2"],
    "weaknesses": ["String 1", "String 2"]
  },
  "final_vocabulary_range_assessment": {
    "category": "Band [X]: [Vietnamese Descriptor from instructions]",
    "justification": "Detailed explanation in English of why this band was awarded.",
    "recommendations_for_improvement": ["Specific action 1", "Specific action 2"]
  }
}

```

**Student Essay**:
{essay}

"""