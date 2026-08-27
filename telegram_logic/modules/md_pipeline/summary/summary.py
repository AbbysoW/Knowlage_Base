import logging
import os
import textwrap
from pathlib import Path
from dotenv import load_dotenv

from kb_schemas import TranscriptionResult
from modules.common.llm_client import LLMClient


logger = logging.getLogger(__name__)


class SummaryModel:
    load_dotenv()
    
    user_content = textwrap.dedent("""\
        Текст для анализа:
        %s
        
        Дополнительная информация:
        source_type: %s
    """)

    @classmethod
    def _send_request(cls, raw_content: str, source_type: str) -> str:
        '''
        raw_content - сырой текст мыслей
        source_type - тип источника
        '''
        try:
            with open(Path(__file__).parent / "sys_prompt.txt", "r") as f:
                system_prompt = f.read()
        
            user_content = cls.user_content % (raw_content, source_type)
        
            return LLMClient.send_request(
                system_prompt=system_prompt, 
                user_content=user_content,
                temperature=0.2,
                )
        
        except FileNotFoundError as e:
            logger.error("Summary prompt unavailable: path=%s", Path(__file__).parent / "sys_prompt.txt", exc_info=True)
            raise

    @classmethod
    def process(cls, user_id: int, data: TranscriptionResult):
        raw_content = data.text
        source_type = data.source_type

        llm_result = cls._send_request(raw_content, source_type)
        result = llm_result
    
        if result:
            return result