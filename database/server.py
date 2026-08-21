

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from kb_schemas import DBPayload
from logic import DBLogic
app = FastAPI()




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