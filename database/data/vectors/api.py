



from pathlib import Path
from time import time
import chromadb

from kb_schemas import Chunk, Formatter
from config import settings


class VectorStore:

    @classmethod
    def init_db(cls):
        cls.client = chromadb.PersistentClient(path=settings.db.vector_store.path)

    @staticmethod
    def _gen_id() -> str:
        """Генерирует id на основе текущего времени (мс с эпохи)."""
        return str(int(time()* 1000))


    # CREATE
    @classmethod
    def create(cls, user_id: int, chunks: list[Chunk], metadata: Formatter = None):
        try:
            collection = cls.client.get_or_create_collection(name=user_id)

            # article_id = cls._gen_id()
        
            # existing = collection.get(ids=[article_id])
        
            # collection.add(
            #     ids=[article_id],
            #     embeddings=[chunk.embedding for chunk in chunks],
            #     documents=[chunk.content for chunk in chunks],
            #     metadatas=[{"path": chunk.path} for chunk in chunks],
            # )


            for chunk in chunks:
                article_id = cls._gen_id()

                collection.add(
                        ids=[article_id],
                        embeddings=chunk.embedding ,
                        documents=chunk.content,
                        metadatas={
                            "path": Path(metadata.primary_category or "Unsorted") / metadata.file_name,
                            "title": metadata.title},
                    )
                
            return {"status": "created"}
                
        except Exception as e:
            pass

    # READ

    @classmethod
    async def read_nearest(cls, user_id: int, vector: list[float], limit: int = 5):
        try:
            collection = cls.client.get_or_create_collection(name=user_id)

            results = collection.query(vector, n_results=limit)
            
            return {"status": "read", 
                    "results": [{
                        'id': id,
                        'content': content,
                        'title': metadata.get('title'),
                        'path': metadata.get('path')
                    } for id, content, metadata in zip(results['ids'], results['documents'], results['metadatas'])]}

        except Exception as e:
            pass
    

    # DELETE
    @classmethod
    def delete_list(cls, user_id: int, paths: list[Path]):

        errs = []
        for path in paths:
            try:
                cls.delete(user_id, path)
            except Exception as e:
                errs.append(path)
        return {"status": "deleted", "errors": errs}

    @classmethod
    def delete(cls, user_id: int, path: Path):
        try:
            collection = cls.client.get_or_create_collection(name=user_id)

            collection.delete(where={"path": path})
            
            return {"status": "deleted"}

        except Exception as e:
            pass
