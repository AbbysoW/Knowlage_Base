
import os
import threading
import logging
from time import monotonic
from pathlib import Path

from sentence_transformers import SentenceTransformer
import torch

from config import settings


logger = logging.getLogger(__name__)


class EmbeddingModel:
    _model: SentenceTransformer | None = None
    _lock = threading.Lock()

    @classmethod
    def _get_model(cls) -> SentenceTransformer:
        with cls._lock:
            if cls._model is None:
                started_at = monotonic()
                logger.info("Embedding model loading: model=%s", settings.embedding_model.name)
                cls._model = SentenceTransformer(settings.embedding_model.name)
                cls._model.eval()
                logger.info("Embedding model loaded: model=%s, duration_ms=%s", settings.embedding_model.name, round((monotonic() - started_at) * 1000))
            return cls._model

    @classmethod
    def get_embedding(cls, x: str) -> list[float]:
        try:
            with torch.no_grad():
                embedding = cls._get_model().encode(x).tolist()
            logger.debug("Embedding generated: input_length=%s, dimensions=%s", len(x), len(embedding))
            return embedding
        except Exception:
            logger.exception("Embedding failed: input_length=%s", len(x))
            raise




if  __name__ ==  '__main__':
    sentence = "Hello, my dog is cute"
    embedding = EmbeddingModel.get_embedding(sentence)
    print(embedding.shape)
    print(type(embedding))
