from services.openai import get_chat_completion
import json
from typing import Dict

def extract_questions_from_text(text: str, question_count: int = 3) -> Dict[str, str]:
    if len(text) < 50:
        return []
    
    messages = [
        {
            "role": "system",
            "content": f"""
            Given some text from a user, try to come up with the top {question_count} questions that this text answers.
            Questions must be succinct. Do not include people or user names in the questions.
            Respond with a line-separated list of the questions.
            """,
        },
        {"role": "user", "content": text},
    ]

    completion = get_chat_completion(
        messages, "gpt-3.5-turbo"
    )  # TODO: change to your preferred model name

    print(f"completion: {completion}")

    try:
        questions = [q.lstrip('0123456789.- ') for q in completion.splitlines()]
        questions = list(filter(lambda i: len(i) > 7, questions))
    except:
        questions = []

    return questions

