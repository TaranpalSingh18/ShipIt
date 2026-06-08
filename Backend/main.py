from fastapi import FastAPI
from routes.auth.auth import auth
from routes.query.query import query
from routes.teardown.template import teardown
from db import declarative_base, engine, get_db, Base


app = FastAPI()
Base.metadata.create_all(bind = engine)
app.include_router(auth)
app.include_router(query)
app.include_router(teardown)