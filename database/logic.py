import json
import uuid
import asyncio
import logging
from pathlib import Path
from weakref import WeakValueDictionary

from kb_schemas import DBPayload, Step
from config import settings
from data.files import FileStore
from data.metadata import SqliteStore
from data.vectors import VectorStore


logger = logging.getLogger(__name__)


class TransactionError(Exception):
    def __init__(self, failed_step: str, original: Exception):
        self.failed_step = failed_step
        self.original = original
        super().__init__(f"Step '{failed_step}' failed: {original}")


class Transaction:
    """Saga-транзакция с WAL для восстановления после краша."""

    def __init__(self, tx_id: str | None = None, payload: dict | None = None):
        self.tx_id = tx_id or str(uuid.uuid4())
        self.payload = payload or {}
        self.steps: list[Step] = []
        self._wal_path = settings.tx.wal_dir / f"{self.tx_id}.json"

    def add_step(self, name: str, do, compensate):
        self.steps.append(Step(name=name, do=do, compensate=compensate))
        return self

    async def _write_wal(self, status: str):
        await asyncio.to_thread(self._write_wal_sync, status)

    def _write_wal_sync(self, status: str):
        settings.tx.wal_dir.mkdir(parents=True, exist_ok=True)
        self._wal_path.write_text(json.dumps({
            "tx_id": self.tx_id,
            "status": status,
            "payload": self.payload,
            "steps": [s.name for s in self.steps],
            "completed": [s.name for s in self.steps if s.done],
        }))

    def _clear_wal(self):
        self._wal_path.unlink(missing_ok=True)

    async def run(self):
        logger.info("Transaction started: tx_id=%s, steps=%s", self.tx_id, len(self.steps))
        await self._write_wal(status="pending")
        completed: list[Step] = []
        try:
            for step in self.steps:
                logger.debug("Transaction step started: tx_id=%s, step=%s", self.tx_id, step.name)
                step.result = await step.do()
                step.done = True
                completed.append(step)
                await self._write_wal(status="pending")
                logger.debug("Transaction step completed: tx_id=%s, step=%s", self.tx_id, step.name)
            self._clear_wal()
            logger.info("Transaction committed: tx_id=%s", self.tx_id)
        except Exception as e:
            failed_name = self.steps[len(completed)].name
            logger.exception("Transaction failed: tx_id=%s, failed_step=%s", self.tx_id, failed_name)
            await self._rollback(completed)
            self._clear_wal()
            raise TransactionError(failed_name, e) from e

    async def _rollback(self, completed: list[Step]):
        for step in reversed(completed):
            try:
                await step.compensate()
            except Exception as e:
                # компенсация упала — это критично, логируем отдельно,
                # это уже не авто-восстановимо, нужен alert/ручной разбор
                logger.critical("Rollback failed: tx_id=%s, step=%s", self.tx_id, step.name, exc_info=True)
                await self._write_wal(status=f"rollback_failed:{step.name}")
                raise


class DBLogic:
    _user_locks: dict[int, asyncio.Lock] = {}
    _locks_guard = asyncio.Lock()

    @classmethod
    async def _get_user_lock(cls, user_id: int) -> asyncio.Lock:
        async with cls._locks_guard:
            if user_id not in cls._user_locks:
                cls._user_locks[user_id] = asyncio.Lock()
            return cls._user_locks[user_id]

    @classmethod
    async def write_to_db(cls, user_id: int, payload: DBPayload):
        logger.debug("Database write waiting for user lock: user_id=%s", user_id)
        async with await cls._get_user_lock(user_id):
            logger.debug("Database write lock acquired: user_id=%s", user_id)
            await cls._write_to_db(user_id, payload)
        logger.info("Database write completed: user_id=%s", user_id)

    @staticmethod
    async def _write_to_db(user_id: int, payload: DBPayload):
        tx = Transaction(payload={"user_id": user_id, **payload.model_dump(mode="json")})

        tx.add_step(
            name="Files",
            do=lambda: FileStore.create(user_id, payload),
            compensate=lambda: FileStore.delete(user_id, payload.metadata.file_name, payload.metadata.primary_category),
        )
        tx.add_step(
            name="Metadata",
            do=lambda: SqliteStore.create(user_id, payload),
            compensate=lambda: SqliteStore.delete(user_id, payload.metadata.title, payload.metadata.primary_category),
        )
        tx.add_step(
            name="Vectors",
            do=lambda: VectorStore.create(user_id, payload.chunks, payload.metadata),
            compensate=lambda: VectorStore.delete(
                user_id,
                Path(payload.metadata.primary_category or "Unsorted") / payload.metadata.file_name,
            ),
        )

        await tx.run()  # бросит TransactionError, если что-то не так, с автоматическим откатом

    @staticmethod
    async def read_nearest(user_id: int, vector: list[float], limit: int = 5):
        return await VectorStore.read_nearest(user_id, vector, limit)