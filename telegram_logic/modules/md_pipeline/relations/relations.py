import asyncio
import textwrap
from concurrent.futures import ProcessPoolExecutor
import logging
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel

from kb_schemas import Relation, TranscriptionResult
from modules.common.embedding_client import EmbeddingModel
from modules.common.llm_client import LLMClient
from .db_search_client import get_neerest_articles


logger = logging.getLogger(__name__)


class RelationModel:
    load_dotenv()
    
    user_content = textwrap.dedent("""\
        Основной документ:
        %s
        
        Предположительно похожие статьи:
        %s
    """)

    class OutputFormat(BaseModel):
        relations: list[Relation]

    output_format = OutputFormat


    @staticmethod
    async def _fetch_articles(user_id: int, raw_content: str):

        await asyncio.wrap_future

        pool = ProcessPoolExecutor(max_workers=1)
        try:
            future = pool.submit(EmbeddingModel.get_embedding, raw_content)
            embedding = await asyncio.wrap_future(future)
        finally:
            pool.shutdown(wait=False)

        response = await get_neerest_articles(user_id, embedding)
        articles = response.get("articles", []) if response else []

        return articles

    @classmethod
    async def _send_request(cls, raw_content: str, articles_str: str) -> list[Relation]:
        '''
        raw_content - сырой текст мыслей
        articles_str - строка с рекомендуемыми статьями
        '''
        try:
            with open(Path(__file__).parent / "sys_prompt.txt", "r") as f:
                system_prompt = f.read()
        
            user_content = cls.user_content % (raw_content, articles_str)
        
            return LLMClient.send_request(
                system_prompt=system_prompt,
                user_content=user_content,
                output_format=cls.output_format,
                temperature=0.1,
            ).relations

        except FileNotFoundError as e:
            logger.error(f"File not found: {e}")


    @staticmethod
    def _format_db_request(articles: list) -> str:
        formatted_articles = (
            [
                f"""
                    - **{article.get('title', 'Unknown')}**
                    Path: {article.get('path', 'Unknown')}
                    {article.get('content', 'No content available')}
                """
                for article in articles
            ]
            if articles
            else ["Couldn't find any article"]
        )

        return "\n\n".join(formatted_articles)

    @classmethod
    def process(cls, user_id: int, data: TranscriptionResult) -> list[Relation]:
        raw_content = data.text

        articles = asyncio.run(cls._fetch_articles(user_id, raw_content))
        articles_str = cls._format_db_request(articles)

        llm_result: list[Relation] = cls._send_request(raw_content, articles_str)
        result = llm_result

        if result and isinstance(result, list):
            return result