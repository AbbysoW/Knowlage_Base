




from typing import Any, Callable

from kb_schemas import DBPayload, NoteDesigner
from .prepare_for_db import prepare_for_db
from .db_client import post_new_article
# from .db_client import


async def send_to_db(user_id: int, note_designer: NoteDesigner):
    try:
        db_payload: DBPayload = await prepare_for_db(note_designer)
        # Implementation for sending db_payload to database
        body = await post_new_article(user_id, db_payload)
        if not body['status']:
            pass

    except Exception as e:
        raise e
