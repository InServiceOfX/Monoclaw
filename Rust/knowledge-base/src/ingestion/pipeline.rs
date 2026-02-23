//! Ingestion pipeline wiring FileIngester → TextChunker → EmbeddingClient → KnowledgeBaseDb.
//!
//! # Example
//!
//! ```rust,no_run
//! use knowledge_base::{
//!     IngestPipeline, PgConfig, EmbeddingClientConfig,
//! };
//!
//! #[tokio::main]
//! async fn main() -> anyhow::Result<()> {
//!     let pg_config = PgConfig::from_env();
//!     let embedding_config = EmbeddingClientConfig::from_env();
//!     let pipeline = IngestPipeline::new(&pg_config, embedding_config).await?;
//!
//!     // Ingest a file
//!     let result = pipeline.ingest_file(std::path::Path::new("article.md")).await?;
//!     println!("Ingested doc {} with {} chunks", result.document_id, result.chunks_inserted);
//!
//!     // Search
//!     let hits = pipeline.search("quantum field theory", 5).await?;
//!     for hit in hits {
//!         println!("{:.3} – {}", hit.similarity_score, hit.content);
//!     }
//!
//!     Ok(())
//! }
//! ```

use std::path::Path;

use anyhow::{Context, Result, bail};
use tracing::{info, instrument};

use crate::database::connection::{KnowledgeBaseDb, create_knowledge_base_pool};
use crate::embedding::{EmbeddingClient, EmbeddingClientConfig};
use crate::ingestion::file_ingester::{FileIngester, IngestedDocument};
use crate::ingestion::text_chunker::TextChunker;
use crate::models::{InsertChunk, InsertDocument};
use crate::PgConfig;

/// Result of a successful ingestion.
#[derive(Debug, Clone)]
pub struct IngestResult {
    /// The generated document id.
    pub document_id: i32,
    /// Number of chunks inserted for this document.
    pub chunks_inserted: usize,
    /// True if the document was already present (dedup by hash) and no new data was written.
    pub was_duplicate: bool,
}

/// Ingestion pipeline orchestrating file reading, chunking, embedding, and storage.
#[derive(Debug, Clone)]
pub struct IngestPipeline {
    db: KnowledgeBaseDb,
    embedding_client: EmbeddingClient,
    chunker: TextChunker,
}

impl IngestPipeline {
    /// Create a new pipeline, initialise DB pool, and ensure tables exist.
    ///
    /// # Errors
    ///
    /// Returns an error if the DB connection fails, the embedding client cannot be created,
    /// or table creation fails.
    #[instrument(skip(pg_config, embedding_config))]
    pub async fn new(pg_config: &PgConfig, embedding_config: EmbeddingClientConfig) -> Result<Self> {
        let pool = create_knowledge_base_pool(pg_config)
            .await
            .context("Failed to create database pool")?;
        let db = KnowledgeBaseDb::new(pool);

        // Ensure pgvector extension and tables exist
        db.create_extension()
            .await
            .context("Failed to create pgvector extension")?;
        db.create_tables()
            .await
            .context("Failed to create knowledge base tables")?;

        let embedding_client = EmbeddingClient::new(embedding_config)
            .context("Failed to create embedding client")?;

        info!("IngestPipeline initialised");

        Ok(Self {
            db,
            embedding_client,
            chunker: TextChunker::default(),
        })
    }

    /// Ingest a file from disk.
    ///
    /// # Deduplication
    ///
    /// If a document with the same content hash already exists, returns immediately
    /// with `was_duplicate: true` and the existing document id.
    #[instrument(skip(self, path), fields(path = %path.display()))]
    pub async fn ingest_file(&self, path: &Path) -> Result<IngestResult> {
        let ingested = FileIngester::ingest_file(path)
            .with_context(|| format!("Failed to ingest file: {}", path.display()))?;

        self.ingest_ingested_document(&ingested).await
    }

    /// Ingest raw text directly (useful for content fetched from URLs, APIs, etc.).
    #[instrument(skip(self, content))]
    pub async fn ingest_text(
        &self,
        content: &str,
        title: &str,
        source_path: &str,
        source_type: &str,
    ) -> Result<IngestResult> {
        let ingested = IngestedDocument {
            title: title.to_string(),
            source_path: source_path.to_string(),
            source_type: source_type.to_string(),
            raw_content: content.to_string(),
            metadata: None,
        };

        self.ingest_ingested_document(&ingested).await
    }

