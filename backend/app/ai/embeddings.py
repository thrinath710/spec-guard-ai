import logging
import threading

from fastembed import TextEmbedding

from backend.app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)

_model: TextEmbedding | None = None
_model_lock = threading.Lock()


def _get_model(settings: Settings) -> TextEmbedding:
    """Load the ONNX embedding model once per process.

    Groq is chat-completions only and exposes no embeddings endpoint, so RAG vectors are
    produced in-process by fastembed rather than by a hosted API or a local Ollama daemon.
    The default model is 768-dimensional to match the existing pgvector column.
    """
    global _model
    if _model is None:
        with _model_lock:
            if _model is None:
                logger.info("Loading embedding model %s", settings.embedding_model)
                _model = TextEmbedding(model_name=settings.embedding_model)
    return _model


class Embedder:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def warm_up(self) -> None:
        """Pay the one-time model load at startup instead of inside the first analysis."""
        _get_model(self.settings)

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        model = _get_model(self.settings)
        return [vector.tolist() for vector in model.embed(texts)]

    def embed_text(self, text: str) -> list[float]:
        return self.embed_texts([text])[0]
