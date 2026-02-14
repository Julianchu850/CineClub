import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from .models import Base

DB_PATH = os.getenv("DB_PATH", "./filmclub.db")
abs_db_path = os.path.abspath(DB_PATH)
DATABASE_URL = f"sqlite:///{abs_db_path}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,          # ✅ prevents QueuePool timeouts
    pool_pre_ping=True
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

def init_db():
    Base.metadata.create_all(bind=engine)
