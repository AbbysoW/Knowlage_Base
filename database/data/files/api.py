





import asyncio
import textwrap
from pathlib import Path
import logging

from kb_schemas import DBPayload
from config import settings


logger = logging.getLogger(__name__)


class FileStore:

    @staticmethod
    def _build_path(user_id: int, primary_category: str | None, file_name: str) -> Path:
        return (
            settings.db.file_store.path
            / f"{user_id}"
            / (primary_category or "Unsorted")
            / file_name
        )


    # CREATE
    @classmethod
    def _create_sync(cls, user_id: int, payload: DBPayload):
        filepath: Path = cls._build_path(user_id, payload.metadata.primary_category, payload.metadata.file_name)
        filepath.parent.mkdir(parents=True, exist_ok=True)

        content = textwrap.dedent(f'''\
            ---
            title: {payload.metadata.title}
            created: {payload.metadata.created_at}
            source_type: {payload.raw_data.source_type}
            tags: {payload.metadata.tags_to_str()}
            entities: {payload.metadata.entities_to_str()}
            related_articles: {payload.metadata.relations_to_str()}
            ---
            # {payload.metadata.title}
            {payload.md}
        ''')

        with filepath.open("x", encoding="utf-8") as f:
            f.write(content)

    @classmethod
    async def create(cls, user_id: int, payload: DBPayload):
        filepath = cls._build_path(user_id, payload.metadata.primary_category, payload.metadata.file_name)
        try:
            await asyncio.to_thread(cls._create_sync, user_id, payload)
            logger.info("File created: user_id=%s, path=%s, bytes=%s", user_id, filepath, len(payload.md.encode("utf-8")))

        except FileExistsError:
            logger.warning("File already exists: user_id=%s, path=%s", user_id, filepath)
            raise

        except FileNotFoundError:
            logger.error("File path unavailable: user_id=%s, path=%s", user_id, filepath, exc_info=True)
            raise
        except Exception:
            logger.exception("File creation failed: user_id=%s, path=%s", user_id, filepath)
            raise


    @classmethod
    async def read(cls, user_id: int, file_name: str, primary_category: str | None):
        pass

    @classmethod
    async def update(cls, user_id: int, file_name: str, primary_category: str | None):
        pass


    # DELETE
    @classmethod
    def _delete_sync(cls, user_id: int, file_name: str, primary_category: str | None):
        filepath = cls._build_path(user_id, primary_category, file_name)
        filepath.unlink(missing_ok=True)

    @classmethod
    async def delete(cls, user_id: int, file_name: str, primary_category: str | None):
        filepath = cls._build_path(user_id, primary_category, file_name)
        try:
            await asyncio.to_thread(cls._delete_sync, user_id, file_name, primary_category)
            logger.info("File deleted: user_id=%s, path=%s", user_id, filepath)
        except PermissionError:
            logger.error("File deletion denied: user_id=%s, path=%s", user_id, filepath, exc_info=True)
            raise
        except Exception:
            logger.exception("File deletion failed: user_id=%s, path=%s", user_id, filepath)
            raise