//! Knowledge Base CLI — ingest files and search.
//!
//! # Ingest a file
//! cargo run --bin kb -- ingest /path/to/document.pdf
//!
//! # Search
//! cargo run --bin kb -- search "quantum field theory" --limit 5
//!
//! # Check embedding server health
//! cargo run --bin kb -- health

use std::path::PathBuf;

use anyhow::{Context, Result};
use clap::{Parser, Subcommand};
use knowledge_base::{
    configuration::config_from_env,
    embedding::{EmbeddingClient, EmbeddingClientConfig},
    ingestion::IngestPipeline,
};
use tracing::{error, info};

#[derive(Parser)]
#[command(name = "kb")]
#[command(about = "Knowledge Base CLI — ingest documents and search")]
struct Cli {
    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    /// Ingest a file (PDF, TXT, MD) into the knowledge base
    Ingest {
        /// Path to the file to ingest
        path: PathBuf,
    },
    /// Search the knowledge base
    Search {
        /// Query string
        query: String,
        /// Maximum number of results (default: 5)
        #[arg(short, long, default_value = "5")]
        limit: i64,
        /// Minimum similarity threshold (0.0–1.0, optional)
        #[arg(short, long)]
        threshold: Option<f32>,
    },
    /// Check embedding server health
    Health,
}

#[tokio::main]
async fn main() -> Result<()> {
    tracing_subscriber::fmt::init();
    let cli = Cli::parse();

    match cli.command {
        Commands::Ingest { path } => ingest_file(path).await,
        Commands::Search { query, limit, threshold } => search(query, limit, threshold).await,
        Commands::Health => check_health().await,
    }
}

async fn ingest_file(path: PathBuf) -> Result<()> {
    if !path.exists() {
        anyhow::bail!("File not found: {}", path.display());
    }

    let pg_config = config_from_env();
    let embedding_config = EmbeddingClientConfig::from_env();

    info!("Initializing pipeline...");
    let pipeline = IngestPipeline::new(&pg_config, embedding_config)
        .await
        .context("Failed to initialize ingest pipeline")?;

    info!("Ingesting {}...", path.display());
    let result = pipeline.ingest_file(&path).await
        .with_context(|| format!("Failed to ingest {}", path.display()))?;

    if result.was_duplicate {
        info!("Document already exists (duplicate). ID: {}", result.document_id);
    } else {
        info!(
            "Ingested document {} with {} chunks",
            result.document_id,
            result.chunks_inserted
        );
    }

    Ok(())
}

async fn search(query: String, limit: i64, threshold: Option<f32>) -> Result<()> {
    let pg_config = config_from_env();
    let embedding_config = EmbeddingClientConfig::from_env();

    info!("Initializing pipeline...");
    let pipeline = IngestPipeline::new(&pg_config, embedding_config)
        .await
        .context("Failed to initialize ingest pipeline")?;

    info!("Searching for: '{}'", query);
    let results = pipeline.search(&query, limit, threshold).await
        .context("Search failed")?;

    if results.is_empty() {
        println!("No results found.");
        return Ok(());
    }

    println!("\nFound {} result(s):\n", results.len());
    for (i, hit) in results.iter().enumerate() {
        let score_pct = hit.similarity_score * 100.0;
        println!(
            "[{}] {:.1}% — {} (chunk {}/{})",
            i + 1,
            score_pct,
            hit.title.as_deref().unwrap_or("(untitled)"),
            hit.chunk_index + 1,
            hit.total_chunks
        );
        if let Some(ref source) = hit.source_path {
            println!("    Source: {}", source);
        }
        println!("    Content: {}\n", truncate(&hit.content, 200));
    }

    Ok(())
}

async fn check_health() -> Result<()> {
    let config = EmbeddingClientConfig::from_env();
    let client = EmbeddingClient::new(config)
        .context("Failed to create embedding client")?;

    match client.health().await {
        Ok(resp) => {
            println!("Embedding server: OK");
            println!("  Model loaded: {}", resp.model_loaded);
            println!("  Status: {}", resp.status);
            Ok(())
        }
        Err(e) => {
            error!("Embedding server health check failed: {}", e);
            anyhow::bail!("Embedding server unreachable. Is it running?");
        }
    }
}

fn truncate(s: &str, max_len: usize) -> String {
    if s.len() <= max_len {
        s.to_string()
    } else {
        format!("{}...", &s[..max_len])
    }
}
