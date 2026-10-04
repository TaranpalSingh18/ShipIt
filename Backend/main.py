import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from db import Base, engine
from routes.auth.auth import auth
from routes.customer.behaviour import behaviour
from routes.query.query import query
from routes.report.router import reports

app = FastAPI()

_cors_origins = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

if os.getenv("AUTO_CREATE_DB", "true").lower() in ("1", "true", "yes"):
    Base.metadata.create_all(bind=engine)

app.include_router(auth)
app.include_router(query)
app.include_router(reports)
app.include_router(behaviour)
