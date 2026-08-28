import os
import textwrap
import logging
from pathlib import Path

from dotenv import load_dotenv
from datetime import datetime

from kb_schemas import NoteDesigner, Fact, FurtherReadingItem, Relation, TranscriptionResult
from modules.common.llm_client import LLMClient


logger = logging.getLogger(__name__)


class MdDesignerModel:
    load_dotenv()
    
    user_content = textwrap.dedent("""\
        ##Основовная информация:
        ###Резюме данной заметки:
        %s

        ###Факты из данной заметки:
        %s

        ###Результаты поиска похожей информации:
        %s

        ###Связи с другими заметками:
        %s

        ##MetaData:
        ##Тип источника:
        %s

        ##Дата создания
        %s
    """)
    output_format = NoteDesigner

    @classmethod
    def _send_request(cls, 
                      summary: str, facts: str, further_reading: str, relations: str,
                      source_type: str, created_at: datetime) -> NoteDesigner:
        '''
        summary - резюме
        facts - факты
        further_reading - результаты поиска
        relations - связи
        '''
        try:
            with open(Path("telegram_logic/modules/md_pipeline/designer/sys_prompt.txt"), "r") as f:
                system_prompt = f.read()
        
            user_content = cls.user_content % (summary, facts, further_reading, relations, source_type, created_at)
        
            return LLMClient.send_request(
                system_prompt=system_prompt,
                user_content=user_content,
                output_format=cls.output_format
            )
        
        except FileNotFoundError:
            logger.exception("Note designer prompt missing")
            raise

    @classmethod
    def process(cls, results: dict, raw_data: TranscriptionResult) -> NoteDesigner:
        summary = results.get('summary')
        facts: list[Fact] = results.get('facts')
        further_reading: list[FurtherReadingItem] = results.get('further_reading')
        relations: list[Relation] = results.get('relations')

        source_type = raw_data.source_type
        created_at = raw_data.timestamp

        llm_result = cls._send_request(
            summary=summary, 
            facts=facts, 
            further_reading=further_reading, 
            relations=relations,
            source_type=source_type,
            created_at=created_at)
        result = llm_result

        logger.info("Note designed: title=%s, category=%s", result.formatter.title, result.formatter.primary_category)
        return result