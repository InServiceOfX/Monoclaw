use crate::configuration::KnowledgeBaseConfig;
use sqlx::PgPool;

/// Create a sqlx PgPool from the given config.
pub async fn create_pool(config: &KnowledgeBaseConfig) -> Result<PgPool, sqlx::Error> {
    PgPool::connect(&config.connection_string()).await
}

/// Wrapper around a PgPool that provides the knowledge base DB interface.
pub struct KnowledgeBaseDb {
    pub(crate) pool: PgPool,
}

impl KnowledgeBaseDb {
    pub fn new(pool: PgPool) -> Self {
        Self { pool }
    }

    /// Expose the underlying pool for advanced use.
    pub fn pool(&self) -> &PgPool {
        &self.pool
    }
}
