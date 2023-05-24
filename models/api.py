from models.models import (
    Document,
    DocumentMetadataFilter,
    Query,
    QueryResult,
)
from pydantic import BaseModel
from typing import List, Optional
from models.models import QuestionAnswer, QuestionTopic


class AnswerRequest(BaseModel):
    chain: str
    question: str
    question_edited: str
    answer: str
    topic_id: str

class EditTopicRequest(BaseModel):
    chain: str
    question: str
    topic_id: str

class EditArchiveRequest(BaseModel):
    chain: str
    question: str
    archived: bool

class UpsertRequest(BaseModel):
    documents: List[Document]

class UpsertResponse(BaseModel):
    ids: List[str]

class AskResponse(BaseModel):
    answer: str
    request_id: str

class QueryRequest(BaseModel):
    queries: List[Query]

class AskRequest(BaseModel):
    chain: str
    question: str
    request_id: Optional[str]

class QueryResponse(BaseModel):
    results: List[QueryResult]

class DeleteRequest(BaseModel):
    ids: Optional[List[str]] = None
    filter: Optional[DocumentMetadataFilter] = None
    delete_all: Optional[bool] = False


class DeleteResponse(BaseModel):
    success: bool

class QAResponse(BaseModel):
    qas: List[QuestionAnswer]
    last_evaluated_key: Optional[str] = None


class TopicsResponse(BaseModel):
    topics: List[QuestionTopic]
