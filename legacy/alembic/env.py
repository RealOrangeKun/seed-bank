"""Alembic environment configuration."""
from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context
import os
import sys
from dotenv import load_dotenv

# Add parent directory to path to import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Load environment variables
load_dotenv()

# Import Base and models
from app.database import Base
from app.models import User, ScanBatch, ScanImage, SeedDetection  # noqa

# this is the Alembic Config object
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Override sqlalchemy.url with environment variable if present
# Use postgresql+psycopg:// to explicitly use psycopg3 (not psycopg2)
raw_url = os.getenv(
    "DATABASE_URL",
    "postgresql://seedbank:seedbank_dev_password@localhost:5432/seedbank_db"
)
# Convert postgresql:// to postgresql+psycopg:// if not already specified
if raw_url.startswith("postgresql://") and "+psycopg" not in raw_url:
    database_url = raw_url.replace("postgresql://", "postgresql+psycopg://", 1)
else:
    database_url = raw_url
config.set_main_option("sqlalchemy.url", database_url)

# Set target metadata
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
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

