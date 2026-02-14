import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .models import Base

# Default: local file in project root
# On Render you can override by setting DB_PATH=/tmp/filmclub.db
DB_PATH = os.getenv("DB_PATH", "./filmclub.db")

# sqlite needs 3 slashes for an absolute path, 4 if the path starts with /
# easiest: normalize to an absolute path
abs_db_path = os.path.abspath(DB_PATH)
DATABASE_URL = f"sqlite:///{abs_db_path}"

engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

def init_db():
    Base.metadata.create_all(bind=engine)
