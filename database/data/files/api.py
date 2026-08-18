





from pathlib import Path

from kb_schemas.models import DBPayload
from config import settings


class FileStore:

    @staticmethod
    async def create(user_id: int, payload: DBPayload):
        try:
            filepath: Path = settings.db.file_store.path / f"{user_id}" / payload.metadata.primary_category or "Unsorted" / payload.metadata.file_name
            filepath.parent.mkdir(parents=True, exist_ok=True)
            filepath.touch(exist_ok=False)

            filepath.write_text(f'''
                ---
                title: {payload.metadata.title}
                created: {payload.metadata.created_at}
                source_type: video
                tags: {payload.metadata.tags_to_str()}
                entities: {payload.metadata.entities_to_str()}
                related_articles: {payload.metadata.relations_to_str()}
                ---
                #{payload.metadata.title}
                {payload.md}
            ''')

        except FileExistsError as e:
            pass

        except FileNotFoundError as e:
            pass

    @staticmethod
    async def read(user_id: int, file_name: str, primary_category: str | None):
        pass

    @staticmethod
    async def update(user_id: int, file_name: str, primary_category: str | None):
        pass

    @staticmethod
    async def delete(user_id: int, file_name: str, primary_category: str | None):
        try:
            filepath: Path = settings.db.file_store.path / f"{user_id}" / primary_category or "Unsorted" / file_name
            filepath.parent.unlink(missing_ok=True)
            
        # except FileExistsError as e:
        #     pass

        # except FileNotFoundError as e:
        #     pass

        except Exception as e:
            pass