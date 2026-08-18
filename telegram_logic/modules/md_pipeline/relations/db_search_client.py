


import httpx


from config import DB_URL


# OUTPUT
http_client = httpx.AsyncClient(
    timeout=httpx.Timeout(10.0, connect=2.0),
    limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
    trust_env=False
)

async def get_neerest_articles(user_id: int, embedding: list[float]):

    try:
        response = await http_client.request(
            "QUERY",
            f"{DB_URL}/db/neerest_articles",  
            json={
                "user_id": user_id,
                "vector": embedding
            }
        )
        response.raise_for_status()
        return response.json()
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