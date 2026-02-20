pub mod configuration;
pub mod database;
pub mod embedding;
pub mod ingestion;
pub mod models;
pub mod sql_statements;

pub use configuration::{PgConfig, config_from_env, config_from_yaml};
pub use embedding::{EmbeddingClient, EmbeddingClientConfig};
pub use models::{Chunk, Document, InsertChunk, InsertDocument, SearchResult};

// Re-export pg_toolkit so dependents don't need a direct dep for basic ops.
pub use pg_toolkit;
