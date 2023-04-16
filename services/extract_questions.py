from services.openai import get_chat_completion
import json
from typing import Dict

def extract_questions_from_text(text: str, question_count: int = 3) -> Dict[str, str]:
    messages = [
        {
            "role": "system",
            "content": f"""
            Given some text from a user, try to come up with the top {question_count} questions that this text answers.
            Respond with a JSON of an array containing the questions.
            """,
        },
        {"role": "user", "content": text},
    ]

    completion = get_chat_completion(
        messages, "gpt-3.5-turbo"
    )  # TODO: change to your preferred model name

    print(f"completion: {completion}")

    try:
        questions = json.loads(completion)
    except:
        questions = []

    return questions

