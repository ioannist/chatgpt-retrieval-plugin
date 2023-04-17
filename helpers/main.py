import logging
from chat_utils import ask
from secrets import OPENAI_API_KEY, SUPABASE_URL, SUPABASE_KEY

import os
from typing import List

import psycopg2


from models.models import QuestionAnswer
conn = psycopg2.connect(dbname='public',
                        user="kebqkljyhdacqbrpigql",
                        password=SUPABASE_KEY,
                        host="https://kebqkljyhdacqbrpigql.supabase.co",
                        port=5432)


def query_questions(chain: str) -> List[QuestionAnswer]:
    response = supabase.table('idx_stakex_cms_questions_chain').select('*').execute()
    print("response: ", response)
    questions_answers: List[QuestionAnswer] = []
    for entry in response.data:
        qa = QuestionAnswer(
            id=entry.id,
            chain=entry.chain,
            question=entry.question,
            embedding=entry.embedding,
            archived=entry.archived,
            used=entry.used,
            category=entry.category,
            answer=entry.answer
        )
        questions_answers.append(qa)
    return questions_answers

#if __name__ == "__main__":
    
    #while True:
    #    user_query = input("Enter your question: ")
    #    openai.api_key = OPENAI_API_KEY
    #    logging.basicConfig(level=logging.WARNING,
    #                        format="%(asctime)s %(levelname)s %(message)s")
    #    print(ask(user_query))