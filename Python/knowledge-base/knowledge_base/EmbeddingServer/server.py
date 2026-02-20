"""FastAPI server wrapping pplx-embed-context-v1-0.6b.

Exposes three endpoints:
  POST /embed        — embed a batch of documents (each doc = list of chunks)
  POST /embed_query  — embed a single query string
  GET  /health       — liveness / model-loaded check

All returned embeddings are L2-normalised float32 vectors of dimension 1024,
ready for pgvector cosine similarity (<=>) without further processing.

Usage:
    python -m knowledge_base.EmbeddingServer.server
    python -m knowledge_base.EmbeddingServer.server --config path/to/config.yml
"""

import argparse
import logging
from contextlib import asynccontextmanager
from typing import List

import numpy as np
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from knowledge_base.EmbeddingServer.configuration import (
    EmbeddingServerConfiguration,
)
from knowledge_base.Embeddings.PplxContextEmbedder import PplxContextEmbedder

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class EmbedRequest(BaseModel):
    """Embed a batch of documents.

    chunks: list of documents; each document is a list of chunk strings.
    Example: [["chunk A1", "chunk A2"], ["chunk B1"]]
    """
    chunks: List[List[str]]


class EmbedResponse(BaseModel):
    """Normalised float32 embeddings per document.

    embeddings[i][j] is the 1024-dim embedding for chunk j of document i.
    """
    embeddings: List[List[List[float]]]


class EmbedQueryRequest(BaseModel):
    """Embed a single query string."""
    query: str


class EmbedQueryResponse(BaseModel):
    """Normalised float32 embedding for a query."""
    embedding: List[float]


class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    device: str
    model_path: str


# ---------------------------------------------------------------------------
# Global state — loaded once at startup
# ---------------------------------------------------------------------------

_embedder: PplxContextEmbedder | None = None
_server_config: EmbeddingServerConfiguration | None = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _l2_normalize(vec: np.ndarray) -> np.ndarray:
    """L2-normalise a 1-D or 2-D array along the last axis."""
    norm = np.linalg.norm(vec, axis=-1, keepdims=True)
    return vec / np.where(norm == 0, 1.0, norm)


def _load_embedder(config: EmbeddingServerConfiguration) -> PplxContextEmbedder:
    embedder = PplxContextEmbedder(
        model_path=config.model_path,
        device=config.device,
    )
    success = embedder.load()
    if not success:
        raise RuntimeError(
            f"Failed to load pplx-embed-context model from {config.model_path}"
        )
    return embedder


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _embedder
    logger.info("Loading embedding model...")
    _embedder = _load_embedder(_server_config)
    logger.info("Model ready.")
    yield
    _embedder = None
    logger.info("Server shut down.")


app = FastAPI(
    title="pplx-embed-context embedding server",
    description="Local HTTP wrapper for pplx-embed-context-v1-0.6b.",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(
        status="ok",
        model_loaded=_embedder is not None and _embedder.is_loaded,
        device=_server_config.device if _server_config else "unknown",
        model_path=_server_config.model_path if _server_config else "unknown",
    )


@app.post("/embed", response_model=EmbedResponse)
async def embed(request: EmbedRequest):
    """Embed a batch of documents.

    Each document is a list of chunks.  Returned embeddings are L2-normalised
    float32 vectors of dimension 1024.
    """
    if _embedder is None or not _embedder.is_loaded:
        raise HTTPException(status_code=503, detail="Model not loaded")

    if not request.chunks:
        raise HTTPException(
            status_code=422, detail="chunks must be a non-empty list")

    for i, doc in enumerate(request.chunks):
        if not doc:
            raise HTTPException(
                status_code=422,
                detail=f"Document at index {i} has no chunks")

    raw: list[np.ndarray] = _embedder.encode(request.chunks)
    if not raw:
        raise HTTPException(
            status_code=500,
            detail="Model returned empty embeddings")

    normalised = [
        _l2_normalize(doc_embs.astype(np.float32)).tolist()
        for doc_embs in raw
    ]
    return EmbedResponse(embeddings=normalised)


@app.post("/embed_query", response_model=EmbedQueryResponse)
async def embed_query(request: EmbedQueryRequest):
    """Embed a single query string.

    Treats the query as a single-chunk document so it goes through the same
    contextual model.  Returned embedding is L2-normalised, dimension 1024.
    """
    if _embedder is None or not _embedder.is_loaded:
        raise HTTPException(status_code=503, detail="Model not loaded")

    if not request.query.strip():
        raise HTTPException(status_code=422, detail="query must not be empty")

    raw = _embedder.encode_single_document([request.query])
    if raw is None:
        raise HTTPException(
            status_code=500,
            detail="Model returned empty embedding for query")

    # raw shape: (1, 1024) — take the single chunk
    vec = _l2_normalize(raw[0].astype(np.float32))
    return EmbedQueryResponse(embedding=vec.tolist())


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    global _server_config

    parser = argparse.ArgumentParser(
        description="Start the pplx-embed-context embedding server.")
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to YAML configuration file.",
    )
    args = parser.parse_args()

    if args.config:
        _server_config = EmbeddingServerConfiguration.from_yaml(args.config)
    else:
        _server_config = EmbeddingServerConfiguration.from_defaults()

    logging.basicConfig(level=logging.INFO)
    logger.info(
        f"Starting server on {_server_config.host}:{_server_config.port} "
        f"| model: {_server_config.model_path} "
        f"| device: {_server_config.device}"
    )

    uvicorn.run(
        app,
        host=_server_config.host,
        port=_server_config.port,
        workers=_server_config.workers,
        log_level="info",
    )


if __name__ == "__main__":
    main()
