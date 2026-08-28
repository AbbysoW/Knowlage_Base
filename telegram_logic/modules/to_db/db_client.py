


import httpx
import logging


from kb_schemas import DBPayload
from config import settings


logger = logging.getLogger(__name__)


# OUTPUT
http_client = httpx.AsyncClient(
    timeout=httpx.Timeout(10.0, connect=2.0),
    limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
    trust_env=False
)

async def post_new_article(user_id: int, payload: DBPayload):
    try:
        logger.debug("Database request started: action=create_article, user_id=%s, chunks=%s", user_id, len(payload.chunks))
        response = await http_client.request(
            "POST",
            f"{settings.db.full_url}/db/new_article",  
            json={
                "user_id": user_id,
                "payload": payload.model_dump(mode="json")
            }
        )
        response.raise_for_status()
        body = response.json()
        logger.info("Database request completed: action=create_article, user_id=%s, status=%s", user_id, body.get('status'))
        return body
        # json structure
        # {
        #  "status": Ok
        # }

    except httpx.TimeoutException:
        # Core service timeout (>10s) - Service may be unresponsive
        logger.warning("Database request timed out: action=create_article, user_id=%s", user_id)
    except httpx.HTTPStatusError as e:
        # Core service HTTP error 
        logger.error("Database request returned HTTP error: action=create_article, user_id=%s, status=%s", user_id, e.response.status_code, exc_info=True)
    except httpx.RequestError as e:
        # Core service connection error
        logger.error("Database request connection failed: action=create_article, user_id=%s, error=%s", user_id, e, exc_info=True)
    except Exception as e:
        # Core send error
        logger.exception("Database request failed: action=create_article, user_id=%s", user_id)
    
    return None


async def close_http_client():
    await http_client.aclose()
    logger.info("Database HTTP client closed")