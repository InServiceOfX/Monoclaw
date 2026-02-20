//! Integration tests for pg-toolkit.
//!
//! These tests require a running PostgreSQL instance. They will create and drop
//! temporary databases to avoid polluting the test environment.
//!
//! To run:
//!   cargo test --test integration_test
//!
//! Requires PostgreSQL running (see Scripts/DockerBuilds/knowledge-base/docker-compose.yml)

use pg_toolkit::{
    PgConfig, create_pool,
    connection::create_system_pool,
    admin::{create_database, drop_database, database_exists, create_extension, extension_exists},
    introspection::{table_exists, list_tables},
};
use std::time::{SystemTime, UNIX_EPOCH};

/// Generate a unique database name for testing.
fn test_db_name() -> String {
    let timestamp = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_millis();
    format!("pg_toolkit_test_{}", timestamp)
}

/// Test database guard that creates a DB on construction and drops it on drop.
/// This ensures cleanup even if the test panics.
struct TestDb {
    config: PgConfig,
    db_name: String,
    dropped: bool,
}

impl TestDb {
    async fn new() -> Option<Self> {
        let config = PgConfig::from_env();
        
        // Try to connect to system database first
        match create_system_pool(&config).await {
            Ok(_) => {}
            Err(e) => {
                eprintln!("Warning: Could not connect to PostgreSQL ({}). Skipping integration tests.", e);
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
    
    fn db_name(&self) -> &str {
        &self.db_name
    }
    
    fn config(&self) -> &PgConfig {
        &self.config
    }
    
    fn config_with_db(&self) -> PgConfig {
        self.config.with_database(&self.db_name)
    }
    
    async fn drop(mut self) {
        if !self.dropped {
            let _ = drop_database(&self.config, &self.db_name).await;
            self.dropped = true;
        }
    }
}

impl Drop for TestDb {
    fn drop(&mut self) {
        if !self.dropped {
            // We can't run async code in Drop, so we spawn a blocking task
            // This is a best-effort cleanup
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
        database_exists(test_db.config(), test_db.db_name()).await.unwrap(),
        "Database should exist after creation"
    );
    
    // Clean up
    test_db.drop().await;
}

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
    assert!(pool.is_ok(), "Should be able to connect to test database");
    
    test_db.drop().await;
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
    
    // Extension should not exist initially (pgvector might already be installed in Docker)
    let _exists_before = extension_exists(&pool, "vector").await.unwrap();
    // Note: pgvector might already be installed in the Docker image
    
    // Create the extension
    create_extension(&pool, "vector").await.expect("Failed to create extension");
    
    // Extension should exist now
    let exists_after = extension_exists(&pool, "vector").await.unwrap();
    assert!(exists_after, "pgvector extension should exist after creation");
    
    test_db.drop().await;
}

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
    
    // Initially no user tables
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
async fn test_database_lifecycle_idempotent() {
    // Test that create_database and drop_database are idempotent
    let config = PgConfig::from_env();
    
    // Try to connect to system database
    if create_system_pool(&config).await.is_err() {
        eprintln!("Skipping test: PostgreSQL not available");
        return;
    }
    
    let db_name = test_db_name();
    
    // Create should succeed
    create_database(&config, &db_name).await.expect("First create should succeed");
    
    // Second create should be a no-op (idempotent)
    create_database(&config, &db_name).await.expect("Second create should succeed (idempotent)");
    
    // Verify it exists
    assert!(database_exists(&config, &db_name).await.unwrap());
    
    // Drop should succeed
    drop_database(&config, &db_name).await.expect("First drop should succeed");
    
    // Second drop should be a no-op (idempotent)
    drop_database(&config, &db_name).await.expect("Second drop should succeed (idempotent)");
    
    // Verify it doesn't exist
    assert!(!database_exists(&config, &db_name).await.unwrap());
}
