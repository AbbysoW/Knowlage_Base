





import json
import uuid
import asyncio

from kb_schemas import DBPayload, Step
from config import settings
from database.data.files.api import FileStore
from database.data.metadata.api import SqliteStore
from database.data.vectors.api import VectorStore




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

    def _write_wal(self, status: str):
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
        self._write_wal(status="pending")
        completed: list[Step] = []
        try:
            for step in self.steps:
                step.result = await step.do()
                step.done = True
                completed.append(step)
                self._write_wal(status="pending")  # прогресс на диск
            self._clear_wal()  # успех — журнал больше не нужен
        except Exception as e:
            failed_name = self.steps[len(completed)].name
            await self._rollback(completed)
            self._clear_wal()
            raise TransactionError(failed_name, e) from e

    async def _rollback(self, completed: list[Step]):
        for step in reversed(completed):
            try:
                await step.compensate()
            except Exception as comp_err:
                # компенсация упала — это критично, логируем отдельно,
                # это уже не авто-восстановимо, нужен alert/ручной разбор
                self._write_wal(status=f"rollback_failed:{step.name}:{comp_err}")
                raise


class DBLogic:

    @staticmethod
    async def write_to_db(user_id: int, payload: DBPayload):
        tx = Transaction(payload={"user_id": user_id, **payload.dict()})

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
            compensate=lambda: VectorStore.delete_list(user_id, [chunk.path for chunk in payload.chunks]),
        )

        await tx.run()  # бросит TransactionError, если что-то не так, с автоматическим откатом

    @staticmethod
    async def read_nearest(user_id: int, vector: list[float], limit: int = 5):
        return await VectorStore.read_nearest(user_id, vector, limit)