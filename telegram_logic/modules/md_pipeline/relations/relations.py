import asyncio
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from dotenv import load_dotenv

from kb_schemas import Relation, TranscriptionResult
from modules.common.embedding_client import EmbeddingModel
from modules.common.llm_client import LLMClient
from .db_search_client import get_neerest_articles


class RelationModel:
    load_dotenv()
    
    user_content = """
        Основной документ:
        %s
        
        Предположительно похожие статьи:
        %s
    """
    output_format = list[Relation]


    @staticmethod
    async def _send_request_db(user_id: int, raw_content: str):
        with ProcessPoolExecutor(max_workers=1) as pool:
            future = pool.submit(EmbeddingModel.get_embedding, raw_content)
        embedding = future.result()

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
        
            return await asyncio.to_thread(LLMClient.send_request,
                system_prompt=system_prompt,
                user_content=user_content,
                output_format=cls.output_format
            )

        except FileNotFoundError as e:
            print(f"File not found: {e}")


    @staticmethod
    def _format_db_request(articles: list) -> str:
        formatted_articles = [f'''
            - **{article.get('title', 'Unknown')}**
            Path: {article.get('path', 'Unknown')}
            {article.get('content', 'No content available')}
        ''' for article in articles]

        return "\n\n".join(formatted_articles)

    @classmethod
    def process(cls, user_id: int, data: TranscriptionResult) -> list[Relation]:
        raw_content = data.text

        articles = asyncio.run(cls._send_request_db(user_id, raw_content))
        articles_str = cls._format_db_request(articles)

        llm_result: list[Relation] = asyncio.run(cls._send_request(raw_content, articles_str))
        result = llm_result

        if result and isinstance(result, list):
            return result