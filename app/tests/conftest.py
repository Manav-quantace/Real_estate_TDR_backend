import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# FORCE model registration
import app.models  # noqa

from app.core.config import get_settings

settings = get_settings()

engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine)


@pytest.fixture(scope="function")
def db():
    connection = engine.connect()
    transaction = connection.begin()

    session = SessionLocal(bind=connection)

    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()
