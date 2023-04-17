from abc import ABC, abstractmethod
from typing import Dict, List, Optional
import asyncio
import math

from models.models import (
    Document,
    DocumentChunk,
    DocumentMetadataFilter,
    Query,
    QueryResult,
    QueryWithEmbedding,
)
from services.chunks import get_document_chunks
from services.openai import get_embeddings
from services.dynamodb import save_question_to_db, query_question_embeddings

def cosine_similarity(v1,v2) -> float:
    "compute cosine similarity of v1 to v2: (v1 dot v2)/{||v1||*||v2||)"
    sumxx, sumxy, sumyy = 0, 0, 0
    for i in range(len(v1)):
        x = v1[i]; y = v2[i]
        sumxx += x*x
        sumyy += y*y
        sumxy += x*y
    return sumxy/math.sqrt(sumxx*sumyy)

class DataStore(ABC):
    async def upsert(
        self, documents: List[Document], chunk_token_size: Optional[int] = None, chain: str = ""
    ) -> List[str]:
        """
        Takes in a list of documents and inserts them into the database.
        First deletes all the existing vectors with the document id (if necessary, depends on the vector db), then inserts the new ones.
        Return a list of document ids.
        """
        # Delete any existing vectors for documents with the input document ids
        await asyncio.gather(
            *[
                self.delete(
                    filter=DocumentMetadataFilter(
                        document_id=document.id,
                    ),
                    delete_all=False,
                )
                for document in documents
                if document.id
            ]
        )

        # Convert the document to chunks
        chunks = get_document_chunks(documents, chunk_token_size, chain)

        # Get a list of current question embeddings for this chain
        old_question_embeddings: List[List[float]] = query_question_embeddings(chain);

        # Loop through the dict items
        for doc_id, chunk_list in chunks.items():
            print(f"Saving questions for document_id: {doc_id}")
            for chunk in chunk_list:

                # Iterate over all questions generated for this text chunk
                for question in chunk.questions:
                    if question.embedding == None:
                        continue
                    # Compare this question with all old questions
                    already_extracted = False
                    for old_question in old_question_embeddings:
                        similarity = cosine_similarity(old_question, question.embedding)
                        if similarity > 0.9:
                            already_extracted = True
                    if already_extracted:
                        continue

                    # Save question to supabase
                    vector = ','.join([str(x) for x in question.embedding])
                    save_question_to_db(chain=chain, question=question.text, embedding=vector)

        return await self._upsert(chunks)

    @abstractmethod
    async def _upsert(self, chunks: Dict[str, List[DocumentChunk]]) -> List[str]:
        """
        Takes in a list of list of document chunks and inserts them into the database.
        Return a list of document ids.
        """

        raise NotImplementedError

    async def query(self, queries: List[Query], chain: str) -> List[QueryResult]:
        """
        Takes in a list of queries and filters and returns a list of query results with matching document chunks and scores.
        """
        # get a list of of just the queries from the Query list
        query_texts = [f"This is regarding {chain}.\n{query.query}" for query in queries]
        query_embeddings = get_embeddings(query_texts)
        # hydrate the queries with embeddings
        queries_with_embeddings = [
            QueryWithEmbedding(**query.dict(), embedding=embedding)
            for query, embedding in zip(queries, query_embeddings)
        ]
        return await self._query(queries_with_embeddings)

    @abstractmethod
    async def _query(self, queries: List[QueryWithEmbedding]) -> List[QueryResult]:
        """
        Takes in a list of queries with embeddings and filters and returns a list of query results with matching document chunks and scores.
        """
        raise NotImplementedError

    @abstractmethod
    async def delete(
        self,
        ids: Optional[List[str]] = None,
        filter: Optional[DocumentMetadataFilter] = None,
        delete_all: Optional[bool] = None,
    ) -> bool:
        """
        Removes vectors by ids, filter, or everything in the datastore.
        Multiple parameters can be used at once.
        Returns whether the operation was successful.
        """
        raise NotImplementedError
