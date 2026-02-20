//! Wire types for the pplx-embed-context embedding server API.
//!
//! These structs are serialised/deserialised to/from the JSON payloads that
//! the Python FastAPI server (`knowledge_base.EmbeddingServer.server`) accepts
//! and returns.

use serde::{Deserialize, Serialize};

// ---------------------------------------------------------------------------
// /embed
// ---------------------------------------------------------------------------

/// Request body for `POST /embed`.
///
/// `chunks[i]` is the ordered list of text chunks for document `i`.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EmbedRequest {
    /// Outer list = documents; inner list = chunks of that document.
    pub chunks: Vec<Vec<String>>,
}

/// Response body for `POST /embed`.
///
/// `embeddings[i][j]` is the L2-normalised 1024-dim vector for chunk `j`
/// of document `i`.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EmbedResponse {
    pub embeddings: Vec<Vec<Vec<f32>>>,
}

// ---------------------------------------------------------------------------
// /embed_query
// ---------------------------------------------------------------------------

/// Request body for `POST /embed_query`.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EmbedQueryRequest {
    pub query: String,
}

/// Response body for `POST /embed_query`.
///
/// `embedding` is a single L2-normalised 1024-dim vector.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EmbedQueryResponse {
    pub embedding: Vec<f32>,
}

// ---------------------------------------------------------------------------
// /health
// ---------------------------------------------------------------------------

/// Response body for `GET /health`.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HealthResponse {
    pub status: String,
    pub model_loaded: bool,
    pub device: String,
    pub model_path: String,
}
