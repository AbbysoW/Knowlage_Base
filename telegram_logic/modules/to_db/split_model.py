
from pathlib import Path
import logging

from kb_schemas import Chunk, NoteDesigner

from modules.common.embedding_client import EmbeddingModel
from modules.common.llm_client import LLMClient


logger = logging.getLogger(__name__)

class Split:

    user_content = '''
        Основной документ:
        %s
    '''
    output_format = list[str]

    @classmethod
    def send_request(cls, raw_content: str) -> list[str]:
        '''
        raw_content - сырой текст мыслей
        articles_str - строка с рекомендуемыми статьями
        '''
        try:
            with open(Path(__file__).parent / "sys_prompt.txt", "r") as f:
                system_prompt = f.read()

                user_content = cls.user_content % (raw_content)

            chunks = LLMClient.send_request(
                system_prompt=system_prompt, 
                user_content=user_content, 
                output_format=cls.output_format
                )
            logger.info("Note split completed: chunk_count=%s", len(chunks))
            return chunks
        
        except FileNotFoundError:
            logger.exception("Chunk split prompt missing")
            raise

    @classmethod
    def split_to_chunks(cls, data: NoteDesigner) -> list[Chunk]:
        raw_content = data.content

        chunks_str = cls.send_request(raw_content)
        chunks = []
        for index, chunk in enumerate(chunks_str):
            try:
                chunks.append(Chunk(content=chunk, embedding=EmbeddingModel.get_embedding(chunk)))
            except Exception:
                logger.exception("Chunk embedding failed: chunk_index=%s", index)
                raise

        logger.info("Chunk payload assembled: chunk_count=%s", len(chunks))
        return chunks