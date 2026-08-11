
import os
from pathlib import Path

from sentence_transformers import SentenceTransformer
import torch

from config import settings


class EmbeddingModel:

    def __init__(self):
        self.model_name = settings.embedding_model.name

        self.model = SentenceTransformer(
            self.model_name, 
            )
        self.model.eval()

    def __call__(self, x: str) -> torch.Tensor:
        return torch.tensor(self.model.encode(x), dtype=torch.float32)


embedding_model = EmbeddingModel()


if  __name__ ==  '__main__':
    embedding_model = EmbeddingModel()
    sentence = "Hello, my dog is cute"
    embedding = embedding_model(sentence)
    print(embedding.shape)
    print(type(embedding))
