import os
from alembic import context

config = context.config

database_url = os.getenv("DATABASE_URL")
if not database_url:
    raise RuntimeError("DATABASE_URL environment variable not set")

config.set_main_option("sqlalchemy.url", database_url)