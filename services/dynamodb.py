import os
import boto3
from boto3.dynamodb.conditions import Key, Attr
from typing import List
from models.models import QuestionAnswer

dynamodb = boto3.resource('dynamodb', region_name='eu-central-1')
table = dynamodb.Table('stakex-cms')

def query_questions(chain: str) -> List[QuestionAnswer]:
    response = table.query(
        KeyConditionExpression=Key('chain').eq(chain)
    )
    questions_answers: List[QuestionAnswer] = []
    for entry in response['Items']:
        qa = QuestionAnswer(
            id=entry.get("id"),
            chain=entry.get("chain"),
            question=entry.get("question"),
            embedding=entry.get("embedding"),
            archived=entry.get("archived"),
            used=entry.get("used"),
            category=entry.get("category"),
            answer=entry.get("answer")
        )
        questions_answers.append(qa)
    return qa

def query_question_embeddings(chain: str) -> List[List[float]]:
    response = table.query(
        KeyConditionExpression=Key('chain').eq(chain),
        ProjectionExpression="embedding"
    )
    results: List[List[float]] = []
    for entry in response['Items']:
        embedding = [float(x) for x in entry.get("embedding").split(",")]
        results.append(embedding)
    return results


def save_question_to_db(chain: str, question: str, embedding: str):
    table.put_item(Item={
                'chain': chain,
                'question': question,
                'embedding': embedding
            }
        )