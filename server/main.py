import os
from typing import Optional
import uvicorn
from fastapi import FastAPI, File, Form, HTTPException, Depends, Body, UploadFile
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from uuid import uuid4

from models.api import (
    DeleteRequest,
    DeleteResponse,
    QueryRequest,
    QueryResponse,
    UpsertRequest,
    UpsertResponse,
    AskResponse,
    AskRequest,
    QAResponse,
    AnswerRequest,
    EditTopicRequest,
    EditArchiveRequest,
    Query,
    TopicsResponse
)
from datastore.factory import get_datastore
from services.file import get_document_from_file
from services.openai import ask_with_chunks
from services.dynamodb import get_question, scan_topics, query_questions, edit_question_answer,edit_question_edited, edit_question_archive, edit_question_topic_id

from models.models import DocumentMetadata, Source

bearer_scheme = HTTPBearer()
BEARER_TOKEN = os.environ.get("BEARER_TOKEN")
assert BEARER_TOKEN is not None
message_requests = {}

def validate_token(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    if credentials.scheme != "Bearer" or credentials.credentials != BEARER_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid or missing token")
    return credentials


app = FastAPI(dependencies=[Depends(validate_token)])
app.mount("/.well-known", StaticFiles(directory=".well-known"), name="static")
origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create a sub-application, in order to access just the query endpoint in an OpenAPI schema, found at http://0.0.0.0:8000/sub/openapi.json when the app is running locally
sub_app = FastAPI(
    title="Retrieval Plugin API",
    description="A retrieval API for querying and filtering documents based on natural language queries and metadata",
    version="1.0.0",
    servers=[{"url": "https://your-app-url.com"}],
    dependencies=[Depends(validate_token)],
)
app.mount("/sub", sub_app)

@app.post(
        "/questions/archive-edit",
        description='Change the archive status of a question. Admin can archive questions they want to ignore.'
        )
async def archive_question(
    request: EditArchiveRequest = Body(...)
):
    try:
        edit_question_archive(
            chain=request.chain,
            question=request.question,
            archived=request.archived
        )
    except Exception as e:
        print("Error:", e)
        raise HTTPException(status_code=500, detail=f"str({e})")


@app.post(
        "/questions/answer",
        description='Answer a question, i.e. save the answer text to the database. You must also provide a topic id, and the edited question.'
        )
async def answer_question(
    request: AnswerRequest = Body(...),
):
    if request.chain == '' or request.question == '':
        raise HTTPException(status_code=400, detail="Invalid chain or question input")
    if request.answer == '' or request.question_edited == '':
        raise HTTPException(status_code=400, detail="Invalid answer or question_edited input")
    try:
        edit_question_answer(
            chain=request.chain,
            question=request.question,
            answer=request.answer
        )
        edit_question_edited(
            chain=request.chain,
            question=request.question,
            question_edited=request.question_edited
        )
        edit_question_topic_id(
            chain=request.chain,
            question=request.question,
            topic_id=request.topic_id
        )
    except Exception as e:
        print("Error:", e)
        raise HTTPException(status_code=500, detail=f"str({e})")
    
@app.post(
        "/questions/topic-edit",
        description='Change the topic id of a question-answer. A QA can have only one topic/topic id.'
        )
async def answer_question(
    request: EditTopicRequest = Body(...),
):
    try:
        edit_question_topic_id(
            chain=request.chain,
            question=request.question,
            topic_id=request.topic_id
        )
    except Exception as e:
        print("Error:", e)
        raise HTTPException(status_code=500, detail=f"str({e})")


@app.get(
    "/questions/qas",
    description='Fetch all questions & answers (even archived ones) for a particular chain'
)
async def get_qas(
    chain: str,
    paginate: bool| None = None,
    key: str | None = None,
):
    try:
        qas, last_evaluated_key = query_questions(chain, paginate, key);
        # print(qas, last_evaluated_key)
        return QAResponse(
            qas=qas,
            last_evaluated_key=last_evaluated_key
        )
    except Exception as e:
        print("Error:", e)
        raise HTTPException(status_code=500, detail=f"str({e})")

@app.get(
    "/questions/qa",
    description='Fetch a question by chain and question/slug.'
)
async def get_qa(
    chain: str,
    question: str
):
    try:
        qa = get_question(
            chain=chain,
            question=question
        );
        return QAResponse(
            qas=[qa]
        )
    except Exception as e:
        print("Error:", e)
        raise HTTPException(status_code=500, detail=f"str({e})")

@app.get(
    "/questions/topics",
    description='Fetch all topics. Topics are global for all chains. Every question must be assigned a topic id by admin.'
)
async def get_topics():
    try:
        topics = scan_topics();
        return TopicsResponse(
            topics=topics
        )
    except Exception as e:
        print("Error:", e)
        raise HTTPException(status_code=500, detail=f"str({e})")


@app.post(
    "/gpt/ask",
    response_model=AskResponse,
    description="""
    Ask GPT a question about a particular chain. The app will search its internal knowledge base for answers,
    forward the most relevant content to Chatgpt, and reply back to the client with an answer and a request id.
    Optionally, you can include the request id of a previous answer and ask Chatgpt to edit it, expand on a topic,
    fix mistakes, etc. Note that, due to an internal token limit, this cannot go on forever.
    """
)
async def ask_question(
    request: AskRequest = Body(...)
):
    try:
        print('Getting chunks')
        query_results = await datastore.query(queries=[Query(query=request.question)], chain=request.chain)
        chunks = [result.text for result in query_results[0].results]

        print('Getting answer from chatgpt')
        question = f"This is a question regarding {request.chain}.\n{request.question}"
        request_id = request.request_id if request.request_id is not None and request.request_id != '' else uuid4().hex
        prev_messages = message_requests.get(request.request_id, [])
        print(f"Using {len(prev_messages)} previous messages")
        (answer, messages) = ask_with_chunks(question=question, chunks=chunks, prev_messages=prev_messages)
        message_requests[request_id] = messages
        return AskResponse(answer=answer, request_id=request_id)
    except Exception as e:
        print("Error:", e)
        raise HTTPException(status_code=500, detail=f"str({e})")

@app.post(
    "/gpt/upsert-file",
    response_model=UpsertResponse,
)
async def upsert_file(
    file: UploadFile = File(...),
    metadata: Optional[str] = Form(None),
    chain: str = "a blockchain network",
    id: str = ""
):
    try:
        metadata_obj = (
            DocumentMetadata.parse_raw(metadata)
            if metadata
            else DocumentMetadata(source=Source.file)
        )
    except:
        metadata_obj = DocumentMetadata(source=Source.file)

    document = await get_document_from_file(file, metadata_obj)

    try:
        if id != '':
            document.id = id
        ids = await datastore.upsert(documents=[document], chain=chain)
        return UpsertResponse(ids=ids)
    except Exception as e:
        print("Error:", e)
        raise HTTPException(status_code=500, detail=f"str({e})")

"""
@app.post(
    "/upsert",
    response_model=UpsertResponse,
)
async def upsert(
    request: UpsertRequest = Body(...),
    chain: str = "a blockchain network"
):
    try:
        ids = await datastore.upsert(documents=request.documents, chain=chain)
        return UpsertResponse(ids=ids)
    except Exception as e:
        print("Error:", e)
        raise HTTPException(status_code=500, detail="Internal Service Error")


@app.post(
    "/query",
    response_model=QueryResponse,
)
async def query_main(
    request: QueryRequest = Body(...),
    chain: str = "a blockchain network"
):
    try:
        results = await datastore.query(
            queries=request.queries,
            chain=chain
        )
        return QueryResponse(results=results)
    except Exception as e:
        print("Error:", e)
        raise HTTPException(status_code=500, detail="Internal Service Error")


@sub_app.post(
    "/query",
    response_model=QueryResponse,
    # NOTE: We are describing the shape of the API endpoint input due to a current limitation in parsing arrays of objects from OpenAPI schemas. This will not be necessary in the future.
    description="Accepts search query objects array each with query and optional filter. Break down complex questions into sub-questions. Refine results by criteria, e.g. time / source, don't do this often. Split queries if ResponseTooLargeError occurs.",
)
async def query(
    request: QueryRequest = Body(...),
    chain: str = "a blockchain network"
):
    try:
        results = await datastore.query(
            queries=request.queries,
            chain=chain
        )
        return QueryResponse(results=results)
    except Exception as e:
        print("Error:", e)
        raise HTTPException(status_code=500, detail="Internal Service Error")


@app.delete(
    "/delete",
    response_model=DeleteResponse,
)
async def delete(
    request: DeleteRequest = Body(...),
):
    if not (request.ids or request.filter or request.delete_all):
        raise HTTPException(
            status_code=400,
            detail="One of ids, filter, or delete_all is required",
        )
    try:
        success = await datastore.delete(
            ids=request.ids,
            filter=request.filter,
            delete_all=request.delete_all,
        )
        return DeleteResponse(success=success)
    except Exception as e:
        print("Error:", e)
        raise HTTPException(status_code=500, detail="Internal Service Error")
"""

@app.on_event("startup")
async def startup():
    global datastore
    datastore = await get_datastore()


def start():
    uvicorn.run("server.main:app", host="0.0.0.0", port=8000, reload=True)

if __name__ == '__main__':
    start()