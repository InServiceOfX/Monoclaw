/// Character-based text chunker with configurable size and overlap.
///
/// Mirrors the Python `TextChunker.chunk_text` logic exactly:
/// - slides a window of `chunk_size` characters,
/// - steps forward by `chunk_size - overlap` each iteration,
/// - strips whitespace from each chunk,
/// - skips empty chunks.
#[derive(Debug, Clone)]
pub struct TextChunker {
    pub chunk_size: usize,
    pub overlap: usize,
}

impl TextChunker {
    /// Create a new `TextChunker`.
    ///
    /// # Panics
    /// Panics if `chunk_size == 0` or `overlap >= chunk_size`.
    pub fn new(chunk_size: usize, overlap: usize) -> Self {
        assert!(chunk_size > 0, "chunk_size must be positive");
        assert!(overlap < chunk_size, "overlap must be less than chunk_size");
        Self { chunk_size, overlap }
    }

    /// Split `text` into overlapping character-based chunks.
    ///
    /// Returns an empty `Vec` if `text` is empty.
    pub fn chunk_text(&self, text: &str) -> Vec<String> {
        if text.is_empty() {
            return Vec::new();
        }

        // Work over char indices to handle multibyte UTF-8 correctly.
        let chars: Vec<char> = text.chars().collect();
        let text_len = chars.len();
        let step = self.chunk_size - self.overlap;

        let mut chunks = Vec::new();
        let mut start = 0usize;

        while start < text_len {
            let end = (start + self.chunk_size).min(text_len);
            let chunk: String = chars[start..end].iter().collect();
            let chunk = chunk.trim().to_string();
            if !chunk.is_empty() {
                chunks.push(chunk);
            }
            if end == text_len {
                break;
            }
            start += step;
        }

        chunks
    }
}

impl Default for TextChunker {
    fn default() -> Self {
        Self::new(500, 50)
    }
}
