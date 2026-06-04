from fastapi import FastAPI
from routes.auth.auth import auth
from db import declarative_base, engine, get_db, Base


app = FastAPI()
Base.metadata.create_all(bind = engine)
app.include_router(auth)