//! PostgreSQL schema introspection.
//!
//! Query-only operations for inspecting an existing database: listing tables,
//! checking existence, column info, etc. None of these mutate the schema.

use anyhow::{Context, Result};
use serde::{Deserialize, Serialize};
use sqlx::PgPool;

/// Metadata for a single user table, mirroring the columns exposed by
/// `pg_tables` (minus system schemas).
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct TableInfo {
    /// Schema the table belongs to (e.g. `"public"`).
    pub schema: String,
    /// Table name.
    pub name: String,
    /// Role that owns the table.
    pub owner: String,
    /// Tablespace name, if explicitly set; `None` means the default tablespace.
    pub tablespace: Option<String>,
    pub has_indexes: bool,
    pub has_rules: bool,
    pub has_triggers: bool,
    pub row_security: bool,
}

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

/// List all user tables across all non-system schemas, with full metadata.
///
/// Excludes `information_schema` and `pg_catalog`. Results are ordered by
/// schema then table name.
pub async fn list_tables(pool: &PgPool) -> Result<Vec<TableInfo>> {
    let rows = sqlx::query_as::<_, (String, String, String, Option<String>, bool, bool, bool, bool)>(
        "SELECT schemaname, tablename, tableowner, tablespace, \
                hasindexes, hasrules, hastriggers, rowsecurity \
         FROM pg_tables \
         WHERE schemaname NOT IN ('information_schema', 'pg_catalog') \
         ORDER BY schemaname, tablename",
    )
    .fetch_all(pool)
    .await
    .context("Failed to list tables")?;

    Ok(rows
        .into_iter()
        .map(|(schema, name, owner, tablespace, has_indexes, has_rules, has_triggers, row_security)| {
            TableInfo { schema, name, owner, tablespace, has_indexes, has_rules, has_triggers, row_security }
        })
        .collect())
}

/// List just the table names in non-system schemas.
///
/// Cheaper than `list_tables` when you only need names.
pub async fn list_table_names(pool: &PgPool) -> Result<Vec<String>> {
    let names: Vec<String> = sqlx::query_scalar(
        "SELECT tablename FROM pg_tables \
         WHERE schemaname NOT IN ('information_schema', 'pg_catalog') \
         ORDER BY tablename",
    )
    .fetch_all(pool)
    .await
    .context("Failed to list table names")?;

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
