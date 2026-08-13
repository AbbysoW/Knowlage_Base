import os
from pathlib import Path
from dotenv import load_dotenv


from modules.common.llm_client import send_request_llm
from modules.common.schemas import TranscriptionResult

load_dotenv()

def send_request(raw_content: str, source_type: str) -> str:
    '''
    raw_content - сырой текст мыслей
    source_type - тип источника
    '''
    with open(Path("TelegramLogic/Modules/MdPipeline/Summary/sys_prompt.txt"), "r") as f:
        system_prompt = f.read()

    user_content = f"""
        Выдели из этого хаоса главное, структурируй и сделай готовую атомарную заметку для базы знаний.

        Текст для анализа:
        {raw_content} 
        
        Дополнительная информация:
        source_type: {source_type}
    """

    return send_request_llm(system_prompt, user_content)

def process(user_id: int, data: TranscriptionResult, results: dict):
    raw_content = data.text
    source_type = data.source_type

    llm_result = send_request(raw_content, source_type)
    result = llm_result

    if result:
        results['summary'] = result