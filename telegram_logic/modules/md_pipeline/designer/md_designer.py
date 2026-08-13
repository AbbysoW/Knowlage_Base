import os
from pathlib import Path

from dotenv import load_dotenv

from modules.common.llm_client import send_request_llm
from modules.common.schemas import NoteDesigner

load_dotenv()

def send_request(summary: str, facts: str, further_reading: str, relations: str) -> NoteDesigner:
    '''
    summary - резюме
    facts - факты
    further_reading - результаты поиска
    relations - связи
    '''

    with open(Path("TelegramLogic/Modules/MdPipeline/Summary/sys_prompt.txt"), "r") as f:
        system_prompt = f.read()

    user_content = f"""
        Резюме данной заметки:
        {summary}

        Факты из данной заметки:
        {facts}

        Результаты поиска похожей информации:
        {further_reading}

        Связи с другими заметками:
        {relations}
    """

    format = NoteDesigner

    return send_request_llm(system_prompt, user_content, format)

def process(results: dict) -> NoteDesigner:
    summary = results.get('summary')
    facts = results.get('facts')
    further_reading = results.get('further_reading')
    relations = results.get('relations')


    llm_result = send_request(summary, facts, further_reading, relations)
    result = llm_result

    return result