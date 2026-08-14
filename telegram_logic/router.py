import asyncio
from datetime import datetime
import logging
from typing import Any, Callable


from kb_schemas import NoteDesigner, TranscriptionResult
from modules.md_pipeline import prepare_md
from modules.to_db import send_to_db

from config import settings


logging.basicConfig(level=settings.log.level)
logger = logging.getLogger(__name__)


background_tasks = set()



# Transcribe

transcriber_registry: dict[str, Callable[[Any], TranscriptionResult]] = {
    'text': lambda x: x,
    # 'audio': 
    # 'image': 
    # 'video': 
}

async def transcribe(data: Any, data_type: str) -> TranscriptionResult:
    try: 
        return transcriber_registry[data_type](data)
    except ValueError as e:
        # log err
        raise ValueError(f"Error occurred while transcribing data of type {data_type}: {e}")


# 
async def process_data(user_id: int, data: str, data_type: str, date: str):
    try:
        transcribed = await transcribe(data, data_type)

        md: NoteDesigner = await prepare_md(user_id, transcribed)

        await send_to_db(user_id, md)

    except ValueError as e:
        # send user error message
        pass

def new_data(user_id: int, data: Any, data_type: str, date: datetime):
    try:
        task = asyncio.create_task(process_data(user_id, data, data_type, date))
        background_tasks.add(task)
        task.add_done_callback(background_tasks.discard)

        return True
    except Exception as e:
        return False