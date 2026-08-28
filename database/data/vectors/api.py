



import asyncio
import logging
from pathlib import Path
import threading
from typing import Optional
from time import time
import chromadb

from kb_schemas import Chunk, Formatter
from config import settings


logger = logging.getLogger(__name__)

class VectorStore:
    _client: Optional[chromadb.PersistentClient] = None
    _lock = threading.Lock()

    @classmethod
    def _get_client(cls) -> chromadb.PersistentClient:
        with cls._lock:
            if cls._client is None:
                cls._client = chromadb.PersistentClient(path=str(settings.db.vector_store.path))
                logger.info("Vector store initialized: path=%s", settings.db.vector_store.path)
            return cls._client

    @staticmethod
    def _gen_id() -> str:
        """Генерирует id на основе текущего времени (мс с эпохи)."""
        return str(int(time()* 1000))


    # CREATE
    @classmethod
    def _create(cls, user_id: int, chunks: list[Chunk], metadata: Formatter = None):
        collection = cls._get_client().get_or_create_collection(name=str(user_id))
   
        for chunk in chunks:
            article_id = cls._gen_id()

            collection.add(
                    ids=[article_id],
                    embeddings=[chunk.embedding],
                    documents=[chunk.content],
                    metadatas=[{
                        "path": str(Path(metadata.primary_category or "Unsorted") / metadata.file_name),
                        "title": metadata.title}],
                )
            
        return True

    @classmethod
    async def create(cls, user_id: int, chunks: list[Chunk], metadata: Formatter = None):
        try:
            if await asyncio.to_thread(cls._create, user_id, chunks, metadata):
                logger.info("Vectors created: user_id=%s, count=%s", user_id, len(chunks))
                return {"status": "created"}
            return {"status": "failed"}
        except ConnectionRefusedError as e:
            logger.error(f"Create failed: Could not connect to vector store: {e}")
            raise
        except Exception as e:
            logger.exception("Create failed")
            raise
        

    # READ
    @classmethod
    def _read_nearest(cls, user_id: int, vector: list[float], limit: int = 5):
        collection = cls._get_client().get_or_create_collection(name=str(user_id))
        return collection.query(query_embeddings=[vector], n_results=limit)

    @classmethod
    async def read_nearest(cls, user_id: int, vector: list[float], limit: int = 5):
        try:
            results = await asyncio.to_thread(cls._read_nearest, user_id, vector, limit)
            
            ids = results["ids"][0]
            documents = results["documents"][0]
            metadatas = results["metadatas"][0]
            response = {"status": "read",
                        "results": [{
                            'id': article_id,
                            'content': content,
                            'title': metadata.get('title'),
                            'path': metadata.get('path')
                            } for article_id, content, metadata in zip(ids, documents, metadatas)]}
            logger.info("Vectors queried: user_id=%s, count=%s, limit=%s", user_id, len(response["results"]), limit)
            return response

        except ConnectionRefusedError as e:
            logger.error(f"Read failed: Could not connect to vector store: {e}")
            raise
        except Exception as e:
            logger.exception("Read failed")
            raise

# DELETE
    @classmethod
    def _delete(cls, user_id: int, path: Path) -> bool:
        collection = cls._get_client().get_or_create_collection(name=str(user_id))
        collection.delete(where={"path": str(path)})
        return True

    @classmethod
    async def delete(cls, user_id: int, path: Path) -> dict:
        try:
            ok = await asyncio.to_thread(cls._delete, user_id, path)
            logger.info("Vectors deleted: user_id=%s, path=%s", user_id, path)
            return {"status": "deleted" if ok else "failed", "path": str(path)}
        except ConnectionRefusedError as e:
            logger.error(f"Delete failed: Could not connect to vector store: {e}")
            raise
        except Exception as e:
            logger.exception("Delete failed")
            raise

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

        status = "deleted" if not errs else "partial"
        logger.info("Vector deletion batch completed: user_id=%s, total=%s, failed=%s, status=%s", user_id, len(paths), len(errs), status)
        return {"status": status, "errors": errs}