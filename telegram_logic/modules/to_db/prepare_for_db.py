

from kb_schemas import DBPayload, NoteDesigner
from .split_model import split_to_chuncks




async def prepare_for_db(note_designer: NoteDesigner) -> DBPayload:
    try:
        return DBPayload(
            chunks=split_to_chuncks(note_designer.content),
            meta=note_designer.formatter,
            md=note_designer.content
        )
    except Exception as e:
        # Handle the exception appropriately
        raise e