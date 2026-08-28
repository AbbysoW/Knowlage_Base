import os
import textwrap
import logging
from pathlib import Path
from dotenv import load_dotenv
from pydantic import BaseModel

from kb_schemas import Fact, TranscriptionResult
from modules.common.llm_client import LLMClient


logger = logging.getLogger(__name__)


class FactsModel:
    load_dotenv()
    
    user_content = textwrap.dedent("""\
        Основной документ:
        %s
    """)

    class OutputFormat(BaseModel):
        facts: list[Fact]

    output_format = OutputFormat

    @classmethod
    def _send_request(cls, raw_content: str) -> list[Fact]:
        '''
        raw_content - сырой текст мыслей
        '''
        try:
            with open(Path("telegram_logic/modules/md_pipeline/facts/sys_prompt.txt"), "r") as f:
                system_prompt = f.read()
        
            user_content = cls.user_content % raw_content
        
            return LLMClient.send_request(
                system_prompt=system_prompt,
                user_content=user_content,
                output_format=cls.output_format,
                temperature=0.0,
            ).facts
        
        except FileNotFoundError:
            logger.exception("Facts prompt missing")
            raise

    @classmethod
    def process(cls, user_id: int, data: TranscriptionResult):
        raw_content = data.text

        llm_result = cls._send_request(raw_content)
        result = llm_result
        
        if result:
            logger.info("Facts extracted: user_id=%s, count=%s", user_id, len(result))
            return result
        logger.warning("Facts extraction returned no items: user_id=%s", user_id)
        return []