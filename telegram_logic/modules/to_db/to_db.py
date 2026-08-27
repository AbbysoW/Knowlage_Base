




import asyncio
import logging
from typing import Any, Callable

from kb_schemas import DBPayload, NoteDesigner, TranscriptionResult

from modules.to_db.split_model import Split
from .db_client import post_new_article
# from .db_client import


logger = logging.getLogger(__name__)






class ToDB:


    @staticmethod
    async def _prepare_payload(note_designer: NoteDesigner, raw_data: TranscriptionResult) -> DBPayload:
        try:
            payload = DBPayload(
                chunks=await asyncio.to_thread(Split.split_to_chunks, note_designer),
                metadata=note_designer.formatter,
                md=note_designer.content,
                raw_data=raw_data
            )
            logger.debug(
                "Database payload prepared: title=%s, chunks=%s",
                payload.metadata.title,
                len(payload.chunks),
            )
            return payload
        except Exception as e:
            # Handle the exception appropriately
            raise e

    @classmethod
    async def send_to_db(cls, user_id: int, note_designer: NoteDesigner, raw_data: TranscriptionResult):
        try:
            db_payload: DBPayload = await cls._prepare_payload(note_designer, raw_data)
            # Implementation for sending db_payload to database
            body = await post_new_article(user_id, db_payload)
            if body is None or body.get('status') != 'ok':
                raise RuntimeError(f"Database write failed: {body!r}")
            logger.info("Article delivery acknowledged: user_id=%s, title=%s", user_id, db_payload.metadata.title)

        except Exception as e:
            logger.error(
                "Article delivery failed: user_id=%s, title=%s",
                user_id,
                note_designer.formatter.title,
                exc_info=True,
            )
            raise e