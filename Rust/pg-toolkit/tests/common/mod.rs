//! Common test utilities for pg-toolkit integration tests.

use pg_toolkit::{
    PgConfig,
    admin::{create_database, drop_database},
    connection::create_system_pool,
};
use std::time::{SystemTime, UNIX_EPOCH};

/// Generate a unique database name for testing.
pub fn test_db_name() -> String {
    let timestamp = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_millis();
    format!("pg_toolkit_test_{}", timestamp)
}

/// Test database guard that creates a DB on construction and drops it on drop.
/// This ensures cleanup even if the test panics.
pub struct TestDb {
    config: PgConfig,
    db_name: String,
    dropped: bool,
}

impl TestDb {
    pub async fn new() -> Option<Self> {
        let config = PgConfig::from_env();

        // Try to connect to system database first
        match create_system_pool(&config).await {
            Ok(_) => {}
            Err(e) => {
                eprintln!(
                    "Warning: Could not connect to PostgreSQL ({}). Skipping integration tests.",
                    e
                );
                return None;
            }
        }

        let db_name = test_db_name();

        // Create the test database
        if let Err(e) = create_database(&config, &db_name).await {
            eprintln!("Failed to create test database: {}", e);
            return None;
        }

        Some(Self {
            config,
            db_name,
            dropped: false,
        })
    }

    pub fn db_name(&self) -> &str {
        &self.db_name
    }

    pub fn config(&self) -> &PgConfig {
        &self.config
    }

    pub fn config_with_db(&self) -> PgConfig {
        self.config.with_database(&self.db_name)
    }

    pub async fn drop(mut self) {
        if !self.dropped {
            let _ = drop_database(&self.config, &self.db_name).await;
            self.dropped = true;
        }
    }
}

impl Drop for TestDb {
    fn drop(&mut self) {
        if !self.dropped {
            // We can't run async code in Drop, so spawn a blocking task
            // This is best-effort cleanup
            let config = self.config.clone();
            let db_name = self.db_name.clone();
            std::thread::spawn(move || {
                let rt = tokio::runtime::Runtime::new().unwrap();
                rt.block_on(async {
                    let _ = drop_database(&config, &db_name).await;
                });
            });
        }
    }
}
