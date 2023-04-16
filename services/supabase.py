import os
from supabase import create_client, Client, APIResponse
from typing import List

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

def query_question_embeddings(chain: str) -> List[List[float]]:
    response: APIResponse = supabase.table('idx_stakex_cms_questions_chain').select('embedding').eq('chain', chain).execute()
    results: List[List[float]] = []
    for entry in response.data:
        if entry.embedding == None or entry.embedding == "":
            continue
        embedding = [float(x) for x in entry.embedding.split(",")]
        results.append(embedding)
    return results


def save_question_to_db(chain: str, question: str, embedding: str):
    data = supabase.table("stakex_cms_questions").insert({
        "chain": chain,
        "question": question,
        "embedding": embedding
        }).execute()
    assert len(data.data) > 0