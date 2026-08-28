
from pathlib import Path

from kb_schemas import Chunk, NoteDesigner

from modules.common.embedding_client import EmbeddingModel
from modules.common.llm_client import LLMClient

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

            return LLMClient.send_request(
                system_prompt=system_prompt, 
                user_content=user_content, 
                output_format=cls.output_format
                )
        
        except FileNotFoundError as e:
            print(f"File not found: {e}")

    @classmethod
    def split_to_chunks(cls, data: NoteDesigner) -> list[Chunk]:
        raw_content = data.content

        chunks_str = cls.send_request(raw_content)
        chunks = [Chunk(
            content=chunk,
            embedding=EmbeddingModel.get_embedding(chunk),
        ) for chunk in chunks_str]

        return chunks