import os
import logging
from sqlalchemy import create_engine, text as sa_text
from sqlalchemy.orm import sessionmaker, declarative_base

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://med_user:strong_password@localhost:5432/medical_db",
)

# med_user does not have CREATE privilege on the public schema (PG15+ default).
# We use a separate schema owned by med_user and set it first in search_path
# so SQLAlchemy's create_all() creates tables there instead.
APP_SCHEMA = "med_app"

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    connect_args={"options": f"-c search_path={APP_SCHEMA},public"},
)

# Ensure the application schema exists (med_user can create schemas)
try:
    with engine.connect() as conn:
        conn.execute(sa_text(f"CREATE SCHEMA IF NOT EXISTS {APP_SCHEMA}"))
        conn.commit()
except Exception as exc:
    logger.warning("[database] could not create schema '%s': %s", APP_SCHEMA, exc)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
