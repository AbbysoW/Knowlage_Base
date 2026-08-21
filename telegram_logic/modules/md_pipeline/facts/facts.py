import os
from pathlib import Path
from dotenv import load_dotenv

from kb_schemas import Fact, TranscriptionResult
from modules.common.llm_client import LLMClient


class FactsModel:
    load_dotenv()
    
    user_content = """
        Основной документ:
        %s
    """
    output_format = list[Fact]

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
                output_format=cls.output_format
            )
        
        except FileNotFoundError as e:
            print(f"File not found: {e}")

    @classmethod
    def process(cls, user_id: int, data: TranscriptionResult):
        raw_content = data.text

        llm_result = cls._send_request(raw_content)
        result = llm_result
        
        if result:
            return result