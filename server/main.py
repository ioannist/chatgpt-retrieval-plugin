import os
from typing import Optional
import uvicorn
from fastapi import FastAPI, File, Form, HTTPException, Depends, Body, UploadFile
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles

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
    EditCategoryRequest,
    EditArchiveRequest
)
from datastore.factory import get_datastore
from services.file import get_document_from_file
from services.openai import ask_with_chunks
from services.dynamodb import query_questions, edit_question_answer, edit_question_archive, edit_question_category

from models.models import DocumentMetadata, Source

bearer_scheme = HTTPBearer()
BEARER_TOKEN = os.environ.get("BEARER_TOKEN")
assert BEARER_TOKEN is not None


def validate_token(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    if credentials.scheme != "Bearer" or credentials.credentials != BEARER_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid or missing token")
    return credentials


app = FastAPI(dependencies=[Depends(validate_token)])
app.mount("/.well-known", StaticFiles(directory=".well-known"), name="static")

# Create a sub-application, in order to access just the query endpoint in an OpenAPI schema, found at http://0.0.0.0:8000/sub/openapi.json when the app is running locally
sub_app = FastAPI(
    title="Retrieval Plugin API",
    description="A retrieval API for querying and filtering documents based on natural language queries and metadata",
    version="1.0.0",
    servers=[{"url": "https://your-app-url.com"}],
    dependencies=[Depends(validate_token)],
)
app.mount("/sub", sub_app)

@app.post("/questions/archive-edit")
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


@app.post("/questions/answer")
async def answer_question(
    request: AnswerRequest = Body(...)
):
    try:
        edit_question_answer(
            chain=request.chain,
            question=request.question,
            answer=request.answer
        )
        edit_question_category(
            chain=request.chain,
            question=request.question,
            category=request.category
        )
    except Exception as e:
        print("Error:", e)
        raise HTTPException(status_code=500, detail=f"str({e})")
    
@app.post("/questions/category-edit")
async def answer_question(
    request: EditCategoryRequest = Body(...)
):
    try:
        edit_question_category(
            chain=request.chain,
            question=request.question,
            category=request.category
        )
    except Exception as e:
        print("Error:", e)
        raise HTTPException(status_code=500, detail=f"str({e})")


@app.get(
    "/questions/{chain}"
)
async def get_qas(
    chain: str
):
    try:
        qas = query_questions(chain);
        print(qas)
        return QAResponse(
            qas=qas
        )
    except Exception as e:
        print("Error:", e)
        raise HTTPException(status_code=500, detail=f"str({e})")

@app.post(
    "/ask-question",
    response_model=AskResponse,
)
async def ask_question(
    request: AskRequest = Body(...),
    chain: str = "a blockchain network"
):
    try:
        query_results = await datastore.query(queries=[request.query], chain=chain)
        chunks = [result.text for result in query_results[0].results]

        question = f"This is a question regarding {chain}.\n{request.question}"
        answer = ask_with_chunks(question=question, chunks=chunks)
        return AskResponse(answer=answer)
    except Exception as e:
        print("Error:", e)
        raise HTTPException(status_code=500, detail=f"str({e})")

@app.post(
    "/upsert-file",
    response_model=UpsertResponse,
)
async def upsert_file(
    file: UploadFile = File(...),
    metadata: Optional[str] = Form(None),
    chain: str = "a blockchain network"
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
        ids = await datastore.upsert(documents=[document], chain=chain)
        return UpsertResponse(ids=ids)
    except Exception as e:
        print("Error:", e)
        raise HTTPException(status_code=500, detail=f"str({e})")


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


@app.on_event("startup")
async def startup():
    global datastore
    datastore = await get_datastore()


def start():
    uvicorn.run("server.main:app", host="0.0.0.0", port=8000, reload=True)

if __name__ == '__main__':
    start()