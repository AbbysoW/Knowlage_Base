

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
    wal_files = list(settings.tx.wal_dir.glob("*.json"))
    logger.info("Transaction recovery scan started: wal_files=%s", len(wal_files))
    return # пока не надо
    for wal_file in settings.tx.wal_dir.glob("*.json"):
        state = json.loads(wal_file.read_text())
        if state["status"].startswith("rollback_failed"):
            logger.critical("Требуется ручной разбор: %s", wal_file)
            continue


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Database service starting")
    await recover_pending_transactions()
    yield
    # Clean up the ML models and release the resources
    logger.info("Database service stopped")


app = FastAPI(lifespan=lifespan)


class NewArticle(BaseModel):
    user_id: int
    payload: DBPayload

@app.post('/db/new_article')
async def post_new_article(article: NewArticle):
    try:
        logger.info("Article persistence started: user_id=%s, chunks=%s", article.user_id, len(article.payload.chunks))
        await DBLogic.write_to_db(article.user_id, article.payload)
        logger.info("Article persistence completed: user_id=%s, status=ok", article.user_id)
        return {"status": "ok"}
    except Exception:
        logger.exception("Article persistence failed: user_id=%s", article.user_id)
        raise HTTPException(status_code=500, detail="Failed to create article")

class NeerestArticlesQuery(BaseModel):
    user_id: int
    vector: list[float]

@app.api_route('/db/neerest_articles', methods=["QUERY"])
async def get_neerest_articles(query: NeerestArticlesQuery):
    try:
        logger.debug("Nearest article query started: user_id=%s, vector_dimensions=%s", query.user_id, len(query.vector))
        response = await DBLogic.read_nearest(query.user_id, query.vector)
        articles = response.get("results", []) if response else []
        logger.info("Nearest article query completed: user_id=%s, count=%s", query.user_id, len(articles))
        return {"articles": articles}
    except Exception:
        logger.exception("Nearest article query failed: user_id=%s", query.user_id)
        raise HTTPException(status_code=500, detail="Failed to read nearest articles")