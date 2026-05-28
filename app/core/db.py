"""Database engine and session helpers."""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

settings = get_settings()

# The SQLAlchemy engine is process-wide because connection pools are intended
# to be reused instead of recreated per request.
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
)

# `autoflush=False` keeps writes explicit, which is safer while the service is
# still defining transaction boundaries and state transition rules.
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    class_=Session,
)


def get_db_session() -> Generator[Session, None, None]:
    """Provide a request-scoped database session and close it reliably.

    The dependency pattern keeps session lifecycle management out of routers and
    prevents leaked connections during exceptions.
    """

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
