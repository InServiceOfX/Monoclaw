//! Knowledge base configuration.
//!
//! Re-exports `pg_toolkit::PgConfig` and provides a convenience constructor
//! with knowledge-base-specific defaults and environment variable names.

use anyhow::Result;
use std::path::Path;

pub use pg_toolkit::PgConfig;

/// Return a `PgConfig` with knowledge-base defaults, reading from env vars:
/// - `KB_HOST`     → default: "localhost"
/// - `KB_PORT`     → default: 5432
/// - `KB_USER`     → default: "knowledgebase"
/// - `KB_PASSWORD` → default: "knowledgebase"
/// - `KB_DATABASE` → default: "knowledge_base"
pub fn config_from_env() -> PgConfig {
    let _ = dotenvy::dotenv();

    PgConfig::new(
        std::env::var("KB_HOST").unwrap_or_else(|_| "localhost".to_string()),
        std::env::var("KB_PORT")
            .ok()
            .and_then(|v| v.parse().ok())
            .unwrap_or(5432_u16),
        std::env::var("KB_USER").unwrap_or_else(|_| "knowledgebase".to_string()),
        std::env::var("KB_PASSWORD").unwrap_or_else(|_| "knowledgebase".to_string()),
        Some(
            std::env::var("KB_DATABASE")
                .unwrap_or_else(|_| "knowledge_base".to_string()),
        ),
    )
}

/// Load knowledge-base config from a YAML file.
pub fn config_from_yaml(path: impl AsRef<Path>) -> Result<PgConfig> {
    PgConfig::from_yaml(path)
}