    /// Internal helper to ingest an already-parsed document.
    #[instrument(skip(self, ingested))]
    async fn ingest_ingested_document(&self, ingested: &IngestedDocument) -> Result<IngestResult> {
        let content_hash = FileIngester::compute_sha256(&ingested.raw_content);

        // Deduplication check
        if self.db.document_exists_by_hash(&content_hash).await? {
            // Fetch existing document id for the return value
            let existing = sqlx::query_as::<_, crate::models::Document>(
                "SELECT id, title, source_path, source_type, raw_content, content_hash, metadata, ingested_at \
                 FROM knowledge_base_documents WHERE content_hash = $1"
            )
            .bind(&content_hash)
            .fetch_optional(self.db.pool())
            .await
            .context("Failed to fetch existing document by hash")?;

            if let Some(doc) = existing {
                info!(document_id = doc.id, "Document already exists (dedup)");
                return Ok(IngestResult {
                    document_id: doc.id,
                    chunks_inserted: 0,
                    was_duplicate: true,
                });
            }
        }

        // Insert document
        let insert_doc = InsertDocument {
            title: Some(ingested.title.clone()),
            source_path: Some(ingested.source_path.clone()),
            source_type: Some(ingested.source_type.clone()),
            raw_content: ingested.raw_content.clone(),
            content_hash: content_hash.clone(),
            metadata: ingested.metadata.clone(),
        };

        let document_id = self.db.insert_document(&insert_doc).await?;
        info!(document_id, "Inserted document");

        // Chunk the content
        let chunks = self.chunker.chunk_text(&ingested.raw_content);
        if chunks.is_empty() {
            bail!("No chunks produced from document content");
        }
        info!(n_chunks = chunks.len(), "Chunked document");

        // Embed all chunks together (contextual model requirement)
        let chunk_embeddings = self.embedding_client.embed_document(&chunks).await?;
        if chunk_embeddings.len() != chunks.len() {
            bail!(
                "Embedding count mismatch: expected {}, got {}",
                chunks.len(),
                chunk_embeddings.len()
            );
        }

        // Insert chunks with embeddings
        let mut chunks_inserted = 0usize;
        for (idx, (chunk_text, embedding)) in chunks.iter().zip(chunk_embeddings.iter()).enumerate() {
            let chunk_hash = FileIngester::compute_sha256(chunk_text);
            let insert_chunk = InsertChunk {
                document_id,
                chunk_index: idx as i32,
                total_chunks: chunks.len() as i32,
                content: chunk_text.clone(),
                content_hash: chunk_hash,
                embedding: Some(embedding.clone()),
            };
            self.db.insert_chunk(&insert_chunk).await?;
            chunks_inserted += 1;
        }

        info!(
            document_id,
            chunks_inserted,
            "Ingestion complete"
        );

        Ok(IngestResult {
            document_id,
            chunks_inserted,
            was_duplicate: false,
        })
    }

    /// Search the knowledge
    /// Search the knowledge base for relevant chunks.
    ///
    /// 1. Embeds the query using the embedding client
    /// 2. Performs cosine similarity search against stored chunk embeddings
    /// 3. Returns top-k results ordered by similarity (highest first)
    ///
    /// # Arguments
    ///
    /// * `query` - The search query string
    /// * `limit` - Maximum number of results to return
    /// * `threshold` - Optional minimum similarity score (0.0–1.0)
    #[instrument(skip(self, query), fields(query_len = query.len()))]
    pub async fn search(
        &self,
        query: &str,
        limit: i64,
        threshold: Option<f32>,
    ) -> Result<Vec<crate::models::SearchResult>> {
        if query.trim().is_empty() {
            bail!("Search query cannot be empty");
        }

        // Embed the query
        let query_embedding = self.embedding_client.embed_query(query).await
            .context("Failed to embed query")?;

        // Search the database
        let results = self.db.vector_similarity_search(&query_embedding, threshold, limit)
            .await
            .context("Database search failed")?;

        info!(query, n_results = results.len(), "Search complete");
        Ok(results)
    }
}
