from typing import List


class TextChunker:
    """Character-based text chunker with configurable size and overlap."""

    def chunk_text(
            self,
            text: str,
            chunk_size: int = 500,
            overlap: int = 50) -> List[str]:
        """
        Split text into overlapping character-based chunks.

        Args:
            text: The input text to chunk.
            chunk_size: Maximum number of characters per chunk.
            overlap: Number of characters to overlap between consecutive chunks.

        Returns:
            List of text chunk strings.
        """
        if not text:
            return []

        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive")

        if overlap < 0:
            raise ValueError("overlap must be non-negative")

        if overlap >= chunk_size:
            raise ValueError("overlap must be less than chunk_size")

        chunks = []
        start = 0
        text_length = len(text)

        while start < text_length:
            end = min(start + chunk_size, text_length)
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            if end == text_length:
                break
            start = end - overlap

        return chunks
