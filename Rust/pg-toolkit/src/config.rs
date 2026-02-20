//! PostgreSQL configuration management.
//!
//! Supports loading from environment variables and YAML files, with sensible
//! defaults for local development.

use anyhow::{Context, Result};
use serde::{Deserialize, Serialize};
use std::path::Path;

/// Configuration for a PostgreSQL connection.
///
/// This struct is generic and not tied to any specific application domain.
/// It supports loading from environment variables or YAML configuration files.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct PgConfig {
    /// PostgreSQL host (default: "localhost")
    pub host: String,
    /// PostgreSQL port (default: 5432)
    pub port: u16,
    /// PostgreSQL username (default: "postgres")
    pub user: String,
    /// PostgreSQL password (default: "postgres")
    pub password: String,
    /// Database name. If None, operations will connect to the system "postgres" database.
    pub database: Option<String>,
}

impl PgConfig {
    /// Create a new config with explicit values.
    pub fn new(
        host: impl Into<String>,
        port: u16,
        user: impl Into<String>,
        password: impl Into<String>,
        database: Option<impl Into<String>>,
    ) -> Self {
        Self {
            host: host.into(),
            port,
            user: user.into(),
            password: password.into(),
            database: database.map(|d| d.into()),
        }
    }

    /// Read configuration from environment variables.
    ///
    /// Looks for `.env` file in the current directory and loads it if present.
    ///
    /// Environment variables (all optional, with defaults):
    /// - `PG_HOST` → default: "localhost"
    /// - `PG_PORT` → default: 5432
    /// - `PG_USER` → default: "postgres"
    /// - `PG_PASSWORD` → default: "postgres"
    /// - `PG_DATABASE` → default: None (connects to system db)
    pub fn from_env() -> Self {
        let _ = dotenvy::dotenv();
        Self {
            host: std::env::var("PG_HOST").unwrap_or_else(|_| "localhost".to_string()),
            port: std::env::var("PG_PORT")
                .ok()
                .and_then(|v| v.parse().ok())
                .unwrap_or(5432),
            user: std::env::var("PG_USER").unwrap_or_else(|_| "postgres".to_string()),
            password: std::env::var("PG_PASSWORD").unwrap_or_else(|_| "postgres".to_string()),
            database: std::env::var("PG_DATABASE").ok(),
        }
    }

    /// Load configuration from a YAML file.
    ///
    /// The YAML file should contain a mapping with keys: host, port, user,
    /// password, and optionally database.
    pub fn from_yaml(path: impl AsRef<Path>) -> Result<Self> {
        let content = std::fs::read_to_string(&path)
            .with_context(|| format!("Failed to read config file: {:?}", path.as_ref()))?;
        let config: Self = serde_yaml::from_str(&content)
            .with_context(|| format!("Failed to parse config file: {:?}", path.as_ref()))?;
        Ok(config)
    }

    /// Build a PostgreSQL connection string for the configured database.
    ///
    /// If `database` is None, returns a connection string without a database
    /// (useful for admin operations like creating/dropping databases).
    pub fn connection_string(&self) -> String {
        match &self.database {
            Some(db) => format!(
                "postgres://{}:{}@{}:{}/{}",
                self.user, self.password, self.host, self.port, db
            ),
            None => format!(
                "postgres://{}:{}@{}:{}",
                self.user, self.password, self.host, self.port
            ),
        }
    }

    /// Build a connection string for the system "postgres" database.
    ///
    /// This is useful for admin operations when you need to connect to
    /// PostgreSQL but don't have a specific database yet.
    pub fn system_connection_string(&self) -> String {
        format!(
            "postgres://{}:{}@{}:{}/postgres",
            self.user, self.password, self.host, self.port
        )
    }

    /// Create a new config with a specific database name.
    pub fn with_database(&self, database: impl Into<String>) -> Self {
        Self {
            host: self.host.clone(),
            port: self.port,
            user: self.user.clone(),
            password: self.password.clone(),
            database: Some(database.into()),
        }
    }

    /// Returns true if this config has a database name set.
    pub fn has_database(&self) -> bool {
        self.database.is_some()
    }
}

impl Default for PgConfig {
    fn default() -> Self {
        Self {
            host: "localhost".to_string(),
            port: 5432,
            user: "postgres".to_string(),
            password: "postgres".to_string(),
            database: None,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_connection_string_with_database() {
        let config = PgConfig::new("localhost", 5432, "user", "pass", Some("mydb"));
        assert_eq!(
            config.connection_string(),
            "postgres://user:pass@localhost:5432/mydb"
        );
    }

    #[test]
    fn test_connection_string_without_database() {
        let config = PgConfig::new("localhost", 5432, "user", "pass", None::<String>);
        assert_eq!(
            config.connection_string(),
            "postgres://user:pass@localhost:5432"
        );
    }

    #[test]
    fn test_system_connection_string() {
        let config = PgConfig::new("localhost", 5432, "user", "pass", None::<String>);
        assert_eq!(
            config.system_connection_string(),
            "postgres://user:pass@localhost:5432/postgres"
        );
    }

    #[test]
    fn test_with_database() {
        let config = PgConfig::new("localhost", 5432, "user", "pass", None::<String>);
        let with_db = config.with_database("mydb");
        assert_eq!(with_db.database, Some("mydb".to_string()));
        assert_eq!(with_db.host, config.host);
    }
}
