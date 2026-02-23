//! Knowledge base database connection.

use pg_toolkit::{PgConfig, create_pool};
use sqlx::PgPool;

pub use pg_toolkit::create_pool as create_pg_pool;

/// Create a sqlx PgPool for the knowledge base database.
pub async fn create_knowledge_base_pool(config: &PgConfig) -> Result<PgPool, sqlx::Error> {
    create_pool(config).await
}

/// Wrapper around a PgPool providing the knowledge base DB interface.
#[derive(Debug, Clone)]
pub struct KnowledgeBaseDb {
    pub(crate) pool: PgPool,
}

impl KnowledgeBaseDb {
    pub fn new(pool: PgPool) -> Self {
        Self { pool }
    }

    pub fn pool(&self) -> &PgPool {
        &self.pool
    }
}
