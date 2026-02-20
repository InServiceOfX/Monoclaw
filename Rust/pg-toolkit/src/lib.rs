//! Generic PostgreSQL toolkit for Rust applications.
//!
//! This crate provides common PostgreSQL operations that are not tied to any
//! specific domain or schema. It handles connection pooling, configuration,
//! database administration, and introspection.
//!
//! # Example
//! ```rust,no_run
//! use pg_toolkit::{PgConfig, create_pool};
//! use pg_toolkit::introspection::table_exists;
//!
//! #[tokio::main]
//! async fn main() -> anyhow::Result<()> {
//!     let config = PgConfig::from_env();
//!     let pool = create_pool(&config).await?;
//!
//!     // Check if a table exists
//!     let exists = table_exists(&pool, "my_table").await?;
//!     println!("Table exists: {}", exists);
//!
//!     Ok(())
//! }
//! ```

pub mod admin;
pub mod config;
pub mod connection;
pub mod introspection;

pub use config::PgConfig;
pub use connection::create_pool;
pub use introspection::TableInfo;
