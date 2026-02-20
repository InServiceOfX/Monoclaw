//! Integration tests for pg-toolkit admin module.
//!
//! Tests: create_database, drop_database, database_exists,
//!        create_extension, extension_exists, list_databases, list_extensions
//!
//! Run with:
//!   cargo test --test test_admin
//!
//! Requires PostgreSQL running (see Scripts/DockerBuilds/knowledge-base/docker-compose.yml)

use pg_toolkit::{
    PgConfig,
    admin::{
        create_database, drop_database, database_exists, create_extension,
        extension_exists, list_databases, list_extensions,
    },
    connection::create_pool,
};
use std::time::{SystemTime, UNIX_EPOCH};

mod common;
use common::TestDb;

/// Generate a unique database name for testing.
fn test_db_name() -> String {
    let timestamp = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_millis();
    format!("pg_toolkit_admin_test_{}", timestamp)
}

#[tokio::test]
async fn test_create_and_drop_database() {
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

    test_db.drop().await;
}

#[tokio::test]
async fn test_database_lifecycle_idempotent() {
    // Test that create_database and drop_database are idempotent
    let config = PgConfig::from_env();

    // Try to connect to system database
    if pg_toolkit::connection::create_system_pool(&config).await.is_err() {
        eprintln!("Skipping test: PostgreSQL not available");
        return;
    }

    let db_name = test_db_name();

    // Create should succeed
    create_database(&config, &db_name)
        .await
        .expect("First create should succeed");

    // Second create should be a no-op (idempotent)
    create_database(&config, &db_name)
        .await
        .expect("Second create should succeed (idempotent)");

    // Verify it exists
    assert!(database_exists(&config, &db_name).await.unwrap());

    // Drop should succeed
    drop_database(&config, &db_name)
        .await
        .expect("First drop should succeed");

    // Second drop should be a no-op (idempotent)
    drop_database(&config, &db_name)
        .await
        .expect("Second drop should succeed (idempotent)");

    // Verify it doesn't exist
    assert!(!database_exists(&config, &db_name).await.unwrap());
}

#[tokio::test]
async fn test_pgvector_extension() {
    let test_db = match TestDb::new().await {
        Some(db) => db,
        None => {
            eprintln!("Skipping test: PostgreSQL not available");
            return;
        }
    };

    let config = test_db.config_with_db();
    let pool = create_pool(&config).await.expect("Failed to connect");

    // Create the extension
    create_extension(&pool, "vector")
        .await
        .expect("Failed to create extension");

    // Extension should exist now
    let exists_after = extension_exists(&pool, "vector").await.unwrap();
    assert!(
        exists_after,
        "pgvector extension should exist after creation"
    );

    // Creating again should be idempotent
    create_extension(&pool, "vector")
        .await
        .expect("Second create_extension should succeed (idempotent)");

    test_db.drop().await;
}

#[tokio::test]
async fn test_list_databases() {
    let test_db = match TestDb::new().await {
        Some(db) => db,
        None => {
            eprintln!("Skipping test: PostgreSQL not available");
            return;
        }
    };

    // List databases
    let databases = list_databases(test_db.config()).await.unwrap();

    // Should contain at least the test database and postgres
    assert!(
        databases.contains(&test_db.db_name().to_string()),
        "Should find the test database"
    );
    assert!(
        databases.contains(&"postgres".to_string()),
        "Should find postgres database"
    );

    test_db.drop().await;
}

#[tokio::test]
async fn test_list_extensions() {
    let test_db = match TestDb::new().await {
        Some(db) => db,
        None => {
            eprintln!("Skipping test: PostgreSQL not available");
            return;
        }
    };

    let config = test_db.config_with_db();
    let pool = create_pool(&config).await.expect("Failed to connect");

    // List extensions (will include default extensions)
    let extensions = list_extensions(&pool).await.unwrap();

    // Should have at least some default extensions
    assert!(
        !extensions.is_empty(),
        "Should have at least some extensions"
    );

    // Create pgvector and verify it's listed
    create_extension(&pool, "vector").await.ok();
    let extensions_after = list_extensions(&pool).await.unwrap();
    assert!(
        extensions_after.contains(&"vector".to_string()),
        "Should find pgvector extension after creation"
    );

    test_db.drop().await;
}
