from services.openai import get_chat_completion
import json
from typing import Dict, List

def extract_topic_id(text: str, topic_names: List[str], topic_ids: List[str]) -> str:
    messages = [
        {
            "role": "system",
            "content": f"""
            Given a comma-separated list of topics: {','.join(topic_names)}.
            Reply back only with the topic that best matches the provided question:
            """,
        },
        {"role": "user", "content": f"\"{text}\""},
    ]
    completion = get_chat_completion(
        messages, "gpt-3.5-turbo"
    )
    completion = completion.lower().strip().strip('\"').strip('.')
    for i, topic in enumerate(topic_names):
        if topic.lower() in completion:
            return topic_ids[i]
    return 'other'

def standardize_question(text: str) -> str:
    messages = [
        {
            "role": "system",
            "content": """
            Remove any usernames, people names, or people nick names from the question, if any.
            Rephrase the question to be in the first person point of view, if possible.
            Reply back with only the rephrased quesiton and do not comment on anything.
            """,
        },
        {"role": "user", "content": f"Question: {text}"},
    ]
    completion = get_chat_completion(
        messages, "gpt-3.5-turbo"
    )
    return completion

def extract_questions_from_text(text: str, question_count: int = 3) -> List[str]:
    if len(text) < 50:
        return []
    
    messages = [
        {
            "role": "system",
            "content": f"""
            Given some text from a user, try to come up with the top {question_count} questions that this text answers.
            Questions must be succinct and only one sentence.
            Respond with a line-separated list of the questions.
            """,
        },
        {"role": "user", "content": {f"Text: {text}"}},
    ]

    completion = get_chat_completion(
        messages, "gpt-3.5-turbo"
    )  # TODO: change to your preferred model name

    print(f"completion: {completion}")

    try:
        questions = [q.lstrip('0123456789.-) ') for q in completion.splitlines()]
        questions = list(filter(lambda i: len(i) > 7, questions))
    except:
        questions = []

    return questions

