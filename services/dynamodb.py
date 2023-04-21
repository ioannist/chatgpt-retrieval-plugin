import os
import boto3
from boto3.dynamodb.conditions import Key, Attr
from typing import List
from models.models import QuestionAnswer

dynamodb = boto3.resource('dynamodb', region_name='eu-central-1')
table = dynamodb.Table('stakex-cms')
table_topics = dynamodb.Table('stakex-cms-topics')
table_sources = dynamodb.Table('stakex-cms-sources')

def edit_question_archive(chain: str, question: str, archived: bool):
    table.update_item(
        Key={
            'chain': chain,
            'question': question
        },
        UpdateExpression='SET #archived = :a',
        ConditionExpression='#question = :q',
        ExpressionAttributeValues={
            ':a': archived,
            ':q': question
        },
        ExpressionAttributeNames={
            '#archived': 'archived',
            '#question': 'question'
        },
    )

def edit_question_category(chain: str, question: str, category: str):
    table.update_item(
        Key={
            'chain': chain,
            'question': question
        },
        UpdateExpression='SET #category = :c',
        ConditionExpression='#question = :q',
        ExpressionAttributeValues={
            ':c': category,
            ':q': question
        },
        ExpressionAttributeNames={
            '#category': 'category',
            '#question': 'question'
        }
    )

def edit_question_answer(chain: str, question: str, answer: str):
    table.update_item(
        Key={
            'chain': chain,
            'question': question
        },
        UpdateExpression='SET #answer = :an',
        ConditionExpression='#question = :q',
        ExpressionAttributeValues={
            ':an': answer,
            ':q': question
        },
        ExpressionAttributeNames={
            '#answer': 'answer',
            '#question': 'question'
        }
    )

def scan_topics() -> List[str]:
    response = table_topics.scan()
    return [(t['topicId'], t['topic']) for t in response['Items']]

def query_questions(chain: str) -> List[QuestionAnswer]:
    response = table.query(
        KeyConditionExpression=Key('chain').eq(chain)
    )
    questions_answers: List[QuestionAnswer] = []
    for entry in response['Items']:
        qa = QuestionAnswer(
            chain=entry.get("chain"),
            question=entry.get("question"),
            embedding=entry.get("embedding"),
            archived=entry.get("archived"),
            used=entry.get("used"),
            category=entry.get("category"),
            answer=entry.get("answer")
        )
        questions_answers.append(qa)
    return questions_answers

def get_source_last_line_processed(chain: str, source_id: str) -> int:
    try:
        response = table_sources.get_item(
            Key={'chain': chain, 'sourceId': source_id},
            ProjectionExpression="lastLineProcessed"
            )
    except:
        return 0
    else:
        return int(response['Item']['lastLineProcessed']) if "Item" in response else 0

def edit_source_last_line_processed(chain: str, source_id: str, line: int):
    table_sources.update_item(
        Key={
            'chain': chain,
            'sourceId': source_id
        },
        UpdateExpression='SET lastLineProcessed = :ln',
        ExpressionAttributeValues={
            ':ln': line,
        },
    )

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


def save_question_to_db(chain: str, question: str, embedding: str, topic_id: str):
    table.put_item(Item={
                'chain': chain,
                'question': question,
                'embedding': embedding,
                'topicId': topic_id
            }
        )