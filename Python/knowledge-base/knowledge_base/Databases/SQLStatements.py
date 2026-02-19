class KnowledgeBaseSQLStatements:
    """Static class containing SQL statements for knowledge base operations."""

    CREATE_DOCUMENTS_TABLE = """
    CREATE TABLE IF NOT EXISTS knowledge_base_documents (
        id SERIAL PRIMARY KEY,
        title TEXT,
        source_path TEXT,
        source_type VARCHAR(50),
        raw_content TEXT NOT NULL,
        content_hash VARCHAR(64) NOT NULL UNIQUE,
        metadata JSONB,
        ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """

    CREATE_CHUNKS_TABLE = """
    CREATE TABLE IF NOT EXISTS knowledge_base_chunks (
        id SERIAL PRIMARY KEY,
        document_id INTEGER NOT NULL REFERENCES knowledge_base_documents(id) ON DELETE CASCADE,
        chunk_index INTEGER NOT NULL,
        total_chunks INTEGER NOT NULL,
        content TEXT NOT NULL,
        content_hash VARCHAR(64) NOT NULL UNIQUE,
        embedding VECTOR(1024),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """

    CREATE_CHUNKS_INDEXES = """
    CREATE INDEX IF NOT EXISTS idx_kb_chunks_embedding_hnsw
    ON knowledge_base_chunks
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

    CREATE INDEX IF NOT EXISTS idx_kb_chunks_document_id
    ON knowledge_base_chunks(document_id);

    CREATE INDEX IF NOT EXISTS idx_kb_chunks_chunk_index
    ON knowledge_base_chunks(chunk_index);
    """

    INSERT_DOCUMENT = """
    INSERT INTO knowledge_base_documents (
        title, source_path, source_type, raw_content, content_hash, metadata
    ) VALUES (
        $1, $2, $3, $4, $5, $6
    ) RETURNING id;
    """

    INSERT_CHUNK = """
    INSERT INTO knowledge_base_chunks (
        document_id, chunk_index, total_chunks, content, content_hash, embedding
    ) VALUES (
        $1, $2, $3, $4, $5, $6
    ) RETURNING id;
    """

    GET_DOCUMENT_BY_ID = """
    SELECT id, title, source_path, source_type, raw_content, content_hash,
           metadata, ingested_at
    FROM knowledge_base_documents
    WHERE id = $1;
    """

    GET_DOCUMENT_BY_HASH = """
    SELECT id, title, source_path, source_type, raw_content, content_hash,
           metadata, ingested_at
    FROM knowledge_base_documents
    WHERE content_hash = $1;
    """

    GET_DOCUMENT_CHUNKS = """
    SELECT id, document_id, chunk_index, total_chunks, content, content_hash,
           embedding, created_at
    FROM knowledge_base_chunks
    WHERE document_id = $1
    ORDER BY chunk_index;
    """

    VECTOR_SIMILARITY_SEARCH = """
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
        1 - (c.embedding <=> $1) AS similarity_score
    FROM knowledge_base_chunks c
    JOIN knowledge_base_documents d ON c.document_id = d.id
    WHERE ($2::float IS NULL OR (1 - (c.embedding <=> $1)) >= $2::float)
    ORDER BY c.embedding <=> $1
    LIMIT $3;
    """
