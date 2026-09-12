import asyncio
import textwrap
from concurrent.futures import ProcessPoolExecutor
import logging
from pathlib import Path
from time import monotonic

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
        started_at = monotonic()
        logger.info("RelationModel article fetch started: user_id=%s, text_length=%s", user_id, len(raw_content))

        try:
            loop = asyncio.get_running_loop()
            with ProcessPoolExecutor(max_workers=1) as pool:
                future = loop.run_in_executor(pool, EmbeddingModel.get_embedding, raw_content)
                logger.info("RelationModel embedding generation queued: user_id=%s", user_id)
                embedding = await asyncio.wait_for(future, timeout=30.0)

            logger.info(
                "RelationModel embedding generated: user_id=%s, duration_ms=%s",
                user_id,
                round((monotonic() - started_at) * 1000),
            )

            response = await asyncio.wait_for(get_neerest_articles(user_id, embedding), timeout=5.0)
            articles = response.get("articles", []) if response else []

            logger.info(
                "Related article search completed: user_id=%s, count=%s, duration_ms=%s",
                user_id,
                len(articles),
                round((monotonic() - started_at) * 1000),
            )
            return articles
        except asyncio.TimeoutError:
            logger.exception(
                "RelationModel article fetch timed out: user_id=%s, elapsed_ms=%s",
                user_id,
                round((monotonic() - started_at) * 1000),
            )
            return []
        except Exception:
            logger.exception("RelationModel article fetch failed: user_id=%s", user_id)
            return []

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

        except FileNotFoundError:
            logger.exception("Relations prompt missing")
            raise


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
        logger.info("RelationModel.process started: user_id=%s, text_length=%s", user_id, len(raw_content))

        try:
            logger.info("RelationModel.process entering async fetch: user_id=%s", user_id)
            articles = asyncio.run(cls._fetch_articles(user_id, raw_content))
            articles_str = cls._format_db_request(articles)

            llm_result: list[Relation] = cls._send_request(raw_content, articles_str)
            result = llm_result

            if result and isinstance(result, list):
                logger.info("Relations extracted: user_id=%s, count=%s", user_id, len(result))
                logger.info("RelationModel.process completed: user_id=%s, relation_count=%s", user_id, len(result))
                return result

            logger.warning("Relations extraction returned no items: user_id=%s", user_id)
            return []
        except Exception:
            logger.exception("RelationModel.process failed: user_id=%s", user_id)
            return []