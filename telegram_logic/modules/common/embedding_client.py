
import os
from pathlib import Path

from sentence_transformers import SentenceTransformer
import torch

from config import settings


class EmbeddingModel:
    _model: SentenceTransformer | None = None

    @classmethod
    def _get_model(cls) -> SentenceTransformer:
        if cls._model is None:
            cls._model = SentenceTransformer(settings.embedding_model.name)
            cls._model.eval()
        return cls._model

    @classmethod
    def get_embedding(cls, x: str) -> torch.Tensor:
        with torch.no_grad():
            return torch.tensor(cls._get_model().encode(x), dtype=torch.float32)




if  __name__ ==  '__main__':
    sentence = "Hello, my dog is cute"
    embedding = EmbeddingModel.get_embedding(sentence)
    print(embedding.shape)
    print(type(embedding))
