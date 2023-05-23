from abc import ABC, abstractmethod
from typing import Dict, List, Optional
import asyncio
import math
from itertools import combinations


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
from services.dynamodb import save_question_to_db, query_question_embeddings, scan_topics, get_source_last_line_processed, edit_source_last_line_processed
from services.extract_questions import extract_topic_id

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
        """
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
        """
        
        print('Get topics from db')
        topics = scan_topics()
        topic_names = [t.topic for t in topics]
        topic_ids = [t.topic_id for t in topics]

        print('Remove lines that have already been processed')
        last_lines_processed = []
        for i, doc in enumerate(documents):
            last_line_processed = get_source_last_line_processed(chain=chain, source_id=doc.id)
            print(f"Last line processed is {last_line_processed}")
            last_lines_processed.append(last_line_processed)
            doc.text = doc.text.split("\n",last_lines_processed[i])[last_lines_processed[i]]

        if doc.text.count('\n') < 100:
            print('No new content found')
            return []

        print('Convert the document to chunks')
        chunks = get_document_chunks(documents, chunk_token_size, chain)

        print('Get a list of current question embeddings for this chain')
        old_question_embeddings: List[List[float]] = query_question_embeddings(chain)
        new_question_embeddings: List[List[float]] = []
        
        print('Loop through the dict items')
        for doc_id, chunk_list in chunks.items():
            print(f"Saving questions for document_id: {doc_id}")
            for chunk in chunk_list:

                print('Iterate over all questions generated for this text chunk')
                for question in chunk.questions:
                    if question.embedding == None:
                        continue
                    print('Compare this question with all old questions')
                    already_extracted = False
                    print('Compare it with all new questions that were just added')
                    for new_question in new_question_embeddings:
                        similarity = cosine_similarity(new_question, question.embedding)
                        if similarity > 0.9:
                            already_extracted = True
                            break
                    if already_extracted:
                        continue
                    for old_question in old_question_embeddings:
                        similarity = cosine_similarity(old_question, question.embedding)
                        if similarity > 0.9:
                            already_extracted = True
                            break
                    if already_extracted:
                        continue
                    
                    print('Save question to database')
                    topic_id = extract_topic_id(text=question.text, topic_names=topic_names, topic_ids=topic_ids)
                    chunk.topic_id = topic_id
                    vector = ','.join([str(x) for x in question.embedding])
                    save_question_to_db(chain=chain, question=question.text, embedding=vector, topic_id=topic_id)
                    new_question_embeddings.append(question.embedding)

        print('Save chunks to vector db')
        result = await self._upsert(chunks=chunks, chain=chain)

        print('Updating last lines processed in db')
        for i, doc in enumerate(documents):
            last_line_processed = last_lines_processed[i] + doc.text.count("\n")
            edit_source_last_line_processed(chain=chain, source_id=doc.id, line=last_line_processed)

        return result

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
        print('Getting embeddings')
        query_embeddings = get_embeddings(query_texts)
        # hydrate the queries with embeddings
        queries_with_embeddings = [
            QueryWithEmbedding(**query.dict(), embedding=embedding)
            for query, embedding in zip(queries, query_embeddings)
        ]
        print('Querying embeddings')
        return await self._query(queries=queries_with_embeddings, chain=chain)

    @abstractmethod
    async def _query(self, queries: List[QueryWithEmbedding], chain: str) -> List[QueryResult]:
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
