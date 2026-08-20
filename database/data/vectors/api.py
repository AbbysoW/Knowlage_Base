



import asyncio
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
    def _create(cls, user_id: int, chunks: list[Chunk], metadata: Formatter = None):
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
            
        return True

    @classmethod
    async def create(cls, user_id: int, chunks: list[Chunk], metadata: Formatter = None):
        try:
            if await asyncio.to_thread(cls._create, user_id, chunks, metadata):
                return {"status": "created"}
            return {"status": "failed"}
        except Exception as e:
            # logger.error(f"Chroma create failed: user={user_id}, chunks={chunks}: {e}")
            pass

        finally:
            return {"status": "failed"}

    # READ
    @classmethod
    def _read_nearest(cls, user_id: int, vector: list[float], limit: int = 5):
        collection = cls.client.get_or_create_collection(name=user_id)
        return collection.query(vector, n_results=limit)

    @classmethod
    async def read_nearest(cls, user_id: int, vector: list[float], limit: int = 5):
        try:
            results = await asyncio.to_thread(cls._read_nearest, user_id, vector, limit)
            
            return {"status": "read", 
                    "results": [{
                        'id': id,
                        'content': content,
                        'title': metadata.get('title'),
                        'path': metadata.get('path')
                    } for id, content, metadata in zip(results['ids'], results['documents'], results['metadatas'])]}

        except Exception as e:
            # logger.error(f"Chroma read failed: user={user_id}, vector={vector}: {e}")
            
            pass
    

# DELETE
    @classmethod
    def _delete(cls, user_id: int, path: Path) -> bool:
        collection = cls.client.get_or_create_collection(name=str(user_id))
        collection.delete(where={"path": str(path)})
        return True

    @classmethod
    async def delete(cls, user_id: int, path: Path) -> dict:
        try:
            ok = await asyncio.to_thread(cls._delete, user_id, path)
            return {"status": "deleted" if ok else "failed", "path": str(path)}
        except Exception as e:
            # logger.error(f"Chroma delete failed: user={user_id}, path={path}: {e}")
            return {"status": "failed", "path": str(path), "error": str(e)}

    @classmethod
    async def delete_list(cls, user_id: int, paths: list[Path]) -> dict:
        results = await asyncio.gather(
            *(cls.delete(user_id, path) for path in paths),
            return_exceptions=True,
        )

        errs = []
        for path, result in zip(paths, results):
            if isinstance(result, Exception) or result.get("status") != "deleted":
                errs.append(path)

        return {"status": "deleted" if not errs else "partial", "errors": errs}
