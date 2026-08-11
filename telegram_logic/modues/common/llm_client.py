import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

def send_request_llm(system_prompt: str, user_content: str) -> str:
    '''
    system_prompt - системный промпт
    user_content - содержание от пользователя
    '''
    client = OpenAI(
        base_url="https://api.deepseek.com", 
        api_key=os.getenv("DEEPSEEK_API_KEY")
    )

    response = client.chat.completions.create(
        model="deepseek-v4-flash",
        messages=[{
            "role": "system",
            "content": system_prompt
        }, {
            "role": "user",
            "content": user_content
        }]
    )

    return response.choices[0].message.content