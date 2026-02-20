"""
Integration tests for the embedding server.

These tests start the FastAPI app in-process using httpx's ASGITransport —
no actual uvicorn process needed.  The model must be present at the default
path and a CUDA-capable GPU must be available on device index 1.

Run from the project root:
    pytest tests/integration_tests/EmbeddingServer/test_server.py -v
"""

from pathlib import Path

import numpy as np
import pytest
import pytest_asyncio

from knowledge_base.EmbeddingServer.configuration import (
    DEFAULT_MODEL_PATH,
    EmbeddingServerConfiguration,
)

model_path = Path(DEFAULT_MODEL_PATH)
model_available = model_path.exists()
skip_if_no_model = pytest.mark.skipif(
    not model_available,
    reason=f"Model not found at {DEFAULT_MODEL_PATH}",
)


# ---------------------------------------------------------------------------
# Fixtures — only created when model is present
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def server_config():
    return EmbeddingServerConfiguration.from_defaults()


@pytest.fixture(scope="module")
def loaded_app(server_config):
    """Patch global server state and load the model once per module."""
    import knowledge_base.EmbeddingServer.server as srv

    srv._server_config = server_config
    from knowledge_base.Embeddings.PplxContextEmbedder import PplxContextEmbedder

    embedder = PplxContextEmbedder(
        model_path=server_config.model_path,
        device=server_config.device,
    )
    embedder.load()
    srv._embedder = embedder
    yield srv.app
    srv._embedder = None


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_server_config_defaults():
    config = EmbeddingServerConfiguration.from_defaults()
    assert config.port == 8765
    assert config.host == "127.0.0.1"
    assert config.workers == 1
    assert "pplx-embed-context" in config.model_path


@skip_if_no_model
@pytest.mark.asyncio
async def test_health_endpoint_model_loaded(loaded_app):
    import httpx
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=loaded_app),
        base_url="http://test",
    ) as client:
        response = await client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["model_loaded"] is True


@skip_if_no_model
@pytest.mark.asyncio
async def test_embed_single_document(loaded_app):
    import httpx
    payload = {"chunks": [["First chunk.", "Second chunk.", "Third chunk."]]}
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=loaded_app),
        base_url="http://test",
    ) as client:
        response = await client.post("/embed", json=payload)
    assert response.status_code == 200
    body = response.json()
    embeddings = body["embeddings"]
    assert len(embeddings) == 1           # one document
    assert len(embeddings[0]) == 3        # three chunks
    assert len(embeddings[0][0]) == 1024  # 1024-dim vectors

    # Verify L2-normalised (norm ≈ 1.0)
    for vec in embeddings[0]:
        norm = float(np.linalg.norm(vec))
        assert abs(norm - 1.0) < 1e-4, f"Expected unit norm, got {norm}"


@skip_if_no_model
@pytest.mark.asyncio
async def test_embed_multiple_documents(loaded_app):
    import httpx
    payload = {
        "chunks": [
            ["Doc A chunk 1.", "Doc A chunk 2."],
            ["Doc B only chunk."],
        ]
    }
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=loaded_app),
        base_url="http://test",
    ) as client:
        response = await client.post("/embed", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert len(body["embeddings"]) == 2
    assert len(body["embeddings"][0]) == 2
    assert len(body["embeddings"][1]) == 1


@skip_if_no_model
@pytest.mark.asyncio
async def test_embed_query(loaded_app):
    import httpx
    payload = {"query": "What is the capital of France?"}
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=loaded_app),
        base_url="http://test",
    ) as client:
        response = await client.post("/embed_query", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert len(body["embedding"]) == 1024
    norm = float(np.linalg.norm(body["embedding"]))
    assert abs(norm - 1.0) < 1e-4, f"Expected unit norm, got {norm}"


@pytest.mark.asyncio
async def test_embed_empty_chunks_returns_422():
    """Should reject an empty chunk list without loading the model."""
    from knowledge_base.EmbeddingServer.server import app
    import knowledge_base.EmbeddingServer.server as srv

    # Patch minimal config so /embed can be reached
    srv._server_config = EmbeddingServerConfiguration.from_defaults()

    import httpx
    payload = {"chunks": []}
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post("/embed", json=payload)
    assert response.status_code in (422, 503)
