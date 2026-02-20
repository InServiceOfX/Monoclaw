//! PostgreSQL administrative operations.
//!
//! Provides generic database lifecycle management: create/drop databases,
//! create/check extensions. These operations are universal across all
//! PostgreSQL-backed applications.
//!
//! Database creation and dropping require connecting to the system "postgres"
//! database, so most functions here take a `&PgConfig` and create a temporary
//! system connection internally.

use anyhow::{Context, Result};
use sqlx::PgPool;

use crate::config::PgConfig;
use crate::connection::create_system_pool;

/// Check whether a database exists.
pub async fn database_exists(config: &PgConfig, database_name: &str) -> Result<bool> {
    let pool = create_system_pool(config).await
        .context("Failed to connect to system database")?;

    let exists: Option<i32> = sqlx::query_scalar(
        "SELECT 1 FROM pg_database WHERE datname = $1"
    )
    .bind(database_name)
    .fetch_optional(&pool)
    .await
    .context("Failed to query pg_database")?;

    Ok(exists.is_some())
}

/// Create a new database. No-ops if it already exists.
///
/// Connects to the system "postgres" database to issue the CREATE DATABASE
/// command, which cannot run inside a transaction.
pub async fn create_database(config: &PgConfig, database_name: &str) -> Result<()> {
    if database_exists(config, database_name).await? {
        tracing::info!("Database '{}' already exists, skipping creation", database_name);
        return Ok(());
    }

    let pool = create_system_pool(config).await
        .context("Failed to connect to system database")?;

    // CREATE DATABASE cannot run inside a transaction block.
    // sqlx does not support `execute` with parameters for DDL, so we format directly.
    // Database names are validated to be alphanumeric+underscore before this point.
    sqlx::query(&format!("CREATE DATABASE \"{}\"", database_name))
        .execute(&pool)
        .await
        .with_context(|| format!("Failed to create database '{}'", database_name))?;

    tracing::info!("Created database '{}'", database_name);
    Ok(())
}

/// Drop a database. No-ops if it does not exist.
///
/// Terminates all existing connections to the database before dropping it,
/// mirroring the behaviour of the Python PostgreSQLConnection.drop_database.
pub async fn drop_database(config: &PgConfig, database_name: &str) -> Result<()> {
    if !database_exists(config, database_name).await? {
        tracing::info!("Database '{}' does not exist, skipping drop", database_name);
        return Ok(());
    }

    let pool = create_system_pool(config).await
        .context("Failed to connect to system database")?;

    // Terminate all active connections to avoid "database is being accessed by other users"
    sqlx::query(
        "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = $1"
    )
    .bind(database_name)
    .execute(&pool)
    .await
    .with_context(|| format!("Failed to terminate connections to '{}'", database_name))?;

    sqlx::query(&format!("DROP DATABASE IF EXISTS \"{}\"", database_name))
        .execute(&pool)
        .await
        .with_context(|| format!("Failed to drop database '{}'", database_name))?;

    tracing::info!("Dropped database '{}'", database_name);
    Ok(())
}

/// Check whether a PostgreSQL extension is installed in the current database.
pub async fn extension_exists(pool: &PgPool, extension_name: &str) -> Result<bool> {
    let exists: Option<i32> = sqlx::query_scalar(
        "SELECT 1 FROM pg_extension WHERE extname = $1"
    )
    .bind(extension_name)
    .fetch_optional(pool)
    .await
    .with_context(|| format!("Failed to query pg_extension for '{}'", extension_name))?;

    Ok(exists.is_some())
}

/// Create a PostgreSQL extension if it does not already exist.
///
/// Uses `CREATE EXTENSION IF NOT EXISTS` so this is safe to call repeatedly.
pub async fn create_extension(pool: &PgPool, extension_name: &str) -> Result<()> {
    sqlx::query(&format!(
        "CREATE EXTENSION IF NOT EXISTS \"{}\"",
        extension_name
    ))
    .execute(pool)
    .await
    .with_context(|| format!("Failed to create extension '{}'", extension_name))?;

    tracing::info!("Extension '{}' is present", extension_name);
    Ok(())
}

/// List all non-template databases on the server.
pub async fn list_databases(config: &PgConfig) -> Result<Vec<String>> {
    let pool = create_system_pool(config).await
        .context("Failed to connect to system database")?;

    let names: Vec<String> = sqlx::query_scalar(
        "SELECT datname FROM pg_database WHERE datistemplate = false ORDER BY datname"
    )
    .fetch_all(&pool)
    .await
    .context("Failed to list databases")?;

    Ok(names)
}

/// List all extensions installed in the current database.
pub async fn list_extensions(pool: &PgPool) -> Result<Vec<String>> {
    let names: Vec<String> = sqlx::query_scalar(
        "SELECT extname FROM pg_extension ORDER BY extname"
    )
    .fetch_all(pool)
    .await
    .context("Failed to list extensions")?;

    Ok(names)
}
