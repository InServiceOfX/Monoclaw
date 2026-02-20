//! Integration tests for pg-toolkit connection module.
//!
//! Tests: PgConfig, create_pool, create_system_pool
//!
//! Run with:
//!   cargo test --test test_connection
//!
//! Requires PostgreSQL running (see Scripts/DockerBuilds/knowledge-base/docker-compose.yml)

use pg_toolkit::{
    PgConfig,
    connection::{create_pool, create_system_pool},
    admin::database_exists,
};

mod common;
use common::TestDb;

#[tokio::test]
async fn test_create_pool_with_database() {
    let test_db = match TestDb::new().await {
        Some(db) => db,
        None => {
            eprintln!("Skipping test: PostgreSQL not available");
            return;
        }
    };

    let config = test_db.config_with_db();

    // Should be able to connect to the test database
    let pool = create_pool(&config).await;
    assert!(
        pool.is_ok(),
        "Should be able to connect to test database: {:?}",
        pool.err()
    );

    test_db.drop().await;
}

#[tokio::test]
async fn test_create_system_pool() {
    let config = PgConfig::from_env();

    // Try to connect to system database
    let pool = create_system_pool(&config).await;

    if pool.is_err() {
        eprintln!(
            "Skipping test: PostgreSQL not available ({:?})",
            pool.err()
        );
        return;
    }

    assert!(
        pool.is_ok(),
        "Should be able to connect to system database"
    );
}

#[tokio::test]
async fn test_config_from_env_uses_defaults() {
    // Test that from_env() produces a valid config
    let config = PgConfig::from_env();

    // Should have sensible defaults
    assert!(!config.host.is_empty());
    assert!(config.port > 0);
    assert!(!config.user.is_empty());
}

#[tokio::test]
async fn test_database_creation_and_pool_connection() {
    let test_db = match TestDb::new().await {
        Some(db) => db,
        None => {
            eprintln!("Skipping test: PostgreSQL not available");
            return;
        }
    };

    // Verify the database exists
    assert!(
        database_exists(test_db.config(), test_db.db_name())
            .await
            .unwrap(),
        "Database should exist after creation"
    );

    // Connect to it
    let config = test_db.config_with_db();
    let pool = create_pool(&config).await;
    assert!(
        pool.is_ok(),
        "Should be able to connect to newly created database"
    );

    test_db.drop().await;
}
