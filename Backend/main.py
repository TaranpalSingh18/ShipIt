import os

from fastapi import FastAPI

from db import Base, engine
from routes.auth.auth import auth
from routes.customer.behaviour import behaviour
from routes.query.query import query
from routes.teardown.template import teardown

app = FastAPI()

if os.getenv("AUTO_CREATE_DB", "true").lower() in ("1", "true", "yes"):
    Base.metadata.create_all(bind=engine)

app.include_router(auth)
app.include_router(query)
app.include_router(teardown)
app.include_router(behaviour)
