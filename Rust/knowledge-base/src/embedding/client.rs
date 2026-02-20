//! HTTP client for the pplx-embed-context embedding server.
//!
//! # Example
//!
//! ```rust,no_run
//! use knowledge_base::embedding::{EmbeddingClient, EmbeddingClientConfig};
//!
//! #[tokio::main]
//! async fn main() -> anyhow::Result<()> {
//!     let client = EmbeddingClient::new(EmbeddingClientConfig::default())?;
//!
//!     // Embed all chunks of one document together (contextual model requirement).
//!     let chunks = vec![
//!         "First chunk of the document.".to_string(),
//!         "Second chunk of the document.".to_string(),
//!     ];
//!     let embeddings = client.embed_document(&chunks).await?;
//!     // embeddings[i] is the 1024-dim embedding for chunks[i]
//!     assert_eq!(embeddings.len(), chunks.len());
//!     assert_eq!(embeddings[0].len(), 1024);
//!
//!     // Embed a query (single chunk, same model).
//!     let query_vec = client.embed_query("What is late chunking?").await?;
//!     assert_eq!(query_vec.len(), 1024);
//!
//!     Ok(())
//! }
//! ```

use std::time::Duration;

use anyhow::{Context, Result, bail};
use reqwest::Client;
use tracing::instrument;

use crate::embedding::config::EmbeddingClientConfig;
use crate::embedding::types::{
    EmbedQueryRequest, EmbedQueryResponse, EmbedRequest, EmbedResponse, HealthResponse,
};

/// Async HTTP client for the embedding server.
///
/// Create once, reuse across many calls — the underlying `reqwest::Client`
/// maintains a connection pool.
#[derive(Debug, Clone)]
pub struct EmbeddingClient {
    embed_client: Client,
    health_client: Client,
    config: EmbeddingClientConfig,
}

impl EmbeddingClient {
    /// Create a new client from the given configuration.
    ///
    /// Builds two `reqwest::Client` instances with different timeouts:
    /// one for embed calls (potentially slow) and one for health checks (fast).
    pub fn new(config: EmbeddingClientConfig) -> Result<Self> {
        let embed_client = Client::builder()
            .timeout(Duration::from_secs(config.embed_timeout_secs))
            .build()
            .context("Failed to build embed HTTP client")?;

        let health_client = Client::builder()
            .timeout(Duration::from_secs(config.health_timeout_secs))
            .build()
            .context("Failed to build health HTTP client")?;

        Ok(Self {
            embed_client,
            health_client,
            config,
        })
    }

    /// Create a client from environment variables (or defaults).
    pub fn from_env() -> Result<Self> {
        Self::new(EmbeddingClientConfig::from_env())
    }

    /// Embed all chunks of a **single document** together.
    ///
    /// This is the primary call site for document ingestion.  The contextual
    /// model requires all chunks of a document to be embedded as a group so
    /// each chunk's embedding reflects its neighbours.
    ///
    /// Returns one 1024-dim L2-normalised vector per input chunk, in order.
    #[instrument(skip(self, chunks), fields(n_chunks = chunks.len()))]
    pub async fn embed_document(&self, chunks: &[String]) -> Result<Vec<Vec<f32>>> {
        if chunks.is_empty() {
            bail!("embed_document: chunks must not be empty");
        }

        let request = EmbedRequest {
            chunks: vec![chunks.to_vec()],
        };

        let response: EmbedResponse = self
            .embed_client
            .post(format!("{}/embed", self.config.server_url))
            .json(&request)
            .send()
            .await
            .context("embed_document: HTTP request failed")?
            .error_for_status()
            .context("embed_document: server returned error status")?
            .json()
            .await
            .context("embed_document: failed to parse response JSON")?;

        response
            .embeddings
            .into_iter()
            .next()
            .context("embed_document: server returned empty embeddings list")
    }

    /// Embed a batch of documents in one round-trip.
    ///
    /// Each element of `docs` is a slice of chunk strings for one document.
    /// Returns `docs.len()` inner `Vec`s, each containing one embedding per
    /// chunk.
    ///
    /// Prefer this over calling `embed_document` in a loop when ingesting
    /// multiple documents.
    #[instrument(skip(self, docs), fields(n_docs = docs.len()))]
    pub async fn embed_documents(&self, docs: &[Vec<String>]) -> Result<Vec<Vec<Vec<f32>>>> {
        if docs.is_empty() {
            bail!("embed_documents: docs must not be empty");
        }

        let request = EmbedRequest {
            chunks: docs.to_vec(),
        };

        let response: EmbedResponse = self
            .embed_client
            .post(format!("{}/embed", self.config.server_url))
            .json(&request)
            .send()
            .await
            .context("embed_documents: HTTP request failed")?
            .error_for_status()
            .context("embed_documents: server returned error status")?
            .json()
            .await
            .context("embed_documents: failed to parse response JSON")?;

        Ok(response.embeddings)
    }

    /// Embed a single query string for similarity search.
    ///
    /// The query is treated as a single-chunk document so it goes through
    /// the same contextual model.  Returns a 1024-dim L2-normalised vector
    /// ready for cosine similarity against stored chunk embeddings.
    #[instrument(skip(self, query), fields(query_len = query.len()))]
    pub async fn embed_query(&self, query: &str) -> Result<Vec<f32>> {
        if query.trim().is_empty() {
            bail!("embed_query: query must not be empty");
        }

        let request = EmbedQueryRequest {
            query: query.to_string(),
        };

        let response: EmbedQueryResponse = self
            .embed_client
            .post(format!("{}/embed_query", self.config.server_url))
            .json(&request)
            .send()
            .await
            .context("embed_query: HTTP request failed")?
            .error_for_status()
            .context("embed_query: server returned error status")?
            .json()
            .await
            .context("embed_query: failed to parse response JSON")?;

        Ok(response.embedding)
    }

    /// Check whether the embedding server is reachable and the model is loaded.
    ///
    /// Returns `Ok(HealthResponse)` if the server responds with HTTP 200,
    /// or an error if the server is unreachable or returns a non-2xx status.
    #[instrument(skip(self))]
    pub async fn health(&self) -> Result<HealthResponse> {
        let response: HealthResponse = self
            .health_client
            .get(format!("{}/health", self.config.server_url))
            .send()
            .await
            .context("health: HTTP request failed")?
            .error_for_status()
            .context("health: server returned error status")?
            .json()
            .await
            .context("health: failed to parse response JSON")?;

        Ok(response)
    }

    /// Return a reference to the active configuration.
    pub fn config(&self) -> &EmbeddingClientConfig {
        &self.config
    }
}
