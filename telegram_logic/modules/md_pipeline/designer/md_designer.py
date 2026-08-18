import os
from pathlib import Path
from dotenv import load_dotenv

from kb_schemas import NoteDesigner, Fact, FurtherReadingItem, Relation, TranscriptionResult
from modules.common.llm_client import LLMClient


class MdDesignerModel:
    load_dotenv()
    
    user_content = """
        Резюме данной заметки:
        %s

        Факты из данной заметки:
        %s

        Результаты поиска похожей информации:
        %s

        Связи с другими заметками:
        %s
    """
    output_format = NoteDesigner

    @classmethod
    def _send_request(cls, summary: str, facts: str, further_reading: str, relations: str) -> NoteDesigner:
        '''
        summary - резюме
        facts - факты
        further_reading - результаты поиска
        relations - связи
        '''
        try:
            with open(Path("telegram_logic/modules/md_pipeline/designer/sys_prompt.txt"), "r") as f:
                system_prompt = f.read()
        
            user_content = cls.user_content % (summary, facts, further_reading, relations)
        
            return LLMClient.send_request(
                system_prompt=system_prompt,
                user_content=user_content,
                output_format=cls.output_format
            )
        
        except FileNotFoundError as e:
            print(f"File not found: {e}")

    @classmethod
    def process(cls, results: dict, raw_data: TranscriptionResult) -> NoteDesigner:
        summary = results.get('summary')
        facts: list[Fact] = results.get('facts')
        further_reading: list[FurtherReadingItem] = results.get('further_reading')
        relations: list[Relation] = results.get('relations')

        llm_result = cls._send_request(summary, facts, further_reading, relations)
        result = llm_result

        return result