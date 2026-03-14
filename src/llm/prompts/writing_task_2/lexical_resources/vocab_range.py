from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field

class SummaryDetail(BaseModel):
    strengths: str = Field(description="list vocab Strengths")
    weaknesses: str = Field(description="list vocab weaknesses and revise them")

class OutputVocabRange(BaseModel):
    vocab_table_analysis: str = Field(description="Markdown table of vocabulary analysis")
    summary: SummaryDetail = Field(description="Structured summary of lexical performance")

vocab_range_parser = PydanticOutputParser(pydantic_object=OutputVocabRange)

# Tối ưu lại cấu trúc Instructions
instructions = """
You are a Senior IELTS Examiner specializing in 'Lexical Resource'. 
Your goal is to evaluate the student's essay based on range, precision, and collocation naturalness.

### CRITERIA FOR ANALYSIS:
1. **L1 (Basic)**: Common words, functional language.
2. **L2 (Less Common)**: Academic or topic-specific terms (Band 7+ level).
3. **L3 (Rare/Sophisticated)**: Precise, nuanced, or idiomatic expressions (Band 8+ level).

### TASK REQUIREMENTS:
Step 1 :  Populate 'vocab_table_analysis' with a Markdown table. 
            +  The table must include: Term, Category (Academic/Collocation/Phrasal Verb), Naturalness, Frequency Level (L1/L2/L3), and Brief Feedback.
            + Example a table's format : | Highlighted Term | Category | Naturalness | Frequency Level | Feedback |
                                         | [financial resources] | [Academic/Collocation] | Natural | L2 | Accurate usage in the context of funding. |
Step 2 : Populate 'summary' with two sections: 
    - **Strengths**: Describe successful use of topic-related clusters and high-level collocations.
    - **Weaknesses**: Identify repetitive words or unnatural collocations (Format: ❌ [Error] → ✅ [Correction]).

{format_instructions}

### STUDENT ESSAY:
{essay}
"""

vocab_range_prompt = ChatPromptTemplate.from_template(instructions)
