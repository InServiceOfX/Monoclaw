"""
Integration tests for PplxContextEmbedder.

USAGE:
Requires the pplx-embed-context-v1-0.6b model to be present at the default
model path and a CUDA-capable GPU at device index 1.

Run from the project root:
    pytest tests/integration_tests/Embeddings/test_PplxContextEmbedder.py -v
"""

from knowledge_base.Embeddings.PplxContextEmbedder import (
    PplxContextEmbedder,
    DEFAULT_MODEL_PATH,
)
from pathlib import Path
import numpy as np
import pytest


model_path = Path(DEFAULT_MODEL_PATH)
model_available = model_path.exists()
skip_if_no_model = pytest.mark.skipif(
    not model_available,
    reason=f"Model not found at {DEFAULT_MODEL_PATH}"
)


def test_PplxContextEmbedder_instantiates():
    embedder = PplxContextEmbedder()
    assert embedder is not None
    assert embedder.is_loaded is False
    assert embedder.EMBEDDING_DIM == 1024


@skip_if_no_model
def test_PplxContextEmbedder_loads_model():
    embedder = PplxContextEmbedder()
    success = embedder.load()
    assert success is True
    assert embedder.is_loaded is True


@skip_if_no_model
def test_PplxContextEmbedder_encode_returns_correct_shape():
    embedder = PplxContextEmbedder()
    embedder.load()

    doc_chunks = [
        ["This is chunk one.", "This is chunk two."],
        ["Another document, single chunk."]
    ]
    results = embedder.encode(doc_chunks)

    assert len(results) == 2

    # First document: 2 chunks -> shape (2, 1024)
    assert isinstance(results[0], np.ndarray)
    assert results[0].shape == (2, 1024)

    # Second document: 1 chunk -> shape (1, 1024)
    assert isinstance(results[1], np.ndarray)
    assert results[1].shape == (1, 1024)


@skip_if_no_model
def test_PplxContextEmbedder_encode_single_document_returns_correct_shape():
    embedder = PplxContextEmbedder()
    embedder.load()

    chunks = ["First chunk.", "Second chunk.", "Third chunk."]
    result = embedder.encode_single_document(chunks)

    assert result is not None
    assert isinstance(result, np.ndarray)
    assert result.shape == (3, 1024)


@skip_if_no_model
def test_PplxContextEmbedder_embeddings_are_finite():
    embedder = PplxContextEmbedder()
    embedder.load()

    chunks = ["The quick brown fox jumps over the lazy dog."]
    result = embedder.encode_single_document(chunks)

    assert result is not None
    assert np.all(np.isfinite(result)), "All embedding values should be finite"
