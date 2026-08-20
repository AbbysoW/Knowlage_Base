import os
import threading
from typing import Any

from openai import OpenAI, APIConnectionError, APITimeoutError, RateLimitError

from config import settings


class LLMClient:
    _client: OpenAI | None = None

    @classmethod
    def _get_client(cls) -> OpenAI:
        with threading.Lock():
            if cls._client is None:
                cls._client = OpenAI(
                    base_url="https://api.deepseek.com",
                    api_key=settings.deepseek_api_key,
                )
            return cls._client

    @classmethod
    def send_request(cls, system_prompt: str, user_content: str, format: Any | None = None):
        try:
            response = cls._get_client().chat.completions.parse(
                model="deepseek-v4-flash",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
                response_format=format,
            )
            return response.choices[0].message.content
        except RateLimitError as e:
            print(f"Rate limit exceeded: {e}")
        except APIConnectionError as e:
            print(f"API connection error: {e}")
        except APITimeoutError as e:
            print(f"API timeout error: {e}")