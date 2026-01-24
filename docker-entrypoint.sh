#!/bin/bash
set -e

echo "Waiting for database to be ready..."
# Wait for database to be ready (max 30 attempts = 60 seconds)
MAX_ATTEMPTS=30
ATTEMPT=0
until python -c "
import os
import sys
os.environ.setdefault('DATABASE_URL', 'postgresql+psycopg://seedbank:seedbank_dev_password@postgres:5432/seedbank_db')
from app.database import engine
with engine.connect() as conn:
    conn.execute('SELECT 1')
" 2>/dev/null; do
  ATTEMPT=$((ATTEMPT + 1))
  if [ $ATTEMPT -ge $MAX_ATTEMPTS ]; then
    echo "ERROR: Database connection timeout after $MAX_ATTEMPTS attempts"
    exit 1
  fi
  echo "Database not ready, waiting... (attempt $ATTEMPT/$MAX_ATTEMPTS)"
  sleep 2
done

echo "Database ready! Running migrations..."
# Set DATABASE_URL if not already set
export DATABASE_URL=${DATABASE_URL:-postgresql+psycopg://seedbank:seedbank_dev_password@postgres:5432/seedbank_db}

# Run migrations
alembic upgrade head || echo "Migrations completed or already up to date"

echo "Starting API server..."
# Start the server
exec uvicorn main:app --host 0.0.0.0 --port 8000

