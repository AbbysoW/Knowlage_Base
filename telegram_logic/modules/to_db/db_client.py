


import logging

import httpx


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
        response = await http_client.request(
            "POST",
            f"{settings.db.full_url}/db/new_article",  
            json={
                "user_id": user_id,
                "payload": payload.model_dump(mode="json")
            }
        )
        response.raise_for_status()
        logger.info(
            "Knowledge article persisted: user_id=%s, title=%s",
            user_id,
            payload.metadata.title,
        )
        return response.json()
        # json structure
        # {
        #  "status": Ok
        # }

    except httpx.TimeoutException:
        # Core service timeout (>10s) - Service may be unresponsive
        logger.error("Database service timeout: user_id=%s, title=%s", user_id, payload.metadata.title)
    except httpx.HTTPStatusError as e:
        # Core service HTTP error 
        logger.error(
            "Database service rejected article: user_id=%s, title=%s, status=%s",
            user_id,
            payload.metadata.title,
            e.response.status_code,
        )
    except httpx.RequestError as e:
        # Core service connection error
        logger.error(
            "Database service unavailable: user_id=%s, title=%s, error=%s",
            user_id,
            payload.metadata.title,
            e,
        )
    except Exception as e:
        # Core send error
        logger.exception(
            "Unexpected database write error: user_id=%s, title=%s",
            user_id,
            payload.metadata.title,
        )
    
    return None


async def close_http_client():
    await http_client.aclose()
    logger.info("Database HTTP client closed")