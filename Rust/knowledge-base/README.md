# knowledge-base

A personal semantic search engine for your documents.

## What It Does

`kb` lets you ingest documents (PDFs for now) and search them using natural language. Instead of keyword matching, it uses vector embeddings to find conceptually similar content.

## Quick Start

```bash
# Ingest a document
./target/release/kb ingest /path/to/document.pdf

# Search your knowledge base
./target/release/kb search "what are the tax changes for 2026" --limit 5
```

## Requirements

- PostgreSQL 14+ with pgvector extension
- Rust toolchain (for building)
- OpenAI API key (for embeddings) or local embedding server

## Setup

1. **Database**: Ensure PostgreSQL is running with pgvector:
   ```bash
   # Using Docker
   docker run -d \
     -e POSTGRES_PASSWORD=postgres \
     -e POSTGRES_DB=knowledge_base \
     -p 5432:5432 \
     pgvector/pgvector:pg16
   ```

2. **Environment**: Create a `.env` file:
   ```
   DATABASE_URL=postgres://postgres:postgres@localhost/knowledge_base
   OPENAI_API_KEY=your_key_here  # or use local embedding server
   ```

3. **Build**:
   ```bash
   cargo build --release
   ```

## How It Works

1. **Ingestion**: PDFs are parsed, text is extracted, and content is split into overlapping chunks
2. **Embedding**: Each chunk is converted to a vector embedding (OpenAI API or local)
3. **Storage**: Chunks + embeddings are stored in PostgreSQL with pgvector
4. **Search**: Query is embedded and matched against stored vectors using cosine similarity

## CLI Reference

### `kb ingest <path>`

Ingest a PDF into the knowledge base.

- Extracts text using `pdf-extract`
- Chunks into ~500 token segments with overlap
- Generates embeddings
- Stores with source path and chunk metadata

### `kb search "<query>" [--limit N]`

Semantic search over ingested documents.

- `--limit`: Number of results (default: 10)
- Results include:
  - Relevance score (higher = more similar)
  - Source file path
  - Chunk number
  - Content snippet

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│   PDF File  │────▶│ Text Extract │────▶│  Chunk + Embed  │
└─────────────┘     └──────────────┘     └─────────────────┘
                                                  │
                                                  ▼
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│  Results    │◀────│  pgvector    │◀────│  PostgreSQL     │
│  (CLI)      │     │  similarity  │     │  storage        │
└─────────────┘     └──────────────┘     └─────────────────┘
```

## Project Structure

```
knowledge-base/
├── src/
│   ├── main.rs              # CLI entry point
│   ├── lib.rs               # Library exports
│   ├── models.rs            # Data models (Document, Chunk, etc.)
│   ├── configuration.rs     # Config loading (env, files)
│   ├── database/
│   │   └── connection.rs    # Database pool management
│   └── ingestion/
│       ├── mod.rs           # Ingestion module
│       ├── pipeline.rs      # Orchestrates ingest flow
│       ├── file_ingester.rs # File handling + hash
│       └── text_chunker.rs  # Text splitting logic
├── Configurations/
│   └── base.yaml            # Default configuration
├── Cargo.toml
└── tests/
    └── integration_test.rs  # Integration tests
```

## Configuration

Configuration is loaded from (in order of precedence):
1. Environment variables
2. `.env` file
3. `Configurations/base.yaml`

Key settings:
- `database_url`: PostgreSQL connection string
- `openai_api_key`: For embeddings (if using OpenAI)
- `embedding_server_url`: For local embedding server
- `chunk_size`: Tokens per chunk (default: 500)
- `chunk_overlap`: Overlap between chunks (default: 50)

## Development

```bash
# Run tests
cargo test

# Run with logging
RUST_LOG=info cargo run -- search "query"

# Build release
cargo build --release
```

## Future Ideas

- [ ] Support more file types (txt, md, docx)
- [ ] Incremental updates (detect changed files)
- [ ] Web UI for browsing/searching
- [ ] Hybrid search (semantic + keyword)
- [ ] Document-level metadata filtering
- [ ] Export search results

## License

MIT
