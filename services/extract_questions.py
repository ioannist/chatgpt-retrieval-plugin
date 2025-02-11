from services.openai import get_chat_completion
import json
from typing import Dict, List

def extract_topic_id(text: str, topic_names: List[str], topic_ids: List[str]) -> str:
    messages = [
        {
            "role": "user",
            "content": f"""
            Given a comma-separated list of topics: {','.join(topic_names)}.
            Reply back only with the topic that best matches the provided question:
            """,
        },
        {"role": "user", "content": f"\"{text}\""},
    ]
    completion = get_chat_completion(
        messages, "gpt-4"
    )
    completion = completion.lower().strip().strip('\"').strip('.')
    for i, topic in enumerate(topic_names):
        if topic.lower() in completion:
            return topic_ids[i]
    return 'other'

def standardize_question(text: str) -> str:
    messages = [
        {
            "role": "user",
            "content": """
            Remove any usernames, people names, or people nick names from the question, if any.
            Reply back with only the modified question and do not comment on anything.
            """,
        },
        {"role": "user", "content": f"Question: {text}"},
    ]
    completion = get_chat_completion(
        messages, "gpt-3.5-turbo"
    )
    return completion

def extract_questions_from_text(text: str, question_count: int = 3) -> List[str]:
    messages = [
        {
            "role": "user",
            "content": f"""
            Given some text from a user, try to come up with {question_count} FAQ-type questions that this text answers.
            Questions must be succinct and only one sentence. Do not ask "who" questions. Do not ask questions about users.
            Respond with a line-separated list of the questions.
            """,
        },
        {"role": "user", "content": text},
    ]

    completion = get_chat_completion(
        messages, "gpt-4"
    )  # TODO: change to your preferred model name

    print(f"completion: {completion}")

    try:
        questions = [q.lstrip('0123456789.-) ').replace("Question: ", "", 1) for q in completion.splitlines()]
        questions = list(filter(lambda i: len(i) > 7, questions))
    except:
        questions = []

    return questions

