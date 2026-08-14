import os
from pathlib import Path

from dotenv import load_dotenv

from kb_schemas import FurtherReadingItem, TranscriptionResult
from modules.common.llm_client import send_request_llm


load_dotenv()

def send_request(raw_content: str) -> list[FurtherReadingItem]:
    '''
    raw_content - сырой текст мыслей
    '''

    with open(Path("TelegramLogic/Modules/MdPipeline/Summary/sys_prompt.txt"), "r") as f:
        system_prompt = f.read()

    user_content = f"""
        Основной документ:
        {raw_content}
    """

    format = list[FurtherReadingItem]

    return send_request_llm(system_prompt, user_content, format)

def process(user_id: int, data: TranscriptionResult, results: dict):
    raw_content = data.text

    llm_result = send_request(raw_content)
    result = llm_result

    if result:
        results['search'] = result