//! Configuration for the embedding server HTTP client.
//!
//! Mirrors the Python `EmbeddingServerConfiguration` but from the client's
//! perspective: it only needs the server URL and timeout settings, not the
//! model path or device (those are server-side concerns).
//!
//! Load order (first wins):
//!   1. `EmbeddingClientConfig::from_yaml(path)`
//!   2. `EmbeddingClientConfig::from_env()`
//!   3. `EmbeddingClientConfig::default()`

use anyhow::{Context, Result};
use serde::{Deserialize, Serialize};
use std::path::Path;

/// Default embedding server base URL.
pub const DEFAULT_EMBEDDING_SERVER_URL: &str = "http://127.0.0.1:8765";
/// Default timeout for `/embed` and `/embed_query` calls (seconds).
pub const DEFAULT_EMBED_TIMEOUT_SECS: u64 = 60;
/// Default timeout for `/health` calls (seconds).
pub const DEFAULT_HEALTH_TIMEOUT_SECS: u64 = 5;

/// Configuration for the embedding HTTP client.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct EmbeddingClientConfig {
    /// Base URL of the embedding server (no trailing slash).
    /// Example: `"http://127.0.0.1:8765"`
    pub server_url: String,

    /// Timeout in seconds for embed / embed_query requests.
    pub embed_timeout_secs: u64,

    /// Timeout in seconds for health-check requests.
    pub health_timeout_secs: u64,
}

impl EmbeddingClientConfig {
    /// Load configuration from environment variables.
    ///
    /// Looks for a `.env` file in the current directory first.
    ///
    /// Supported variables (all optional; fall back to defaults):
    /// - `KB_EMBEDDING_SERVER_URL`
    /// - `KB_EMBED_TIMEOUT_SECS`
    /// - `KB_HEALTH_TIMEOUT_SECS`
    pub fn from_env() -> Self {
        let _ = dotenvy::dotenv();
        Self {
            server_url: std::env::var("KB_EMBEDDING_SERVER_URL")
                .unwrap_or_else(|_| DEFAULT_EMBEDDING_SERVER_URL.to_string()),
            embed_timeout_secs: std::env::var("KB_EMBED_TIMEOUT_SECS")
                .ok()
                .and_then(|v| v.parse().ok())
                .unwrap_or(DEFAULT_EMBED_TIMEOUT_SECS),
            health_timeout_secs: std::env::var("KB_HEALTH_TIMEOUT_SECS")
                .ok()
                .and_then(|v| v.parse().ok())
                .unwrap_or(DEFAULT_HEALTH_TIMEOUT_SECS),
        }
    }

    /// Load configuration from a YAML file.
    ///
    /// Expected keys (all optional; fall back to defaults):
    /// ```yaml
    /// server_url: "http://127.0.0.1:8765"
    /// embed_timeout_secs: 60
    /// health_timeout_secs: 5
    /// ```
    pub fn from_yaml(path: impl AsRef<Path>) -> Result<Self> {
        let content = std::fs::read_to_string(&path)
            .with_context(|| {
                format!(
                    "Failed to read embedding client config: {:?}",
                    path.as_ref()
                )
            })?;
        let config: Self = serde_yaml::from_str(&content).with_context(|| {
            format!(
                "Failed to parse embedding client config: {:?}",
                path.as_ref()
            )
        })?;
        Ok(config)
    }
}

impl Default for EmbeddingClientConfig {
    fn default() -> Self {
        Self {
            server_url: DEFAULT_EMBEDDING_SERVER_URL.to_string(),
            embed_timeout_secs: DEFAULT_EMBED_TIMEOUT_SECS,
            health_timeout_secs: DEFAULT_HEALTH_TIMEOUT_SECS,
        }
    }
}
