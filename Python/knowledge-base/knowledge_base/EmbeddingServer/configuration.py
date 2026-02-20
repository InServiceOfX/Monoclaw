from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import yaml

DEFAULT_MODEL_PATH = (
    "/media/propdev/9dc1a908-7eff-4e1c-8231-ext4"
    "/home/propdev/Data/Models/Embeddings/perplexity-ai"
    "/pplx-embed-context-v1-0.6b"
)
DEFAULT_DEVICE = "cuda:1"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765


@dataclass
class EmbeddingServerConfiguration:
    """Configuration for the pplx-embed-context embedding server.

    Fields:
        model_path: Local path to the pplx-embed-context-v1 model directory.
        device: Torch device string, e.g. "cuda:1" or "cpu".
        host: Bind address for the server.
        port: Port to listen on.
        workers: Number of uvicorn worker processes (1 recommended for GPU).
    """
    model_path: str = DEFAULT_MODEL_PATH
    device: str = DEFAULT_DEVICE
    host: str = DEFAULT_HOST
    port: int = DEFAULT_PORT
    workers: int = 1

    @classmethod
    def from_yaml(cls, yaml_path: Path | str) -> "EmbeddingServerConfiguration":
        yaml_path = Path(yaml_path)
        with open(yaml_path, "r") as f:
            config = yaml.safe_load(f)
        return cls(
            model_path=config.get("model_path", DEFAULT_MODEL_PATH),
            device=config.get("device", DEFAULT_DEVICE),
            host=config.get("host", DEFAULT_HOST),
            port=int(config.get("port", DEFAULT_PORT)),
            workers=int(config.get("workers", 1)),
        )

    @classmethod
    def from_defaults(cls) -> "EmbeddingServerConfiguration":
        return cls()
