from models.models import (
    Document,
    DocumentMetadataFilter,
    Query,
    QueryResult,
)
from pydantic import BaseModel
from typing import List, Optional
from models import QuestionAnswer

class UpsertRequest(BaseModel):
    documents: List[Document]


class UpsertResponse(BaseModel):
    ids: List[str]

class AskResponse(BaseModel):
    answer: str


class QueryRequest(BaseModel):
    queries: List[Query]

class AskRequest(BaseModel):
    query: Query


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
