use anyhow::{Context, Result};
use chrono::{DateTime, Utc};
use pgvector::Vector;
use sqlx::Row;

use crate::database::connection::KnowledgeBaseDb;
use crate::models::{Chunk, Document, InsertChunk, InsertDocument, SearchResult};
use crate::sql_statements::KnowledgeBaseSql;

impl KnowledgeBaseDb {
    /// Create the pgvector extension if it does not already exist.
    /// Delegates to pg_toolkit::admin for the generic extension creation logic.
    pub async fn create_extension(&self) -> Result<()> {
        pg_toolkit::admin::create_extension(&self.pool, "vector").await
    }

    /// Create the knowledge base tables and indexes (idempotent).
    pub async fn create_tables(&self) -> Result<()> {
        sqlx::query(KnowledgeBaseSql::CREATE_DOCUMENTS_TABLE)
            .execute(&self.pool)
            .await
            .context("Failed to create documents table")?;

        sqlx::query(KnowledgeBaseSql::CREATE_CHUNKS_TABLE)
            .execute(&self.pool)
            .await
            .context("Failed to create chunks table")?;

        sqlx::query(KnowledgeBaseSql::CREATE_HNSW_INDEX)
            .execute(&self.pool)
            .await
            .context("Failed to create HNSW index")?;

        sqlx::query(KnowledgeBaseSql::CREATE_DOCUMENT_ID_INDEX)
            .execute(&self.pool)
            .await
            .context("Failed to create document_id index")?;

        sqlx::query(KnowledgeBaseSql::CREATE_CHUNK_INDEX_INDEX)
            .execute(&self.pool)
            .await
            .context("Failed to create chunk_index index")?;

        Ok(())
    }

    /// Return true if a document with the given content_hash already exists.
    pub async fn document_exists_by_hash(&self, hash: &str) -> Result<bool> {
        let row = sqlx::query(KnowledgeBaseSql::GET_DOCUMENT_BY_HASH)
            .bind(hash)
            .fetch_optional(&self.pool)
            .await
            .context("Failed to check document by hash")?;
        Ok(row.is_some())
    }

    /// Insert a document record and return its generated id.
    pub async fn insert_document(&self, doc: &InsertDocument) -> Result<i32> {
        let row = sqlx::query(KnowledgeBaseSql::INSERT_DOCUMENT)
            .bind(&doc.title)
            .bind(&doc.source_path)
            .bind(&doc.source_type)
            .bind(&doc.raw_content)
            .bind(&doc.content_hash)
            .bind(&doc.metadata)
            .fetch_one(&self.pool)
            .await
            .context("Failed to insert document")?;

        let id: i32 = row.try_get("id")?;
        Ok(id)
    }

    /// Insert a chunk record (with optional embedding) and return its generated id.
    pub async fn insert_chunk(&self, chunk: &InsertChunk) -> Result<i32> {
        let embedding: Option<Vector> = chunk
            .embedding
            .as_ref()
            .map(|v| Vector::from(v.clone()));

        let row = sqlx::query(KnowledgeBaseSql::INSERT_CHUNK)
            .bind(chunk.document_id)
            .bind(chunk.chunk_index)
            .bind(chunk.total_chunks)
            .bind(&chunk.content)
            .bind(&chunk.content_hash)
            .bind(embedding)
            .fetch_one(&self.pool)
            .await
            .context("Failed to insert chunk")?;

        let id: i32 = row.try_get("id")?;
        Ok(id)
    }

    /// Retrieve a document by primary key; returns None if not found.
    pub async fn get_document_by_id(&self, id: i32) -> Result<Option<Document>> {
        let doc = sqlx::query_as::<_, Document>(KnowledgeBaseSql::GET_DOCUMENT_BY_ID)
            .bind(id)
            .fetch_optional(&self.pool)
            .await
            .context("Failed to get document by id")?;
        Ok(doc)
    }

    /// Retrieve all chunks for a document, ordered by chunk_index.
    pub async fn get_document_chunks(&self, doc_id: i32) -> Result<Vec<Chunk>> {
        let chunks = sqlx::query_as::<_, Chunk>(KnowledgeBaseSql::GET_DOCUMENT_CHUNKS)
            .bind(doc_id)
            .fetch_all(&self.pool)
            .await
            .context("Failed to get document chunks")?;
        Ok(chunks)
    }

    /// Cosine similarity search over chunk embeddings.
    ///
    /// - `embedding`: the query vector (must be 1024-dimensional)
    /// - `threshold`: optional minimum similarity score (0.0–1.0); pass None to return all
    /// - `limit`: maximum number of results to return
    pub async fn vector_similarity_search(
        &self,
        embedding: &[f32],
        threshold: Option<f32>,
        limit: i64,
    ) -> Result<Vec<SearchResult>> {
        let query_vec = Vector::from(embedding.to_vec());

        let rows = sqlx::query(KnowledgeBaseSql::VECTOR_SIMILARITY_SEARCH)
            .bind(query_vec)
            .bind(threshold)
            .bind(limit)
            .fetch_all(&self.pool)
            .await
            .context("Failed to perform vector similarity search")?;

        let mut results = Vec::with_capacity(rows.len());
        for row in rows {
            results.push(SearchResult {
                id: row.try_get("id")?,
                document_id: row.try_get("document_id")?,
                chunk_index: row.try_get("chunk_index")?,
                total_chunks: row.try_get("total_chunks")?,
                content: row.try_get("content")?,
                content_hash: row.try_get("content_hash")?,
                created_at: row.try_get::<Option<DateTime<Utc>>, _>("created_at")?,
                title: row.try_get("title")?,
                source_path: row.try_get("source_path")?,
                source_type: row.try_get("source_type")?,
                similarity_score: row.try_get("similarity_score")?,
            });
        }
        Ok(results)
    }

    /// Drop the knowledge base tables (chunks first to satisfy the FK constraint).
    pub async fn drop_tables(&self) -> Result<()> {
        sqlx::query("DROP TABLE IF EXISTS knowledge_base_chunks CASCADE;")
            .execute(&self.pool)
            .await
            .context("Failed to drop chunks table")?;

        sqlx::query("DROP TABLE IF EXISTS knowledge_base_documents CASCADE;")
            .execute(&self.pool)
            .await
            .context("Failed to drop documents table")?;

        Ok(())
    }
}
