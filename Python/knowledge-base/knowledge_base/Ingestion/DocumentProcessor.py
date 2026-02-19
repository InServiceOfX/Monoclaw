from pathlib import Path
from typing import Optional
import hashlib

from ..Databases.PostgreSQLInterface import KnowledgeBaseInterface
from ..Embeddings.PplxContextEmbedder import PplxContextEmbedder
from ..Embeddings.TextChunker import TextChunker
from .FileIngester import FileIngester


class DocumentProcessor:
    """Orchestrates file ingestion, chunking, embedding, and DB persistence."""

    def __init__(
            self,
            embedder: PplxContextEmbedder,
            chunker: TextChunker,
            db_interface: KnowledgeBaseInterface,
            chunk_size: int = 500,
            overlap: int = 50):
        """
        Args:
            embedder: Loaded PplxContextEmbedder instance.
            chunker: TextChunker instance.
            db_interface: KnowledgeBaseInterface connected to the database.
            chunk_size: Characters per chunk.
            overlap: Overlap characters between consecutive chunks.
        """
        self._embedder = embedder
        self._chunker = chunker
        self._db = db_interface
        self._file_ingester = FileIngester()
        self._chunk_size = chunk_size
        self._overlap = overlap

    async def process_file(self, file_path: Path) -> Optional[int]:
        """
        Ingest a file, chunk, embed, and store in the database.

        Returns:
            The document ID on success, or None on failure / duplicate.
        """
        file_path = Path(file_path)
        doc_data = self._file_ingester.ingest_file(file_path)
        if doc_data is None:
            return None

        return await self.process_text(
            text=doc_data["raw_content"],
            title=doc_data["title"],
            source_type=doc_data["source_type"],
            source_path=doc_data["source_path"],
            metadata=doc_data.get("metadata")
        )

    async def process_text(
            self,
            text: str,
            title: str,
            source_type: str,
            source_path: Optional[str] = None,
            metadata: Optional[dict] = None) -> Optional[int]:
        """
        Chunk, embed, and store arbitrary text as a document.

        Returns:
            The document ID on success, or None on failure / duplicate.
        """
        content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()

        already_exists = await self._db.document_exists_by_hash(content_hash)
        if already_exists:
            print(f"Document already exists (hash={content_hash}), skipping.")
            return None

        document_id = await self._db.insert_document(
            title=title,
            source_path=source_path,
            source_type=source_type,
            raw_content=text,
            content_hash=content_hash,
            metadata=metadata
        )
        if document_id is None:
            print("Failed to insert document record.")
            return None

        chunks = self._chunker.chunk_text(
            text,
            chunk_size=self._chunk_size,
            overlap=self._overlap)

        if not chunks:
            print("No chunks produced from text.")
            return document_id

        embeddings_list = self._embedder.encode_single_document(chunks)

        total_chunks = len(chunks)
        for i, chunk_text in enumerate(chunks):
            chunk_hash = hashlib.sha256(
                f"{content_hash}:{i}:{chunk_text}".encode("utf-8")
            ).hexdigest()

            embedding = None
            if embeddings_list is not None and i < len(embeddings_list):
                embedding = embeddings_list[i].tolist()

            chunk_id = await self._db.insert_chunk(
                document_id=document_id,
                chunk_index=i,
                total_chunks=total_chunks,
                content=chunk_text,
                content_hash=chunk_hash,
                embedding=embedding
            )
            if chunk_id is None:
                print(f"Failed to insert chunk {i} for document {document_id}")

        print(
            f"Processed document '{title}' -> id={document_id}, "
            f"{total_chunks} chunks."
        )
        return document_id
