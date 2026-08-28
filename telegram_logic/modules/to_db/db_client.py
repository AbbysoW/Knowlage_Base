


import httpx


from kb_schemas import DBPayload
from config import settings


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
        return response.json()
        # json structure
        # {
        #  "status": Ok
        # }

    except httpx.TimeoutException:
        # Core service timeout (>10s) - Service may be unresponsive
        ...
    except httpx.HTTPStatusError as e:
        # Core service HTTP error 
        ...
    except httpx.RequestError as e:
        # Core service connection error
        ...
    except Exception as e:
        # Core send error
        ...
    
    return None


async def close_http_client():
    await http_client.aclose()