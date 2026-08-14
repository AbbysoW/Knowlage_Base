
from pathlib import Path


from kb_schemas import Chunk

def get_sentence_embedding(sentence: str):
    return embedding_model(sentence)


def send_request(raw_content: str) -> list[str]:
    '''
    raw_content - сырой текст мыслей
    articles_str - строка с рекомендуемыми статьями
    '''

    with open(Path("TelegramLogic/Modules/MdPipeline/Summary/sys_prompt.txt"), "r") as f:
        system_prompt = f.read()

        user_content = f"""
            Основной документ:
            {raw_content}
        """
        format = list[str]

    return send_request_llm(system_prompt, user_content, format)


def split_to_chuncks(data: str) -> list[Chunk]:
    raw_content = data.text

    chunks_str = send_request(raw_content)
    chunks = [Chunk(
        content=chunk,
        embedding=get_sentence_embedding(chunk)
    ) for chunk in chunks_str]

    return chunks