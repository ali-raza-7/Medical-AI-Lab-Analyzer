import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Default to SQLite if DATABASE_URL is not set, or use PostgreSQL if provided
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./medical_ai.db")

# SQLite requires 'check_same_thread: False' for FastAPI's async operations
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
