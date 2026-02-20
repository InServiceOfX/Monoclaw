//! PostgreSQL connection pooling.

use crate::config::PgConfig;
use sqlx::PgPool;

/// Create a new PostgreSQL connection pool from the given configuration.
///
/// This is a thin wrapper around `PgPool::connect` that uses the config's
/// connection string. The pool will be configured with default sqlx settings.
///
/// # Example
/// ```rust,no_run
/// use pg_toolkit::{PgConfig, create_pool};
///
/// #[tokio::main]
/// async fn main() -> anyhow::Result<()> {
///     let config = PgConfig::from_env();
///     let pool = create_pool(&config).await?;
///     // Use pool...
///     Ok(())
/// }
/// ```
pub async fn create_pool(config: &PgConfig) -> Result<PgPool, sqlx::Error> {
    PgPool::connect(&config.connection_string()).await
}

/// Create a connection pool to the system "postgres" database.
///
/// This is useful for admin operations like creating or dropping databases
/// when you don't yet have a connection to the target database.
pub async fn create_system_pool(config: &PgConfig) -> Result<PgPool, sqlx::Error> {
    PgPool::connect(&config.system_connection_string()).await
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_create_pool_requires_running_db() {
        // This test documents that create_pool requires a running database.
        // We can't test the actual connection without a running PostgreSQL instance.
        // Integration tests can verify the actual behavior.
    }
}
