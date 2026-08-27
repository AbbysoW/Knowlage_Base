
import os
import threading
import logging
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
                cls._model = SentenceTransformer(settings.embedding_model.name)
                cls._model.eval()
                logger.info("Embedding model initialized: model=%s", settings.embedding_model.name)
            return cls._model

    @classmethod
    def get_embedding(cls, x: str) -> list[float]:
        with torch.no_grad():
            return cls._get_model().encode(x).tolist()




if  __name__ ==  '__main__':
    sentence = "Hello, my dog is cute"
    embedding = EmbeddingModel.get_embedding(sentence)
    print(embedding.shape)
    print(type(embedding))
