

import json
import logging

from fastapi import FastAPI, HTTPException
from fastapi.concurrency import asynccontextmanager
from pydantic import BaseModel

from kb_schemas import DBPayload
from logic import DBLogic
from config import settings


logger = logging.getLogger(__name__)


async def recover_pending_transactions():
    logger.debug("Pending transaction recovery skipped: feature_disabled=true")
    return # пока не надо
    for wal_file in settings.tx.wal_dir.glob("*.json"):
        state = json.loads(wal_file.read_text())
        if state["status"].startswith("rollback_failed"):
            logger.critical("Требуется ручной разбор: %s", wal_file)
            continue


@asynccontextmanager
async def lifespan(app: FastAPI):
    await recover_pending_transactions()
    logger.info("Database service started")
    yield
    logger.info("Database service stopped")
    # Clean up the ML models and release the resources


app = FastAPI(lifespan=lifespan)


class NewArticle(BaseModel):
    user_id: int
    payload: DBPayload

@app.post('/db/new_article')
async def post_new_article(article: NewArticle):
    try:
        await DBLogic.write_to_db(article.user_id, article.payload)
        logger.info("Article write request completed: user_id=%s, title=%s", article.user_id, article.payload.metadata.title)
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Failed to create article: {e}")
        raise HTTPException(status_code=500, detail="Failed to create article")

class NeerestArticlesQuery(BaseModel):
    user_id: int
    vector: list[float]

@app.api_route('/db/neerest_articles', methods=["QUERY"])
async def get_neerest_articles(query: NeerestArticlesQuery):
    try:
        response = await DBLogic.read_nearest(query.user_id, query.vector)
        logger.debug("Nearest article request completed: user_id=%s, matches=%s", query.user_id, len(response.get("results", [])) if response else 0)
        return {"articles": response.get("results", [])} if response else {"articles": []}
    except Exception as e:
        logger.error(f"Failed to read nearest articles: {e}")
        raise HTTPException(status_code=500, detail="Failed to read nearest articles")