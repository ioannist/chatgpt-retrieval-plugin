import os
import boto3
from boto3.dynamodb.conditions import Key, Attr
from typing import List
from models.models import QuestionAnswer, QuestionTopic

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

def edit_question_topic_id(chain: str, question: str, topic_id: str):
    table.update_item(
        Key={
            'chain': chain,
            'question': question
        },
        UpdateExpression='SET #topicId = :c',
        ConditionExpression='#question = :q',
        ExpressionAttributeValues={
            ':c': topic_id,
            ':q': question
        },
        ExpressionAttributeNames={
            '#topicId': 'topicId',
            '#question': 'question'
        }
    )

def edit_question_edited(chain: str, question: str, question_edited: str):
    table.update_item(
        Key={
            'chain': chain,
            'question': question
        },
        UpdateExpression='SET #questionEdited = :qe',
        ConditionExpression='#question = :q',
        ExpressionAttributeValues={
            ':qe': question_edited,
            ':q': question
        },
        ExpressionAttributeNames={
            '#questionEdited': 'questionEdited',
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

def scan_topics() -> List[QuestionTopic]:
    response = table_topics.scan()
    print(response)
    data = response['Items']
    while 'LastEvaluatedKey' in response:
        response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
        data.extend(response['Items'])
    print(data)
    return [QuestionTopic(topic_id=t['topicId'], topic=t['topic']) for t in data]

def query_questions(chain: str) -> List[QuestionAnswer]:
    questions_answers: List[QuestionAnswer] = []

    pagination_config = {
        'PageSize': 100,  # Adjust the page size as per your requirement
    }

    while True:
        response = table.query(
            KeyConditionExpression=Key('chain').eq(chain),
            ProjectionExpression="chain,question,archived,used,topicId,answer",
            PaginationConfig=pagination_config
        )

        for entry in response.get('Items', []):
            qa = QuestionAnswer(
                chain=entry.get("chain"),
                question=entry.get("question"),
                # embedding=entry.get("embedding"),
                archived=entry.get("archived"),
                used=entry.get("used"),
                topic_id=entry.get("topicId"),
                answer=entry.get("answer")
            )
            questions_answers.append(qa)

        if 'LastEvaluatedKey' in response:
            pagination_config['ExclusiveStartKey'] = response['LastEvaluatedKey']
        else:
            break

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