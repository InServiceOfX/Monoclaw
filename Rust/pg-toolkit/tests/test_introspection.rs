//! Integration tests for pg-toolkit introspection module.
//!
//! Tests: table_exists, list_tables, list_columns, current_database
//!
//! Run with:
//!   cargo test --test test_introspection
//!
//! Requires PostgreSQL running (see Scripts/DockerBuilds/knowledge-base/docker-compose.yml)

use pg_toolkit::{
    connection::create_pool,
    introspection::{table_exists, list_tables, list_columns, current_database},
};

mod common;
use common::TestDb;

#[tokio::test]
async fn test_table_exists_and_list_tables() {
    let test_db = match TestDb::new().await {
        Some(db) => db,
        None => {
            eprintln!("Skipping test: PostgreSQL not available");
            return;
        }
    };

    let config = test_db.config_with_db();
    let pool = create_pool(&config).await.expect("Failed to connect");

    // Initially no user tables (or only default ones)
    let tables = list_tables(&pool).await.expect("Failed to list tables");
    let initial_count = tables.len();

    // Create a test table
    sqlx::query("CREATE TABLE test_table (id SERIAL PRIMARY KEY, name TEXT)")
        .execute(&pool)
        .await
        .expect("Failed to create test table");

    // Table should exist
    assert!(
        table_exists(&pool, "test_table").await.unwrap(),
        "test_table should exist"
    );

    // Non-existent table should not exist
    assert!(
        !table_exists(&pool, "non_existent_table").await.unwrap(),
        "non_existent_table should not exist"
    );

    // List tables should include it
    let tables_after = list_tables(&pool).await.unwrap();
    assert_eq!(tables_after.len(), initial_count + 1);
    assert!(tables_after.contains(&"test_table".to_string()));

    // Drop the table
    sqlx::query("DROP TABLE test_table")
        .execute(&pool)
        .await
        .expect("Failed to drop test table");

    // Table should no longer exist
    assert!(
        !table_exists(&pool, "test_table").await.unwrap(),
        "test_table should not exist after drop"
    );

    test_db.drop().await;
}

#[tokio::test]
async fn test_list_columns() {
    let test_db = match TestDb::new().await {
        Some(db) => db,
        None => {
            eprintln!("Skipping test: PostgreSQL not available");
            return;
        }
    };

    let config = test_db.config_with_db();
    let pool = create_pool(&config).await.expect("Failed to connect");

    // Create a test table with specific columns
    sqlx::query(
        "CREATE TABLE test_columns_table (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            count INTEGER DEFAULT 0
        )"
    )
    .execute(&pool)
    .await
    .expect("Failed to create test table");

    // List columns
    let columns = list_columns(&pool, "test_columns_table")
        .await
        .expect("Failed to list columns");

    // Should have the columns we created
    assert!(columns.contains(&"id".to_string()));
    assert!(columns.contains(&"name".to_string()));
    assert!(columns.contains(&"count".to_string()));

    // Non-existent table should return empty list
    let empty_columns = list_columns(&pool, "non_existent_table")
        .await
        .unwrap();
    assert!(empty_columns.is_empty());

    // Cleanup
    sqlx::query("DROP TABLE test_columns_table")
        .execute(&pool)
        .await
        .ok();

    test_db.drop().await;
}

#[tokio::test]
async fn test_current_database() {
    let test_db = match TestDb::new().await {
        Some(db) => db,
        None => {
            eprintln!("Skipping test: PostgreSQL not available");
            return;
        }
    };

    let config = test_db.config_with_db();
    let pool = create_pool(&config).await.expect("Failed to connect");

    // Get current database name
    let db_name = current_database(&pool).await.expect("Failed to get current database");

    // Should match the database we connected to
    assert_eq!(
        db_name,
        test_db.db_name(),
        "Current database should match the test database"
    );

    test_db.drop().await;
}

#[tokio::test]
async fn test_list_tables_includes_only_user_tables() {
    let test_db = match TestDb::new().await {
        Some(db) => db,
        None => {
            eprintln!("Skipping test: PostgreSQL not available");
            return;
        }
    };

    let config = test_db.config_with_db();
    let pool = create_pool(&config).await.expect("Failed to connect");

    // list_tables should exclude system tables
    let tables = list_tables(&pool).await.unwrap();

    // Should not contain pg_catalog or information_schema tables
    for table in &tables {
        assert!(!table.starts_with("pg_"), "Should not include pg_catalog tables");
    }

    // Create a user table and verify it's listed
    sqlx::query("CREATE TABLE user_test_table (id INTEGER)")
        .execute(&pool)
        .await
        .ok();

    let tables_after = list_tables(&pool).await.unwrap();
    assert!(
        tables_after.contains(&"user_test_table".to_string()),
        "User table should be listed"
    );

    // Cleanup
    sqlx::query("DROP TABLE user_test_table")
        .execute(&pool)
        .await
        .ok();

    test_db.drop().await;
}
