import asyncio
from datetime import datetime
import logging
from typing import Any, Callable

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore

from kb_schemas import NoteDesigner, TranscriptionResult
from modules.md_pipeline import prepare_md
from modules.to_db import ToDB
from modules.common.task_queue import TaskQueue
from config import settings


logger = logging.getLogger(__name__)


# Transcribe

transcriber_registry: dict[str, Callable[[Any], TranscriptionResult]] = {
    'text': lambda x: TranscriptionResult(text=x, source_type='text'),
    # 'audio': 
    # 'image': 
    # 'video': 
}

async def transcribe(data: Any, data_type: str) -> TranscriptionResult:
    try:
        return transcriber_registry[data_type](data)
    except KeyError as e:
        # неизвестный/неподдерживаемый data_type — раньше проваливалось как
        # необработанный KeyError мимо except ValueError ниже
        logger.error(
            "transcribe: неподдерживаемый data_type=%s (user data не транскрибирован)",
            data_type,
            exc_info=True,
        )
        raise ValueError(f"Unsupported data_type: {data_type!r}") from e
    except ValueError as e:
        logger.error(
            "transcribe: ошибка транскрибации, data_type=%s",
            data_type,
            exc_info=True,
        )
        raise ValueError(f"Error occurred while transcribing data of type {data_type}: {e}") from e



async def process_data(user_id: int, data: str, data_type: str, date: datetime):
    try:
        transcribed = await transcribe(data, data_type)
        transcribed.timestamp = date

        md: NoteDesigner = await prepare_md(user_id, transcribed)

        await ToDB.send_to_db(user_id, md, transcribed)

    except ValueError:
        logger.error(
            "process_data: некорректные входные данные (user_id=%s, data_type=%s)",
            user_id, data_type,
            exc_info=True,
        )
        # send user error message
        pass
    except Exception:
        raise


task_queue = TaskQueue(handler=process_data, worker_count=3, maxsize=200)


def new_data(user_id: int, data: Any, data_type: str, date: datetime):
    return task_queue.submit(user_id, data, data_type, date)
