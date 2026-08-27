





import asyncio
import sqlite3
import json
import logging
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from contextlib import contextmanager

from config import settings
from kb_schemas import DBPayload


logger = logging.getLogger(__name__)


class SqliteStore:

    @staticmethod
    @contextmanager
    def _get_connection():
        """Контекстный менеджер для соединения с БД (авто commit/close)."""
        settings.db.metadata_store.path.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(settings.db.metadata_store.db_file)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=5000;")
        conn.execute("PRAGMA foreign_keys = ON;")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    
    @classmethod
    def init_db(cls) -> None:
        """Создаёт таблицу MetaData, если она ещё не существует."""
        with cls._get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS MetaData (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id     INTEGER NOT NULL,
                    title       TEXT NOT NULL,
                    tags        TEXT,      -- JSON-массив строк
                    entities    TEXT,      -- JSON-массив строк
                    category    TEXT,
                    source_type TEXT,
                    created     TEXT        -- дата в формате YYYY-MM-DD
                );
                """
            )

    # UTILS
    @classmethod
    def _serialize_list(cls, value: Optional[List[Any]]) -> Optional[str]:
        if value is None:
            return None
        return json.dumps(value, ensure_ascii=False)
    
    @classmethod
    def _deserialize_list(cls, value: Optional[str]) -> List[Any]:
        if not value:
            return []
        return json.loads(value)
    
    @classmethod
    def _row_to_dict(cls, row: sqlite3.Row) -> Dict[str, Any]:
        d = dict(row)
        d["tags"] = cls._deserialize_list(d.get("tags"))
        d["entities"] = cls._deserialize_list(d.get("entities"))
        return d
    
    @classmethod
    def _normalize_date(cls, value) -> str:
        """Приводит date/datetime/str к строке YYYY-MM-DD."""
        if value is None:
            return date.today().isoformat()
        if isinstance(value, (date, datetime)):
            return value.isoformat()[:10]
        return str(value)



    
    # CREATE
    @classmethod
    def _create_sync(cls, user_id: int, payload: DBPayload):
        metadata = payload.metadata
        raw_data = payload.raw_data

        with cls._get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO MetaData
                    (user_id, title, tags, entities, category, source_type, created)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    metadata.title,
                    cls._serialize_list(metadata.tags),
                    cls._serialize_list(metadata.entities),
                    metadata.primary_category,
                    raw_data.source_type,
                    cls._normalize_date(metadata.created_at),
                )
            )
            new_id = cursor.lastrowid
        return cls.read_metadata_by_id(new_id)
    
    @classmethod
    async def create(cls, user_id: int, payload: DBPayload):
        try:
            result = await asyncio.to_thread(cls._create_sync, user_id, payload)
            logger.info("Metadata stored: user_id=%s, title=%s", user_id, payload.metadata.title)
            return result
        except sqlite3.OperationalError as e:
            logger.error(f"Create failed: couldn't connect to the database: {e}")
            raise
        except sqlite3.IntegrityError as e:
            logger.error(f"Create failed: integrity error occurred: {e}")
            raise
        except Exception as e:
            logger.exception("Create failed")
            raise

    # READ
    @classmethod
    def _read_metadata_by_id(cls, record_id: int):
        with cls._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM MetaData WHERE id = ?", (record_id,)
            ).fetchone()
        return cls._row_to_dict(row) if row else None

    @classmethod
    async def read_metadata_by_id(cls, record_id: int) -> Optional[Dict[str, Any]]:
        """Возвращает одну запись по id или None, если не найдена."""
        try:
            return await asyncio.to_thread(cls._read_metadata_by_id, record_id)
        except sqlite3.OperationalError as e:
            logger.error(f"Read failed: couldn't connect to the database: {e}")
            raise
        except Exception as e:
            logger.exception("Read failed")
            raise

    @classmethod
    async def read(cls, user_id: int, file_name: str, primary_category: str | None):
        pass

    @classmethod
    async def update(cls, user_id: int, file_name: str, primary_category: str | None):
        pass


    # DELETE
    @classmethod
    def _delete(cls, user_id: int, title: str, primary_category: str | None):
        with cls._get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM MetaData WHERE user_id = ? AND title = ? AND category IS ?",
                (user_id, title, primary_category),
            )
            if cursor.rowcount == 0:
                logger.warning(f"Compensating delete matched 0 rows: user={user_id} title={title}")

    @classmethod
    async def delete(cls, user_id: int, title: str, primary_category: str | None):
        try:
            await asyncio.to_thread(cls._delete, user_id, title, primary_category)
            logger.info("Metadata deleted: user_id=%s, title=%s, category=%s", user_id, title, primary_category)
        except sqlite3.OperationalError as e:
            logger.error(f"Delete failed: couldn't connect to the database: {e}")
            raise
        except Exception as e:
            logger.exception("Delete failed")
            raise


