


import httpx
import logging


from config import settings


logger = logging.getLogger(__name__)


# OUTPUT
http_client = httpx.AsyncClient(
    timeout=httpx.Timeout(10.0, connect=2.0),
    limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
    trust_env=False
)

async def get_neerest_articles(user_id: int, embedding: list[float]):

    try:
        logger.debug("Nearest articles search started: user_id=%s, vector_dimensions=%s", user_id, len(embedding))
        response = await http_client.request(
            "QUERY",
            f"{settings.db.full_url}/db/neerest_articles",  
            json={
                "user_id": user_id,
                "vector": embedding
            }
        )
        response.raise_for_status()
        body = response.json()
        logger.info("Nearest articles search completed: user_id=%s, count=%s", user_id, len(body.get("articles", [])))
        return body
        # json structure
        # articles: list[
        #     {
        #         "path": str,
        #         "title": str,
        #         "content": str
        #     }
        # ]

    except httpx.TimeoutException:
        # Core service timeout (>10s) - Service may be unresponsive
        logger.warning("Nearest articles search timed out: user_id=%s", user_id)
    except httpx.HTTPStatusError as e:
        # Core service HTTP error 
        logger.error("Nearest articles search returned HTTP error: user_id=%s, status=%s", user_id, e.response.status_code, exc_info=True)
    except httpx.RequestError as e:
        # Core service connection error
        logger.error("Nearest articles search connection failed: user_id=%s, error=%s", user_id, e, exc_info=True)
    except Exception:
        # Core send error
        logger.exception("Nearest articles search failed: user_id=%s", user_id)
    
    return None


async def close_http_client():
    await http_client.aclose()
    logger.info("Search HTTP client closed")