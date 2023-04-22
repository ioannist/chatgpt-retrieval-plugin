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
    answer: str
    topic_id: str

class EditCategoryRequest(BaseModel):
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


class QueryRequest(BaseModel):
    queries: List[Query]

class AskRequest(BaseModel):
    chain: str
    question: str

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


class TopicsResponse(BaseModel):
    topics: List[QuestionTopic]
