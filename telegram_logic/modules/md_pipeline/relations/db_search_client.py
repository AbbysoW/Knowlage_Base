


import asyncio
import logging
from time import monotonic

import httpx

from config import settings


logger = logging.getLogger(__name__)


# OUTPUT
http_client = httpx.AsyncClient(
    timeout=httpx.Timeout(10.0, connect=2.0),
    limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
    trust_env=False
)


async def get_neerest_articles(user_id: int, embedding: list[float], timeout: float = 5.0):
    started_at = monotonic()
    request_url = f"{settings.db.full_url}/db/neerest_articles"

    logger.warning(
        "Nearest articles search started: user_id=%s, vector_dimensions=%s, method=QUERY, url=%s, timeout_s=%.1f",
        user_id,
        len(embedding),
        request_url,
        timeout,
    )

    try:
        response = await asyncio.wait_for(
            http_client.request(
                "QUERY",
                request_url,
                json={
                    "user_id": user_id,
                    "vector": embedding,
                },
            ),
            timeout=timeout,
        )
        response.raise_for_status()
        body = response.json()
        logger.info(
            "Nearest articles search completed: user_id=%s, count=%s, duration_ms=%s",
            user_id,
            len(body.get("articles", [])),
            round((monotonic() - started_at) * 1000),
        )
        return body
        # json structure
        # articles: list[
        #     {
        #         "path": str,
        #         "title": str,
        #         "content": str
        #     }
        # ]

    except asyncio.TimeoutError:
        logger.error(
            "Nearest articles search timed out after %.1fs: user_id=%s, method=QUERY, url=%s",
            timeout,
            user_id,
            request_url,
            exc_info=True,
        )
    except httpx.TimeoutException:
        # Core service timeout (>10s) - Service may be unresponsive
        logger.warning(
            "Nearest articles search timed out by httpx: user_id=%s, method=QUERY, url=%s, elapsed_ms=%s",
            user_id,
            request_url,
            round((monotonic() - started_at) * 1000),
            exc_info=True,
        )
    except httpx.HTTPStatusError as e:
        # Core service HTTP error
        logger.error(
            "Nearest articles search returned HTTP error: user_id=%s, status=%s, url=%s",
            user_id,
            e.response.status_code,
            request_url,
            exc_info=True,
        )
    except httpx.RequestError as e:
        # Core service connection error
        logger.error(
            "Nearest articles search connection failed: user_id=%s, url=%s, error=%s",
            user_id,
            request_url,
            e,
            exc_info=True,
        )
    except Exception:
        # Core send error
        logger.exception("Nearest articles search failed: user_id=%s, url=%s", user_id, request_url)

    logger.warning(
        "Nearest articles search ended without response: user_id=%s, elapsed_ms=%s, url=%s",
        user_id,
        round((monotonic() - started_at) * 1000),
        request_url,
    )
    return None


async def close_http_client():
    await http_client.aclose()
    logger.info("Search HTTP client closed")