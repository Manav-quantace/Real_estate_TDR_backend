import os
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool, create_engine
from alembic import context

# --- 1. Import your Base and Models ---
from app.db.base import Base
from app.models.project import Project
from app.models.round import Round
from app.models.government_charge import GovernmentCharge
from app.models.slum_portal_membership import SlumPortalMembership

# this is the Alembic Config object
config = context.config

# --- 2. Fetch and Set Database URL from ENV ---
database_url = os.getenv("DATABASE_URL")
if not database_url:
    # If running locally and you have a .env file, you might want to load_dotenv() here
    raise RuntimeError("DATABASE_URL environment variable not set")

# Override the ini file's URL with the environment variable
config.set_main_option("sqlalchemy.url", database_url)

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set the metadata for 'autogenerate' support
target_metadata = Base.metadata

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    # We use create_engine directly since we already have the URL
    connectable = create_engine(config.get_main_option("sqlalchemy.url"), poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(
            connection=connection, 
            target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()