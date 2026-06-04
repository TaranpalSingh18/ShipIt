import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

load_dotenv()

db_url = os.getenv("DATABASE_URL")

engine = create_engine(db_url) ## connects python to postgres
session_local = sessionmaker(bind = engine) ## creates one db session per query
Base = declarative_base() ## used to define ORM tables

def get_db():
    db = session_local()
    try:
        yield db
    finally:
        db.close()

