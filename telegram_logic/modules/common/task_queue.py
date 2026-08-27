# telegram_logic/task_queue.py
import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from pydantic import BaseModel
from typing import Any, Callable, Awaitable

logger = logging.getLogger(__name__)


class Job(BaseModel):
    user_id: int
    data: Any
    data_type: str
    date: datetime


class TaskQueue:

    def __init__(
        self,
        handler: Callable[[int, Any, str, datetime], Awaitable[None]],
        worker_count: int = 3,
        maxsize: int = 200,
    ):
        self._handler = handler
        self._queue: asyncio.Queue[Job] = asyncio.Queue(maxsize=maxsize)
        self._worker_count = worker_count
        self._workers: list[asyncio.Task] = []

    def start(self):
        self._workers = [
            asyncio.create_task(self._worker_loop(i))
            for i in range(self._worker_count)
        ]
        logger.info("TaskQueue: запущено %d воркеров", self._worker_count)

    async def stop(self):
        # дожидаемся обработки того, что уже в очереди, затем гасим воркеров
        await self._queue.join()
        for w in self._workers:
            w.cancel()
        results = await asyncio.gather(*self._workers, return_exceptions=True)

        for worker_id, result in enumerate(results):
            if isinstance(result, Exception) and not isinstance(result, asyncio.CancelledError):
                logger.error(
                    "TaskQueue.stop: worker %d завершился с ошибкой при остановке",
                    worker_id,
                    exc_info=(type(result), result, result.__traceback__),
                )

        logger.info("TaskQueue: остановлено %d воркеров", len(self._workers))


    def submit(self, user_id: int, data: Any, data_type: str, date: datetime) -> bool:
        try:
            self._queue.put_nowait(Job(user_id, data, data_type, date))
            return True
        except asyncio.QueueFull:
            logger.warning(
                "TaskQueue.submit: очередь переполнена, job для user=%s отброшен",
                user_id,
            )
            return False
        except Exception:
            # раньше любая другая ошибка (например, невалидные данные для Job)
            # ушла бы наверх необработанной и без единой строчки в лог
            logger.error(
                "TaskQueue.submit: не удалось создать/поставить job для user=%s, data_type=%s",
                user_id, data_type,
                exc_info=True,
            )
            return False

    async def _worker_loop(self, worker_id: int):
        while True:
            job = await self._queue.get()
            try:
                await self._handler(job.user_id, job.data, job.data_type, job.date)
            except Exception:
                logger.error(
                    "TaskQueue._worker_loop: worker %d, job для user=%s (data_type=%s) упал",
                    worker_id, job.user_id, job.data_type,
                    exc_info=True,
                )
            finally:
                self._queue.task_done()