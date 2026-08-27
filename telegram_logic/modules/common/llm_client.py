import os
import threading
import logging
from typing import Any
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from openai import OpenAI, APIConnectionError, APITimeoutError, RateLimitError

from config import settings


logger = logging.getLogger(__name__)


class LLMClient:
    _client: OpenAI | None = None
    _lock = threading.Lock()

    @classmethod
    def _get_client(cls) -> OpenAI:
        with cls._lock:
            if cls._client is None:
                cls._client = OpenAI(
                    base_url="https://api.deepseek.com",
                    api_key=settings.deepseek_api_key,
                )
                logger.info("LLM client initialized: provider=deepseek")
            return cls._client

    @classmethod
    @retry(
        retry=retry_if_exception_type(RateLimitError),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        stop=stop_after_attempt(4),
    )
    def send_request(cls, system_prompt: str, user_content: str, output_format: Any | None = None, temperature: float = 0.5):
        try:
            response = cls._get_client().chat.completions.parse(
                model="deepseek-v4-flash",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
                response_format=output_format,
                temperature=temperature,
            )
            return response.choices[0].message.content
        except RateLimitError:
            logger.warning("LLM rate limit reached; retrying request")
        except APIConnectionError:
            logger.error("LLM provider connection failed", exc_info=True)
        except APITimeoutError:
            logger.error("LLM provider request timed out", exc_info=True)