//! Integration tests for pg-toolkit introspection module.
//!
//! Tests: table_exists, list_tables, list_table_names, list_columns,
//!        current_database
//!
//! Run with:
//!   cargo test --test test_introspection
//!
//! Requires PostgreSQL running (see Scripts/DockerBuilds/knowledge-base/docker-compose.yml)

use pg_toolkit::{
    connection::create_pool,
    introspection::{table_exists, list_tables, list_table_names, list_columns, current_database},
};

mod common;
use common::TestDb;

#[tokio::test]
async fn test_table_exists_and_list_table_names() {
    let test_db = match TestDb::new().await {
        Some(db) => db,
        None => {
            eprintln!("Skipping test: PostgreSQL not available");
            return;
        }
    };

    let config = test_db.config_with_db();
    let pool = create_pool(&config).await.expect("Failed to connect");

    // Initially no user tables
    let names = list_table_names(&pool).await.expect("Failed to list table names");
    let initial_count = names.len();

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

    // list_table_names should include it
    let names_after = list_table_names(&pool).await.unwrap();
    assert_eq!(names_after.len(), initial_count + 1);
    assert!(names_after.contains(&"test_table".to_string()));

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
async fn test_list_tables_full_info() {
    let test_db = match TestDb::new().await {
        Some(db) => db,
        None => {
            eprintln!("Skipping test: PostgreSQL not available");
            return;
        }
    };

    let config = test_db.config_with_db();
    let pool = create_pool(&config).await.expect("Failed to connect");

    sqlx::query("CREATE TABLE info_test_table (id SERIAL PRIMARY KEY, val TEXT)")
        .execute(&pool)
        .await
        .expect("Failed to create test table");

    let tables = list_tables(&pool).await.expect("Failed to list tables");

    let entry = tables
        .iter()
        .find(|t| t.name == "info_test_table")
        .expect("info_test_table should appear in list_tables");

    assert_eq!(entry.schema, "public");
    // owner is whatever role created the table; just assert it's non-empty
    assert!(!entry.owner.is_empty());
    // A freshly-created table with a PRIMARY KEY will have an index
    assert!(entry.has_indexes, "table with PK should have indexes");

    // Cleanup
    sqlx::query("DROP TABLE info_test_table")
        .execute(&pool)
        .await
        .ok();

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

    assert!(columns.contains(&"id".to_string()));
    assert!(columns.contains(&"name".to_string()));
    assert!(columns.contains(&"count".to_string()));

    // Non-existent table should return empty list
    let empty_columns = list_columns(&pool, "non_existent_table").await.unwrap();
    assert!(empty_columns.is_empty());

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

    let db_name = current_database(&pool).await.expect("Failed to get current database");
    assert_eq!(db_name, test_db.db_name());

    test_db.drop().await;
}

#[tokio::test]
async fn test_list_tables_excludes_system_tables() {
    let test_db = match TestDb::new().await {
        Some(db) => db,
        None => {
            eprintln!("Skipping test: PostgreSQL not available");
            return;
        }
    };

    let config = test_db.config_with_db();
    let pool = create_pool(&config).await.expect("Failed to connect");

    // Neither list_tables nor list_table_names should surface pg_catalog entries
    let tables = list_tables(&pool).await.unwrap();
    for t in &tables {
        assert!(!t.name.starts_with("pg_"), "Should not include pg_catalog tables");
    }

    let names = list_table_names(&pool).await.unwrap();
    for name in &names {
        assert!(!name.starts_with("pg_"), "Should not include pg_catalog tables");
    }

    // Create a user table and verify both functions see it
    sqlx::query("CREATE TABLE user_test_table (id INTEGER)")
        .execute(&pool)
        .await
        .ok();

    let tables_after = list_tables(&pool).await.unwrap();
    assert!(
        tables_after.iter().any(|t| t.name == "user_test_table"),
        "list_tables should include user_test_table"
    );

    let names_after = list_table_names(&pool).await.unwrap();
    assert!(
        names_after.contains(&"user_test_table".to_string()),
        "list_table_names should include user_test_table"
    );

    sqlx::query("DROP TABLE user_test_table")
        .execute(&pool)
        .await
        .ok();

    test_db.drop().await;
}
