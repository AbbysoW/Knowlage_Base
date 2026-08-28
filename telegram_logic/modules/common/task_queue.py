# telegram_logic/task_queue.py
import asyncio
import logging
from time import monotonic
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
        logger.info("TaskQueue started: workers=%s, capacity=%s", self._worker_count, self._queue.maxsize)

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
                    exc_info=result,
                )

        logger.info("TaskQueue: остановлено %d воркеров", len(self._workers))


    def submit(self, user_id: int, data: Any, data_type: str, date: datetime) -> bool:
        try:
            self._queue.put_nowait(
                Job(user_id=user_id, data=data, data_type=data_type, date=date)
            )
            logger.debug("Task queued: user_id=%s, data_type=%s, queue_size=%s", user_id, data_type, self._queue.qsize())
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
            started_at = monotonic()
            try:
                await self._handler(job.user_id, job.data, job.data_type, job.date)
                logger.info("Task completed: worker=%s, user_id=%s, data_type=%s, duration_ms=%s", worker_id, job.user_id, job.data_type, round((monotonic() - started_at) * 1000))
            except Exception:
                logger.error(
                    "TaskQueue._worker_loop: worker %d, job для user=%s (data_type=%s) упал",
                    worker_id, job.user_id, job.data_type,
                    exc_info=True,
                )
            finally:
                self._queue.task_done()