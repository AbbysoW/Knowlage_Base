

from fastapi import FastAPI
from pydantic import BaseModel

from kb_schemas import DBPayload
from logic import DBPayload
app = FastAPI()




class NewArticle(BaseModel):
    user_id: int
    payload: DBPayload

@app.post('/db/new_article')
async def post_new_article(article: NewArticle):
    try: 
        try:
            await DBPayload.write_to_db(article.user_id, article.payload)
            # transaction logic for adding new article
            # if write fails -> raise err
        except Exception:
            pass
            # launch undo logic
    except Exception as e:
        pass


class NeerestArticlesQuery(BaseModel):
    user_id: int
    vector: list[float]

@app.api_route('/db/neerest_articles', methods=["QUERY"])
async def get_neerest_articles(query: NeerestArticlesQuery):
    pass