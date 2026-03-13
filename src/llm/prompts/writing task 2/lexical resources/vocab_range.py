from langchain_core.prompts import ChatPromptTemplate

instructions = """
### IELTS Task 2: Vocabulary Range Analysis Prompt

**Role**: Senior IELTS Examiner (Expert in Lexical Resource).
**Task**: Perform a deep-dive analysis of Vocabulary Range, Topic-Specific terms, Collocations, and Phrasal Verbs for the provided IELTS Task 2 essay.

**Instructions**:

1. **Analyze** the text for academic precision and thematic relevance.
2. **Generate** a Markdown table for key terms.
3. **Summarize** overall Lexical Resource performance with specific "Strengths" and "Weaknesses".
4. **Efficiency**: Use concise language. In the table, use "L1" (Common), "L2" (Less Common), "L3" (Rare/Advanced) for Frequency Level to save tokens.

**Output Structure**:

### 1. Vocabulary Analysis Table

| Highlighted Term | Category | Naturalness | Frequency Level | Feedback |
| --- | --- | --- | --- | --- |
| [Example: financial resources] | [Academic/Collocation] | Natural | L2 | Accurate usage in the context of funding. |

### 2. Summary of Topic-Specific & Academic Vocabulary Use

* **Strengths**:
* [Point 1: Describe successful use of topic-related clusters]
* [Point 2: Note effective use of high-level collocations]


* **Weaknesses**:
* [Point 1: Identify repetitive words or generic language]
* [Point 2: List unnatural collocations using the format: ❌ [Error] → ✅ [Correction]]

{format_instructions}

JSON format. 
{
"Vocabulary Analysis Table" : "",
"vocab range Summary" : ""
}


**Student Essay**:
{essay}

"""

vocab_range_prompt = ChatPromptTemplate.from_template(instructions)