

import json

from fastapi import FastAPI, HTTPException, logger
from fastapi.concurrency import asynccontextmanager
from pydantic import BaseModel

from kb_schemas import DBPayload
from logic import DBLogic
from config import settings


async def recover_pending_transactions():
    return # пока не надо
    for wal_file in settings.tx.wal_dir.glob("*.json"):
        state = json.loads(wal_file.read_text())
        if state["status"].startswith("rollback_failed"):
            logger.critical("Требуется ручной разбор: %s", wal_file)
            continue


@asynccontextmanager
async def lifespan(app: FastAPI):
    recover_pending_transactions()
    yield
    # Clean up the ML models and release the resources


app = FastAPI(lifespan=lifespan)


class NewArticle(BaseModel):
    user_id: int
    payload: DBPayload

@app.post('/db/new_article')
async def post_new_article(article: NewArticle):
    try:
        await DBLogic.write_to_db(article.user_id, article.payload)
    except Exception as exc:
        pass


class NeerestArticlesQuery(BaseModel):
    user_id: int
    vector: list[float]

@app.api_route('/db/neerest_articles', methods=["QUERY"])
async def get_neerest_articles(query: NeerestArticlesQuery):
    response = await DBLogic.read_nearest(query.user_id, query.vector)
    return {"articles": response.get("results", [])} if response else {"articles": []}













