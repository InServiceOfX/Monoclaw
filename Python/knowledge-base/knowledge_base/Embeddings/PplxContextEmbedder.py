from pathlib import Path
from typing import List, Optional
import numpy as np

DEFAULT_MODEL_PATH = (
    "/media/propdev/9dc1a908-7eff-4e1c-8231-ext4"
    "/home/propdev/Data/Models/Embeddings/perplexity-ai"
    "/pplx-embed-context-v1-0.6b"
)

DEFAULT_DEVICE = "cuda:1"  # RTX 3060 is GPU device 1


class PplxContextEmbedder:
    """Wrapper around pplx-embed-context-v1-0.6b for document chunk embedding.

    The model accepts doc_chunks: list[list[str]] (list of documents, each a
    list of text chunks) and returns a list of numpy arrays shaped
    (num_chunks, 1024) per document. Embedding dimension is 1024.
    """

    EMBEDDING_DIM = 1024

    def __init__(
            self,
            model_path: str = DEFAULT_MODEL_PATH,
            device: str = DEFAULT_DEVICE):
        """
        Args:
            model_path: Path to the local pplx-embed-context-v1 model directory
            device: Torch device string (e.g. "cuda:1", "cpu")
        """
        self._model_path = model_path
        self._device = device
        self._model = None

    def load(self) -> bool:
        """Load the model onto the target device. Returns True on success."""
        try:
            from transformers import AutoModel
            print(f"Loading pplx-embed-context model from {self._model_path} ...")
            self._model = AutoModel.from_pretrained(
                self._model_path,
                trust_remote_code=True
            )
            self._model = self._model.to(self._device)
            self._model.eval()
            print(f"Model loaded on {self._device}")
            return True
        except Exception as e:
            print(f"Error loading model: {e}")
            return False

    @property
    def is_loaded(self) -> bool:
        return self._model is not None

    def encode(
            self,
            doc_chunks: List[List[str]]) -> List[np.ndarray]:
        """
        Embed multiple documents.

        Args:
            doc_chunks: List of documents; each document is a list of chunk
                strings.

        Returns:
            List of numpy arrays, one per document, each shaped
            (num_chunks, 1024).
        """
        if not self.is_loaded:
            raise RuntimeError(
                "Model not loaded. Call load() before encode().")
        try:
            embeddings = self._model.encode(doc_chunks)
            return embeddings
        except Exception as e:
            print(f"Error encoding documents: {e}")
            return []

    def encode_single_document(self, chunks: List[str]) -> Optional[np.ndarray]:
        """
        Embed a single document's chunks.

        Args:
            chunks: List of text chunks for one document.

        Returns:
            numpy array of shape (num_chunks, 1024), or None on failure.
        """
        if not self.is_loaded:
            raise RuntimeError(
                "Model not loaded. Call load() before encode_single_document().")
        try:
            results = self.encode([chunks])
            if results:
                return results[0]
            return None
        except Exception as e:
            print(f"Error encoding single document: {e}")
            return None
