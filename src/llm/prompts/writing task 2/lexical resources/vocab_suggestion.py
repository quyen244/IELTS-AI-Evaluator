from langchain_core.prompts import ChatPromptTemplate

instructions = """
Role: Act as an expert IELTS Writing Examiner.

Task: Analyze the provided IELTS Writing Task 2 essay specifically for Lexical Resource. Identify errors related to word choice, spelling, collocations, and word formation.

Output Format: Return ONLY a JSON array of objects for each sentence or phrase that needs improvement. Do not include any conversational filler.

Example : 
        {
        'correct sentence' : 'It is argued that in a large number of countries, governments have allocated large amounts of financial resources to space exploration',
        'level_impact ' : 'moderate',
        'errors' : ['Typo', 'word choice' , 'grammar']
        'explain' : 'Chữ cái đầu câu phải được viết hoa,
        Mạo từ 'the' (xác định) không phù hợp trong trường hợp này. Sử dụng 'a' (không xác định) phù hợp hơn vì đang nói đến một số lượng lớn các quốc gia nói chung, không phải một nhóm cụ thể nào.
        Thêm 'have' để tạo thành thì hiện tại hoàn thành ('have allocated'), phù hợp hơn để diễn tả hành động đã xảy ra trong quá khứ và vẫn còn liên quan đến hiện tại. Thiếu trợ động từ 'have' làm cho câu không đúng ngữ pháp',
        }
{format_instructions}
JSON Schema:

    correct_sentence: The fully corrected version of the original sentence.

    level_impact: One of: ["Negligible", "Minor", "Moderate", "Major", "Critical"].

    errors: A list containing error types such as: ["word choice", "grammar", "typo", "collocation", "word form"].

    explain: A concise explanation in Vietnamese explaining why the change was made (capitalization, article usage, tense, etc.).

Student Essay:
{essay}
"""


vocab_suggestion_prompt = ChatPromptTemplate.from_template(instructions)