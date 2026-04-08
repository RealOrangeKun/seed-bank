"""Database connection and session management."""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database URL from environment or default
# Use postgresql+psycopg:// to explicitly use psycopg3 (not psycopg2)
raw_url = os.getenv(
    "DATABASE_URL",
    "postgresql://seedbank:seedbank_dev_password@localhost:5432/seedbank_db"
)
# Convert postgresql:// to postgresql+psycopg:// if not already specified
if raw_url.startswith("postgresql://") and "+psycopg" not in raw_url:
    DATABASE_URL = raw_url.replace("postgresql://", "postgresql+psycopg://", 1)
else:
    DATABASE_URL = raw_url

# Create SQLAlchemy engine
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,  # Verify connections before using
    pool_size=10,
    max_overflow=20,
)

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


def get_db():
    """Dependency for FastAPI to get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

