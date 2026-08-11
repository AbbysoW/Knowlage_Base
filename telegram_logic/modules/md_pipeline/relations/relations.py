import os
from pathlib import Path

from dotenv import load_dotenv

from modules.common.embedding_client import embedding_model
from modules.common.llm_client import send_request_llm
from modules.common.schemas import Relation, TranscriptionResult
from .db_search_client import get_neerest_articles



load_dotenv()


def send_request_db(user_id: int, raw_content: str):
    embadding = embedding_model(raw_content)

    json = get_neerest_articles(user_id, embadding)
    articles = json["articles"]

    return articles


def send_request(raw_content: str, articles_str: str) -> list[Relation]:
    '''
    raw_content - сырой текст мыслей
    articles_str - строка с рекомендуемыми статьями
    '''

    with open(Path("TelegramLogic/Modules/MdPipeline/Summary/sys_prompt.txt"), "r") as f:
        system_prompt = f.read()

        user_content = f"""
            Основной документ:
            {raw_content}
            
            Предположительно похожие статьи:
            {articles_str}
        """
        format = list[Relation]

    return send_request_llm(system_prompt, user_content, format)


def format_db_request(articles: list) -> str:
    formatted_articles = [f'''
        - **{article['title']}**
        Path: {article['path']}
        {article['content']}
    ''' for article in articles]

    return "\n\n".join(formatted_articles)


def process(user_id: int, data: TranscriptionResult, results: dict) -> list[Relation]:
    raw_content = data.text

    articles = send_request_db(user_id, raw_content)
    articles_str = format_db_request(articles)

    llm_result = send_request(raw_content, articles_str)

    result = llm_result

    if result and isinstance(result, list):
        results['relations'] = result
