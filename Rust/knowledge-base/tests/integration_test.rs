// Integration tests for the knowledge-base crate.
//
// Run with:
//   cargo test --features integration --test integration_test
//
// Requires PostgreSQL running with the knowledge_base database.
// See: Scripts/DockerBuilds/knowledge-base/docker-compose.yml
//
// If the DB is unavailable, tests skip gracefully with a warning message.

#[cfg(feature = "integration")]
mod tests {
    use knowledge_base::{
        configuration::KnowledgeBaseConfig,
        database::connection::{create_pool, KnowledgeBaseDb},
        ingestion::{FileIngester, TextChunker},
        models::{InsertChunk, InsertDocument},
    };

    async fn setup_db() -> Option<KnowledgeBaseDb> {
        let config = KnowledgeBaseConfig::from_env();
        match create_pool(&config).await {
            Ok(pool) => {
                let db = KnowledgeBaseDb::new(pool);
                Some(db)
            }
            Err(e) => {
                eprintln!(
                    "Warning: Could not connect to DB ({}). \
                     Skipping integration tests. Run docker-compose up first.",
                    e
                );
                None
            }
        }
    }

    #[tokio::test]
    async fn test_create_tables_works() {
        let Some(db) = setup_db().await else {
            return;
        };
        db.create_extension().await.expect("create_extension failed");
        db.create_tables().await.expect("create_tables failed");
    }

    #[tokio::test]
    async fn test_insert_and_retrieve_document() {
        let Some(db) = setup_db().await else {
            return;
        };
        db.create_extension().await.expect("create_extension failed");
        db.create_tables().await.expect("create_tables failed");

        let content = "Integration test document content — unique at ".to_string()
            + &std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_nanos()
                .to_string();
        let content_hash = FileIngester::compute_sha256(&content);

        let doc = InsertDocument {
            title: Some("Integration Test Doc".to_string()),
            source_path: Some("/tmp/integration_test.txt".to_string()),
            source_type: Some("text".to_string()),
            raw_content: content.clone(),
            content_hash: content_hash.clone(),
            metadata: Some(serde_json::json!({ "test": true })),
        };

        let doc_id = db.insert_document(&doc).await.expect("insert_document failed");
        assert!(doc_id > 0, "Expected positive document id");

        // Confirm it exists by hash
        let exists = db
            .document_exists_by_hash(&content_hash)
            .await
            .expect("document_exists_by_hash failed");
        assert!(exists, "Document should exist by hash after insertion");

        // Retrieve by id
        let retrieved = db
            .get_document_by_id(doc_id)
            .await
            .expect("get_document_by_id failed");
        assert!(retrieved.is_some(), "Should retrieve document by id");
        assert_eq!(retrieved.unwrap().content_hash, content_hash);

        // Clean up
        db.drop_tables().await.expect("drop_tables failed");
    }

    #[tokio::test]
    async fn test_vector_similarity_search() {
        let Some(db) = setup_db().await else {
            return;
        };
        db.create_extension().await.expect("create_extension failed");
        db.create_tables().await.expect("create_tables failed");

        let content = "Vector similarity search test document — ".to_string()
            + &std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_nanos()
                .to_string();
        let content_hash = FileIngester::compute_sha256(&content);

        let doc = InsertDocument {
            title: Some("Similarity Test".to_string()),
            source_path: None,
            source_type: Some("text".to_string()),
            raw_content: content.clone(),
            content_hash: content_hash.clone(),
            metadata: None,
        };

        let doc_id = db.insert_document(&doc).await.expect("insert_document failed");

        // Insert a chunk with a known 1024-dim embedding
        let embedding: Vec<f32> = (0..1024).map(|i| (i as f32) / 1024.0).collect();
        let chunk_hash = FileIngester::compute_sha256(&format!("{}:0:chunk text", content_hash));

        let chunk = InsertChunk {
            document_id: doc_id,
            chunk_index: 0,
            total_chunks: 1,
            content: "chunk text".to_string(),
            content_hash: chunk_hash,
            embedding: Some(embedding.clone()),
        };

        db.insert_chunk(&chunk).await.expect("insert_chunk failed");

        // Query with the same embedding — should return similarity ~1.0
        let results = db
            .vector_similarity_search(&embedding, None, 5)
            .await
            .expect("vector_similarity_search failed");

        assert!(!results.is_empty(), "Expected at least one similarity result");
        let top = &results[0];
        assert!((top.similarity_score - 1.0).abs() < 1e-4, "Expected near-perfect similarity");

        // Clean up
        db.drop_tables().await.expect("drop_tables failed");
    }

    #[tokio::test]
    async fn test_text_chunker_basic() {
        let chunker = TextChunker::new(10, 2);
        let text = "Hello, world! This is a test.";
        let chunks = chunker.chunk_text(text);
        assert!(!chunks.is_empty(), "Should produce at least one chunk");
        // Each chunk should be at most chunk_size characters
        for chunk in &chunks {
            assert!(chunk.chars().count() <= 10);
        }
    }

    #[tokio::test]
    async fn test_file_ingester_sha256() {
        let hash = FileIngester::compute_sha256("hello");
        // Known SHA-256 of "hello"
        assert_eq!(
            hash,
            "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"
        );
    }
}
