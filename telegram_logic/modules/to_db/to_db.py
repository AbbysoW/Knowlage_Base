




import asyncio
import logging
from typing import Any, Callable

from kb_schemas import DBPayload, NoteDesigner, TranscriptionResult

from modules.to_db.split_model import Split
from .db_client import post_new_article
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
            logger.info("Database payload prepared: chunks=%s, markdown_length=%s", len(payload.chunks), len(payload.md))
            return payload
        except Exception:
            logger.exception("Database payload preparation failed")
            raise

    @classmethod
    async def send_to_db(cls, user_id: int, note_designer: NoteDesigner, raw_data: TranscriptionResult):
        try:
            db_payload: DBPayload = await cls._prepare_payload(note_designer, raw_data)
            # Implementation for sending db_payload to database
            body = await post_new_article(user_id, db_payload)
            if body is None or body.get('status') != 'ok':
                logger.error("Database persistence rejected: user_id=%s, status=%s", user_id, body.get('status') if body else None)
                raise RuntimeError(f"Database write failed: {body!r}")
            logger.info("Database persistence confirmed: user_id=%s", user_id)
        except Exception:
            logger.exception("Database persistence failed: user_id=%s", user_id)
            raise