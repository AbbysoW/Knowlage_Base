




import asyncio
from typing import Any, Callable

from kb_schemas import DBPayload, NoteDesigner, TranscriptionResult

from telegram_logic.modules.to_db.split_model import Split
from .db_client import post_new_article
# from .db_client import






class ToDB:


    @staticmethod
    async def _prepare_payload(note_designer: NoteDesigner, raw_data: TranscriptionResult) -> DBPayload:
        try:
            return DBPayload(
                chunks=await asyncio.to_thread(Split.split_to_chunks, note_designer),
                metedata=note_designer.formatter,
                md=note_designer.content,
                raw_data=raw_data
            )
        except Exception as e:
            # Handle the exception appropriately
            raise e

    @classmethod
    async def send_to_db(cls, user_id: int, note_designer: NoteDesigner, raw_data: TranscriptionResult):
        try:
            db_payload: DBPayload = await cls._prepare_payload(note_designer, raw_data)
            # Implementation for sending db_payload to database
            body = await post_new_article(user_id, db_payload)
            if not body['status']:
                pass

        except Exception as e:
            raise e