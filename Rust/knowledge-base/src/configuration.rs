use anyhow::Result;
use serde::{Deserialize, Serialize};
use std::path::Path;

/// Configuration for the knowledge base PostgreSQL connection.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct KnowledgeBaseConfig {
    pub host: String,
    pub port: u16,
    pub user: String,
    pub password: String,
    pub database: String,
}

impl KnowledgeBaseConfig {
    /// Read configuration from environment variables, falling back to defaults.
    ///
    /// Env vars: KB_HOST, KB_PORT, KB_USER, KB_PASSWORD, KB_DATABASE
    pub fn from_env() -> Self {
        let _ = dotenvy::dotenv();

        Self {
            host: std::env::var("KB_HOST").unwrap_or_else(|_| "localhost".to_string()),
            port: std::env::var("KB_PORT")
                .ok()
                .and_then(|v| v.parse().ok())
                .unwrap_or(5432),
            user: std::env::var("KB_USER").unwrap_or_else(|_| "knowledgebase".to_string()),
            password: std::env::var("KB_PASSWORD")
                .unwrap_or_else(|_| "knowledgebase".to_string()),
            database: std::env::var("KB_DATABASE")
                .unwrap_or_else(|_| "knowledge_base".to_string()),
        }
    }

    /// Build a PostgreSQL connection string from this config.
    pub fn connection_string(&self) -> String {
        format!(
            "postgres://{}:{}@{}:{}/{}",
            self.user, self.password, self.host, self.port, self.database
        )
    }

    /// Load configuration from a YAML file.
    pub fn from_yaml(path: impl AsRef<Path>) -> Result<Self> {
        let content = std::fs::read_to_string(path)?;
        let config: Self = serde_yaml::from_str(&content)?;
        Ok(config)
    }
}

impl Default for KnowledgeBaseConfig {
    fn default() -> Self {
        Self {
            host: "localhost".to_string(),
            port: 5432,
            user: "knowledgebase".to_string(),
            password: "knowledgebase".to_string(),
            database: "knowledge_base".to_string(),
        }
    }
}
