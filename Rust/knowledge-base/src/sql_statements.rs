/// SQL statements for knowledge base operations.
///
/// All queries use PostgreSQL $N positional parameters (sqlx convention).
pub struct KnowledgeBaseSql;

impl KnowledgeBaseSql {
    pub const CREATE_VECTOR_EXTENSION: &'static str =
        "CREATE EXTENSION IF NOT EXISTS vector;";

    pub const CREATE_DOCUMENTS_TABLE: &'static str = "
        CREATE TABLE IF NOT EXISTS knowledge_base_documents (
            id SERIAL PRIMARY KEY,
            title TEXT,
            source_path TEXT,
            source_type VARCHAR(50),
            raw_content TEXT NOT NULL,
            content_hash VARCHAR(64) NOT NULL UNIQUE,
            metadata JSONB,
            ingested_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
    ";

    pub const CREATE_CHUNKS_TABLE: &'static str = "
        CREATE TABLE IF NOT EXISTS knowledge_base_chunks (
            id SERIAL PRIMARY KEY,
            document_id INTEGER NOT NULL REFERENCES knowledge_base_documents(id) ON DELETE CASCADE,
            chunk_index INTEGER NOT NULL,
            total_chunks INTEGER NOT NULL,
            content TEXT NOT NULL,
            content_hash VARCHAR(64) NOT NULL UNIQUE,
            embedding VECTOR(1024),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
    ";

    /// HNSW index on embedding + B-tree indexes on document_id and chunk_index.
    /// Executed as separate statements (sqlx does not support multi-statement in execute).
    pub const CREATE_HNSW_INDEX: &'static str = "
        CREATE INDEX IF NOT EXISTS idx_kb_chunks_embedding_hnsw
        ON knowledge_base_chunks
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64);
    ";

    pub const CREATE_DOCUMENT_ID_INDEX: &'static str = "
        CREATE INDEX IF NOT EXISTS idx_kb_chunks_document_id
        ON knowledge_base_chunks(document_id);
    ";

    pub const CREATE_CHUNK_INDEX_INDEX: &'static str = "
        CREATE INDEX IF NOT EXISTS idx_kb_chunks_chunk_index
        ON knowledge_base_chunks(chunk_index);
    ";

    /// Insert a document and return its id.
    /// Params: $1=title, $2=source_path, $3=source_type, $4=raw_content, $5=content_hash, $6=metadata
    pub const INSERT_DOCUMENT: &'static str = "
        INSERT INTO knowledge_base_documents (
            title, source_path, source_type, raw_content, content_hash, metadata
        ) VALUES (
            $1, $2, $3, $4, $5, $6
        ) RETURNING id;
    ";

    /// Insert a chunk and return its id.
    /// Params: $1=document_id, $2=chunk_index, $3=total_chunks, $4=content, $5=content_hash, $6=embedding
    pub const INSERT_CHUNK: &'static str = "
        INSERT INTO knowledge_base_chunks (
            document_id, chunk_index, total_chunks, content, content_hash, embedding
        ) VALUES (
            $1, $2, $3, $4, $5, $6
        ) RETURNING id;
    ";

    /// Retrieve a document by its primary key.
    /// Params: $1=id
    pub const GET_DOCUMENT_BY_ID: &'static str = "
        SELECT id, title, source_path, source_type, raw_content, content_hash,
               metadata, ingested_at
        FROM knowledge_base_documents
        WHERE id = $1;
    ";

    /// Retrieve a document by its content hash (for deduplication).
    /// Params: $1=content_hash
    pub const GET_DOCUMENT_BY_HASH: &'static str = "
        SELECT id, title, source_path, source_type, raw_content, content_hash,
               metadata, ingested_at
        FROM knowledge_base_documents
        WHERE content_hash = $1;
    ";

    /// Retrieve all chunks for a document, ordered by chunk_index.
    /// Params: $1=document_id
    pub const GET_DOCUMENT_CHUNKS: &'static str = "
        SELECT id, document_id, chunk_index, total_chunks, content, content_hash,
               created_at
        FROM knowledge_base_chunks
        WHERE document_id = $1
        ORDER BY chunk_index;
    ";

    /// Cosine similarity search over chunk embeddings, joining document metadata.
    /// Params: $1=query_vector (pgvector::Vector), $2=similarity_threshold (f32 or NULL), $3=limit (i64)
    pub const VECTOR_SIMILARITY_SEARCH: &'static str = "
        SELECT
            c.id,
            c.document_id,
            c.chunk_index,
            c.total_chunks,
            c.content,
            c.content_hash,
            c.created_at,
            d.title,
            d.source_path,
            d.source_type,
            1.0 - (c.embedding <=> $1) AS similarity_score
        FROM knowledge_base_chunks c
        JOIN knowledge_base_documents d ON c.document_id = d.id
        WHERE ($2::float4 IS NULL OR (1.0 - (c.embedding <=> $1)) >= $2::float4)
        ORDER BY c.embedding <=> $1
        LIMIT $3;
    ";

    /// Check whether a table exists in the current database.
    /// Params: $1=table_name
    pub const CHECK_TABLE_EXISTS: &'static str = "
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
          AND table_name = $1;
    ";
}
