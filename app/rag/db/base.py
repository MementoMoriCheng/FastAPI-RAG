import json

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import DeclarativeMeta, declarative_base
from sqlalchemy.orm import sessionmaker
from app.settings.config import settings

engine = create_engine(
    # settings.SQLALCHEMY_DATABASE_URI,
    "mysql+pymysql://root:123456@localhost/Langchain_RAG",
    json_serializer=lambda obj: json.dumps(obj, ensure_ascii=False),
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base: DeclarativeMeta = declarative_base()
