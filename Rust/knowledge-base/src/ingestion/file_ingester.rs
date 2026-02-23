use anyhow::{bail, Context, Result};
use sha2::{Digest, Sha256};
use std::path::Path;

/// The result of ingesting a file — raw document fields ready for DB insertion.
#[derive(Debug, Clone)]
pub struct IngestedDocument {
    pub title: String,
    pub source_path: String,
    pub source_type: String,
    pub raw_content: String,
    pub metadata: Option<serde_json::Value>,
}

/// Reads supported file types (.txt, .md) and returns document fields.
#[derive(Debug, Default)]
pub struct FileIngester;

impl FileIngester {
    pub fn new() -> Self {
        Self
    }

    /// Read a file and return an `IngestedDocument`.
    ///
    /// Supported extensions: `.txt`, `.md`
    /// Returns `Err` for unsupported file types or I/O failures.
    pub fn ingest_file(path: &Path) -> Result<IngestedDocument> {
        if !path.exists() {
            bail!("File not found: {}", path.display());
        }

        let extension = path
            .extension()
            .and_then(|e| e.to_str())
            .unwrap_or("")
            .to_lowercase();

        match extension.as_str() {
            "txt" | "md" => Self::ingest_text_file(path),
            "pdf" => Self::ingest_pdf_file(path),
            other => bail!("Unsupported file type: .{}", other),
        }
    }

    fn ingest_text_file(path: &Path) -> Result<IngestedDocument> {
        let raw_content = std::fs::read_to_string(path)
            .with_context(|| format!("Failed to read file: {}", path.display()))?;

        let source_type = if path
            .extension()
            .and_then(|e| e.to_str())
            .map(|e| e.eq_ignore_ascii_case("md"))
            .unwrap_or(false)
        {
            "markdown".to_string()
        } else {
            "text".to_string()
        };

        let title = path
            .file_stem()
            .and_then(|s| s.to_str())
            .unwrap_or("untitled")
            .to_string();

        let source_path = path
            .canonicalize()
            .unwrap_or_else(|_| path.to_path_buf())
            .to_string_lossy()
            .to_string();

        let size_bytes = path.metadata().map(|m| m.len()).unwrap_or(0);
        let filename = path
            .file_name()
            .and_then(|f| f.to_str())
            .unwrap_or("")
            .to_string();

        let metadata = serde_json::json!({
            "filename": filename,
            "size_bytes": size_bytes,
        });

        Ok(IngestedDocument {
            title,
            source_path,
            source_type,
            raw_content,
            metadata: Some(metadata),
        })
    }

    fn ingest_pdf_file(path: &Path) -> Result<IngestedDocument> {
        let raw_content = pdf_extract::extract_text(path)
            .with_context(|| format!("Failed to extract text from PDF: {}", path.display()))?;

        if raw_content.trim().is_empty() {
            bail!(
                "PDF contains no extractable text (scanned/image-only?): {}",
                path.display()
            );
        }

        let title = path
            .file_stem()
            .and_then(|s| s.to_str())
            .unwrap_or("untitled")
            .to_string();

        let source_path = path
            .canonicalize()
            .unwrap_or_else(|_| path.to_path_buf())
            .to_string_lossy()
            .to_string();

        let size_bytes = path.metadata().map(|m| m.len()).unwrap_or(0);
        let filename = path
            .file_name()
            .and_then(|f| f.to_str())
            .unwrap_or("")
            .to_string();

        let metadata = serde_json::json!({
            "filename": filename,
            "size_bytes": size_bytes,
        });

        Ok(IngestedDocument {
            title,
            source_path,
            source_type: "pdf".to_string(),
            raw_content,
            metadata: Some(metadata),
        })
    }

    /// Compute the SHA-256 hex digest of a string.
    pub fn compute_sha256(content: &str) -> String {
        let mut hasher = Sha256::new();
        hasher.update(content.as_bytes());
        hex::encode(hasher.finalize())
    }
}
