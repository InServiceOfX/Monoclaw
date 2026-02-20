//! PostgreSQL schema introspection.
//!
//! Query-only operations for inspecting an existing database: listing tables,
//! checking existence, column info, etc. None of these mutate the schema.

use anyhow::{Context, Result};
use sqlx::PgPool;

/// Return true if a table with the given name exists in the public schema.
pub async fn table_exists(pool: &PgPool, table_name: &str) -> Result<bool> {
    let exists: Option<i32> = sqlx::query_scalar(
        "SELECT 1 FROM information_schema.tables \
         WHERE table_schema = 'public' AND table_name = $1"
    )
    .bind(table_name)
    .fetch_optional(pool)
    .await
    .with_context(|| format!("Failed to check if table '{}' exists", table_name))?;

    Ok(exists.is_some())
}

/// List all user table names in the public schema.
pub async fn list_tables(pool: &PgPool) -> Result<Vec<String>> {
    let names: Vec<String> = sqlx::query_scalar(
        "SELECT tablename FROM pg_tables \
         WHERE schemaname NOT IN ('information_schema', 'pg_catalog') \
         ORDER BY tablename"
    )
    .fetch_all(pool)
    .await
    .context("Failed to list tables")?;

    Ok(names)
}

/// Return a list of column names for the given table.
pub async fn list_columns(pool: &PgPool, table_name: &str) -> Result<Vec<String>> {
    let names: Vec<String> = sqlx::query_scalar(
        "SELECT column_name FROM information_schema.columns \
         WHERE table_schema = 'public' AND table_name = $1 \
         ORDER BY ordinal_position"
    )
    .bind(table_name)
    .fetch_all(pool)
    .await
    .with_context(|| format!("Failed to list columns for table '{}'", table_name))?;

    Ok(names)
}

/// Return the current database name the pool is connected to.
pub async fn current_database(pool: &PgPool) -> Result<String> {
    let name: String = sqlx::query_scalar("SELECT current_database()")
        .fetch_one(pool)
        .await
        .context("Failed to get current database name")?;

    Ok(name)
}
