//! Embedding client module for the pplx-embed-context-v1-0.6b model.
//!
//! The model runs as a separate Python FastAPI server
//! (`knowledge_base.EmbeddingServer.server`).  This module provides the Rust
//! HTTP client that talks to it.
//!
//! # Typical usage
//!
//! ```rust,no_run
//! use knowledge_base::embedding::{EmbeddingClient, EmbeddingClientConfig};
//!
//! # #[tokio::main]
//! # async fn main() -> anyhow::Result<()> {
//! let config = EmbeddingClientConfig::from_env();
//! let client = EmbeddingClient::new(config)?;
//!
//! // Check that the server is up before starting ingestion.
//! let health = client.health().await?;
//! assert!(health.model_loaded, "embedding server model not loaded");
//!
//! // Embed a document's chunks together (contextual model requirement).
//! let chunks = vec![
//!     "Introduction to the topic.".to_string(),
//!     "Further detail and analysis.".to_string(),
//! ];
//! let embeddings = client.embed_document(&chunks).await?;
//!
//! // Embed a query for retrieval.
//! let query_vec = client.embed_query("What does the document say?").await?;
//! # Ok(())
//! # }
//! ```

pub mod client;
pub mod config;
pub mod types;

pub use client::EmbeddingClient;
pub use config::EmbeddingClientConfig;
pub use types::{EmbedQueryRequest, EmbedQueryResponse, EmbedRequest, EmbedResponse, HealthResponse};
