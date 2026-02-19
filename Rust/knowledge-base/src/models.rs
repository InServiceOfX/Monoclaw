use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};

/// A document row from knowledge_base_documents.
#[derive(Debug, Clone, Serialize, Deserialize, sqlx::FromRow)]
pub struct Document {
    pub id: i32,
    pub title: Option<String>,
    pub source_path: Option<String>,
    pub source_type: Option<String>,
    pub raw_content: String,
    pub content_hash: String,
    pub metadata: Option<serde_json::Value>,
    pub ingested_at: Option<DateTime<Utc>>,
}

/// A chunk row from knowledge_base_chunks.
#[derive(Debug, Clone, Serialize, Deserialize, sqlx::FromRow)]
pub struct Chunk {
    pub id: i32,
    pub document_id: i32,
    pub chunk_index: i32,
    pub total_chunks: i32,
    pub content: String,
    pub content_hash: String,
    // embedding is intentionally omitted from FromRow — use raw queries when needed
    pub created_at: Option<DateTime<Utc>>,
}

/// A similarity search result, joining chunk + document fields.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SearchResult {
    pub id: i32,
    pub document_id: i32,
    pub chunk_index: i32,
    pub total_chunks: i32,
    pub content: String,
    pub content_hash: String,
    pub created_at: Option<DateTime<Utc>>,
    pub title: Option<String>,
    pub source_path: Option<String>,
    pub source_type: Option<String>,
    pub similarity_score: f64,
}

/// Input struct for inserting a new document (not a DB row struct).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct InsertDocument {
    pub title: Option<String>,
    pub source_path: Option<String>,
    pub source_type: Option<String>,
    pub raw_content: String,
    pub content_hash: String,
    pub metadata: Option<serde_json::Value>,
}

/// Input struct for inserting a new chunk (not a DB row struct).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct InsertChunk {
    pub document_id: i32,
    pub chunk_index: i32,
    pub total_chunks: i32,
    pub content: String,
    pub content_hash: String,
    pub embedding: Option<Vec<f32>>,
}
