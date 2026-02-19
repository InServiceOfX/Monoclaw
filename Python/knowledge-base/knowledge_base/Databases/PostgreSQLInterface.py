from .CommonSQLStatements import CommonSQLStatements
from .PostgreSQLConnection import PostgreSQLConnection
from .SQLStatements import KnowledgeBaseSQLStatements

from typing import Any, Dict, List, Optional
import json


class KnowledgeBaseInterface:
    """Database interface for knowledge base document and chunk operations."""

    DOCUMENTS_TABLE_NAME = "knowledge_base_documents"
    CHUNKS_TABLE_NAME = "knowledge_base_chunks"

    def __init__(self, postgres_connection: PostgreSQLConnection):
        """
        Args:
            postgres_connection: PostgreSQLConnection instance pointed at the
                knowledge_base database
        """
        self._postgres_connection = postgres_connection
        self._database_name = postgres_connection._database_name

    async def create_tables(self) -> bool:
        """Create the knowledge base tables and indexes if they don't exist."""
        try:
            if not await self._postgres_connection.extension_exists("vector"):
                success = await self._postgres_connection.create_extension(
                    "vector")
                if not success:
                    print("Failed to create pgvector extension")
                    return False

            async with self._postgres_connection.connect() as conn:
                await conn.execute(
                    KnowledgeBaseSQLStatements.CREATE_DOCUMENTS_TABLE)
                await conn.execute(
                    KnowledgeBaseSQLStatements.CREATE_CHUNKS_TABLE)
                await conn.execute(
                    KnowledgeBaseSQLStatements.CREATE_CHUNKS_INDEXES)

                return True
        except Exception as e:
            print(f"Error creating knowledge base tables: {e}")
            return False

    async def table_exists(self, table_name: str = None) -> bool:
        """Check if the given table exists."""
        try:
            target_table = table_name or self.DOCUMENTS_TABLE_NAME
            async with self._postgres_connection.connect() as conn:
                exists = await conn.fetchval(
                    CommonSQLStatements.CHECK_TABLE_EXISTS,
                    target_table)
                return exists is not None
        except Exception as e:
            print(f"Error checking if table exists: {e}")
            return False

    async def insert_document(
            self,
            title: Optional[str],
            source_path: Optional[str],
            source_type: Optional[str],
            raw_content: str,
            content_hash: str,
            metadata: Optional[Dict[str, Any]] = None) -> Optional[int]:
        """
        Insert a document record into knowledge_base_documents.

        Returns:
            The ID of the inserted document, or None if failed
        """
        try:
            metadata_json = json.dumps(metadata) if metadata is not None else None
            async with self._postgres_connection.connect() as conn:
                result = await conn.fetchval(
                    KnowledgeBaseSQLStatements.INSERT_DOCUMENT,
                    title,
                    source_path,
                    source_type,
                    raw_content,
                    content_hash,
                    metadata_json
                )
                return result
        except Exception as e:
            print(f"Error inserting document: {e}")
            return None

    async def insert_chunk(
            self,
            document_id: int,
            chunk_index: int,
            total_chunks: int,
            content: str,
            content_hash: str,
            embedding: Optional[List[float]] = None) -> Optional[int]:
        """
        Insert a chunk record into knowledge_base_chunks.

        Returns:
            The ID of the inserted chunk, or None if failed
        """
        try:
            embedding_str = PostgreSQLConnection.convert_list_to_string(
                embedding) if embedding is not None else None
            async with self._postgres_connection.connect() as conn:
                result = await conn.fetchval(
                    KnowledgeBaseSQLStatements.INSERT_CHUNK,
                    document_id,
                    chunk_index,
                    total_chunks,
                    content,
                    content_hash,
                    embedding_str
                )
                return result
        except Exception as e:
            print(f"Error inserting chunk: {e}")
            return None

    async def document_exists_by_hash(self, content_hash: str) -> bool:
        """Check if a document with the given content hash already exists."""
        try:
            async with self._postgres_connection.connect() as conn:
                result = await conn.fetchval(
                    KnowledgeBaseSQLStatements.GET_DOCUMENT_BY_HASH,
                    content_hash)
                return result is not None
        except Exception as e:
            print(f"Error checking document by hash: {e}")
            return False

    async def get_document_by_id(
            self,
            document_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve a document by its ID."""
        try:
            async with self._postgres_connection.connect() as conn:
                row = await conn.fetchrow(
                    KnowledgeBaseSQLStatements.GET_DOCUMENT_BY_ID,
                    document_id)
                if row is None:
                    return None
                return dict(row)
        except Exception as e:
            print(f"Error retrieving document by id: {e}")
            return None

    async def get_document_chunks(
            self,
            document_id: int) -> List[Dict[str, Any]]:
        """Retrieve all chunks for a given document, ordered by chunk_index."""
        try:
            async with self._postgres_connection.connect() as conn:
                rows = await conn.fetch(
                    KnowledgeBaseSQLStatements.GET_DOCUMENT_CHUNKS,
                    document_id)
                return [dict(row) for row in rows]
        except Exception as e:
            print(f"Error retrieving document chunks: {e}")
            return []

    async def vector_similarity_search(
            self,
            query_embedding: List[float],
            similarity_threshold: Optional[float] = None,
            limit: int = 10) -> List[Dict[str, Any]]:
        """
        Perform cosine similarity search over knowledge base chunks.

        Args:
            query_embedding: 1024-dimensional query vector
            similarity_threshold: Optional minimum similarity score (0.0 to 1.0)
            limit: Maximum number of results

        Returns:
            List of dicts with chunk content, document metadata, and similarity_score
        """
        try:
            async with self._postgres_connection.connect() as conn:
                embedding_str = PostgreSQLConnection.convert_list_to_string(
                    query_embedding)
                rows = await conn.fetch(
                    KnowledgeBaseSQLStatements.VECTOR_SIMILARITY_SEARCH,
                    embedding_str,
                    similarity_threshold,
                    limit)

                results = []
                for row in rows:
                    results.append({
                        'id': row['id'],
                        'document_id': row['document_id'],
                        'chunk_index': row['chunk_index'],
                        'total_chunks': row['total_chunks'],
                        'content': row['content'],
                        'content_hash': row['content_hash'],
                        'created_at': row['created_at'],
                        'title': row['title'],
                        'source_path': row['source_path'],
                        'source_type': row['source_type'],
                        'similarity_score': row['similarity_score']
                    })
                return results
        except Exception as e:
            print(f"Error performing vector similarity search: {e}")
            return []

    async def drop_tables(self) -> bool:
        """Drop the knowledge base tables (chunks first due to FK constraint)."""
        try:
            async with self._postgres_connection.connect() as conn:
                await conn.execute(
                    f"DROP TABLE IF EXISTS {self.CHUNKS_TABLE_NAME} CASCADE")
                await conn.execute(
                    f"DROP TABLE IF EXISTS {self.DOCUMENTS_TABLE_NAME} CASCADE")
                return True
        except Exception as e:
            print(f"Error dropping tables: {e}")
            return False
